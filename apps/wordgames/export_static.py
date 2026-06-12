from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
DIST_DIR = REPO_ROOT / "dist"
STATIC_DIR = BASE_DIR / "static"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ["WORDSPRINT_STATIC_EXPORT"] = "1"

from app import app, manifest_payload, render_localized_page
from wordgames_catalog import SUPPORTED_LANGUAGES, SUPPORTED_PAGES


LANGUAGE_ORDER = ("en", "tr", "nl", "id", "ms")
PAGE_ORDER = (
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
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def clean_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)


def copy_static_assets() -> None:
    shutil.copytree(STATIC_DIR, DIST_DIR / "static")
    shutil.copy2(STATIC_DIR / "service-worker.js", DIST_DIR / "service-worker.js")


def export_page(lang: str, page: str, output_path: Path) -> None:
    rendered = render_localized_page(lang, page)
    if rendered is None:
        raise RuntimeError(f"Failed to render {lang}/{page}")
    write_text(output_path, rendered)


def export_manifest() -> None:
    import json

    write_text(
        DIST_DIR / "manifest.webmanifest",
        json.dumps(manifest_payload(), ensure_ascii=False, indent=2) + "\n",
    )


def main() -> None:
    languages = [lang for lang in LANGUAGE_ORDER if lang in SUPPORTED_LANGUAGES]
    pages = [page for page in PAGE_ORDER if page in SUPPORTED_PAGES]

    clean_dist()
    copy_static_assets()

    with app.app_context():
        export_page("en", "home", DIST_DIR / "index.html")
        for lang in languages:
            export_page(lang, "home", DIST_DIR / lang / "index.html")
            for page in pages:
                export_page(lang, page, DIST_DIR / lang / page / "index.html")
        export_manifest()

    print(f"Exported WordSprint static site to {DIST_DIR}")


if __name__ == "__main__":
    main()
