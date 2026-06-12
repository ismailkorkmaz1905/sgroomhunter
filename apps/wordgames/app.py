from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, Response, abort, render_template, render_template_string, request, send_from_directory, url_for


BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from wordgames_catalog import (
    CATEGORIES,
    CHAINS,
    CROSSWORDS,
    DICTIONARIES,
    LADDERS,
    SUDOKUS,
    SUPPORTED_LANGUAGES,
    SUPPORTED_PAGES,
    TYPOS,
    WORDS,
)
from wordgames_validation import validate_all_datasets


def detect_app_version() -> str:
    env_version = (
        os.environ.get("APP_VERSION")
        or os.environ.get("RENDER_GIT_COMMIT")
        or os.environ.get("RENDER_GIT_BRANCH")
    )
    if env_version:
        return env_version[:7]

    try:
        repo_root = BASE_DIR.parent.parent
        version = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if version:
            return version
    except Exception:
        pass

    return "local"


APP_VERSION = detect_app_version()

validate_all_datasets(WORDS, TYPOS, LADDERS, CHAINS, CATEGORIES, CROSSWORDS, SUDOKUS)


def get_base_path() -> str:
    value = os.environ.get("WORDSPRINT_BASE_PATH", "").strip()
    if not value or value == "/":
        return ""
    return "/" + value.strip("/")


def prefixed_path(path: str) -> str:
    base_path = get_base_path()
    normalized_path = "/" + path.lstrip("/")
    return f"{base_path}{normalized_path}"


def static_asset_url(filename: str) -> str:
    return prefixed_path(f"/static/{filename}")


def manifest_payload() -> dict:
    base_path = get_base_path()
    start_url = f"{base_path}/en/" if base_path else "/en"
    scope = f"{base_path}/" if base_path else "/"
    return {
        "name": "WordSprint",
        "short_name": "WordSprint",
        "description": "Fast multilingual word games with Daily Ladder, Word Scramble, and Typo Hunt.",
        "start_url": start_url,
        "scope": scope,
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#fbf6ed",
        "theme_color": "#1e2433",
        "lang": "en",
        "icons": [
            {"src": static_asset_url("icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static_asset_url("icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {
                "src": static_asset_url("icons/icon-512-maskable.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }


_PAGE_GAME_DATA: dict[str, list[str]] = {
    "home": [],
    "daily-ladder": ["ladders"],
    "word-scramble": ["words"],
    "typo-hunt": ["typos"],
    "word-chain": ["chains"],
    "category-blitz": ["categories"],
    "mini-crossword": ["crosswords"],
    "mini-sudoku": ["sudokus"],
    "history": [],
    "privacy": [],
    "about": [],
    "terms": [],
}

_DATA_SOURCES = {
    "words": WORDS,
    "typos": TYPOS,
    "ladders": LADDERS,
    "chains": CHAINS,
    "categories": CATEGORIES,
    "crosswords": CROSSWORDS,
    "sudokus": SUDOKUS,
}


def render_localized_page(lang: str, page: str = "home"):
    if lang not in SUPPORTED_LANGUAGES:
        return None

    normalized_page = "daily-ladder" if page == "daily-word" else (page or "home")
    if normalized_page not in SUPPORTED_PAGES:
        return None

    dictionary = DICTIONARIES[lang]
    seo_map = {
        "home": ("homeTitle", "homeDescription"),
        "daily-ladder": ("dailyTitle", "dailyDescription"),
        "word-scramble": ("scrambleTitle", "scrambleDescription"),
        "typo-hunt": ("typoTitle", "typoDescription"),
        "word-chain": ("chainTitle", "chainDescription"),
        "category-blitz": ("categoryTitle", "categoryDescription"),
        "mini-crossword": ("crosswordTitle", "crosswordDescription"),
        "mini-sudoku": ("sudokuTitle", "sudokuDescription"),
        "history": ("historyTitle", "historyDescription"),
        "privacy": ("privacyTitle", "privacyDescription"),
        "about": ("aboutTitle", "aboutDescription"),
        "terms": ("termsTitle", "termsDescription"),
    }
    title_key, description_key = seo_map[normalized_page]

    game_data = {key: _DATA_SOURCES[key][lang] for key in _PAGE_GAME_DATA.get(normalized_page, [])}

    return render_template(
        "wordgames.html",
        lang=lang,
        page=normalized_page,
        title=dictionary["seo"][title_key],
        description=dictionary["seo"][description_key],
        app_version=APP_VERSION,
        base_path=get_base_path(),
        asset_url=static_asset_url,
        manifest_url=prefixed_path("/manifest.webmanifest"),
        service_worker_url=prefixed_path("/service-worker.js"),
        app_data={
            "lang": lang,
            "page": normalized_page,
            "availableLanguages": list(DICTIONARIES.keys()),
            "dictionary": dictionary,
            "version": APP_VERSION,
            "basePath": get_base_path(),
            **game_data,
        },
    )


def create_app() -> Flask:
    app = Flask(
        "wordgames",
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    @app.route("/")
    def root():
        return render_localized_page("en", "home")

    @app.route("/en")
    def english_home():
        return render_localized_page("en", "home")

    @app.route("/healthz")
    def healthcheck():
        return {"status": "ok"}, 200

    @app.route("/ads.txt")
    def ads_txt():
        publisher_id = (os.environ.get("ADSENSE_PUBLISHER_ID") or "").strip()
        if publisher_id:
            body = f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0\n"
        else:
            body = (
                "# Add your AdSense publisher ID in Render as ADSENSE_PUBLISHER_ID\n"
                "# Example:\n"
                "# google.com, pub-0000000000000000, DIRECT, f08c47fec0942fa0\n"
            )
        return Response(body, mimetype="text/plain; charset=utf-8")

    @app.route("/robots.txt")
    def robots_txt():
        body = (
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"
        )
        return Response(body, mimetype="text/plain; charset=utf-8")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        urls: list[str] = []
        for lang in sorted(SUPPORTED_LANGUAGES):
            urls.append(url_for("localized_page", lang=lang, _external=True))
            for page in ("daily-ladder", "word-scramble", "typo-hunt", "history", "privacy", "about", "terms"):
                urls.append(url_for("localized_page", lang=lang, page=page, _external=True))
            for page in ("mini-crossword", "mini-sudoku", "word-chain", "category-blitz"):
                urls.append(url_for("localized_page", lang=lang, page=page, _external=True))
        xml = render_template_string(
            """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for loc in urls %}
  <url><loc>{{ loc }}</loc></url>
{% endfor %}
</urlset>
""",
            urls=urls,
        )
        return Response(xml, mimetype="application/xml")

    @app.route("/manifest.webmanifest")
    def manifest():
        return Response(
            json.dumps(manifest_payload(), ensure_ascii=False, indent=2),
            mimetype="application/manifest+json",
        )

    @app.route("/service-worker.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = f"{get_base_path()}/" if get_base_path() else "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/<lang>", methods=["GET", "POST"])
    @app.route("/<lang>/<page>", methods=["GET", "POST"])
    def localized_page(lang: str, page: str = "home"):
        if request.method != "GET":
            abort(404)
        rendered = render_localized_page(lang, page)
        if rendered is None:
            abort(404)
        return rendered

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5051, debug=False, use_reloader=False)
