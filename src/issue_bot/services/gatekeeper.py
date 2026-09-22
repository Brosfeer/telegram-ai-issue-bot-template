import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from issue_bot.core.storage import inspect_image_file

logger = logging.getLogger(__name__)

# Standard UI/UX quality keywords
QA_UI_KEYWORDS = [
    "ui", "ux", "screen", "design", "layout", "padding", "margin", "radius", "border",
    "color", "colors", "font", "typography", "icon", "icons", "button", "buttons",
    "navbar", "header", "tabbar", "tabs", "dock", "card", "cards", "banner", "banners",
    "shadow", "blur", "dark mode", "light mode", "rtl", "ltr", "alignment", "align",
    "gap", "spacing", "flex", "height", "width", "overflow", "clipping", "clipped",
    "cut off", "slider", "carousel", "shimmer", "loading", "spinner", "modal", "toast"
]

# Standard functional bug keywords
QA_BUG_KEYWORDS = [
    "bug", "issue", "crash", "error", "exception", "freeze", "hang", "slow", "broken",
    "not working", "fails", "failed", "duplicate", "inaccurate", "timeout", "network", "api",
    "stuck", "lag", "flicker", "reload", "null", "undefined", "unresponsive"
]

# Pure conversational chatter patterns (greetings, simple words)
CONVERSATIONAL_CHATTER_PATTERNS = [
    r"^(?:hi|hello|hey|sup|yo)$",
    r"^(?:ok|okay|k|thx|thanks|thank\s+you|ty)$",
    r"^(?:good|cool|nice|great|fine)$",
    r"^(?:test|testing)$",
    r"^(?:bye|goodbye|cya)$",
    r"^[\W_0-9]+$"  # Emojis, punctuation, or numbers only
]

def check_text_relevance(text: str) -> Tuple[bool, str]:
    """
    Evaluate if a user message or QA note contains actionable software feedback.
    Returns (is_relevant, reason).
    """
    s = (text or "").strip()
    if not s:
        return False, "empty_text"

    # Explicit issue reference (e.g. #42, #100)
    if re.search(r"#\d+", s):
        return True, "explicit_issue_reference"

    # Conversational chatter
    for pat in CONVERSATIONAL_CHATTER_PATTERNS:
        if re.match(pat, s, re.IGNORECASE):
            return False, "conversational_chatter"

    # Length guard
    if len(s) < 3:
        return False, "too_short"

    # Repetitive gibberish
    cleaned_chars = [c for c in s.lower() if not c.isspace()]
    if len(cleaned_chars) >= 4 and len(set(cleaned_chars)) <= 2:
        return False, "gibberish_spam"

    lowered = s.lower()
    has_ui_context = any(k in lowered for k in QA_UI_KEYWORDS)
    has_bug_context = any(k in lowered for k in QA_BUG_KEYWORDS)
    has_action_context = any(k in lowered for k in [
        "fix", "update", "change", "improve", "adjust", "resolve", "add", "remove", "refactor"
    ])

    if has_ui_context or has_bug_context or has_action_context:
        return True, "valid_qa_context"

    return False, "unrelated_context"

def validate_batch_relevance(
    items: List[Dict[str, Any]],
    custom_instruction: Optional[str] = None
) -> Tuple[bool, str]:
    """Determine if a batch of items (images + text) contains legitimate QA items."""
    if not items and not custom_instruction:
        return False, "Batch contains no items or instructions."

    all_texts = []
    if custom_instruction:
        all_texts.append(custom_instruction)
    for it in items:
        cap = it.get("caption")
        if cap and cap.strip():
            all_texts.append(cap.strip())

    combined_text = " ".join(all_texts).strip()
    has_relevant_text = False
    if combined_text:
        is_rel, _ = check_text_relevance(combined_text)
        if is_rel:
            has_relevant_text = True

    image_items = [it for it in items if it.get("item_type") == "image"]
    text_items = [it for it in items if it.get("item_type") == "text"]

    if text_items and not image_items:
        if has_relevant_text:
            return True, "Valid QA text notes."
        return False, "Text notes lack actionable UI, bug, or modification context."

    if image_items:
        if has_relevant_text:
            return True, "Valid QA screenshots and notes."

        valid_shots = 0
        for img in image_items:
            loc = img.get("local_path")
            if loc:
                meta = inspect_image_file(Path(loc))
                if meta.get("valid") and meta.get("file_size", 0) > 1000:
                    valid_shots += 1

        if valid_shots > 0:
            return True, "Valid screenshots detected."

        return False, "Uploaded images appear corrupted or invalid."

    return False, "Batch does not contain any valid QA items."
