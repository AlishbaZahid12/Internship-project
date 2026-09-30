"""
Shared helper functions used across the project.
Supports both English and Urdu (Romanized and Urdu-script) input, since
speech recognition may return either depending on what was said.
"""

import re

WORD_TO_DIGIT = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "to": "2", "too": "2",
    "three": "3", "four": "4", "for": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "ate": "8", "nine": "9",
}

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Urdu-script number words (spoken numbers, not digit characters)
URDU_NUMBER_WORDS = {
    "صفر": 0, "ایک": 1, "دو": 2, "تین": 3, "چار": 4,
    "پانچ": 5, "چھ": 6, "سات": 7, "آٹھ": 8, "نو": 9, "دس": 10,
}

# Eastern Arabic (Urdu/Persian) digit characters -> ASCII digits
URDU_DIGIT_CHARS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

HOMOPHONES = {"to": 2, "too": 2, "for": 4, "ate": 8, "won": 1}

AFFIRMATIVE_WORDS = {
    "yes", "yeah", "yep", "yup", "correct", "right", "confirm", "sure",
    "okay", "ok", "affirmative", "true", "haan", "ha",
    "ہاں", "جی", "جی ہاں", "بالکل", "ٹھیک",
}

NEGATIVE_WORDS = {
    "no", "nope", "nah", "wrong", "incorrect", "cancel", "negative",
    "false", "nahi", "nahin",
    "نہیں", "نہ", "غلط",
}


def _normalize_urdu_digits(text: str) -> str:
    return text.translate(URDU_DIGIT_CHARS)


def _words(text: str) -> list:
    text = _normalize_urdu_digits(text.lower())
    # Keep Urdu script characters too, not just a-z0-9
    return re.findall(r"[a-z0-9\u0600-\u06FF']+", text)


def has_word(text: str, *candidates: str) -> bool:
    """True if any candidate appears as a whole word."""
    return bool(set(_words(text)) & set(candidates))


def extract_digits(spoken_text: str) -> str:
    """'one two three four' / '1 2 3 4' / Urdu digits -> '1234' (PINs, phone numbers)."""
    text = _normalize_urdu_digits(spoken_text.lower())
    digits = []
    for word in text.split():
        clean_word = "".join(c for c in word if c.isalnum())
        if clean_word.isdigit():
            digits.append(clean_word)
        elif clean_word in WORD_TO_DIGIT:
            digits.append(WORD_TO_DIGIT[clean_word])
    return "".join(digits)


def extract_number(text: str):
    """First standalone number in the text (age, etc.). Handles Urdu digits too."""
    text = _normalize_urdu_digits(text)
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def extract_choice(spoken_text: str):
    """
    Menu choice from speech, English or Urdu: 'two', '2', 'دو' -> 2.
    'cancel' -> 0. Returns None if no number was heard.
    """
    text = _normalize_urdu_digits(spoken_text.lower())
    if "cancel" in text or "منسوخ" in text:
        return 0

    for word in _words(text):
        if word.isdigit():
            return int(word)
        if word in NUMBER_WORDS:
            return NUMBER_WORDS[word]
        if word in URDU_NUMBER_WORDS:
            return URDU_NUMBER_WORDS[word]

    words = _words(text)
    if len(words) <= 2:
        for word in words:
            if word in HOMOPHONES:
                return HOMOPHONES[word]
    return None


def is_negative(spoken_text: str) -> bool:
    words = set(_words(spoken_text))
    return bool(words & NEGATIVE_WORDS) or "not" in words or "don't" in words


def is_affirmative(spoken_text: str) -> bool:
    words = set(_words(spoken_text))
    return bool(words & AFFIRMATIVE_WORDS) and not is_negative(spoken_text)