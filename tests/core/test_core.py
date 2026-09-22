import pytest
from pathlib import Path
from issue_bot.config import settings
from issue_bot.core.storage import sanitize_filename, get_target_filepath, inspect_image_file
from issue_bot.core.database import Database

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_bot.db"
    test_storage = tmp_path / "images"
    monkeypatch.setattr(settings, "DB_PATH", test_db)
    monkeypatch.setattr(settings, "STORAGE_DIR", test_storage)
    Database.init_db()
    yield

def test_settings_configuration():
    assert settings.BASE_DIR is not None
    assert settings.TARGET_BASE_BRANCH == "main"
    assert settings.ADMIN_USER_ID >= 0

def test_storage_sanitize_filename():
    assert sanitize_filename("../traversal/shot.png") == "shot.png"
    assert sanitize_filename("Defect (Header #1).png") == "Defect_Header_1.png"
    assert sanitize_filename("///") == "unnamed_image.png"

def test_storage_get_target_filepath():
    path = get_target_filepath("screenshot.png")
    assert path.parent == settings.STORAGE_DIR
    assert path.suffix == ".png"

def test_database_batch_workflow():
    user_id = 12345
    batch = Database.get_or_create_open_batch(user_id)
    assert batch["id"] is not None
    assert batch["status"] == "open"

    item_id = Database.add_item_to_batch(
        batch_id=batch["id"],
        user_id=user_id,
        item_type="text",
        caption="Sample bug observation"
    )
    assert item_id is not None
    items = Database.get_batch_items(batch["id"])
    assert len(items) == 1
    assert items[0]["caption"] == "Sample bug observation"

    # Concurrency lock
    assert Database.lock_batch_for_processing(batch["id"]) is True
    # Double lock fails
    assert Database.lock_batch_for_processing(batch["id"]) is False

    Database.unlock_batch(batch["id"])
    Database.close_batch(batch["id"])
    assert Database.get_open_batch(user_id) is None

def test_access_control():
    user_id = 998877
    assert Database.is_user_authorized(user_id) is False
    Database.authorize_user(user_id, "tester", "QA Tester", role="qa")
    assert Database.is_user_authorized(user_id) is True
    assert Database.is_admin(user_id) is False
    assert Database.revoke_user(user_id) is True
    assert Database.is_user_authorized(user_id) is False
