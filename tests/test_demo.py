"""Demo smoke test: boots docs/app.js against a fake DOM under Node."""

import json
import re
import subprocess
import unittest

from tests.helpers import LABEL, NODE, ROOT

DOCS = ROOT / "docs"


@unittest.skipUnless(NODE, "node is required for the demo smoke test")
class DemoUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run([NODE, str(ROOT / "tests" / "js" / "ui_smoke.js")],
                              capture_output=True, text=True, check=True)
        cls.steps = {s["name"]: s for s in json.loads(proc.stdout)["steps"]}

    def test_boots_on_first_sample_with_label(self):
        s = self.steps["boot"]
        self.assertTrue(s["problemsHidden"])
        self.assertFalse(s["resultsHidden"])
        self.assertEqual(s["label"], LABEL)
        self.assertIn("$15,510.00", s["totals"])
        self.assertEqual(s["compareRows"], 3)
        self.assertEqual(s["scenarioOptions"], 4)  # "as entered" + 3 scenarios
        self.assertEqual(s["burnChart"], 1)
        self.assertEqual(s["beChart"], 2)
        self.assertEqual(len(s["winners"]), 4)

    def test_bad_input_shows_cli_identical_error(self):
        s = self.steps["bad cash"]
        self.assertFalse(s["problemsHidden"])
        self.assertTrue(s["resultsHidden"])
        self.assertIn('input: "starting_cash" must be a number, got text "lots"', s["problems"])
        self.assertTrue(s["invalidCash"])
        self.assertTrue(self.steps["fixed cash"]["problemsHidden"])
        self.assertFalse(self.steps["fixed cash"]["invalidCash"])

    def test_scenario_switcher_changes_numbers(self):
        self.assertIn("$11,462.00", self.steps["lean scenario"]["totals"])
        self.assertIn("5.4 months", self.steps["lean scenario"]["runway"])

    def test_rows_add_and_remove(self):
        self.assertEqual(self.steps["added row"]["oneTimeRows"], 7)
        self.assertIn("one_time_costs item 7", self.steps["added row"]["problems"])
        self.assertEqual(self.steps["added row"]["invalidRowInputs"], 2)  # blank name + category
        self.assertEqual(self.steps["removed row"]["oneTimeRows"], 6)
        self.assertEqual(self.steps["removed row"]["invalidRowInputs"], 0)
        self.assertEqual(self.steps["removed row"]["focused"], "button")  # focus stays in the table
        self.assertTrue(self.steps["removed row"]["problemsHidden"])

    def test_undefined_break_even_hides_chart(self):
        s = self.steps["price below variable"]
        self.assertIn("Break-even is undefined", s["breakEven"])
        self.assertEqual(s["beChart"], 0)

    def test_every_sample_loads(self):
        for name in ("sample 0", "sample 1", "sample 2"):
            s = self.steps[name]
            self.assertTrue(s["problemsHidden"], s["problems"])
            self.assertEqual(s["label"], LABEL)

    def test_blank_start_only_warns(self):
        s = self.steps["blank"]
        self.assertFalse(s["resultsHidden"])
        self.assertIn("one_time_costs is empty", s["problems"])
        self.assertNotIn("problem to fix", s["problems"])
        self.assertNotIn("problems to fix", s["problems"])


class DemoStatic(unittest.TestCase):
    def test_no_external_resources_or_network(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        js = (DOCS / "app.js").read_text(encoding="utf-8")
        for src in re.findall(r'(?:src|href)="([^"]+)"', html):
            with self.subTest(src):
                self.assertFalse(src.startswith(("http:", "https:", "//")), src)
        for needle in ("fetch(", "XMLHttpRequest", "WebSocket", "import(", "sendBeacon"):
            self.assertNotIn(needle, js)

    def test_inputs_are_labelled(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn('lang="en"', html)
        for m in re.finditer(r"<input[^>]*>", html):
            tag = m.group(0)
            before = html[:m.start()]
            inside_label = before.rfind("<label") > before.rfind("</label>")
            with self.subTest(tag):
                self.assertTrue(inside_label or "aria-label" in tag, tag)


if __name__ == "__main__":
    unittest.main()
