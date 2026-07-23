import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from boss_zhipin.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_matches_existing_behavior(self):
        config = load_config()

        self.assertEqual(config.search.keyword, "前端")
        self.assertEqual(config.search.city_code, "101200100")
        self.assertEqual(config.search.page_count, 5)
        self.assertEqual(config.search.minimum_salary_k, 15)
        self.assertEqual(config.search.maximum_experience_years, 3)
        self.assertEqual(config.output.path, Path("var/outputs/wuhan-frontend-jobs.xlsx"))

    def test_environment_overrides_toml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('[search]\nkeyword = "Python"\npage_count = 2\n', encoding="utf-8")
            with patch.dict(os.environ, {"BOSS_KEYWORD": "Go", "BOSS_PAGE_COUNT": "3"}, clear=False):
                config = load_config(path)

        self.assertEqual(config.search.keyword, "Go")
        self.assertEqual(config.search.page_count, 3)

    def test_explicit_overrides_have_highest_priority(self):
        with patch.dict(os.environ, {"BOSS_KEYWORD": "Go"}, clear=False):
            config = load_config(overrides={"search.keyword": "Rust"})

        self.assertEqual(config.search.keyword, "Rust")

    def test_invalid_positive_number_fails_before_use(self):
        with patch.dict(os.environ, {"BOSS_PAGE_COUNT": "0"}, clear=False):
            with self.assertRaises(ConfigError):
                load_config()


if __name__ == "__main__":
    unittest.main()
