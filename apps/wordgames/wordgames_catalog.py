from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGUAGES = {"en", "tr", "nl", "id", "ms"}
SUPPORTED_PAGES = {
    "home",
    "daily-ladder",
    "word-scramble",
    "typo-hunt",
    "word-chain",
    "category-blitz",
    "mini-crossword",
    "mini-sudoku",
    "history",
    "privacy",
    "about",
    "terms",
}


def load_json(*parts: str):
    with (BASE_DIR.joinpath(*parts)).open("r", encoding="utf-8") as handle:
        return json.load(handle)


DICTIONARIES = {
    "en": load_json("i18n", "en.json"),
    "tr": load_json("i18n", "tr.json"),
    "nl": load_json("i18n", "nl.json"),
    "id": load_json("i18n", "id.json"),
    "ms": load_json("i18n", "ms.json"),
}

WORDS = {
    language: load_json("data", "words", language, "common.json")
    for language in SUPPORTED_LANGUAGES
}

TYPOS = {
    language: load_json("data", "typos", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}

LADDERS = {
    language: load_json("data", "ladders", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}

CHAINS = {
    language: load_json("data", "chains", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}

CATEGORIES = {
    language: load_json("data", "categories", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}

CROSSWORDS = {
    language: load_json("data", "crosswords", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}

SUDOKUS = {
    language: load_json("data", "sudokus", f"{language}.json")
    for language in SUPPORTED_LANGUAGES
}
