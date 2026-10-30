"""Teaching material is present and the chapter figure is embeddable."""

import re
import unittest
import xml.etree.ElementTree as ET

from tests.helpers import ROOT

SVG_NS = "{http://www.w3.org/2000/svg}"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Concepts(unittest.TestCase):
    def test_covers_required_topics(self):
        text = read("docs/concepts.md").lower()
        for topic in ("fixed", "variable", "one-time", "recurring", "burn rate", "runway",
                      "break-even", "contingency", "forgetting recurring costs",
                      "confusing revenue with profit", "pricing below variable cost",
                      "ignoring runway", "try it yourself"):
            with self.subTest(topic):
                self.assertIn(topic, text)

    def test_break_even_formula_and_worked_example(self):
        text = read("docs/concepts.md")
        self.assertIn("break-even units    = monthly fixed costs ÷ contribution margin", text)
        self.assertIn("900 ÷ 12 = **75 candles a month**", text)


class Readme(unittest.TestCase):
    def test_run_instructions_and_worked_example(self):
        text = read("README.md")
        self.assertIn("python3 -m startup_costs report", text)
        self.assertIn("docs/index.html", text)
        self.assertIn("## Worked example", text)
        # the worked example's numbers match the real CLI output (see test_cli)
        for number in ("$15,510", "$1,355 a month", "1.8 months", "399 drinks", "5.7 months"):
            self.assertIn(number, text)


class Chapter(unittest.TestCase):
    def test_thesis_summary_and_figure(self):
        text = read("CHAPTER.md")
        self.assertIn("## Thesis", text)
        self.assertIn("## Project summary", text)
        svg = re.search(r"```html\n(<svg.*?</svg>)\n```", text, re.S).group(1)
        root = ET.fromstring(svg)
        self.assertEqual(root.tag, SVG_NS + "svg")
        self.assertEqual(root.get("role"), "img")
        self.assertIsNotNone(root.find(SVG_NS + "title"))
        self.assertIsNotNone(root.find(SVG_NS + "desc"))

    def test_crossing_dot_sits_on_both_lines(self):
        svg = re.search(r"(<svg.*?</svg>)", read("CHAPTER.md"), re.S).group(1)
        root = ET.fromstring(svg)
        dot = root.find(SVG_NS + "circle")
        cx, cy = float(dot.get("cx")), float(dot.get("cy"))
        lines = {l.get("class"): l for l in root.iter(SVG_NS + "line")
                 if l.get("class") in ("rev", "cost") and l.get("x1") == "40"}
        for cls in ("rev", "cost"):
            l = lines[cls]
            x1, y1, x2, y2 = (float(l.get(k)) for k in ("x1", "y1", "x2", "y2"))
            y_at = y1 + (y2 - y1) * (cx - x1) / (x2 - x1)
            self.assertAlmostEqual(y_at, cy, places=6, msg=cls)


if __name__ == "__main__":
    unittest.main()
