import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScriptTests(unittest.TestCase):
    def test_portable_scripts_are_valid_posix_shell(self):
        for script in ("setup.sh", "run_daily.sh"):
            result = subprocess.run(["sh", "-n", str(ROOT / script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{script}: {result.stderr}")

    def test_daily_runner_invokes_installed_cli(self):
        text = (ROOT / "run_daily.sh").read_text(encoding="utf-8")
        self.assertIn('.venv/bin/boss-zhipin" collect', text)
        self.assertNotIn("boss_jobs.py", text)

    def test_scheduler_templates_use_same_daily_runner(self):
        service = (ROOT / "systemd/boss-zhipin.service.template").read_text(encoding="utf-8")
        timer = (ROOT / "systemd/boss-zhipin.timer").read_text(encoding="utf-8")
        launchd = (ROOT / "launchd.plist.template").read_text(encoding="utf-8")
        self.assertIn("__WORK_DIR__/run_daily.sh", service)
        self.assertIn("OnCalendar=*-*-* 09:00:00", timer)
        self.assertIn("__RUN_SCRIPT__", launchd)
        self.assertIn("var/logs/launchd.out.log", launchd)


if __name__ == "__main__":
    unittest.main()
