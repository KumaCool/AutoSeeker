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
            [str(PYTHON), "-m", "boss_zhipin.cli", *arguments],
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
        self.assertIn("1.0.0", result.stdout)

    def test_collect_delegates_to_legacy_main(self):
        from unittest.mock import patch

        from boss_zhipin import cli

        with (
            patch("boss_jobs.load_cookies", return_value={"zp_at": "token"}),
            patch("boss_zhipin.application.collect_jobs.collect_jobs") as collect,
        ):
            collect.return_value = type("Result", (), {"matched_count": 0, "new_count": 0})()
            result = cli.main(["collect", "--page-count", "1"])

        self.assertEqual(result, 0)

    def test_legacy_project_root_is_added_to_import_path(self):
        import sys

        from boss_zhipin import cli
        from boss_zhipin.config import PROJECT_ROOT

        with patch.object(sys, "path", [entry for entry in sys.path if entry != str(PROJECT_ROOT)]):
            cli.ensure_legacy_import_path()
            self.assertEqual(sys.path[0], str(PROJECT_ROOT))

    def test_config_show_redacts_cookie_path(self):
        result = self.run_cli("config", "show")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<redacted-path>", result.stdout)
        self.assertNotIn("var/secrets/cookies.json", result.stdout)

    def test_help_lists_auth_command(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("auth", result.stdout)


if __name__ == "__main__":
    unittest.main()
