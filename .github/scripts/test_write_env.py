"""Tests of write_env.py.

Usage (from the repo root): python -m unittest discover -s .github/scripts
"""

import shutil
import subprocess
import unittest

from write_env import OPTIONAL, REQUIRED, EnvFileError, render_env_file


def complete_environment(**changes: str) -> dict[str, str]:
    environ: dict[str, str] = {name: f"value-of-{name.lower()}" for name in REQUIRED}
    environ.update(changes)
    return environ


def source_with_bash(content: str, name: str) -> str:
    """Value of `name` once the file is sourced by bash, as the pod start script does."""
    script = f"set -a\n{content}set +a\nprintf '%s' \"${name}\""
    # Full path: under Windows, a bare "bash" can resolve to the WSL launcher of System32
    bash = shutil.which("bash") or "bash"
    return subprocess.run([bash, "-c", script], capture_output=True, text=True, check=True).stdout


class RenderEnvFileTest(unittest.TestCase):
    def test_every_required_variable_is_written(self):
        content = render_env_file(complete_environment())
        for name in REQUIRED:
            self.assertIn(f"{name}='value-of-{name.lower()}'\n", content)

    def test_the_cookie_is_always_secure(self):
        self.assertIn("AUTH_COOKIE_SECURE='true'\n", render_env_file(complete_environment()))

    def test_a_missing_required_variable_is_refused(self):
        environ = complete_environment()
        del environ["JWT_SECRET_KEY"]
        environ["POSTGRES_PASSWORD"] = ""
        with self.assertRaises(EnvFileError) as raised:
            render_env_file(environ)
        self.assertIn("POSTGRES_PASSWORD", str(raised.exception))
        self.assertIn("JWT_SECRET_KEY", str(raised.exception))

    def test_optional_variables_are_written_only_when_set(self):
        content = render_env_file(complete_environment(GOOGLE_CLIENT_ID="client-id", LOG_LEVEL=""))
        self.assertIn("GOOGLE_CLIENT_ID='client-id'\n", content)
        for name in OPTIONAL:
            if name != "GOOGLE_CLIENT_ID":
                self.assertNotIn(f"{name}=", content)

    def test_other_variables_of_the_job_are_never_written(self):
        content = render_env_file(complete_environment(SFTP_PASSWORD="not-for-the-pod"))
        self.assertNotIn("not-for-the-pod", content)

    def test_a_line_break_in_a_value_is_refused(self):
        with self.assertRaises(EnvFileError):
            render_env_file(complete_environment(SMTP_PASSWORD="first\nsecond"))

    def test_shell_characters_survive_sourcing_unchanged(self):
        secret = "a'b\"c $HOME `id` \\ ;&|*"
        content = render_env_file(complete_environment(JWT_SECRET_KEY=secret))
        self.assertEqual(source_with_bash(content, "JWT_SECRET_KEY"), secret)


if __name__ == "__main__":
    unittest.main()
