from pathlib import Path
import re
import unittest


PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"


class FrontendMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_no_literal_backslash_n_in_page_source(self):
        self.assertNotIn("\\n", self.html)

    def test_journey_navigation_is_in_flow_and_keeps_all_destinations(self):
        self.assertRegex(self.html, r"\.journey-nav\{position:relative")
        self.assertNotRegex(self.html, r"\.journey-nav\{position:fixed")
        nav = re.search(r'<nav class="journey-nav".*?</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        self.assertEqual(nav.group(0).count('data-stage='), 5)
        self.assertIn("min-height:42px", self.html)

    def test_aqi_number_is_in_gauge_and_label_is_outside_it(self):
        gauge_stack = re.search(r'<div class="gauge-stack">(.*?)</div><div class="aqi-desc">', self.html, re.S)
        self.assertIsNotNone(gauge_stack)
        content = gauge_stack.group(1)
        gauge = re.search(r'<div class="gauge">(.*?)</div>', content, re.S)
        self.assertIsNotNone(gauge)
        self.assertIn('id="aqiValue"', gauge.group(1))
        self.assertNotIn("gauge-label", gauge.group(1))
        self.assertIn("gauge-label", content)
        self.assertIn(".gauge-number{position:relative;z-index:1", self.html)
        self.assertIn(".gauge svg{z-index:0", self.html)


if __name__ == "__main__":
    unittest.main()
