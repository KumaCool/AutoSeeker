import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from auto_seeker.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_uses_sqlite_storage(self):
        config = load_config()

        self.assertEqual(config.search.keyword, "前端")
        self.assertEqual(config.search.city_code, "101200100")
        self.assertEqual(config.search.page_count, 5)
        self.assertEqual(config.search.minimum_salary_k, 15)
        self.assertEqual(config.search.maximum_experience_years, 3)
        self.assertEqual(config.storage.database, Path("var/data/autoseeker.sqlite3"))
        self.assertEqual(config.web.host, "127.0.0.1")
        self.assertEqual(config.web.port, 8080)
        self.assertEqual(config.web.page_size, 50)

    def test_config_show_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(Path(__file__).resolve().parents[1] / ".venv/bin/autoseeker"), "config", "show"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"keyword": "前端"', result.stdout)

    def test_environment_overrides_toml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('[search]\nkeyword = "Python"\npage_count = 2\n', encoding="utf-8")
            with patch.dict(os.environ, {"AUTOSEEKER_KEYWORD": "Go", "AUTOSEEKER_PAGE_COUNT": "3"}, clear=False):
                config = load_config(path)

        self.assertEqual(config.search.keyword, "Go")
        self.assertEqual(config.search.page_count, 3)

    def test_explicit_overrides_have_highest_priority(self):
        with patch.dict(os.environ, {"AUTOSEEKER_KEYWORD": "Go"}, clear=False):
            config = load_config(overrides={"search.keyword": "Rust"})

        self.assertEqual(config.search.keyword, "Rust")

    def test_invalid_positive_number_fails_before_use(self):
        with patch.dict(os.environ, {"AUTOSEEKER_PAGE_COUNT": "0"}, clear=False):
            with self.assertRaises(ConfigError):
                load_config()

    def test_invalid_web_port_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[web]\nport = 70000\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
