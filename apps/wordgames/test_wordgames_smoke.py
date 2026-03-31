from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")


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
        self.assertEqual(len(payload["words"]), 50)
        self.assertEqual(len(payload["availableLanguages"]), 5)

    def test_turkish_payload_keeps_real_unicode(self):
        response = self.client.get("/tr")
        html = response.get_data(as_text=True)
        match = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["dictionary"]["seo"]["dailyTitle"], "Günlük Merdiven | WordSprint")
        self.assertEqual(payload["dictionary"]["profile"]["promptTitle"], "Sana nasıl hitap edeyim?")

    def test_analytics_summary_has_richer_breakdowns(self):
        response = self.client.get("/analytics-summary")
        summary = response.get_json()
        self.assertIn("by_page", summary)
        self.assertIn("daily_visits", summary)

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
