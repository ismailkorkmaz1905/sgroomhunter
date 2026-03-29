#!/usr/bin/env python3
"""
PropertyGuru listing monitor with Telegram approval and WhatsApp outreach.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import subprocess
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import requests

try:
    import curl_cffi.requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

BASE_DIR = Path(__file__).resolve().parent


def default_config_path() -> Path:
    local_path = BASE_DIR / "propertyguru_monitor_config.local.json"
    if local_path.exists():
        return local_path
    return BASE_DIR / "propertyguru_monitor_config.json"


DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Referer": "https://www.propertyguru.com.sg/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

DEFAULT_MESSAGE_TEMPLATE = (
    "Hi {agent_name}, I’m Ismail, a Turkish consultant on an Employment Pass. "
    "I usually live alone, but my girlfriend may occasionally stay over on some "
    "weekends. I cook proper meals regularly, so I’m looking for a place where "
    "normal cooking and occasional overnight guests are clearly allowed. I’m "
    "interested in a 1-year lease starting in late April or on 1 May.\n\n"
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


@dataclass
class SearchListing:
    listing_id: str
    title: str
    url: str
    price: int
    price_pretty: str
    posted_unix: int
    posted_text: str
    district_text: str
    street_name: str
    property_type: str
    studio_or_room_text: str
    bedrooms: int | None
    bathrooms: int | None
    floor_area_text: str
    agent_name: str
    agency_name: str


@dataclass
class ListingDetails:
    listing_id: str
    url: str
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor PropertyGuru listings and route approvals via Telegram."
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


def build_session():
    if cffi_requests:
        session = cffi_requests.Session(impersonate="chrome124")
    else:
        session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


def ensure_newest_sort(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["sort"] = ["date"]
    query["order"] = ["desc"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def extract_next_data(html_text: str) -> dict[str, Any]:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text)
    if not match:
        raise RuntimeError("Could not find __NEXT_DATA__ in the page HTML.")
    return json.loads(match.group(1))


def strip_html(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\\s+", " ", html.unescape(value)).strip()


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"\\D+", "", value)
    if digits.startswith("65") and len(digits) == 10:
        return digits
    if len(digits) == 8:
        return f"65{digits}"
    return digits


def load_config(path: Path) -> dict[str, Any]:
    return load_json(
        path,
        {
            "search_urls": [
                "https://www.propertyguru.com.sg/property-for-rent/is-near-aljunied-mrt?sort=date&order=desc",
                "https://www.propertyguru.com.sg/property-for-rent/is-near-eunos-mrt?sort=date&order=desc",
                "https://www.propertyguru.com.sg/property-for-rent/is-near-kembangan-mrt?sort=date&order=desc",
                "https://www.propertyguru.com.sg/property-for-rent/is-near-tanah-merah-mrt?sort=date&order=desc",
                "https://www.propertyguru.com.sg/property-for-rent/is-near-marine-parade-mrt?sort=date&order=desc",
                "https://www.propertyguru.com.sg/property-for-rent/is-near-te28-siglap-mrt?sort=date&order=desc"
            ],
            "max_pages_per_search": 3,
            "min_price": 1700,
            "max_price": 2000,
            "max_age_days": 14,
            "require_room_rental": True,
            "require_attached_bathroom": True,
            "require_private_bathroom_keywords": [
                "master",
                "masterbedroom",
                "masterbed room",
                "attached toilet",
                "attached bath",
                "ensuite",
                "private bathroom",
                "attached bathroom",
            ],
            "banned_keywords": [
                "light cooking",
                "microwave only",
                "induction only",
                "boiling only",
                "no cooking",
                "cooking not allowed",
                "visitor until",
                "visitors until",
                "no visitor",
                "no visitors",
                "no overnight",
                "no overnight guest",
                "no overnight stay",
                "female only",
                "male only",
                "common bathroom",
                "shared bathroom",
                "shared bathrooms",
                "bathroom shared",
                "shared with other tenants",
                "worker",
                "workers",
                "shared room",
                "landlord stays",
                "owner stays",
            ],
            "message_template_file": "propertyguru_outreach_template.txt",
            "state_file": ".propertyguru_monitor_state.json",
            "notify_rejections": True,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "poll_interval_seconds": 3600,
            "send_mode": "preview",
            "post_send_wait_seconds": 12,
            "browser_channel": "chrome",
            "profile_dir": ".playwright-profile/propertyguru-helper",
            "chrome_executable": "chrome.exe",
            "log_level": "INFO",
        },
    )


def _find_feature_text(features: list[Any], target: str) -> str:
    for item in features:
        if isinstance(item, list):
            for sub in item:
                if target in (sub.get("dataAutomationId") or ""):
                    return sub.get("text") or ""
        elif isinstance(item, dict):
            if target in (item.get("dataAutomationId") or ""):
                return item.get("text") or ""
    return ""


def build_search_listing(raw: dict[str, Any]) -> SearchListing:
    listing = raw["listingData"]
    return SearchListing(
        listing_id=str(listing["id"]),
        title=listing.get("localizedTitle") or "",
        url=listing.get("url") or "",
        price=int(listing.get("price", {}).get("value") or 0),
        price_pretty=listing.get("price", {}).get("pretty") or "",
        posted_unix=int(listing.get("postedOn", {}).get("unix") or 0),
        posted_text=listing.get("recency", {}).get("text") or "",
        district_text=listing.get("additionalData", {}).get("districtText") or "",
        street_name=listing.get("fullAddress") or "",
        property_type=listing.get("badges", [{}])[-1].get("text", ""),
        studio_or_room_text=_find_feature_text(listing.get("listingFeatures", []), "unit-type"),
        bedrooms=listing.get("bedrooms"),
        bathrooms=listing.get("bathrooms"),
        floor_area_text=(listing.get("area") or {}).get("localeStringValue", ""),
        agent_name=(listing.get("agent") or {}).get("name", ""),
        agency_name=(listing.get("agency") or {}).get("name", ""),
    )


def fetch_search_page(session, url: str) -> dict[str, Any]:
    response = session.get(ensure_newest_sort(url), timeout=30)
    response.raise_for_status()
    return extract_next_data(response.text)


def fetch_search_results(session, config: dict[str, Any]) -> list[SearchListing]:
    results: list[SearchListing] = []
    seen_ids: set[str] = set()
    for base_url in config["search_urls"]:
        next_url = ensure_newest_sort(base_url)
        for _ in range(int(config.get("max_pages_per_search", 1))):
            data = fetch_search_page(session, next_url)
            page_data = data["props"]["pageProps"]["pageData"]["data"]
            for raw in page_data["listingsData"]:
                listing = build_search_listing(raw)
                if listing.listing_id in seen_ids:
                    continue
                seen_ids.add(listing.listing_id)
                results.append(listing)
            pagination = page_data.get("paginationData") or {}
            current_page = int(pagination.get("currentPage") or 1)
            total_pages = int(pagination.get("totalPages") or current_page)
            if current_page >= total_pages:
                break
            parsed = urlparse(next_url)
            query = parse_qs(parsed.query)
            query["page"] = [str(current_page + 1)]
            next_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    results.sort(key=lambda item: item.posted_unix, reverse=True)
    return results


def _extract_detail_posted_text(detail_items: list[str], listing_detail: dict[str, Any]) -> str:
    for value in detail_items:
        if value.lower().startswith("listed on "):
            return value
    dates = listing_detail.get("dates") or {}
    for key in ("formattedLastPosted", "formattedListedDate"):
        if dates.get(key):
            return str(dates[key])
    return ""


def _normalize_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def collect_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower_text = text.lower()
    hits = [keyword for keyword in keywords if keyword.lower() in lower_text]
    return sorted(set(hits))


def fetch_listing_details(session, url: str) -> ListingDetails:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = extract_next_data(response.text)["props"]["pageProps"]["pageData"]["data"]
    listing_detail = data["listingDetail"]
    listing_data = data["listingData"]
    property_unit = listing_detail.get("propertyUnit") or {}
    description = strip_html((data.get("descriptionBlockData") or {}).get("description") or "")
    detail_items = [
        item.get("value", "")
        for item in ((data.get("detailsData") or {}).get("metatable") or {}).get("items", [])
    ]
    haystack_parts = [
        listing_detail.get("localizedTitle") or "",
        listing_detail.get("localizedHeadline") or "",
        description,
        " ".join(detail_items),
        " ".join(feature.get("description", "") for feature in property_unit.get("features") or []),
    ]
    haystack = " ".join(part for part in haystack_parts if part)
    allow_flags = collect_keyword_hits(
        haystack,
        [
            "couples okay",
            "overnight guests allowed",
            "normal cooking",
            "cooking allowed",
            "full cooking",
            "all cooking",
            "stove",
            "hob",
            "attached toilet",
            "private bathroom",
            "attached bathroom",
            "ensuite",
            "masterbedroom",
            "master bedroom",
        ],
    )
    risk_flags = collect_keyword_hits(
        haystack,
        [
            "light cooking",
            "microwave",
            "induction",
            "boiling only",
            "no overnight",
            "no visitors",
            "visitors until",
            "visitor until",
            "female only",
            "male only",
            "1 pax only",
            "owner stays",
            "landlord stays",
        ],
    )
    agent = listing_detail.get("agent") or {}
    agency = listing_detail.get("agency") or {}
    return ListingDetails(
        listing_id=str(listing_detail["id"]),
        url=listing_data.get("url") or url,
        title=listing_detail.get("localizedTitle") or "",
        headline=listing_detail.get("localizedHeadline") or "",
        description=description,
        posted_unix=int((listing_data.get("lastPosted") or {}).get("unix") or 0),
        posted_text=_extract_detail_posted_text(detail_items, listing_detail),
        price=int(listing_data.get("price") or 0),
        price_pretty=listing_data.get("pricePretty") or "",
        street_name=listing_data.get("streetName") or "",
        district_text=listing_data.get("districtText") or "",
        property_type=listing_data.get("propertyType") or "",
        studio_or_room_text=listing_data.get("studioOrRoomText") or "",
        bedrooms=_normalize_optional_int(listing_data.get("bedrooms")),
        bathrooms=_normalize_optional_int(listing_data.get("bathrooms")),
        floor_area_text=listing_data.get("floorAreaText") or "",
        room_type=str(property_unit.get("roomType") or ""),
        cooking_type=str(property_unit.get("cookingType") or ""),
        visitors_allowed=str(property_unit.get("visitorsAllowed") or ""),
        tenant_gender=str(property_unit.get("tenantGender") or ""),
        max_tenants=str(property_unit.get("maxTenants") or ""),
        owner_stays=str(property_unit.get("ownerStays") or ""),
        furnishing_text=str(property_unit.get("furnishingText") or ""),
        agent_name=agent.get("name") or "",
        agent_phone=normalize_phone(agent.get("mobile") or agent.get("phone")),
        agent_phone_pretty=(agent.get("mobilePretty") or agent.get("phonePretty") or ""),
        agency_name=agency.get("name") or "",
        detail_values=detail_items,
        allow_flags=allow_flags,
        risk_flags=risk_flags,
        reject_reasons=[],
    )


def listing_passes_filters(details: ListingDetails, config: dict[str, Any]) -> bool:
    details.reject_reasons.clear()
    if details.price < int(config.get("min_price", 0)):
        details.reject_reasons.append("price_below_limit")
    if details.price > int(config["max_price"]):
        details.reject_reasons.append("price_above_limit")
    max_age_seconds = int(config["max_age_days"]) * 86400
    if details.posted_unix and now_utc_ts() - details.posted_unix > max_age_seconds:
        details.reject_reasons.append("listing_too_old")
    if config.get("require_room_rental") and "room" not in details.studio_or_room_text.lower():
        details.reject_reasons.append("not_room_rental")
    if config.get("require_attached_bathroom"):
        if (details.bathrooms or 0) < 1:
            details.reject_reasons.append("no_bathroom")
        private_keywords = [kw.lower() for kw in config.get("require_private_bathroom_keywords", [])]
        if private_keywords:
            combined = " ".join(
                [details.title, details.headline, details.description, " ".join(details.detail_values)]
            ).lower()
            if not any(keyword in combined for keyword in private_keywords):
                details.reject_reasons.append("private_bathroom_not_clear")
    combined = " ".join([details.title, details.headline, details.description, " ".join(details.detail_values)]).lower()
    for keyword in config.get("banned_keywords", []):
        if keyword.lower() in combined:
            details.reject_reasons.append(f"banned:{keyword}")
    return not details.reject_reasons


def build_outreach_message(details: ListingDetails, template: str) -> str:
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


def format_listing_summary(details: ListingDetails) -> str:
    lines = [
        f"{details.title} - {details.price_pretty}",
        f"{details.street_name} | {details.district_text}",
        f"Posted: {details.posted_text or 'unknown'}",
        f"Agent: {details.agent_name or 'unknown'}",
        f"Phone: {details.agent_phone_pretty or details.agent_phone or 'unknown'}",
        f"URL: {details.url}",
    ]
    if details.allow_flags:
        lines.append("Positive signals: " + ", ".join(details.allow_flags))
    if details.risk_flags:
        lines.append("Risk signals: " + ", ".join(details.risk_flags))
    if details.reject_reasons:
        lines.append("Rejected by filter: " + ", ".join(details.reject_reasons))
    return "\n".join(lines)


def send_rejected_candidates_to_telegram(
    candidates: list[ListingDetails],
    template: str,
    state: dict[str, Any],
    telegram: TelegramClient,
    config: dict[str, Any],
) -> None:
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
            "Rejected PropertyGuru listing\n\n"
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


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = str(chat_id) if chat_id else ""
        self.base_url = f"https://api.telegram.org/bot{token}"

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
        response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=30)
        response.raise_for_status()

    def get_updates(self, offset: int) -> tuple[int, list[dict[str, Any]]]:
        if not self.enabled:
            return offset, []
        response = requests.get(
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
        response = requests.post(
            f"{self.base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=30,
        )
        if not response.ok:
            logging.warning("answerCallbackQuery failed: %s", response.text)


def open_whatsapp_preview(details: ListingDetails, message: str, config: dict[str, Any]) -> str:
    url = f"https://web.whatsapp.com/send?phone={details.agent_phone}&text={quote(message)}"
    chrome_executable = config.get("chrome_executable", "chrome.exe")
    try:
        subprocess.Popen([chrome_executable, url])
    except FileNotFoundError:
        opened = webbrowser.open(url)
        if not opened:
            subprocess.Popen(["powershell", "-Command", f"Start-Process '{url}'"])
    return f"Opened WhatsApp preview for {details.agent_name or details.listing_id}."


def auto_send_whatsapp(details: ListingDetails, message: str, config: dict[str, Any]) -> str:
    if not sync_playwright:
        raise RuntimeError("Playwright is not installed.")
    profile_dir = str(Path(config.get("profile_dir", ".playwright-profile/propertyguru-helper")).resolve())
    channel = config.get("browser_channel", "chrome")
    target = f"https://web.whatsapp.com/send?phone={details.agent_phone}&text={quote(message)}"
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel=channel,
            headless=False,
        )
        try:
            page = context.new_page()
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(12000)
            clicked = False
            for selector in ("button[aria-label='Send']", "div[aria-label='Send']", "span[data-icon='send']"):
                try:
                    locator = page.locator(selector).first
                    locator.wait_for(timeout=8000)
                    locator.click(timeout=5000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                raise RuntimeError("Could not find WhatsApp send button in the controlled profile.")
            page.wait_for_timeout(int(config.get("post_send_wait_seconds", 12)) * 1000)
            return f"WhatsApp message sent to {details.agent_name or details.agent_phone_pretty}."
        finally:
            context.close()


def handle_approval(
    listing_id: str,
    state: dict[str, Any],
    telegram: TelegramClient,
    config: dict[str, Any],
) -> None:
    pending = state.get("pending_candidates", {})
    payload = pending.get(listing_id)
    if not payload:
        telegram.send_message(f"Listing {listing_id} is not pending anymore.")
        return
    details = ListingDetails(**payload["details"])
    message = payload["message"]
    try:
        if config.get("send_mode") == "auto_send":
            result = auto_send_whatsapp(details, message, config)
        else:
            result = open_whatsapp_preview(details, message, config)
    except Exception as exc:
        telegram.send_message(f"Approve failed for {listing_id}: {exc}")
        return
    state["pending_listing_ids"] = [x for x in state["pending_listing_ids"] if x != listing_id]
    state.get("pending_candidates", {}).pop(listing_id, None)
    if listing_id not in state["approved_listing_ids"]:
        state["approved_listing_ids"].append(listing_id)
    telegram.send_message(result)


def handle_rejection(
    listing_id: str,
    state: dict[str, Any],
    telegram: TelegramClient,
) -> None:
    pending = state.get("pending_candidates", {})
    if listing_id in pending:
        state["pending_listing_ids"] = [x for x in state["pending_listing_ids"] if x != listing_id]
        state.get("pending_candidates", {}).pop(listing_id, None)
        if listing_id not in state["rejected_listing_ids"]:
            state["rejected_listing_ids"].append(listing_id)
        telegram.send_message(f"Rejected listing {listing_id}.")
    else:
        telegram.send_message(f"Listing {listing_id} is not pending anymore.")


def process_telegram_updates(
    state: dict[str, Any],
    telegram: TelegramClient,
    config: dict[str, Any],
) -> None:
    offset = int(state.get("telegram_update_offset", 0))
    new_offset, updates = telegram.get_updates(offset)
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


def shortlist_candidates(
    session,
    config: dict[str, Any],
    state: dict[str, Any],
    template: str,
) -> tuple[list[ListingDetails], dict[str, dict[str, Any]], list[ListingDetails]]:
    pending_lookup: dict[str, dict[str, Any]] = {}
    shortlisted: list[ListingDetails] = []
    rejected: list[ListingDetails] = []
    seen_ids = set(state.get("seen_listing_ids", []))
    blocked_ids = set(state.get("approved_listing_ids", [])) | set(state.get("rejected_listing_ids", []))
    for listing in fetch_search_results(session, config):
        if listing.listing_id in blocked_ids:
            continue
        try:
            details = fetch_listing_details(session, listing.url)
        except Exception as exc:
            logging.warning("Skipping listing %s because detail fetch failed: %s", listing.listing_id, exc)
            seen_ids.add(listing.listing_id)
            continue
        if listing.listing_id in seen_ids and listing.listing_id not in state.get("pending_listing_ids", []):
            continue
        if not listing_passes_filters(details, config):
            rejected.append(details)
            seen_ids.add(listing.listing_id)
            continue
        message = build_outreach_message(details, template)
        shortlisted.append(details)
        pending_lookup[listing.listing_id] = {"details": asdict(details), "message": message}
        seen_ids.add(listing.listing_id)
    state["seen_listing_ids"] = sorted(seen_ids)
    return shortlisted, pending_lookup, rejected


def send_new_candidates_to_telegram(
    candidates: list[ListingDetails],
    pending_lookup: dict[str, dict[str, Any]],
    state: dict[str, Any],
    telegram: TelegramClient,
) -> None:
    pending_ids = set(state.get("pending_listing_ids", []))
    pending_candidates = state.setdefault("pending_candidates", {})
    for details in candidates:
        if details.listing_id in pending_ids:
            continue
        payload = pending_lookup[details.listing_id]
        pending_candidates[details.listing_id] = payload
        message = payload["message"]
        text = (
            "New PropertyGuru match\n\n"
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


def print_scan_results(candidates: list[ListingDetails], template: str, top: int) -> None:
    if not candidates:
        print("No listings matched the current filters.")
        return
    for index, details in enumerate(candidates[:top], start=1):
        print(f"\n[{index}] {format_listing_summary(details)}")
        print("\nDraft message:")
        print(build_outreach_message(details, template))


def load_template(path: Path) -> str:
    if not path.exists():
        path.write_text(DEFAULT_MESSAGE_TEMPLATE, encoding="utf-8")
        return DEFAULT_MESSAGE_TEMPLATE
    content = path.read_text(encoding="utf-8").strip()
    return content or DEFAULT_MESSAGE_TEMPLATE


def run_scan_once(config: dict[str, Any], top: int) -> int:
    session = build_session()
    state = load_json(resolve_path(config["state_file"]), DEFAULT_STATE)
    template = load_template(resolve_path(config["message_template_file"]))
    candidates, _, _ = shortlist_candidates(session, config, state, template)
    print_scan_results(candidates, template, top)
    return 0


def run_monitor_cycle(config: dict[str, Any]) -> int:
    session = build_session()
    state_path = resolve_path(config["state_file"])
    state = load_json(state_path, DEFAULT_STATE)
    template = load_template(resolve_path(config["message_template_file"]))
    telegram = TelegramClient(config.get("telegram_bot_token", ""), str(config.get("telegram_chat_id", "")))
    if telegram.enabled:
        process_telegram_updates(state, telegram, config)
        save_json(state_path, state)
    candidates, pending_lookup, rejected = shortlist_candidates(session, config, state, template)
    save_json(state_path, state)
    if telegram.enabled:
        send_rejected_candidates_to_telegram(rejected, template, state, telegram, config)
        send_new_candidates_to_telegram(candidates, pending_lookup, state, telegram)
        save_json(state_path, state)
    else:
        print_scan_results(candidates, template, top=5)
    return 0


def run_loop(config: dict[str, Any]) -> int:
    logging.info("Starting PropertyGuru monitor loop.")
    while True:
        try:
            run_monitor_cycle(config)
        except Exception:
            logging.exception("Monitor cycle failed.")
        time.sleep(int(config.get("poll_interval_seconds", 3600)))


def main() -> int:
    args = parse_args()
    config = load_config(resolve_path(args.config))
    logging.basicConfig(
        level=getattr(logging, str(config.get("log_level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
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
