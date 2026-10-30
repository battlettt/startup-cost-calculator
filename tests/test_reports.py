import csv
import io
import json
import re
import unittest
from html.parser import HTMLParser

from tests.helpers import EXAMPLES, LABEL, base, load_json, model_of

from startup_costs.model import check
from startup_costs.reports import (
    CSV_COLUMNS, build_report, render_csv, render_html, render_json, render_text,
)


def report_for(data):
    model, errors, warnings = check(data)
    assert not errors, errors
    return build_report(model, warnings)


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.stack, self.text = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in ("meta", "br", "link", "line", "polyline"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_data(self, data):
        self.text.append(data)


class TextReport(unittest.TestCase):
    def test_sections_and_numbers(self):
        text = render_text(report_for(base()))
        for heading in ("ONE-TIME COSTS", "MONTHLY RECURRING COSTS", "RUNWAY", "BREAK-EVEN",
                        "SCENARIOS", "WINNERS"):
            self.assertIn(heading, text)
        self.assertIn(LABEL, text)
        self.assertIn("Total one-time cost: $3,850.00", text)
        self.assertIn("Contingency buffer (10%): $350.00", text)
        self.assertIn("Monthly burn: $900.00", text)
        self.assertIn("lasts about 6.8 months", text)
        self.assertIn("you need 150 units a month", text)

    def test_warnings_and_undefined_shown(self):
        data = base(one_time_costs=[], revenue={"unit_price": 2, "variable_cost_per_unit": 3})
        text = render_text(report_for(data))
        self.assertIn("WARNINGS", text)
        self.assertIn("one_time_costs is empty", text)
        self.assertIn("(none entered)", text)
        self.assertIn("Break-even is undefined", text)
        self.assertIn("undefined", text.split("SCENARIOS")[1])

    def test_unlabelled_input_is_flagged_as_assumptions(self):
        text = render_text(report_for(base(label=None)))
        self.assertIn("treat every figure as an assumption", text)


class JsonReport(unittest.TestCase):
    def test_round_trips_full_report(self):
        rep = report_for(base())
        parsed = json.loads(render_json(rep))
        self.assertEqual(parsed, json.loads(json.dumps(rep)))
        self.assertEqual(parsed["analysis"]["one_time"]["total"], 3850)
        self.assertEqual(parsed["label"], LABEL)
        self.assertEqual(len(parsed["comparison"]["scenarios"]), 3)

    def test_undefined_break_even_is_null_not_infinite(self):
        out = render_json(report_for(base(revenue={"unit_price": 2, "variable_cost_per_unit": 3})))
        self.assertNotIn("Infinity", out)
        self.assertNotIn("NaN", out)
        self.assertIsNone(json.loads(out)["analysis"]["break_even"]["units"])


class CsvReport(unittest.TestCase):
    def test_one_row_per_scenario(self):
        rows = list(csv.DictReader(io.StringIO(render_csv(report_for(base())))))
        self.assertEqual([r["scenario"] for r in rows], ["lean", "standard", "premium"])
        self.assertEqual(list(rows[0].keys()), CSV_COLUMNS)
        std = rows[1]
        self.assertEqual(float(std["one_time_total"]), 3850)
        self.assertEqual(float(std["monthly_burn"]), 900)
        self.assertEqual(float(std["runway_months"]), 6.83)
        self.assertEqual(std["break_even_units_whole"], "150")
        self.assertEqual(std["label"], LABEL)

    def test_blank_cells_for_not_applicable(self):
        rows = list(csv.DictReader(io.StringIO(render_csv(report_for(base(starting_cash=0))))))
        self.assertEqual(rows[1]["runway_status"], "shortfall")
        self.assertEqual(rows[1]["runway_months"], "")

    def test_overrides_and_commas_quoted(self):
        data = base(scenarios=[{"name": "lean, cheap", "overrides": [{"item": "Oven", "amount": 1}]}])
        rows = list(csv.DictReader(io.StringIO(render_csv(report_for(data)))))
        self.assertEqual(rows[0]["scenario"], "lean, cheap")
        self.assertEqual(rows[0]["overrides"], "one_time:Oven=1")


class HtmlReport(unittest.TestCase):
    def test_self_contained_and_printable(self):
        html = render_html(report_for(base()))
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<style>", html)
        self.assertIn("@media print", html)
        self.assertNotRegex(html, r"<script|<link|<img|@import|url\(")
        # the only URL is the SVG namespace identifier
        self.assertEqual(set(re.findall(r"https?://[^\"' ]+", html)), {"http://www.w3.org/2000/svg"})

    def test_well_formed_with_label_and_tables(self):
        html = render_html(report_for(base()))
        parser = _Collector()
        parser.feed(html)
        self.assertEqual(parser.stack, [])
        tags = [t for t, _ in parser.tags]
        self.assertEqual(tags.count("table"), 3)
        self.assertIn("svg", tags)
        text = "".join(parser.text)
        self.assertIn(LABEL, text)
        self.assertIn("$3,850.00", text)
        self.assertIn("Cheapest to launch", text)

    def test_chart_is_labelled_for_screen_readers(self):
        html = render_html(report_for(base()))
        self.assertIn('role="img"', html)
        self.assertIn("<title id=\"burn-title\">", html)
        self.assertIn("<desc id=\"burn-desc\">", html)

    def test_shortfall_has_no_chart(self):
        html = render_html(report_for(base(starting_cash=0)))
        self.assertNotIn("<svg", html)
        self.assertIn("Not enough cash", html)

    def test_user_text_is_escaped(self):
        data = base(name="<script>alert(1)</script> & Co")
        data["one_time_costs"][0]["name"] = "<b>Oven</b>"
        html = render_html(report_for(data))
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co", html)
        self.assertIn("&lt;b&gt;Oven&lt;/b&gt;", html)


class AllFormatsOnSamples(unittest.TestCase):
    def test_every_sample_renders_in_every_format(self):
        for path in EXAMPLES:
            rep = report_for(load_json(path))
            for render in (render_text, render_json, render_html, render_csv):
                with self.subTest(sample=path.name, fmt=render.__name__):
                    out = render(rep)
                    self.assertTrue(out.strip())
                    if render is not render_csv:
                        self.assertIn(LABEL, out)


if __name__ == "__main__":
    unittest.main()
