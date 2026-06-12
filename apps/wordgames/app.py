from __future__ import annotations

import hmac
import json
import os
import sqlite3
import subprocess
import sys
from base64 import b64decode
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, redirect, render_template, render_template_string, request, send_from_directory, url_for


BASE_DIR = Path(__file__).resolve().parent
ANALYTICS_DB = BASE_DIR / "analytics.sqlite3"

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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS player_profiles (
                client_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                lang TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    if path in {"/healthz", "/analytics", "/analytics-summary"}:
        return False
    return status_code in {200, 404}


def log_visit_event(path: str, lang: str | None, page: str | None, status_code: int) -> None:
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
        by_page = connection.execute(
            """
            SELECT COALESCE(page, 'unknown') AS page, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY page
            ORDER BY visits DESC, page ASC
            """
            ,
            (f"-{days} days",),
        ).fetchall()
        daily_visits = connection.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS visits
            FROM visit_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 14
            """
            ,
            (f"-{days} days",),
        ).fetchall()
        recent_names = connection.execute(
            """
            SELECT display_name, lang, updated_at
            FROM player_profiles
            ORDER BY updated_at DESC
            LIMIT 12
            """
        ).fetchall()

    return {
        "days": days,
        "privacy_mode": "anonymous-aggregate-only",
        "totals": {"visits": totals["visits"] if totals else 0},
        "by_path": [dict(row) for row in by_path],
        "by_language": [dict(row) for row in by_language],
        "by_device": [dict(row) for row in by_device],
        "by_browser": [dict(row) for row in by_browser],
        "by_page": [dict(row) for row in by_page],
        "daily_visits": [dict(row) for row in daily_visits],
        "recent_names": [dict(row) for row in recent_names],
    }


def normalize_display_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned[:40]


def upsert_player_profile(client_id: str, display_name: str, lang: str | None) -> None:
    with sqlite3.connect(ANALYTICS_DB) as connection:
        connection.execute(
            """
            INSERT INTO player_profiles (client_id, display_name, lang, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(client_id) DO UPDATE SET
                display_name = excluded.display_name,
                lang = excluded.lang,
                updated_at = CURRENT_TIMESTAMP
            """,
            (client_id, display_name, lang),
        )
        connection.commit()


def analytics_auth_enabled() -> bool:
    return bool(os.environ.get("ANALYTICS_USERNAME") and os.environ.get("ANALYTICS_PASSWORD"))


def check_basic_auth(auth_header: str | None) -> bool:
    if not analytics_auth_enabled():
        return True
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        decoded = b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
    except Exception:
        return False
    username, separator, password = decoded.partition(":")
    if not separator:
        return False
    return hmac.compare_digest(username, os.environ.get("ANALYTICS_USERNAME", "")) and hmac.compare_digest(
        password, os.environ.get("ANALYTICS_PASSWORD", "")
    )


def analytics_unauthorized_response() -> Response:
    return Response(
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="WordGames Analytics"'},
    )


def render_analytics_dashboard(summary: dict) -> str:
    return render_template("analytics.html", summary=summary)


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
            "staticBuild": os.environ.get("WORDSPRINT_STATIC_EXPORT") == "1",
            **game_data,
        },
    )


def create_app() -> Flask:
    ensure_analytics_db()

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

    def authorize_analytics():
        if not check_basic_auth(request.headers.get("Authorization")):
            return analytics_unauthorized_response(), None
        return None, get_analytics_summary()

    @app.route("/analytics")
    def analytics_dashboard():
        unauthorized, summary = authorize_analytics()
        if unauthorized is not None:
            return unauthorized
        return render_analytics_dashboard(summary)

    @app.route("/analytics-summary")
    def analytics_summary():
        unauthorized, summary = authorize_analytics()
        if unauthorized is not None:
            return unauthorized
        return jsonify(summary)

    @app.route("/profile-name", methods=["POST"])
    def profile_name():
        payload = request.get_json(silent=True) or {}
        client_id = str(payload.get("clientId", "")).strip()
        display_name = normalize_display_name(str(payload.get("displayName", "")))
        lang = str(payload.get("lang", "")).strip() or None

        if not client_id or len(client_id) > 100:
            return jsonify({"ok": False, "error": "invalid_client"}), 400
        if not display_name:
            return jsonify({"ok": False, "error": "invalid_name"}), 400

        upsert_player_profile(client_id, display_name, lang)
        return jsonify({"ok": True}), 200

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
