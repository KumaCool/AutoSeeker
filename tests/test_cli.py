import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [str(PYTHON), "-m", "auto_seeker.cli", *arguments],
            cwd=ROOT,
            env=ENV,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_help_lists_collect_command(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("collect", result.stdout)

    def test_version_is_available(self):
        result = self.run_cli("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0.1.0", result.stdout)

    def test_collect_uses_sqlite_repository(self):
        from auto_seeker import cli

        with (
            patch("auto_seeker.auth.load_cookie_file", return_value={"zp_at": "token"}) as loader,
            patch("auto_seeker.application.collect_jobs.collect_jobs") as collect,
            patch("auto_seeker.infrastructure.sqlite_repository.SQLiteJobRepository") as repository,
        ):
            collect.return_value = type("Result", (), {"run_id": 1, "matched_count": 0, "new_count": 0})()
            result = cli.main(["collect", "--page-count", "1"])

        self.assertEqual(result, 0)
        loader.assert_called_once()
        repository.assert_called_once()

    def test_config_show_redacts_cookie_path(self):
        result = self.run_cli("config", "show")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<redacted-path>", result.stdout)
        self.assertNotIn("var/secrets/cookies.json", result.stdout)

    def test_help_lists_auth_command(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("auth", result.stdout)

    def test_help_lists_web_command(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("web", result.stdout)

    def test_web_command_runs_uvicorn_with_configured_values(self):
        from auto_seeker import cli

        with patch("uvicorn.run") as run:
            result = cli.main(["web", "--host", "127.0.0.2", "--port", "9090"])

        self.assertEqual(result, 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["host"], "127.0.0.2")
        self.assertEqual(run.call_args.kwargs["port"], 9090)


if __name__ == "__main__":
    unittest.main()
