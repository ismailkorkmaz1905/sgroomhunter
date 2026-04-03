#!/usr/bin/env python3
"""
Facebook room listing monitor with Telegram approval and WhatsApp outreach.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import requests

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MESSAGE_TEMPLATE = (
    "Hi, I'm Ismail, a Turkish consultant on an Employment Pass. "
    "I usually live alone, but my girlfriend may occasionally stay over on some "
    "weekends. I cook proper meals regularly, so I'm looking for a place where "
    "normal cooking and occasional overnight guests are clearly allowed. "
    "I'm interested in a 1-year lease starting in late April or on 1 May.\n\n"
    "Listing: {listing_url}\n\n"
    "Please let me know if this arrangement works for you. Thank you."
)

DEFAULT_STATE = {
    "seen_listing_ids": [],
    "pending_listing_ids": [],
    "pending_candidates": {},
    "approved_listing_ids": [],
    "rejected_listing_ids": [],
    "telegram_update_offset": 0,
}

MONEY_RE = re.compile(r"(?:S?\$)\s?([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+?65[\s-]*)?([89]\d{3}[\s-]*\d{4}))")


@dataclass
class FacebookListingDetails:
    listing_id: str
    url: str
    source_group: str
    query: str
    title: str
    headline: str
    description: str
    posted_unix: int
    posted_text: str
    price: int
    price_pretty: str
    street_name: str
    district_text: str
    property_type: str
    studio_or_room_text: str
    bedrooms: int | None
    bathrooms: int | None
    floor_area_text: str
    room_type: str
    cooking_type: str
    visitors_allowed: str
    tenant_gender: str
    max_tenants: str
    owner_stays: str
    furnishing_text: str
    agent_name: str
    agent_phone: str
    agent_phone_pretty: str
    agency_name: str
    detail_values: list[str]
    allow_flags: list[str]
    risk_flags: list[str]
    reject_reasons: list[str]


def default_config_path() -> Path:
    local_path = BASE_DIR / "facebook_monitor_config.local.json"
    if local_path.exists():
        return local_path
    return BASE_DIR / "facebook_monitor_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor Facebook room listings and route approvals via Telegram."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("scan-once", "run-once", "run"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--config", default=str(default_config_path()))
        sub.add_argument("--top", type=int, default=5)
    return parser.parse_args()


def now_utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return json.loads(json.dumps(default))
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def load_config(path: Path) -> dict[str, Any]:
    return load_json(
        path,
        {
            "group_urls": ["https://www.facebook.com/groups/125221981227101/"],
            "search_terms": [
                "master room ensuite",
                "master bedroom ensuite",
                "master room attached bathroom",
                "master room private bathroom",
                "visitors allowed cooking allowed master room",
            ],
            "cookies_file": "fb_cookies.json",
            "raw_output_file": "raw_posts.json",
            "message_template_file": "facebook_outreach_template.txt",
            "state_file": ".facebook_monitor_state.json",
            "poll_interval_seconds": 1800,
            "scroll_rounds": 12,
            "navigation_timeout_ms": 90000,
            "min_text_length": 80,
            "min_price": 0,
            "max_price": 2000,
            "max_age_days": 14,
            "require_room_rental": True,
            "require_master_room": True,
            "require_attached_bathroom": True,
            "require_visitors_allowed": True,
            "require_cooking_allowed": True,
            "private_bathroom_keywords": [
                "master",
                "master room",
                "masterbedroom",
                "master bedroom",
                "ensuite",
                "en suite",
                "attached bath",
                "attached bathroom",
                "attached toilet",
                "private bathroom",
                "own bathroom",
            ],
            "banned_keywords": [
                "common room",
                "shared bath",
                "shared bathroom",
                "light cooking",
                "no cooking",
                "boiling only",
                "microwave only",
                "no visitors",
                "visitors not allowed",
                "no overnight",
                "female only",
                "male only",
                "owner stays",
                "staying with owner",
                "landlord stays",
                "prefer non-china tenant",
                "no wet kitchen",
            ],
            "east_areas": [
                "Eunos",
                "Kembangan",
                "Bedok",
                "Paya Lebar",
                "Simei",
                "Tampines",
                "Pasir Ris",
                "Geylang",
                "Kallang",
                "Katong",
                "Marine Parade",
                "Siglap",
                "Tanah Merah",
                "MacPherson",
                "Dakota",
                "Mountbatten",
                "Expo",
                "Changi",
            ],
            "notify_rejections": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "send_mode": "preview",
            "post_send_wait_seconds": 12,
            "browser_headless": True,
            "browser_channel": "msedge",
            "browser_launch_args": [],
            "profile_dir": ".playwright-profile/facebook-helper",
            "chrome_executable": "chrome.exe",
            "log_file": "facebook_monitor.log",
            "log_level": "INFO",
        },
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def stable_listing_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return str(int(digest[:16], 16))


def normalize_fb_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        keep_keys = {"story_fbid", "fbid", "multi_permalinks"}
        filtered_query = [(key, value) for key, value in query_pairs if key in keep_keys]
        query = urlencode(filtered_query)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
    except Exception:
        return url


def absolutize_and_clean(page, href: str) -> str:
    try:
        absolute = page.evaluate("h => new URL(h, location.href).toString()", href)
        return normalize_fb_url(absolute)
    except Exception:
        return normalize_fb_url(href)


def safe_click(locator) -> bool:
    try:
        locator.evaluate("node => node.click()")
        return True
    except Exception:
        return False


def expand_see_more_in_container(container) -> None:
    for text in ("Daha fazlasını gör", "Daha fazla", "See more", "See More"):
        try:
            button = container.get_by_text(text, exact=False)
            if button.count() > 0:
                safe_click(button.first)
                time.sleep(0.2)
        except Exception:
            continue


def get_meta(page, prop: str) -> str:
    try:
        locator = page.locator(f'meta[property="{prop}"]').first
        if locator.count() == 0:
            return ""
        return normalize_text(locator.get_attribute("content") or "")
    except Exception:
        return ""


def extract_listing_text(page) -> str:
    try:
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass
    time.sleep(1.0)
    combined = normalize_text(f"{get_meta(page, 'og:title')} {get_meta(page, 'og:description')}")
    if combined:
        return combined
    try:
        main = page.locator('div[role="main"]').first
        if main.count() > 0:
            expand_see_more_in_container(main)
            return normalize_text(main.inner_text() or "")
    except Exception:
        return ""
    return ""


def extract_post_text(page) -> str:
    try:
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass
    time.sleep(1.0)
    expand_see_more_in_container(page)
    try:
        msg = page.locator('div[data-ad-preview="message"]').first
        if msg.count() > 0:
            expand_see_more_in_container(msg)
            text = normalize_text(msg.inner_text() or "")
            if text:
                return text
    except Exception:
        pass
    try:
        main = page.locator('div[role="main"]').first
        if main.count() > 0:
            expand_see_more_in_container(main)
            return normalize_text(main.inner_text() or "")
    except Exception:
        return ""
    return ""


def extract_text_for_link(page, url: str) -> str:
    lower = url.lower()
    if "/commerce/listing/" in lower or "/marketplace/item/" in lower:
        return extract_listing_text(page)
    return extract_post_text(page)


def find_search_box(page):
    for selector in (
        "input[placeholder*='Search']",
        "input[aria-label*='Search']",
        "input[type='search']",
    ):
        try:
            element = page.query_selector(selector)
            if element:
                return element
        except Exception:
            continue
    return None


def _normalize_samesite(value: Any) -> str:
    if value is None:
        return "Lax"
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower == "strict":
            return "Strict"
        if lower in {"none", "no_restriction"}:
            return "None"
    return "Lax"


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return default


def load_cookies_into_context(context, cookies_path: Path) -> None:
    raw = json.loads(cookies_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("cookies"), list):
        raw_list = raw["cookies"]
    elif isinstance(raw, list):
        raw_list = raw
    else:
        raise ValueError("Cookie JSON must be a list or {'cookies': [...]} .")
    cookies = []
    for cookie in raw_list:
        if not isinstance(cookie, dict):
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        domain = cookie.get("domain") or cookie.get("host")
        path = cookie.get("path") or "/"
        expires = cookie.get("expires")
        if expires is None:
            expires = cookie.get("expirationDate")
        if isinstance(expires, str):
            try:
                expires = float(expires)
            except Exception:
                expires = None
        if not (name and value and domain):
            continue
        item = {
            "name": str(name),
            "value": str(value),
            "domain": str(domain),
            "path": str(path),
            "httpOnly": _as_bool(cookie.get("httpOnly"), False),
            "secure": _as_bool(cookie.get("secure"), True),
            "sameSite": _normalize_samesite(cookie.get("sameSite")),
        }
        if isinstance(expires, (int, float)):
            item["expires"] = expires
        cookies.append(item)
    if not cookies:
        raise ValueError("Could not normalize any Facebook cookies.")
    context.add_cookies(cookies)


def extract_rent(text: str) -> int:
    match = MONEY_RE.search(text or "")
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return 0


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D+", "", value)
    if digits.startswith("65") and len(digits) == 10:
        return digits
    if len(digits) == 8:
        return f"65{digits}"
    return digits


def extract_phone(text: str) -> tuple[str, str]:
    match = PHONE_RE.search(text or "")
    if not match:
        return "", ""
    pretty = re.sub(r"\s+", " ", match.group(0)).strip()
    return normalize_phone(pretty), pretty


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def infer_allowed(text: str, allow_patterns: list[str], deny_patterns: list[str]) -> str:
    if has_any(text, deny_patterns):
        return "no"
    if has_any(text, allow_patterns):
        return "yes"
    return ""


def location_hit(text: str, east_areas: list[str]) -> str:
    for area in east_areas:
        if re.search(rf"\b{re.escape(area)}\b", text, re.IGNORECASE):
            return area
    return ""


def derive_listing_id(url: str, text: str) -> str:
    if url:
        slug = normalize_fb_url(url)
    else:
        slug = normalize_text(text)[:80]
    return stable_listing_id(slug)


def migrate_state_listing_ids(state: dict[str, Any]) -> bool:
    pending_candidates = state.get("pending_candidates", {})
    if not isinstance(pending_candidates, dict) or not pending_candidates:
        return False
    changed = False
    migrated_pending: dict[str, dict[str, Any]] = {}
    migrated_pending_ids: list[str] = []
    for old_id, payload in pending_candidates.items():
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        url = str(details.get("url", "") or "")
        text = " ".join(
            str(part)
            for part in (
                details.get("title", ""),
                details.get("headline", ""),
                details.get("description", ""),
            )
            if part
        )
        new_id = derive_listing_id(url, text) if (url or text) else str(old_id)
        if new_id != str(old_id):
            changed = True
        if isinstance(details, dict):
            details["listing_id"] = new_id
        migrated_pending[new_id] = payload
        if new_id not in migrated_pending_ids:
            migrated_pending_ids.append(new_id)
    if changed:
        state["pending_candidates"] = migrated_pending
        state["pending_listing_ids"] = migrated_pending_ids
    return changed


def collect_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower_text = text.lower()
    hits = [keyword for keyword in keywords if keyword.lower() in lower_text]
    return sorted(set(hits))


def is_listing_like_url(url: str) -> bool:
    lower = url.lower()
    return any(
        token in lower
        for token in (
            "/commerce/listing/",
            "/marketplace/item/",
            "/posts/",
            "/permalink/",
            "story_fbid=",
            "multi_permalinks",
        )
    )


def collect_posts(config: dict[str, Any]) -> list[dict[str, Any]]:
    if not sync_playwright:
        raise RuntimeError("Playwright is not installed.")
    cookies_file = resolve_path(config["cookies_file"])
    raw_output_file = resolve_path(config["raw_output_file"])
    group_urls = config.get("group_urls", [])
    search_terms = config.get("search_terms", [])
    scroll_rounds = int(config.get("scroll_rounds", 12))
    timeout_ms = int(config.get("navigation_timeout_ms", 90000))
    min_text_length = int(config.get("min_text_length", 80))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=config.get("browser_channel", "msedge"),
            headless=bool(config.get("browser_headless", True)),
            args=list(config.get("browser_launch_args", [])),
        )
        context = browser.new_context()
        page = context.new_page()
        page.goto("about:blank")
        load_cookies_into_context(context, cookies_file)
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        time.sleep(3)
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for group_url in group_urls:
            logging.info("Scanning Facebook group %s", group_url)
            group_start_count = len(results)
            page.goto(group_url, wait_until="domcontentloaded", timeout=timeout_ms)
            time.sleep(5)
            for _ in range(scroll_rounds):
                try:
                    page.mouse.wheel(0, 1800)
                except Exception:
                    break
                time.sleep(1.5)
            anchors = page.query_selector_all(
                "a[href*='/commerce/listing/'], "
                "a[href*='/marketplace/item/'], "
                "a[href*='/posts/'], "
                "a[href*='permalink'], "
                "a[href*='story_fbid='], "
                "a[href*='multi_permalinks']"
            )
            logging.info("Facebook group %s surfaced %s candidate anchors", group_url, len(anchors))
            for anchor in anchors[:300]:
                href = anchor.get_attribute("href") or ""
                if not href:
                    continue
                url = absolutize_and_clean(page, href)
                if not url or url in seen_urls or not is_listing_like_url(url):
                    continue
                detail_page = context.new_page()
                try:
                    detail_page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    text = normalize_text(extract_text_for_link(detail_page, url))
                except Exception as exc:
                    logging.debug("Facebook detail fetch failed for %s: %s", url, exc)
                    text = ""
                finally:
                    detail_page.close()
                if len(text) < min_text_length:
                    continue
                seen_urls.add(url)
                results.append(
                    {
                        "group": group_url,
                        "query": ",".join(search_terms),
                        "url": url,
                        "text": text,
                        "ts": now_utc_ts(),
                    }
                )
            logging.info(
                "Facebook group %s collected %s new candidate links (total=%s)",
                group_url,
                len(results) - group_start_count,
                len(results),
            )
        raw_output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info("Facebook scrape wrote %s raw posts to %s", len(results), raw_output_file)
        context.close()
        browser.close()
    return results


def build_listing_details(item: dict[str, Any], config: dict[str, Any]) -> FacebookListingDetails:
    text = normalize_text(item.get("text", ""))
    lower_text = text.lower()
    rent = extract_rent(text)
    phone, phone_pretty = extract_phone(text)
    location = location_hit(text, list(config.get("east_areas", [])))
    is_master = has_any(text, [r"\bmaster\s+room\b", r"\bmaster\s+bed(room)?\b", r"\bmasterbed(room)?\b"])
    has_private_bath = has_any(
        text,
        [
            r"\b(en[-\s]?suite)\b",
            r"\battached\s+bath(room)?\b",
            r"\bprivate\s+bath(room)?\b",
            r"\bown\s+bath(room)?\b",
        ],
    )
    visitors_allowed = infer_allowed(
        text,
        [r"\bvisitors?\s+allowed\b", r"\bguests?\s+allowed\b", r"\bovernight\s+guests?\s+allowed\b"],
        [r"\bno\s+visitors\b", r"\bno\s+guests?\b", r"\bvisitors?\s+not\s+allowed\b", r"\bno\s+overnight\b"],
    )
    cooking_allowed = infer_allowed(
        text,
        [r"\bcooking\s+allowed\b", r"\bnormal\s+cooking\b", r"\bfull\s+cooking\b", r"\bcan\s+cook\b"],
        [r"\blight\s+cooking\b", r"\bno\s+cooking\b", r"\bboiling\s+only\b", r"\bmicrowave\s+only\b"],
    )
    owner_stays = "True" if has_any(text, [r"\bowner\s+stays\b", r"\bstaying\s+with\s+owner\b", r"\blandlord\s+stays\b"]) else ""
    tenant_gender = ""
    if has_any(text, [r"\bfemale\s+only\b", r"\bladies\s+only\b"]):
        tenant_gender = "female"
    elif has_any(text, [r"\bmale\s+only\b"]):
        tenant_gender = "male"
    detail_values = [part.strip() for part in re.split(r"[.!?•]+", text) if part.strip()]
    allow_flags = collect_keyword_hits(
        lower_text,
        [
            "visitors allowed",
            "guests allowed",
            "normal cooking",
            "full cooking",
            "cooking allowed",
            "private bathroom",
            "attached bathroom",
            "ensuite",
            "master room",
            "no landlord",
            "no agent fee",
        ],
    )
    risk_flags = collect_keyword_hits(
        lower_text,
        [
            "common room",
            "shared bath",
            "light cooking",
            "no cooking",
            "no visitors",
            "owner stays",
            "staying with owner",
            "female only",
            "male only",
        ],
    )
    title = text[:120]
    price_pretty = f"S$ {rent:,} /mo" if rent else ""
    room_type = "master" if is_master else "common" if "common room" in lower_text else ""
    return FacebookListingDetails(
        listing_id=derive_listing_id(item.get("url", ""), text),
        url=item.get("url", ""),
        source_group=item.get("group", ""),
        query=item.get("query", ""),
        title=title,
        headline=title,
        description=text,
        posted_unix=int(item.get("ts") or 0),
        posted_text="Facebook scrape",
        price=rent,
        price_pretty=price_pretty,
        street_name="",
        district_text=location,
        property_type="Room rental" if "room" in lower_text else "",
        studio_or_room_text="Room" if "room" in lower_text else "",
        bedrooms=1 if is_master else None,
        bathrooms=1 if has_private_bath else None,
        floor_area_text="",
        room_type=room_type,
        cooking_type="all" if cooking_allowed == "yes" else "light" if "light cooking" in lower_text else "none" if cooking_allowed == "no" else "",
        visitors_allowed=visitors_allowed,
        tenant_gender=tenant_gender,
        max_tenants="",
        owner_stays=owner_stays,
        furnishing_text="",
        agent_name="",
        agent_phone=phone,
        agent_phone_pretty=phone_pretty,
        agency_name="Facebook",
        detail_values=detail_values,
        allow_flags=allow_flags,
        risk_flags=risk_flags,
        reject_reasons=[],
    )


def listing_passes_filters(details: FacebookListingDetails, config: dict[str, Any]) -> bool:
    details.reject_reasons.clear()
    if details.price and details.price < int(config.get("min_price", 0)):
        details.reject_reasons.append("price_below_limit")
    if details.price and details.price > int(config.get("max_price", 0)):
        details.reject_reasons.append("price_above_limit")
    max_age_seconds = int(config.get("max_age_days", 14)) * 86400
    if details.posted_unix and now_utc_ts() - details.posted_unix > max_age_seconds:
        details.reject_reasons.append("listing_too_old")
    if config.get("require_room_rental") and "room" not in details.studio_or_room_text.lower():
        details.reject_reasons.append("not_room_rental")
    if config.get("require_master_room") and details.room_type != "master":
        details.reject_reasons.append("not_master_room")
    if config.get("require_attached_bathroom"):
        combined = " ".join([details.title, details.headline, details.description, " ".join(details.detail_values)]).lower()
        private_keywords = [kw.lower() for kw in config.get("private_bathroom_keywords", [])]
        if not any(keyword in combined for keyword in private_keywords):
            details.reject_reasons.append("private_bathroom_not_clear")
    if config.get("require_visitors_allowed") and details.visitors_allowed != "yes":
        details.reject_reasons.append("visitors_not_clearly_allowed")
    if config.get("require_cooking_allowed") and details.cooking_type != "all":
        details.reject_reasons.append("cooking_not_clearly_allowed")
    combined = " ".join(
        [
            details.title,
            details.headline,
            details.description,
            " ".join(details.detail_values),
            details.room_type,
            details.cooking_type,
            details.visitors_allowed,
            details.tenant_gender,
            details.owner_stays,
        ]
    ).lower()
    for keyword in config.get("banned_keywords", []):
        if keyword.lower() in combined:
            details.reject_reasons.append(f"banned:{keyword}")
    details.reject_reasons[:] = list(dict.fromkeys(details.reject_reasons))
    return not details.reject_reasons


def build_outreach_message(details: FacebookListingDetails, template: str) -> str:
    values = {
        "agent_name": details.agent_name or "there",
        "listing_title": details.title or "your listing",
        "headline": details.headline or "",
        "district": details.district_text or "",
        "street_name": details.street_name or "",
        "price": details.price_pretty or "",
        "listing_url": details.url,
        "posted_text": details.posted_text or "",
        "property_type": details.property_type or "",
    }
    return template.format_map(values)


def format_listing_summary(details: FacebookListingDetails) -> str:
    lines = [
        f"{details.title} - {details.price_pretty or 'price unknown'}",
        f"Area: {details.district_text or 'unknown'}",
        f"Phone: {details.agent_phone_pretty or details.agent_phone or 'unknown'}",
        f"Source group: {details.source_group or 'unknown'}",
        f"URL: {details.url}",
    ]
    if details.allow_flags:
        lines.append("Positive signals: " + ", ".join(details.allow_flags))
    if details.risk_flags:
        lines.append("Risk signals: " + ", ".join(details.risk_flags))
    if details.reject_reasons:
        lines.append("Rejected by filter: " + ", ".join(details.reject_reasons))
    return "\n".join(lines)


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = str(chat_id) if chat_id else ""
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        self.session.trust_env = False

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str, inline_keyboard: list[list[dict[str, str]]] | None = None) -> None:
        if not self.enabled:
            return
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if inline_keyboard:
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
        try:
            response = self.session.post(f"{self.base_url}/sendMessage", json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            logging.exception("Telegram sendMessage failed.")

    def get_updates(self, offset: int) -> tuple[int, list[dict[str, Any]]]:
        if not self.enabled:
            return offset, []
        response = self.session.get(
            f"{self.base_url}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("result", [])
        new_offset = offset
        if results:
            new_offset = max(update["update_id"] for update in results) + 1
        return new_offset, results

    def answer_callback(self, callback_query_id: str, text: str) -> None:
        if not self.enabled:
            return
        try:
            self.session.post(
                f"{self.base_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
                timeout=30,
            )
        except requests.RequestException:
            logging.exception("Telegram answerCallbackQuery failed.")


def open_whatsapp_preview(details: FacebookListingDetails, message: str, config: dict[str, Any]) -> str:
    if not details.agent_phone:
        return f"No phone number found for {details.listing_id}; cannot open WhatsApp preview."
    url = f"https://web.whatsapp.com/send?phone={details.agent_phone}&text={quote(message)}"
    chrome_executable = config.get("chrome_executable", "chrome.exe")
    try:
        subprocess.Popen([chrome_executable, url])
    except FileNotFoundError:
        opened = webbrowser.open(url)
        if not opened:
            subprocess.Popen(["powershell", "-Command", f"Start-Process '{url}'"])
    return f"Opened WhatsApp preview for {details.listing_id}."


def handle_approval(listing_id: str, state: dict[str, Any], telegram: TelegramClient, config: dict[str, Any]) -> None:
    payload = state.get("pending_candidates", {}).get(listing_id)
    if not payload:
        telegram.send_message(f"Listing {listing_id} is not pending anymore.")
        return
    details = FacebookListingDetails(**payload["details"])
    message = payload["message"]
    try:
        result = open_whatsapp_preview(details, message, config)
    except Exception as exc:
        telegram.send_message(f"Approve failed for {listing_id}: {exc}")
        return
    state["pending_listing_ids"] = [item for item in state["pending_listing_ids"] if item != listing_id]
    state.get("pending_candidates", {}).pop(listing_id, None)
    if listing_id not in state["approved_listing_ids"]:
        state["approved_listing_ids"].append(listing_id)
    telegram.send_message(result)


def handle_rejection(listing_id: str, state: dict[str, Any], telegram: TelegramClient) -> None:
    pending = state.get("pending_candidates", {})
    if listing_id in pending:
        state["pending_listing_ids"] = [item for item in state["pending_listing_ids"] if item != listing_id]
        state.get("pending_candidates", {}).pop(listing_id, None)
        if listing_id not in state["rejected_listing_ids"]:
            state["rejected_listing_ids"].append(listing_id)
        telegram.send_message(f"Rejected listing {listing_id}.")
    else:
        telegram.send_message(f"Listing {listing_id} is not pending anymore.")


def process_telegram_updates(state: dict[str, Any], telegram: TelegramClient, config: dict[str, Any]) -> None:
    offset = int(state.get("telegram_update_offset", 0))
    try:
        new_offset, updates = telegram.get_updates(offset)
    except requests.RequestException:
        logging.exception("Telegram getUpdates failed; continuing without approval sync.")
        return
    state["telegram_update_offset"] = new_offset
    for update in updates:
        callback = update.get("callback_query")
        if not callback:
            continue
        data = callback.get("data", "")
        callback_id = callback.get("id", "")
        if data.startswith("approve:"):
            listing_id = data.split(":", 1)[1]
            telegram.answer_callback(callback_id, "Approved")
            handle_approval(listing_id, state, telegram, config)
        elif data.startswith("reject:"):
            listing_id = data.split(":", 1)[1]
            telegram.answer_callback(callback_id, "Rejected")
            handle_rejection(listing_id, state, telegram)


def shortlist_candidates(config: dict[str, Any], state: dict[str, Any], template: str) -> tuple[list[FacebookListingDetails], dict[str, dict[str, Any]], list[FacebookListingDetails]]:
    pending_lookup: dict[str, dict[str, Any]] = {}
    shortlisted: list[FacebookListingDetails] = []
    rejected: list[FacebookListingDetails] = []
    seen_ids = set(state.get("seen_listing_ids", []))
    blocked_ids = set(state.get("approved_listing_ids", [])) | set(state.get("rejected_listing_ids", []))
    for item in collect_posts(config):
        details = build_listing_details(item, config)
        if details.listing_id in blocked_ids:
            continue
        if details.listing_id in seen_ids and details.listing_id not in state.get("pending_listing_ids", []):
            continue
        if not listing_passes_filters(details, config):
            rejected.append(details)
            seen_ids.add(details.listing_id)
            continue
        message = build_outreach_message(details, template)
        shortlisted.append(details)
        pending_lookup[details.listing_id] = {"details": asdict(details), "message": message}
        seen_ids.add(details.listing_id)
    state["seen_listing_ids"] = sorted(seen_ids)
    logging.info(
        "Facebook shortlist finished: shortlisted=%s rejected=%s seen=%s pending=%s",
        len(shortlisted),
        len(rejected),
        len(state["seen_listing_ids"]),
        len(state.get("pending_listing_ids", [])),
    )
    return shortlisted, pending_lookup, rejected


def send_rejected_candidates_to_telegram(candidates: list[FacebookListingDetails], template: str, state: dict[str, Any], telegram: TelegramClient, config: dict[str, Any]) -> None:
    if not telegram.enabled or not config.get("notify_rejections", True):
        return
    pending_ids = set(state.get("pending_listing_ids", []))
    pending_candidates = state.setdefault("pending_candidates", {})
    for details in candidates:
        if details.listing_id in pending_ids:
            continue
        message = build_outreach_message(details, template)
        pending_candidates[details.listing_id] = {"details": asdict(details), "message": message}
        text = (
            "Rejected Facebook listing\n\n"
            f"{format_listing_summary(details)}\n\n"
            "Draft message:\n"
            f"{message}"
        )
        keyboard = [[
            {"text": "Approve", "callback_data": f"approve:{details.listing_id}"},
            {"text": "Reject", "callback_data": f"reject:{details.listing_id}"},
        ]]
        telegram.send_message(text, inline_keyboard=keyboard)
        state["pending_listing_ids"].append(details.listing_id)


def send_new_candidates_to_telegram(candidates: list[FacebookListingDetails], pending_lookup: dict[str, dict[str, Any]], state: dict[str, Any], telegram: TelegramClient) -> None:
    pending_ids = set(state.get("pending_listing_ids", []))
    pending_candidates = state.setdefault("pending_candidates", {})
    for details in candidates:
        if details.listing_id in pending_ids:
            continue
        payload = pending_lookup[details.listing_id]
        pending_candidates[details.listing_id] = payload
        text = (
            "New Facebook room match\n\n"
            f"{format_listing_summary(details)}\n\n"
            "Draft message:\n"
            f"{payload['message']}"
        )
        keyboard = [[
            {"text": "Approve", "callback_data": f"approve:{details.listing_id}"},
            {"text": "Reject", "callback_data": f"reject:{details.listing_id}"},
        ]]
        telegram.send_message(text, inline_keyboard=keyboard)
        state["pending_listing_ids"].append(details.listing_id)


def load_template(path: Path) -> str:
    if not path.exists():
        path.write_text(DEFAULT_MESSAGE_TEMPLATE, encoding="utf-8")
        return DEFAULT_MESSAGE_TEMPLATE
    content = path.read_text(encoding="utf-8").strip()
    return content or DEFAULT_MESSAGE_TEMPLATE


def print_scan_results(candidates: list[FacebookListingDetails], top: int) -> None:
    if not candidates:
        print("No Facebook listings matched the current filters.")
        return
    for index, details in enumerate(candidates[:top], start=1):
        print(f"\n[{index}] {format_listing_summary(details)}")


def run_scan_once(config: dict[str, Any], top: int) -> int:
    state = load_json(resolve_path(config["state_file"]), DEFAULT_STATE)
    migrate_state_listing_ids(state)
    template = load_template(resolve_path(config["message_template_file"]))
    candidates, _, _ = shortlist_candidates(config, state, template)
    print_scan_results(candidates, top)
    return 0


def run_monitor_cycle(config: dict[str, Any]) -> int:
    state_path = resolve_path(config["state_file"])
    state = load_json(state_path, DEFAULT_STATE)
    if migrate_state_listing_ids(state):
        save_json(state_path, state)
    template = load_template(resolve_path(config["message_template_file"]))
    telegram = TelegramClient(config.get("telegram_bot_token", ""), str(config.get("telegram_chat_id", "")))
    if telegram.enabled:
        process_telegram_updates(state, telegram, config)
        save_json(state_path, state)
    candidates, pending_lookup, rejected = shortlist_candidates(config, state, template)
    save_json(state_path, state)
    if telegram.enabled:
        send_rejected_candidates_to_telegram(rejected, template, state, telegram, config)
        send_new_candidates_to_telegram(candidates, pending_lookup, state, telegram)
        save_json(state_path, state)
    else:
        print_scan_results(candidates, top=5)
    return 0


def run_loop(config: dict[str, Any]) -> int:
    logging.info("Starting Facebook monitor loop.")
    while True:
        try:
            run_monitor_cycle(config)
        except Exception:
            logging.exception("Facebook monitor cycle failed.")
        time.sleep(int(config.get("poll_interval_seconds", 1800)))


def main() -> int:
    args = parse_args()
    config = load_config(resolve_path(args.config))
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    # Keep a persistent log by default even when the local override omits log_file.
    log_file = str(config.get("log_file", "facebook_monitor.log") or "facebook_monitor.log").strip()
    if log_file:
        handlers.append(logging.FileHandler(resolve_path(log_file), encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, str(config.get("log_level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )
    if args.command == "scan-once":
        return run_scan_once(config, args.top)
    if args.command == "run-once":
        return run_monitor_cycle(config)
    if args.command == "run":
        return run_loop(config)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
