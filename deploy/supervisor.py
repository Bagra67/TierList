"""Superviseur du pod (docs/technical/deployment.md), lancé par le lanceur (deploy/launcher.sh).

Il ouvre le port une fois pour toutes et le passe à uvicorn (--fd) : pendant le changement de
version, les connexions attendent dans la file du noyau au lieu d'être refusées. Quand le
déploiement réécrit CURRENT, il prépare la nouvelle version (extraction, dépendances, migrations)
pendant que l'ancienne sert, puis arrête l'ancienne et démarre la nouvelle sur le même port. Une
version qui ne se prépare pas ou ne démarre pas laisse la précédente en ligne.

Bibliothèque standard seulement : il tourne avec le Python du pod, avant toute dépendance.
"""

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

KEEP_RELEASES = 3
POLL_SECONDS = float(os.environ.get("TIERLIST_POLL_SECONDS", "2"))
HEALTH_TIMEOUT_SECONDS = float(os.environ.get("TIERLIST_HEALTH_TIMEOUT_SECONDS", "120"))
STOP_TIMEOUT_SECONDS = 20
LISTEN_BACKLOG = 2048
# Le panel MineStrator (egg Pterodactyl « python generic ») considère le pod démarré quand la
# console affiche exactement cette ligne
READY_LINE = "change this part"
VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def log(message: str) -> None:
    print(f"[supervisor] {message}", flush=True)


class ReleaseError(Exception):
    pass


class Supervisor:
    def __init__(self, home: Path, port: int) -> None:
        self.home = home
        self.port = port
        self.releases_dir = home / "releases"
        self.current_file = home / "CURRENT"
        self.last_good_file = home / ".last-good"
        self.status_file = home / "deploy-status"
        self.stop_requested = threading.Event()
        self.listener = self._listen()
        self.process: subprocess.Popen[bytes] | None = None
        self.version: str | None = None

    def _listen(self) -> socket.socket:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # uvicorn --fd enveloppe le socket en AF_UNIX : asyncio ne règle donc pas TCP_NODELAY sur
        # les connexions acceptées. Réglé sur le socket d'écoute, Linux le donne à chacune
        listener.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        listener.bind(("0.0.0.0", self.port))
        listener.listen(LISTEN_BACKLOG)
        listener.set_inheritable(True)
        return listener

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self._request_stop)
        signal.signal(signal.SIGINT, self._request_stop)
        seen: int = self._current_mtime()
        if not self._serve_first():
            log("Aucune version ne démarre")
            return 1
        print(READY_LINE, flush=True)
        while not self.stop_requested.wait(POLL_SECONDS):
            if self.process is not None and self.process.poll() is not None:
                log(f"uvicorn s'est arrêté (code {self.process.returncode}) : redémarrage")
                self.process = None
            if self.process is None and self.version is not None:
                self._start(self.version)
            modified: int = self._current_mtime()
            if modified == seen:
                continue
            seen = modified
            wanted: str | None = self._read_version(self.current_file)
            if wanted is not None:
                self._switch_to(wanted)
        self._stop()
        log("Arrêt demandé : terminé")
        return 0

    def _request_stop(self, signum: int, frame: object) -> None:
        self.stop_requested.set()

    def _serve_first(self) -> bool:
        current: str | None = self._read_version(self.current_file)
        candidates: list[str] = [current] if current is not None else []
        last_good: str | None = self._read_version(self.last_good_file)
        if last_good is not None and last_good != current:
            candidates.append(last_good)
        for version in candidates:
            if self.stop_requested.is_set():
                return False
            if self._activate(version):
                return True
        return False

    def _switch_to(self, version: str) -> None:
        log(f"Nouvelle version demandée : {version}")
        self._write_status("preparing", version, "préparation en cours")
        previous: str | None = self.version
        if self._activate(version):
            return
        if self.process is None and previous is not None and not self.stop_requested.is_set():
            log(f"Retour à {previous}")
            self._start(previous)

    def _activate(self, version: str) -> bool:
        try:
            self._prepare(version)
        except ReleaseError as error:
            if not self.stop_requested.is_set():
                log(f"Version {version} non préparée : {error}")
                self._write_status("failed", version, str(error))
            return False
        self._stop()
        if self._start(version):
            self._served(version)
            return True
        if not self.stop_requested.is_set():
            log(f"Version {version} ne répond pas")
            self._write_status("failed", version, "uvicorn ne répond pas")
        return False

    def _served(self, version: str) -> None:
        self.version = version
        self._write_atomically(self.last_good_file, f"{version}\n")
        self._write_status("ok", version, "en ligne")
        prune_releases(self.releases_dir, version)
        log(f"Version {version} en ligne")

    def _prepare(self, version: str) -> None:
        release_dir: Path = self.releases_dir / version
        if not (release_dir / "start.sh").is_file():
            self._extract(version, release_dir)
        log(f"Préparation de {version}")
        try:
            preparation = subprocess.Popen(
                ["bash", str(release_dir / "start.sh"), "prepare"], env=self._child_env()
            )
        except OSError as error:
            raise ReleaseError(f"start.sh prepare impossible : {error}") from error
        while preparation.poll() is None:
            if self.stop_requested.wait(0.5):
                preparation.terminate()
                preparation.wait()
                raise ReleaseError("arrêt demandé pendant la préparation")
        if preparation.returncode != 0:
            raise ReleaseError(f"start.sh prepare a échoué (code {preparation.returncode})")

    def _extract(self, version: str, release_dir: Path) -> None:
        archive: Path = self.releases_dir / f"tierlist-{version}.tar.gz"
        if not archive.is_file():
            raise ReleaseError(f"archive introuvable : {archive}")
        log(f"Extraction de {archive}")
        staging_dir: Path = self.releases_dir / f".extract-{version}"
        shutil.rmtree(staging_dir, ignore_errors=True)
        shutil.rmtree(release_dir, ignore_errors=True)
        try:
            staging_dir.mkdir(parents=True)
            with tarfile.open(archive) as bundle:
                bundle.extractall(staging_dir, filter="data")
            (staging_dir / f"tierlist-{version}").rename(release_dir)
        except (OSError, tarfile.TarError) as error:
            raise ReleaseError(f"extraction impossible : {error}") from error
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def _start(self, version: str) -> bool:
        log(f"Démarrage de {version}")
        self.process = subprocess.Popen(
            ["bash", str(self.releases_dir / version / "start.sh"), "serve"],
            env=self._child_env(),
            pass_fds=(self.listener.fileno(),),
        )
        deadline: float = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        while time.monotonic() < deadline and not self.stop_requested.is_set():
            if self.process.poll() is not None:
                break
            if self._is_healthy():
                return True
            time.sleep(0.5)
        self._stop()
        return False

    def _is_healthy(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/health", timeout=2
            ) as response:
                return response.status == 200
        except OSError:
            return False

    def _stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                log("uvicorn ne s'arrête pas : arrêt forcé")
                self.process.kill()
                self.process.wait()
        self.process = None

    def _child_env(self) -> dict[str, str]:
        return {
            **os.environ,
            "TIERLIST_HOME": str(self.home),
            "TIERLIST_LISTEN_FD": str(self.listener.fileno()),
        }

    def _current_mtime(self) -> int:
        try:
            return self.current_file.stat().st_mtime_ns
        except OSError:
            return 0

    @staticmethod
    def _read_version(path: Path) -> str | None:
        try:
            version: str = path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not VERSION_PATTERN.fullmatch(version):
            log(f"Version invalide dans {path.name} : « {version} »")
            return None
        return version

    def _write_status(self, state: str, version: str, detail: str) -> None:
        self._write_atomically(self.status_file, f"{state} {version} {detail}\n")

    @staticmethod
    def _write_atomically(path: Path, text: str) -> None:
        temporary: Path = path.with_name(f".{path.name}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)
        except OSError as error:
            log(f"{path.name} non écrit : {error}")


def prune_releases(releases_dir: Path, version: str) -> None:
    try:
        archives: list[Path] = sorted(
            releases_dir.glob("tierlist-*.tar.gz"),
            key=lambda archive: archive.stat().st_mtime,
            reverse=True,
        )
    except OSError as error:
        log(f"Anciennes versions non supprimées : {error}")
        return
    kept: int = 1
    for archive in archives:
        old_version: str = archive.name.removeprefix("tierlist-").removesuffix(".tar.gz")
        if old_version == version:
            continue
        if kept < KEEP_RELEASES:
            kept += 1
            continue
        log(f"Suppression de l'ancienne version {old_version}")
        archive.unlink(missing_ok=True)
        shutil.rmtree(releases_dir / old_version, ignore_errors=True)


def main() -> int:
    home: Path = Path(os.environ.get("TIERLIST_HOME", Path(__file__).resolve().parent))
    port: int = int(os.environ.get("SERVER_PORT") or "8000")
    return Supervisor(home, port).run()


if __name__ == "__main__":
    sys.exit(main())
