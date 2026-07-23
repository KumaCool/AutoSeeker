from pathlib import Path

WORK_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = WORK_DIR / "var"
SECRETS_DIR = RUNTIME_DIR / "secrets"
CACHE_DIR = RUNTIME_DIR / "cache" / "security-js"
LOG_DIR = RUNTIME_DIR / "logs"
OUTPUT_DIR = RUNTIME_DIR / "outputs"
PROFILE_DIR = RUNTIME_DIR / "browser-profile"
COOKIE_FILE = SECRETS_DIR / "cookies.json"
COOKIE_TEXT_FILE = SECRETS_DIR / "cookies.txt"
EXCEL_FILE = OUTPUT_DIR / "wuhan-frontend-jobs.xlsx"

LEGACY_COOKIE_FILE = WORK_DIR / "cookies.json"
LEGACY_COOKIE_TEXT_FILE = WORK_DIR / "cookies.txt"
LEGACY_PROFILE_DIR = WORK_DIR / ".browser-profile"
LEGACY_EXCEL_FILE = WORK_DIR / "outputs" / "wuhan-frontend-jobs.xlsx"


def prepare_runtime_dirs():
    for path in (SECRETS_DIR, CACHE_DIR, LOG_DIR, OUTPUT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def active_profile_dir():
    if PROFILE_DIR.exists() or not LEGACY_PROFILE_DIR.exists():
        return PROFILE_DIR
    return LEGACY_PROFILE_DIR
