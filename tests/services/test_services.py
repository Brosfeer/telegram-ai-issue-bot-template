import pytest
from issue_bot.services.github_service import (
    extract_issue_url_and_number,
    detect_primary_label,
    format_title_case,
    is_ui_context,
)
from issue_bot.services.gatekeeper import (
    check_text_relevance,
    validate_batch_relevance,
)
from issue_bot.services.sub_issue_service import diagnose_and_simplify_qa_item

def test_github_service_helpers():
    url_info = extract_issue_url_and_number("Created issue https://github.com/my-org/my-repo/issues/42")
    assert url_info == {
        "issue_url": "https://github.com/my-org/my-repo/issues/42",
        "issue_number": 42
    }

    assert detect_primary_label("Crash during checkout") == "bug"
    assert detect_primary_label("Add dark mode switcher") == "enhancement"
    assert format_title_case("fix navigation bar padding") == "Bug(ui): Fix Navigation Bar Padding"
    assert is_ui_context("Padding between store cards is cut off") is True

def test_gatekeeper_validation():
    # Valid feedback
    rel, reason = check_text_relevance("Navbar icons are misaligned on iOS")
    assert rel is True
    assert reason == "valid_qa_context"

    # Chatter rejection
    chatter, reason = check_text_relevance("hello")
    assert chatter is False
    assert reason == "conversational_chatter"

    # Batch validation
    batch_valid, _ = validate_batch_relevance([
        {"item_type": "text", "caption": "Fix navigation bar padding"}
    ])
    assert batch_valid is True

def test_sub_issue_diagnosis():
    diag = diagnose_and_simplify_qa_item("App crashes with unhandled exception on login")
    assert "Runtime" in diag["subsystem"]
    assert "login" in diag["simplification"]
