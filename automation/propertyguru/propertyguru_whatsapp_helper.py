#!/usr/bin/env python3
"""
Semi-automated PropertyGuru -> WhatsApp outreach helper.

This tool opens PropertyGuru listings, tries to locate the WhatsApp contact
entry point, builds a customized message, and opens the chat in WhatsApp Web.
The user still reviews and sends the message manually.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote, urlparse

from playwright.sync_api import BrowserContext, Error, Page, TimeoutError, sync_playwright

try:
    import curl_cffi.requests as cffi_requests
except ImportError:
    cffi_requests = None

BASE_DIR = Path(__file__).resolve().parent


DEFAULT_TEMPLATE = (
    "Hi {agent_name}, I saw your PropertyGuru listing for {title} in "
    "{location}. Is it still available? I would like to arrange a viewing. "
    "Thanks."
)

DEFAULT_LISTINGS_FILE = """# Add one PropertyGuru listing URL per line.
# Example:
# https://www.propertyguru.com.sg/listing/for-rent-some-listing-slug-12345678
"""


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "there"


@dataclass
class ListingContext:
    url: str
    title: str = ""
    price: str = ""
    location: str = ""
    agent_name: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open PropertyGuru listings and prepare WhatsApp messages."
    )
    parser.add_argument(
        "--input",
        default=str(BASE_DIR / "listings.txt"),
        help="Text file with one PropertyGuru listing URL per line.",
    )
    parser.add_argument(
        "--template-file",
        help="Optional text file for the message template.",
    )
    parser.add_argument(
        "--profile-dir",
        default=str(Path(__file__).resolve().parents[2] / ".playwright-profile" / "propertyguru-helper"),
        help="Directory for the persistent browser profile.",
    )
    parser.add_argument(
        "--channel",
        default="chrome",
        help="Browser channel to use, for example chrome, msedge, chromium.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run headless. Usually keep this off for WhatsApp Web.",
    )
    parser.add_argument(
        "--max-listings",
        type=int,
        default=0,
        help="Limit how many listings to process. 0 means all.",
    )
    return parser.parse_args()


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def read_listing_urls(path: Path) -> list[str]:
    if not path.exists():
        path.write_text(DEFAULT_LISTINGS_FILE, encoding="utf-8")
        raise FileNotFoundError(
            f"Input file not found, so a sample file was created at: {path}"
        )

    urls: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    if not urls:
        raise ValueError(f"No listing URLs found in {path}")
    return urls


def load_template(path: Path | None) -> str:
    if not path:
        return DEFAULT_TEMPLATE
    content = path.read_text(encoding="utf-8").strip()
    return content or DEFAULT_TEMPLATE


def normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def first_text(page: Page, selectors: Iterable[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            text = locator.text_content(timeout=1500)
        except TimeoutError:
            continue
        if text:
            return normalize_space(text)
    return ""


def extract_listing_context(page: Page, url: str) -> ListingContext:
    page.wait_for_load_state("domcontentloaded")
    title = first_text(
        page,
        [
            "h1",
            "[data-testid='listing-title']",
            "[class*='listing-title']",
            "meta[property='og:title']",
        ],
    )
    if not title:
        try:
            title = normalize_space(page.title())
        except Error:
            title = ""

    price = first_text(
        page,
        [
            "[data-testid='listing-price']",
            "[class*='price']",
            "text=/S\\$|RM|\\$/",
        ],
    )
    location = first_text(
        page,
        [
            "[data-testid='listing-location']",
            "[class*='location']",
            "text=/Singapore|Kuala Lumpur|Johor|Selangor/i",
        ],
    )
    agent_name = first_text(
        page,
        [
            "[data-testid='agent-name']",
            "[class*='agent-name']",
            "[class*='advertiser-name']",
        ],
    )
    return ListingContext(
        url=url,
        title=title,
        price=price,
        location=location,
        agent_name=agent_name,
    )


def parse_whatsapp_href(href: str) -> tuple[str, str]:
    parsed = urlparse(href)
    host = parsed.netloc.lower()
    phone = ""
    preset_text = ""

    if "wa.me" in host:
        phone = parsed.path.strip("/")
    query = parse_qs(parsed.query)
    if query.get("phone"):
        phone = query["phone"][0]
    if query.get("text"):
        preset_text = query["text"][0]
    return phone, preset_text


def extract_whatsapp_fallback_from_html(page: Page) -> str | None:
    html = page.content()
    fallback = extract_whatsapp_fallback_from_text(html)
    if fallback:
        return fallback

    return None


def extract_whatsapp_fallback_from_text(html: str) -> str | None:
    if not html:
        return None

    direct_match = re.search(r'https://wa\.me/[^"\']+', html, re.I)
    if direct_match:
        return direct_match.group(0).replace("&amp;", "&")

    phone_patterns = [
        r'"mobile":"\+?(\d{8,15})"',
        r'"phone":"(\d{8,15})"',
        r'"whatsAppEnquiry":\{"phone":"(\d{8,15})"',
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, html)
        if match:
            return f"https://wa.me/{match.group(1)}"

    return None


def fetch_listing_html_fallback(url: str) -> str:
    if not cffi_requests:
        return ""
    session = cffi_requests.Session(impersonate="chrome124")
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def find_whatsapp_link(page: Page) -> str | None:
    hrefs = page.locator("a[href*='wa.me'], a[href*='whatsapp.com']").evaluate_all(
        "(nodes) => nodes.map((node) => node.href).filter(Boolean)"
    )
    if hrefs:
        return hrefs[0]

    clickable_candidates = [
        page.get_by_role("link", name=re.compile("whatsapp", re.I)).first,
        page.get_by_role("button", name=re.compile("whatsapp", re.I)).first,
        page.get_by_text(re.compile("whatsapp", re.I)).first,
    ]

    for locator in clickable_candidates:
        try:
            if locator.count() == 0:
                continue
        except Error:
            continue

        try:
            with page.context.expect_page(timeout=5000) as popup_info:
                locator.click(timeout=3000)
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded")
            return popup.url
        except TimeoutError:
            pass
        except Error:
            pass

        try:
            locator.click(timeout=3000)
            page.wait_for_timeout(2000)
            if "wa.me" in page.url or "whatsapp.com" in page.url:
                return page.url
        except Error:
            continue

    fallback = extract_whatsapp_fallback_from_html(page)
    if fallback:
        return fallback

    try:
        html = fetch_listing_html_fallback(page.url)
    except Exception:
        return None
    return extract_whatsapp_fallback_from_text(html)


def build_message(template: str, listing: ListingContext, preset_text: str) -> str:
    if preset_text and template == DEFAULT_TEMPLATE:
        return preset_text
    values = SafeDict(
        agent_name=listing.agent_name or "there",
        title=listing.title or "your listing",
        price=listing.price or "",
        location=listing.location or "the area",
        listing_url=listing.url,
    )
    return template.format_map(values).strip()


def ensure_whatsapp_ready(page: Page) -> None:
    page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print(
        "\nWhatsApp Web is open. If needed, scan the QR code once. "
        "Press Enter here when you are ready to continue."
    )
    try:
        input()
    except EOFError:
        print("No interactive input available; continuing automatically.")


def advance_whatsapp_redirect(page: Page) -> None:
    page.wait_for_timeout(3000)

    button_candidates = [
        page.get_by_role("link", name=re.compile("continue to chat", re.I)).first,
        page.get_by_role("button", name=re.compile("continue to chat", re.I)).first,
        page.get_by_role("link", name=re.compile("use whatsapp web", re.I)).first,
        page.get_by_role("button", name=re.compile("use whatsapp web", re.I)).first,
        page.get_by_text(re.compile("continue to chat", re.I)).first,
        page.get_by_text(re.compile("use whatsapp web", re.I)).first,
    ]

    for locator in button_candidates:
        try:
            if locator.count() == 0:
                continue
            locator.click(timeout=5000)
            page.wait_for_timeout(4000)
        except Error:
            continue


def open_whatsapp_chat(context: BrowserContext, phone: str, message: str) -> Page:
    encoded_message = quote(message)
    page = context.new_page()

    if phone:
        wa_target = f"https://wa.me/{quote(phone)}?text={encoded_message}"
        page.goto(wa_target, wait_until="domcontentloaded")
        advance_whatsapp_redirect(page)
        if "web.whatsapp.com" in page.url or "whatsapp.com/send" in page.url:
            page.wait_for_timeout(5000)
            return page

    target = f"https://web.whatsapp.com/send?text={encoded_message}"
    if phone:
        target += f"&phone={quote(phone)}"
    page.goto(target, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    return page


def process_listing(
    context: BrowserContext, listing_url: str, template: str, whatsapp_ready: bool
) -> bool:
    page = context.new_page()
    try:
        print(f"\nOpening listing: {listing_url}")
        page.goto(listing_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        listing = extract_listing_context(page, listing_url)
        print(
            f"Detected title='{listing.title}' location='{listing.location}' "
            f"agent='{listing.agent_name}'"
        )

        whatsapp_href = find_whatsapp_link(page)
        if not whatsapp_href:
            print("No WhatsApp entry point was found on this page.")
            return whatsapp_ready

        phone, preset_text = parse_whatsapp_href(whatsapp_href)
        message = build_message(template, listing, preset_text)
        print(f"Prepared message:\n{message}\n")

        if not whatsapp_ready:
            ensure_whatsapp_ready(page)
            whatsapp_ready = True

        chat_page = open_whatsapp_chat(context, phone, message)
        print(
            "Review the prefilled message in WhatsApp Web and click Send manually.\n"
            "Press Enter here after you finish with this listing."
        )
        try:
            input()
        except EOFError:
            print("No interactive input available; leaving the chat open briefly.")
            chat_page.wait_for_timeout(15000)
        chat_page.close()
        return whatsapp_ready
    finally:
        page.close()


def run() -> int:
    args = parse_args()
    input_path = resolve_path(args.input)
    profile_dir = Path(args.profile_dir)
    template = load_template(resolve_path(args.template_file) if args.template_file else None)
    try:
        urls = read_listing_urls(input_path)
    except FileNotFoundError as exc:
        print(str(exc))
        print("Open that file, paste your listing URLs, then run the command again.")
        return 1
    except ValueError as exc:
        print(str(exc))
        print("Add at least one real PropertyGuru listing URL to the input file.")
        return 1
    if args.max_listings > 0:
        urls = urls[: args.max_listings]

    whatsapp_ready = False
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel=args.channel,
            headless=args.headless,
        )
        try:
            for listing_url in urls:
                whatsapp_ready = process_listing(
                    context=context,
                    listing_url=listing_url,
                    template=template,
                    whatsapp_ready=whatsapp_ready,
                )
        finally:
            context.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("\nStopped by user.")
        raise SystemExit(130)
