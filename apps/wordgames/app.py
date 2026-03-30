from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGUAGES = {"en", "tr", "nl", "id"}
SUPPORTED_PAGES = {"home", "daily-ladder", "word-scramble", "typo-hunt", "privacy"}
ANALYTICS_DB = BASE_DIR / "analytics.sqlite3"


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


def ensure_analytics_db() -> None:
    with sqlite3.connect(ANALYTICS_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS visit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                path TEXT NOT NULL,
                lang TEXT,
                page TEXT,
                status_code INTEGER NOT NULL,
                device_type TEXT NOT NULL,
                browser_family TEXT NOT NULL,
                referrer_domain TEXT
            )
            """
        )
        connection.commit()


def infer_device_type(user_agent: str) -> str:
    lowered = user_agent.lower()
    mobile_markers = ("iphone", "android", "mobile", "ipad")
    return "mobile" if any(marker in lowered for marker in mobile_markers) else "desktop"


def infer_browser_family(user_agent: str) -> str:
    lowered = user_agent.lower()
    if "edg/" in lowered:
        return "Edge"
    if "chrome/" in lowered and "edg/" not in lowered:
        return "Chrome"
    if "firefox/" in lowered:
        return "Firefox"
    if "safari/" in lowered and "chrome/" not in lowered:
        return "Safari"
    return "Other"


def extract_referrer_domain(referrer: str | None) -> str | None:
    if not referrer:
        return None
    parsed = urlparse(referrer)
    return parsed.netloc or None


def should_log_request(path: str, status_code: int, method: str) -> bool:
    if method != "GET":
        return False
    if path.startswith("/static/"):
        return False
    if path in {"/healthz", "/analytics-summary"}:
        return False
    return status_code in {200, 404}


def log_visit_event(path: str, lang: str | None, page: str | None, status_code: int) -> None:
    ensure_analytics_db()
    user_agent = request.headers.get("User-Agent", "")
    with sqlite3.connect(ANALYTICS_DB) as connection:
        connection.execute(
            """
            INSERT INTO visit_events (
                path,
                lang,
                page,
                status_code,
                device_type,
                browser_family,
                referrer_domain
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                path,
                lang,
                page,
                status_code,
                infer_device_type(user_agent),
                infer_browser_family(user_agent),
                extract_referrer_domain(request.headers.get("Referer")),
            ),
        )
        connection.commit()


def get_analytics_summary(days: int = 7) -> dict:
    ensure_analytics_db()
    with sqlite3.connect(ANALYTICS_DB) as connection:
        connection.row_factory = sqlite3.Row
        totals = connection.execute(
            """
            SELECT COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            """,
            (f"-{days} days",),
        ).fetchone()
        by_path = connection.execute(
            """
            SELECT path, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY path
            ORDER BY visits DESC, path ASC
            LIMIT 10
            """,
            (f"-{days} days",),
        ).fetchall()
        by_language = connection.execute(
            """
            SELECT COALESCE(lang, 'unknown') AS lang, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY lang
            ORDER BY visits DESC, lang ASC
            """,
            (f"-{days} days",),
        ).fetchall()
        by_device = connection.execute(
            """
            SELECT device_type, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY device_type
            ORDER BY visits DESC, device_type ASC
            """,
            (f"-{days} days",),
        ).fetchall()
        by_browser = connection.execute(
            """
            SELECT browser_family, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY browser_family
            ORDER BY visits DESC, browser_family ASC
            """,
            (f"-{days} days",),
        ).fetchall()

    return {
        "days": days,
        "privacy_mode": "anonymous-aggregate-only",
        "totals": {"visits": totals["visits"] if totals else 0},
        "by_path": [dict(row) for row in by_path],
        "by_language": [dict(row) for row in by_language],
        "by_device": [dict(row) for row in by_device],
        "by_browser": [dict(row) for row in by_browser],
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
        "privacy": ("privacyTitle", "privacyDescription"),
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

    @app.route("/analytics-summary")
    def analytics_summary():
        return jsonify(get_analytics_summary())

    @app.route("/<lang>")
    @app.route("/<lang>/<page>")
    def localized_page(lang: str, page: str = "home"):
        rendered = render_localized_page(lang, page)
        if rendered is None:
            if lang not in SUPPORTED_LANGUAGES:
                return redirect(url_for("english_home"))
            return redirect(url_for("localized_page", lang="en"))
        return rendered

    @app.after_request
    def capture_analytics(response):
        if should_log_request(request.path, response.status_code, request.method):
            segments = [segment for segment in request.path.split("/") if segment]
            lang = segments[0] if segments and segments[0] in SUPPORTED_LANGUAGES else None
            page = segments[1] if len(segments) > 1 else ("home" if lang else None)
            log_visit_event(request.path, lang, page, response.status_code)
        return response

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5051, debug=False, use_reloader=False)
