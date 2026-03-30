from __future__ import annotations

import json
import os
import sqlite3
from base64 import b64decode
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, redirect, render_template, render_template_string, request, send_from_directory, url_for


BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGUAGES = {"en", "tr", "nl", "id", "ms"}
SUPPORTED_PAGES = {"home", "daily-ladder", "word-scramble", "typo-hunt", "word-chain", "category-blitz", "privacy", "about", "terms"}
ANALYTICS_DB = BASE_DIR / "analytics.sqlite3"


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
    "en": load_json("data", "words", "en", "common.json"),
    "tr": load_json("data", "words", "tr", "common.json"),
    "nl": load_json("data", "words", "nl", "common.json"),
    "id": load_json("data", "words", "id", "common.json"),
    "ms": load_json("data", "words", "ms", "common.json"),
}

TYPOS = {
    "en": load_json("data", "typos", "en.json"),
    "tr": load_json("data", "typos", "tr.json"),
    "nl": load_json("data", "typos", "nl.json"),
    "id": load_json("data", "typos", "id.json"),
    "ms": load_json("data", "typos", "ms.json"),
}

LADDERS = {
    "en": load_json("data", "ladders", "en.json"),
    "tr": load_json("data", "ladders", "tr.json"),
    "nl": load_json("data", "ladders", "nl.json"),
    "id": load_json("data", "ladders", "id.json"),
    "ms": load_json("data", "ladders", "ms.json"),
}

CHAINS = {
    "en": load_json("data", "chains", "en.json"),
    "tr": load_json("data", "chains", "tr.json"),
    "nl": load_json("data", "chains", "nl.json"),
    "id": load_json("data", "chains", "id.json"),
    "ms": load_json("data", "chains", "ms.json"),
}

CATEGORIES = {
    "en": load_json("data", "categories", "en.json"),
    "tr": load_json("data", "categories", "tr.json"),
    "nl": load_json("data", "categories", "nl.json"),
    "id": load_json("data", "categories", "id.json"),
    "ms": load_json("data", "categories", "ms.json"),
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
        "recent_names": [dict(row) for row in recent_names],
    }


def normalize_display_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned[:40]


def upsert_player_profile(client_id: str, display_name: str, lang: str | None) -> None:
    ensure_analytics_db()
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
    return (
        username == os.environ.get("ANALYTICS_USERNAME")
        and password == os.environ.get("ANALYTICS_PASSWORD")
    )


def analytics_unauthorized_response() -> Response:
    return Response(
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="WordGames Analytics"'},
    )


def render_analytics_dashboard(summary: dict) -> str:
    template = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>WordGames Analytics</title>
      <style>
        :root {
          --bg: #f6f2ea;
          --ink: #1d2433;
          --muted: #5e6677;
          --surface: #fffdf9;
          --line: rgba(30, 36, 51, 0.12);
          --accent: #1f7a6b;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "Segoe UI", sans-serif;
          color: var(--ink);
          background: linear-gradient(180deg, #faf6ef 0%, #edf1f7 100%);
        }
        .wrap {
          width: min(1120px, calc(100% - 24px));
          margin: 0 auto;
          padding: 24px 0 48px;
        }
        .hero, .panel {
          background: rgba(255,255,255,0.86);
          border: 1px solid var(--line);
          border-radius: 24px;
          padding: 22px;
          box-shadow: 0 18px 45px rgba(33, 36, 48, 0.08);
          backdrop-filter: blur(6px);
        }
        .hero { margin-bottom: 16px; }
        .eyebrow {
          margin: 0 0 8px;
          color: var(--accent);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }
        h1, h2 { margin: 0; }
        .hero p, .panel p, li {
          color: var(--muted);
          line-height: 1.6;
        }
        .metrics {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin-top: 18px;
        }
        .metric {
          background: var(--surface);
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 16px;
        }
        .metric span {
          display: block;
          margin-bottom: 8px;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 12px;
          font-weight: 700;
        }
        .metric strong { font-size: 28px; }
        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-top: 16px;
        }
        ul {
          margin: 16px 0 0;
          padding-left: 18px;
        }
        li + li { margin-top: 10px; }
        .hint {
          margin-top: 16px;
          font-size: 14px;
        }
        @media (max-width: 820px) {
          .metrics, .grid { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <section class="hero">
          <p class="eyebrow">Private analytics</p>
          <h1>WordGames dashboard</h1>
          <p>This page shows privacy-friendly aggregate usage only. No raw IP addresses, no analytics cookies, and no fingerprinting.</p>
          <div class="metrics">
            <div class="metric"><span>Visits</span><strong>{{ summary.totals.visits }}</strong></div>
            <div class="metric"><span>Window</span><strong>{{ summary.days }}d</strong></div>
            <div class="metric"><span>Privacy</span><strong>{{ summary.privacy_mode }}</strong></div>
            <div class="metric"><span>Top route</span><strong>{{ summary.by_path[0].path if summary.by_path else "-" }}</strong></div>
          </div>
        </section>
        <section class="grid">
          <article class="panel">
            <h2>Top routes</h2>
            <ul>
              {% for row in summary.by_path %}
              <li><strong>{{ row.path }}</strong> — {{ row.visits }} visits</li>
              {% else %}
              <li>No data yet.</li>
              {% endfor %}
            </ul>
          </article>
          <article class="panel">
            <h2>Languages</h2>
            <ul>
              {% for row in summary.by_language %}
              <li><strong>{{ row.lang }}</strong> — {{ row.visits }} visits</li>
              {% else %}
              <li>No data yet.</li>
              {% endfor %}
            </ul>
          </article>
          <article class="panel">
            <h2>Devices</h2>
            <ul>
              {% for row in summary.by_device %}
              <li><strong>{{ row.device_type }}</strong> — {{ row.visits }} visits</li>
              {% else %}
              <li>No data yet.</li>
              {% endfor %}
            </ul>
          </article>
          <article class="panel">
            <h2>Browsers</h2>
            <ul>
              {% for row in summary.by_browser %}
              <li><strong>{{ row.browser_family }}</strong> — {{ row.visits }} visits</li>
              {% else %}
              <li>No data yet.</li>
              {% endfor %}
            </ul>
          </article>
          <article class="panel">
            <h2>Recent names</h2>
            <ul>
              {% for row in summary.recent_names %}
              <li><strong>{{ row.display_name }}</strong> — {{ row.lang or "unknown" }}</li>
              {% else %}
              <li>No names submitted yet.</li>
              {% endfor %}
            </ul>
          </article>
        </section>
        <p class="hint">If you still want the raw aggregate JSON for debugging, use <code>/analytics-summary</code>.</p>
      </div>
    </body>
    </html>
    """
    return render_template_string(template, summary=summary)


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
        "privacy": ("privacyTitle", "privacyDescription"),
        "about": ("aboutTitle", "aboutDescription"),
        "terms": ("termsTitle", "termsDescription"),
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
            "chains": CHAINS,
            "categories": CATEGORIES,
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
            for page in ("daily-ladder", "word-scramble", "typo-hunt", "privacy", "about", "terms"):
                urls.append(url_for("localized_page", lang=lang, page=page, _external=True))
            for page in ("word-chain", "category-blitz"):
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
        return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")

    @app.route("/service-worker.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
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
