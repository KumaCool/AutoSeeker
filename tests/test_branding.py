import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_distribution_and_cli_are_autoseeker(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "autoseeker"', pyproject)
        self.assertIn('autoseeker = "auto_seeker.cli:main"', pyproject)
        self.assertNotIn("boss-zhipin-jobs", pyproject)

    def test_python_package_is_auto_seeker(self):
        self.assertTrue((ROOT / "src/auto_seeker/__init__.py").is_file())
        self.assertFalse((ROOT / "src/boss_zhipin").exists())

    def test_cli_reports_new_product_name(self):
        result = subprocess.run(
            [str(ROOT / ".venv/bin/python"), "-m", "auto_seeker.cli", "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("autoseeker 0.1.0", result.stdout)

    def test_root_readme_uses_autoseeker_title(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# AutoSeeker"))


if __name__ == "__main__":
    unittest.main()
