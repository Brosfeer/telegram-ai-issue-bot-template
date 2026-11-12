import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the repository (project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load environment variables from .env in project root
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip()

# Primary Super Admin / Owner ID (numeric, from @userinfobot)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Authorized Telegram User IDs (initial whitelist from .env)
ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS = [
    int(uid.strip()) for uid in ALLOWED_USER_IDS_RAW.split(",") if uid.strip().isdigit()
]
if ADMIN_USER_ID > 0 and ADMIN_USER_ID not in ALLOWED_USER_IDS:
    ALLOWED_USER_IDS.append(ADMIN_USER_ID)

# Target repository directory, GitHub remote identifier, and active working branch
TARGET_REPO_DIR_SETTING = os.getenv("TARGET_REPO_DIR", str(BASE_DIR))
TARGET_REPO_DIR = Path(TARGET_REPO_DIR_SETTING).resolve()
TARGET_REPO_NAME = os.getenv("TARGET_REPO_NAME", "your-org/your-target-repo").strip()
TARGET_BASE_BRANCH = os.getenv("TARGET_BASE_BRANCH", "main").strip()

# Path to AGY CLI executable
AGY_PATH = Path(os.getenv("AGY_PATH", "agy")).resolve()

# Storage directory for uploaded QA screenshots
STORAGE_DIR_SETTING = os.getenv("STORAGE_DIR", "data/images")
STORAGE_DIR = Path(STORAGE_DIR_SETTING)
if not STORAGE_DIR.is_absolute():
    STORAGE_DIR = BASE_DIR / STORAGE_DIR

# SQLite database file path
DB_PATH_SETTING = os.getenv("DB_PATH", "data/bot.db")
DB_PATH = Path(DB_PATH_SETTING)
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH

# Supported image file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}

def is_user_authorized(user_id: int) -> bool:
    """Check if user is authorized via Admin ID, static whitelist, or database."""
    if (ADMIN_USER_ID > 0 and user_id == ADMIN_USER_ID) or user_id in ALLOWED_USER_IDS:
        return True
    try:
        from issue_bot.core.database import Database
        return Database.is_user_authorized(user_id)
    except Exception:
        return False

def init_directories():
    """Ensure storage and database directories exist."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
