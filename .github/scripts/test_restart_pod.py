"""Tests of restart_pod.sh, against a local HTTP server standing for the MineStrator panel.

Usage (from the repo root): python -m unittest discover -s .github/scripts
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).with_name("restart_pod.sh")


class FakePanel:
    """Answers each request with the next status of `statuses`, and keeps the requests."""

    def __init__(self, statuses: list[int]) -> None:
        self.statuses = list(statuses)
        self.requests: list[dict] = []
        panel = self

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                panel.requests.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "content_type": self.headers.get("Content-Type"),
                        "body": self.rfile.read(length).decode(),
                    }
                )
                status = panel.statuses.pop(0)
                body = json.dumps({"api": {"code": status}}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def run_script(**env: str) -> tuple[int, str, str]:
    """Runs the script; returns its exit code, the job summary and the step outputs."""
    with tempfile.TemporaryDirectory() as folder:
        summary = Path(folder, "summary")
        outputs = Path(folder, "outputs")
        environ = {
            "PATH": os.environ["PATH"],
            "GITHUB_STEP_SUMMARY": str(summary),
            "GITHUB_OUTPUT": str(outputs),
            "RESTART_RETRY_DELAY_SECONDS": "0",
            **env,
        }
        # Full path: under Windows, a bare "bash" can resolve to the WSL launcher of System32
        bash = shutil.which("bash") or "bash"
        result = subprocess.run([bash, str(SCRIPT)], env=environ, capture_output=True, text=True)
        read = lambda path: path.read_text(encoding="utf-8") if path.exists() else ""  # noqa: E731
        return result.returncode, read(summary), read(outputs)


class RestartPodTest(unittest.TestCase):
    def panel(self, *statuses: int) -> FakePanel:
        panel = FakePanel(list(statuses))
        self.addCleanup(panel.close)
        return panel

    def configured(self, panel: FakePanel) -> dict[str, str]:
        return {"PANEL_URL": panel.url, "PANEL_SERVER_ID": "123456", "PANEL_API_KEY": "secret-key"}

    def test_without_server_or_key_the_restart_is_left_to_the_panel(self):
        code, summary, outputs = run_script(PANEL_API_KEY="secret-key")
        self.assertEqual(code, 0)
        self.assertIn("Restart the pod by hand", summary)
        self.assertIn("restarted=false", outputs)

    def test_a_200_restarts_the_pod_with_the_minestrator_request(self):
        panel = self.panel(200)
        code, summary, outputs = run_script(**self.configured(panel))
        self.assertEqual(code, 0)
        self.assertIn("restarted=true", outputs)
        self.assertIn("restarted through the MineStrator panel API", summary)
        self.assertEqual(
            panel.requests,
            [
                {
                    "path": "/server/123456/poweraction",
                    "authorization": "Bearer secret-key",
                    "content_type": "application/json",
                    "body": '{"poweraction":"restart"}',
                }
            ],
        )

    def test_a_400_or_401_fails_with_its_reason_in_the_summary(self):
        for status, reason in ((400, "PANEL_SERVER_ID"), (401, "PANEL_API_KEY")):
            with self.subTest(status=status):
                panel = self.panel(status)
                code, summary, outputs = run_script(**self.configured(panel))
                self.assertEqual(code, 1)
                self.assertIn("Pod restart failed", summary)
                self.assertIn(f"({status}): check {reason}", summary)
                self.assertIn("restarted=false", outputs)
                self.assertNotIn("secret-key", summary)
                self.assertEqual(len(panel.requests), 1)

    def test_a_429_is_retried_once(self):
        panel = self.panel(429, 200)
        code, _, outputs = run_script(**self.configured(panel))
        self.assertEqual(code, 0)
        self.assertIn("restarted=true", outputs)
        self.assertEqual(len(panel.requests), 2)

    def test_a_second_429_fails(self):
        panel = self.panel(429, 429)
        code, summary, _ = run_script(**self.configured(panel))
        self.assertEqual(code, 1)
        self.assertIn("too many requests to the panel (429), even after a new try", summary)
        self.assertEqual(len(panel.requests), 2)

    def test_an_unreachable_panel_fails(self):
        panel = self.panel()
        url = panel.url
        panel.close()
        code, summary, _ = run_script(PANEL_URL=url, PANEL_SERVER_ID="123456", PANEL_API_KEY="k")
        self.assertEqual(code, 1)
        self.assertIn("could not be reached", summary)


if __name__ == "__main__":
    unittest.main()
