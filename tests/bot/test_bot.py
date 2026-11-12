import pytest
from telegram import ReplyKeyboardMarkup
from issue_bot.config import settings
from issue_bot.bot.keyboards import get_persistent_keyboard, format_batch_card
from issue_bot.bot.app import create_application

def test_persistent_keyboard(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_USER_ID", 999888)
    qa_kb = get_persistent_keyboard(user_id=112233)
    assert isinstance(qa_kb, ReplyKeyboardMarkup)
    assert qa_kb.is_persistent is True

    admin_kb = get_persistent_keyboard(user_id=999888)
    assert isinstance(admin_kb, ReplyKeyboardMarkup)
    admin_buttons = [btn.text for row in admin_kb.keyboard for btn in row]
    assert "⚡ Quick Issue" in admin_buttons

def test_format_batch_card(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_USER_ID", 999888)
    batch = {"id": 1, "status": "open"}
    items = [{"id": 101, "item_type": "text", "caption": "Button is unclickable on mobile"}]
    card_text, markup = format_batch_card(batch, items, user_id=112233)
    assert "Batch #1" in card_text
    assert "Button is unclickable" in card_text
    assert markup is not None

def test_format_batch_card_isolated_and_drop_chips(monkeypatch):
    from datetime import datetime, timezone
    today_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    monkeypatch.setattr(settings, "ADMIN_USER_ID", 999888)
    batch = {"id": 42, "status": "open"}
    items = [
        {"id": 10, "item_type": "image", "caption": "Old crash", "created_at": "2026-10-01 10:00:00"},
        {"id": 11, "item_type": "image", "caption": "Today layout defect", "created_at": today_ts}
    ]
    card_text, markup = format_batch_card(batch, items, user_id=112233, new_item_id=11)
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]

    # Isolated trigger button present
    assert "single:ai:11" in callbacks
    # Date-scoped trigger button present
    assert "batch:today:42" in callbacks
    # Main trigger present
    assert "batch:ai:42" in callbacks
    # Granular drop chips present
    assert "batch:drop:10" in callbacks
    assert "batch:drop:11" in callbacks

def test_create_application(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "000000000:TEST_BOT_TOKEN_MOCK")
    app = create_application()
    assert app is not None
