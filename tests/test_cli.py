import os
import subprocess
import unittest
from pathlib import Path


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

        with patch("boss_jobs.main") as legacy_main:
            result = cli.main(["collect"])

        self.assertEqual(result, 0)
        legacy_main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
