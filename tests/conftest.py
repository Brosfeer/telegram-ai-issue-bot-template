import sys
import pytest
from pathlib import Path

# Add project root and src to sys.path
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"

for p in [str(root_dir), str(src_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Ensure all tests run with isolated temporary database and storage."""
    from issue_bot.config import settings
    from issue_bot.core.database import Database

    test_db = tmp_path / "test_bot.db"
    test_storage = tmp_path / "images"
    monkeypatch.setattr(settings, "DB_PATH", test_db)
    monkeypatch.setattr(settings, "STORAGE_DIR", test_storage)
    Database.init_db()
    yield
