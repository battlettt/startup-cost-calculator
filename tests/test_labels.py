"""Every sample, README example and demo sample must be labelled synthetic."""

import unittest

from tests.helpers import EXAMPLES, LABEL, ROOT, load_json

from startup_costs.cli import EXAMPLE_INPUT


class SyntheticLabels(unittest.TestCase):
    def test_at_least_three_samples(self):
        self.assertGreaterEqual(len(EXAMPLES), 3)

    def test_every_sample_file_is_labelled_twice(self):
        for path in EXAMPLES:
            with self.subTest(path.name):
                data = load_json(path)
                self.assertEqual(data["label"], LABEL)          # shown in every report
                self.assertIn(LABEL, data["_comment"])          # seen by anyone opening the file
                self.assertIn(LABEL, path.read_text(encoding="utf-8"))

    def test_init_example_is_labelled(self):
        self.assertEqual(EXAMPLE_INPUT["label"], LABEL)

    def test_demo_and_docs_carry_the_label(self):
        for rel in ("docs/index.html", "docs/samples.js", "README.md", "docs/concepts.md", "CHAPTER.md"):
            with self.subTest(rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(LABEL, text)

    def test_readme_worked_example_is_labelled_where_it_appears(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        section = text.split("## Worked example", 1)[1].split("\n## ", 1)[0]
        self.assertIn(LABEL, section)

    def test_no_market_data_claims(self):
        bad = ("market data shows", "industry average", "according to market", "typical market rate")
        for rel in ("README.md", "docs/concepts.md", "CHAPTER.md", "docs/index.html"):
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            for phrase in bad:
                with self.subTest(rel, phrase=phrase):
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
