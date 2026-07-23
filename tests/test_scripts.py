import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectLayoutTests(unittest.TestCase):
    def test_portable_scripts_are_valid_posix_shell(self):
        for path in ("scripts/setup.sh", "scripts/run-daily.sh", "deploy/systemd/install-user-timer.sh"):
            result = subprocess.run(["sh", "-n", str(ROOT / path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}")

    def test_macos_scripts_are_grouped(self):
        login = (ROOT / "scripts/macos/login.sh").read_text(encoding="utf-8")
        installer = (ROOT / "scripts/macos/install-launchd.sh").read_text(encoding="utf-8")
        self.assertIn("-m auto_seeker.browser_auth", login)
        self.assertIn("deploy/launchd/autoseeker.plist.template", installer)

    def test_scheduler_templates_use_run_daily_script(self):
        service = (ROOT / "deploy/systemd/autoseeker.service.template").read_text(encoding="utf-8")
        launchd = (ROOT / "deploy/launchd/autoseeker.plist.template").read_text(encoding="utf-8")
        self.assertIn("__WORK_DIR__/scripts/run-daily.sh", service)
        self.assertIn("__RUN_SCRIPT__", launchd)

    def test_key_directories_have_readmes(self):
        directories = [
            "scripts",
            "scripts/macos",
            "deploy",
            "deploy/systemd",
            "deploy/launchd",
            "config",
            "src",
            "tests",
            "var",
        ]
        for directory in directories:
            readme = ROOT / directory / "README.md"
            self.assertTrue(readme.is_file(), f"missing {readme}")
            self.assertGreater(len(readme.read_text(encoding="utf-8").strip()), 40)

    def test_root_no_longer_contains_helper_scripts(self):
        old_paths = [
            "setup.sh",
            "run_daily.sh",
            "login.sh",
            "install_launchd.sh",
            "launchd.plist.template",
            "systemd",
            "cookies.example.json",
        ]
        self.assertEqual([path for path in old_paths if (ROOT / path).exists()], [])


if __name__ == "__main__":
    unittest.main()
