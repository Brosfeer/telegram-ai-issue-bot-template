"""Re-export gatekeeper from services layer."""
from issue_bot.services.gatekeeper import (
    QA_UI_KEYWORDS,
    QA_BUG_KEYWORDS,
    CONVERSATIONAL_CHATTER_PATTERNS,
    check_text_relevance,
    validate_batch_relevance,
)

__all__ = [
    "QA_UI_KEYWORDS",
    "QA_BUG_KEYWORDS",
    "CONVERSATIONAL_CHATTER_PATTERNS",
    "check_text_relevance",
    "validate_batch_relevance",
]
