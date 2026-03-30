from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, redirect, render_template, url_for


BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGUAGES = {"en", "tr", "nl", "id"}
SUPPORTED_PAGES = {"home", "daily-ladder", "word-scramble", "typo-hunt"}


def load_json(*parts: str):
    with (BASE_DIR.joinpath(*parts)).open("r", encoding="utf-8") as handle:
        return json.load(handle)


DICTIONARIES = {
    "en": load_json("i18n", "en.json"),
    "tr": load_json("i18n", "tr.json"),
    "nl": load_json("i18n", "nl.json"),
    "id": load_json("i18n", "id.json"),
}

WORDS = {
    "en": load_json("data", "words", "en", "common.json"),
    "tr": load_json("data", "words", "tr", "common.json"),
    "nl": load_json("data", "words", "nl", "common.json"),
    "id": load_json("data", "words", "id", "common.json"),
}

TYPOS = {
    "en": load_json("data", "typos", "en.json"),
    "tr": load_json("data", "typos", "tr.json"),
    "nl": load_json("data", "typos", "nl.json"),
    "id": load_json("data", "typos", "id.json"),
}

LADDERS = {
    "en": load_json("data", "ladders", "en.json"),
    "tr": load_json("data", "ladders", "tr.json"),
    "nl": load_json("data", "ladders", "nl.json"),
    "id": load_json("data", "ladders", "id.json"),
}


def create_app() -> Flask:
    app = Flask(
        "wordgames",
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    @app.route("/")
    def root():
        return redirect(url_for("localized_page", lang="en"))

    @app.route("/<lang>")
    @app.route("/<lang>/<page>")
    def localized_page(lang: str, page: str = "home"):
        if lang not in SUPPORTED_LANGUAGES:
            return redirect(url_for("localized_page", lang="en"))

        normalized_page = "daily-ladder" if page == "daily-word" else (page or "home")
        if normalized_page not in SUPPORTED_PAGES:
            return redirect(url_for("localized_page", lang=lang))

        dictionary = DICTIONARIES[lang]
        seo_map = {
            "home": ("homeTitle", "homeDescription"),
            "daily-ladder": ("dailyTitle", "dailyDescription"),
            "word-scramble": ("scrambleTitle", "scrambleDescription"),
            "typo-hunt": ("typoTitle", "typoDescription"),
        }
        title_key, description_key = seo_map[normalized_page]

        return render_template(
            "wordgames.html",
            lang=lang,
            page=normalized_page,
            title=dictionary["seo"][title_key],
            description=dictionary["seo"][description_key],
            app_data={
                "lang": lang,
                "page": normalized_page,
                "dictionaries": DICTIONARIES,
                "words": WORDS,
                "typos": TYPOS,
                "ladders": LADDERS,
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5051, debug=False, use_reloader=False)
