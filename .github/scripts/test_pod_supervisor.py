import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

SUPERVISOR = Path(__file__).resolve().parents[2] / "deploy" / "supervisor.py"

FAKE_START_SH = """#!/usr/bin/env bash
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
    prepare)
        [ ! -f "$here/slow-prepare" ] || sleep 3
        [ ! -f "$here/fail-prepare" ]
        ;;
    serve)
        [ ! -f "$here/fail-serve" ] || exit 1
        exec python3 "$FAKE_UVICORN" "$TIERLIST_LISTEN_FD" "$(basename "$here")"
        ;;
esac
"""

FAKE_UVICORN = """import json, os, signal, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

fd, release = int(sys.argv[1]), sys.argv[2]
time.sleep(0.5)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "release": release, "pid": os.getpid()}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler, bind_and_activate=False)
server.daemon_threads = False
server.socket.close()
server.socket = socket.socket(fileno=fd)
signal.signal(signal.SIGTERM, lambda *args: threading.Thread(target=server.shutdown).start())
server.serve_forever()
server.server_close()
"""


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def load_supervisor_module():
    spec = importlib.util.spec_from_file_location("supervisor", SUPERVISOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(sys.platform == "win32", "passing a socket to a child process needs POSIX")
class PodSupervisorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.port = free_port()
        self.fake_uvicorn = self.home / "fake_uvicorn.py"
        self.fake_uvicorn.write_text(FAKE_UVICORN)
        self.supervisor: subprocess.Popen[bytes] | None = None

    def tearDown(self) -> None:
        if self.supervisor is not None and self.supervisor.poll() is None:
            self.supervisor.terminate()
            self.supervisor.wait(30)

    def add_release(self, version: str, *flags: str) -> None:
        release_dir = self.home / "releases" / version
        release_dir.mkdir(parents=True)
        (release_dir / "start.sh").write_text(FAKE_START_SH)
        for flag in flags:
            (release_dir / flag).touch()

    def set_current(self, version: str) -> None:
        (self.home / "CURRENT").write_text(f"{version}\n")

    def start_supervisor(self) -> None:
        env = {
            **os.environ,
            "TIERLIST_HOME": str(self.home),
            "SERVER_PORT": str(self.port),
            "TIERLIST_POLL_SECONDS": "0.1",
            "TIERLIST_HEALTH_TIMEOUT_SECONDS": "10",
            "FAKE_UVICORN": str(self.fake_uvicorn),
        }
        self.supervisor = subprocess.Popen(
            [sys.executable, str(SUPERVISOR)], env=env, stdout=subprocess.DEVNULL
        )

    def served_release(self) -> str:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/health", timeout=30
        ) as response:
            return json.load(response)["release"]

    def served_pid(self) -> int:
        url = f"http://127.0.0.1:{self.port}/api/health"
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)["pid"]

    def wait_for(self, condition, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if condition():
                    return
            except OSError:
                pass
            time.sleep(0.05)
        self.fail("condition not met in time")

    def status(self) -> str:
        try:
            return (self.home / "deploy-status").read_text().strip()
        except OSError:
            return ""

    def test_a_new_version_takes_over_without_refusing_a_request(self) -> None:
        self.add_release("v1")
        self.add_release("v2")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")
        failures: list[str] = []
        releases: set[str] = set()
        stop = threading.Event()

        def hammer() -> None:
            while not stop.is_set():
                try:
                    releases.add(self.served_release())
                except OSError as error:
                    failures.append(str(error))
                time.sleep(0.01)

        client = threading.Thread(target=hammer)
        client.start()
        self.set_current("v2")
        self.wait_for(lambda: "v2" in releases)
        time.sleep(0.2)
        stop.set()
        client.join()

        self.assertEqual(failures, [])
        self.assertEqual(self.served_release(), "v2")
        self.assertTrue(self.status().startswith("ok v2"))

    def test_rewriting_the_same_version_restarts_uvicorn_to_read_the_new_settings(self) -> None:
        self.add_release("v1")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")
        first_pid = self.served_pid()

        self.set_current("v1")

        self.wait_for(lambda: self.served_pid() != first_pid)
        self.assertEqual(self.served_release(), "v1")

    def test_the_status_says_a_version_is_being_prepared_until_it_serves(self) -> None:
        self.add_release("v1")
        self.add_release("v2", "slow-prepare")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")

        self.set_current("v2")

        self.wait_for(lambda: self.status().startswith("preparing v2"))
        self.assertEqual(self.served_release(), "v1")
        self.wait_for(lambda: self.status().startswith("ok v2"))

    def test_stopping_the_pod_during_a_preparation_ends_it_without_a_failed_status(self) -> None:
        self.add_release("v1")
        self.add_release("v2", "slow-prepare")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")
        self.set_current("v2")
        self.wait_for(lambda: self.status().startswith("preparing v2"))

        self.supervisor.send_signal(signal.SIGTERM)

        self.assertEqual(self.supervisor.wait(30), 0)
        self.assertTrue(self.status().startswith("preparing v2"))

    def test_a_version_that_fails_to_prepare_leaves_the_previous_one_serving(self) -> None:
        self.add_release("v1")
        self.add_release("v2", "fail-prepare")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")

        self.set_current("v2")
        self.wait_for(lambda: self.status().startswith("failed v2"))

        self.assertEqual(self.served_release(), "v1")

    def test_a_version_that_does_not_start_brings_the_previous_one_back(self) -> None:
        self.add_release("v1")
        self.add_release("v2", "fail-serve")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")

        self.set_current("v2")
        self.wait_for(lambda: self.status().startswith("failed v2"))

        self.wait_for(lambda: self.served_release() == "v1")

    def test_a_pod_restart_on_a_broken_version_serves_the_last_good_one(self) -> None:
        self.add_release("v1")
        self.add_release("v2", "fail-prepare")
        (self.home / ".last-good").write_text("v1\n")
        self.set_current("v2")

        self.start_supervisor()

        self.wait_for(lambda: self.served_release() == "v1")

    def test_stopping_the_pod_stops_uvicorn_and_closes_the_port(self) -> None:
        self.add_release("v1")
        self.set_current("v1")
        self.start_supervisor()
        self.wait_for(lambda: self.served_release() == "v1")

        self.supervisor.send_signal(signal.SIGTERM)

        self.assertEqual(self.supervisor.wait(30), 0)
        with self.assertRaises(OSError):
            self.served_release()

    def test_only_the_last_three_releases_are_kept(self) -> None:
        releases_dir = self.home / "releases"
        releases_dir.mkdir()
        for age, version in enumerate(["v5", "v4", "v3", "v2", "v1"]):
            (releases_dir / version).mkdir()
            archive = releases_dir / f"tierlist-{version}.tar.gz"
            archive.touch()
            os.utime(archive, (1000 - age, 1000 - age))
        module = load_supervisor_module()
        supervisor = object.__new__(module.Supervisor)
        supervisor.releases_dir = releases_dir

        supervisor._prune("v4")

        self.assertEqual(
            sorted(path.name for path in releases_dir.iterdir() if path.is_dir()),
            ["v3", "v4", "v5"],
        )


if __name__ == "__main__":
    unittest.main()
