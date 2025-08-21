from typing import Optional

from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator


# Minimal greeting lexicon across languages; extend as needed
GREETING_LEXICON = {
    "en": {"hello", "hi", "hey", "good morning", "good afternoon", "good evening"},
    "fr": {"bonjour", "salut", "coucou"},
    "ar": {"مرحبا", "اهلا", "السلام عليكم"},
    "es": {"hola", "buenos dias", "buenas tardes", "buenas noches"},
    "de": {"hallo", "guten tag", "guten morgen", "guten abend"},
    "it": {"ciao", "salve", "buongiorno", "buonasera"},
}


def detect_language(text: str) -> Optional[str]:
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return None


def is_greeting(user_text: str) -> Optional[str]:
    """
    Returns the language code if the text looks like a greeting in that language; otherwise None.
    """
    text = (user_text or "").strip().lower()
    if not text:
        return None

    # Quick lexicon check per language
    for lang_code, greetings in GREETING_LEXICON.items():
        for g in greetings:
            if text == g or text.startswith(g + " ") or (g in text and len(text.split()) <= 4):
                return lang_code

    # Fallback to language detection and check against that language's greetings
    lang = detect_language(text)
    if lang and lang in GREETING_LEXICON:
        for g in GREETING_LEXICON[lang]:
            if text == g or text.startswith(g + " ") or (g in text and len(text.split()) <= 4):
                return lang
    return None


def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return ""
    try:
        if target_lang == "en":
            # Ensure deterministic behavior even if translator auto-detect is wrong
            return GoogleTranslator(source="auto", target="en").translate(text)
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text


def make_greeting_response(lang: str) -> str:
    base_response = "Hello! How can I help you today?"
    if not lang or lang == "en":
        return base_response
    return translate_text(base_response, lang)


def localized_not_found(lang: Optional[str]) -> str:
    base = "I couldn’t find this in the knowledge base."
    if not lang or lang == "en":
        return base
    return translate_text(base, lang)


