from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")
REPO_ROOT = APP_PATH.parent.parent.parent


def load_app_module():
    spec = importlib.util.spec_from_file_location("wordgames_test_runtime", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WordGamesSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_app_module()
        cls.client = cls.module.app.test_client()

    def test_core_routes_render(self):
        routes = [
            "/",
            "/en",
            "/tr",
            "/nl",
            "/id",
            "/ms",
            "/en/history",
            "/en/daily-ladder",
            "/en/word-scramble",
            "/en/typo-hunt",
            "/en/word-chain",
            "/en/category-blitz",
            "/en/mini-crossword",
            "/en/mini-sudoku",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_payload_is_current_locale_only(self):
        response = self.client.get("/en")
        html = response.get_data(as_text=True)
        match = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertIn("dictionary", payload)
        self.assertNotIn("dictionaries", payload)
        self.assertEqual(payload["lang"], "en")
        self.assertNotIn("words", payload)
        self.assertNotIn("ladders", payload)
        self.assertEqual(len(payload["availableLanguages"]), 5)

        scramble_response = self.client.get("/en/word-scramble")
        scramble_html = scramble_response.get_data(as_text=True)
        scramble_match = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', scramble_html)
        self.assertIsNotNone(scramble_match)
        scramble_payload = json.loads(scramble_match.group(1))
        self.assertIn("words", scramble_payload)
        self.assertNotIn("ladders", scramble_payload)

    def test_turkish_payload_keeps_real_unicode(self):
        response = self.client.get("/tr")
        html = response.get_data(as_text=True)
        match = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["dictionary"]["seo"]["dailyTitle"], "Günlük Merdiven | WordSprint")
        self.assertEqual(payload["dictionary"]["profile"]["promptTitle"], "Sana nasıl hitap edeyim?")

    def test_backend_only_routes_are_removed(self):
        for route in ("/profile-name", "/analytics", "/analytics-summary"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 404)
        response = self.client.post("/profile-name", json={"displayName": "Test"})
        self.assertEqual(response.status_code, 404)

    def test_static_export_has_no_backend_references(self):
        env = os.environ.copy()
        env["WORDSPRINT_BASE_PATH"] = "/wordsprint"
        subprocess.run(
            [sys.executable, "apps/wordgames/export_static.py"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        dist = REPO_ROOT / "dist"
        for path in (
            "index.html",
            "en/index.html",
            "tr/index.html",
            "nl/index.html",
            "id/index.html",
            "ms/index.html",
            "en/daily-ladder/index.html",
            "static/wordgames.js",
            "manifest.webmanifest",
            "service-worker.js",
        ):
            with self.subTest(path=path):
                self.assertTrue((dist / path).exists())

        forbidden = (
            "/profile-name",
            "analytics.sqlite3",
            "/analytics",
            "/analytics-summary",
            "sqlite3",
            "visit_events",
            "player_profiles",
            "ANALYTICS_USERNAME",
            "ANALYTICS_PASSWORD",
        )
        for file_path in dist.rglob("*"):
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for token in forbidden:
                    with self.subTest(file=str(file_path), token=token):
                        self.assertNotIn(token, content)

    def test_crossword_difficulty_has_variety_per_locale(self):
        for lang, puzzles in self.module.CROSSWORDS.items():
            counts = {"easy": 0, "medium": 0, "hard": 0}
            for puzzle in puzzles:
                difficulty = puzzle.get("difficulty")
                if difficulty:
                    counts[difficulty] += 1
                else:
                    size = int(puzzle["size"])
                    counts["easy" if size <= 3 else "medium" if size == 4 else "hard"] += 1
            with self.subTest(lang=lang):
                self.assertGreaterEqual(counts["easy"], 3)
                self.assertGreaterEqual(counts["medium"], 3)
                self.assertGreaterEqual(counts["hard"], 3)

    def test_ladder_pool_is_expanded_per_locale(self):
        from collections import Counter

        for lang, ladders in self.module.LADDERS.items():
            with self.subTest(lang=lang):
                self.assertGreaterEqual(len(ladders), 8)
                word_usage = Counter(word for ladder in ladders for word in ladder["path"])
                self.assertLessEqual(max(word_usage.values()), 3)


if __name__ == "__main__":
    unittest.main()
