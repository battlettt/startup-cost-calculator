import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import EXAMPLES, FIXTURES, LABEL, ROOT, SRC, base, load_json, run_cli

from startup_costs.cli import EXAMPLE_INPUT
from startup_costs.model import check


class Init(unittest.TestCase):
    def test_init_writes_valid_commented_labelled_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "idea.json")
            code, out, _ = run_cli("init", path)
            self.assertEqual(code, 0)
            self.assertIn("Wrote example input", out)
            data = load_json(path)
            self.assertEqual(data["label"], LABEL)
            self.assertTrue(any(k.startswith("_comment") for k in data))
            model, errors, warnings = check(data)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            code, out, _ = run_cli("report", path)
            self.assertEqual(code, 0)
            self.assertIn("Weekend market stall", out)

    def test_init_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "idea.json")
            with open(path, "w") as fh:
                fh.write("keep me")
            code, _, err = run_cli("init", path)
            self.assertEqual(code, 1)
            self.assertIn("--force", err)
            with open(path) as fh:
                self.assertEqual(fh.read(), "keep me")
            self.assertEqual(run_cli("init", path, "--force")[0], 0)
            self.assertEqual(load_json(path), EXAMPLE_INPUT)


class Validate(unittest.TestCase):
    def test_samples_validate(self):
        for path in EXAMPLES:
            with self.subTest(path.name):
                code, out, err = run_cli("validate", str(path))
                self.assertEqual(code, 0, err)
                self.assertIn("is valid", out)

    def test_invalid_input_exits_non_zero_with_numbered_errors(self):
        code, out, err = run_cli("validate", str(FIXTURES / "invalid_negative_and_range.json"))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Invalid input: 4 errors found.", err)
        self.assertIn('one_time_costs item 1 ("Oven"): "amount" must not be negative (got -3000)', err)
        self.assertIn('"contingency_pct" must be between 0 and 100 (got 120)', err)

    def test_warnings_go_to_stderr(self):
        code, _, err = run_cli("validate", str(FIXTURES / "valid_empty_lists.json"))
        self.assertEqual(code, 0)
        self.assertIn("warning: one_time_costs is empty", err)

    def test_every_invalid_fixture_fails(self):
        for path in sorted(FIXTURES.glob("invalid_*.json")):
            with self.subTest(path.name):
                self.assertEqual(run_cli("validate", str(path))[0], 1)
                self.assertEqual(run_cli("report", str(path))[0], 1)

    def test_missing_file(self):
        code, _, err = run_cli("validate", "/nonexistent/file.json")
        self.assertEqual(code, 1)
        self.assertIn("cannot read file", err)

    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w") as fh:
                fh.write('{"name": "x",\n "starting_cash": 5,,}')
            code, _, err = run_cli("report", path)
            self.assertEqual(code, 1)
            self.assertIn("not valid JSON (line 2", err)

    def test_usage_error_exit_two(self):
        self.assertEqual(run_cli("report")[0], 2)
        self.assertEqual(run_cli("report", "x.json", "--format", "pdf")[0], 2)
        self.assertEqual(run_cli()[0], 2)


class Report(unittest.TestCase):
    def test_every_sample_every_format_to_stdout_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in EXAMPLES:
                for fmt in ("text", "json", "html", "csv"):
                    with self.subTest(sample=path.name, fmt=fmt):
                        code, out, err = run_cli("report", str(path), "--format", fmt)
                        self.assertEqual(code, 0, err)
                        target = os.path.join(tmp, f"{path.stem}.{fmt}")
                        code, out2, err2 = run_cli("report", str(path), "-f", fmt, "-o", target)
                        self.assertEqual(code, 0, err2)
                        self.assertEqual(out2, "")
                        with open(target, encoding="utf-8", newline="") as fh:
                            self.assertEqual(fh.read(), out)
                        if fmt == "json":
                            self.assertEqual(json.loads(out)["label"], LABEL)
                        elif fmt == "csv":
                            rows = list(csv.DictReader(io.StringIO(out)))
                            self.assertEqual(len(rows), len(load_json(path)["scenarios"]))
                        else:
                            self.assertIn(LABEL, out)

    def test_sample_headline_numbers(self):
        expectations = {
            "coffee_cart.json": ["Total one-time cost: $15,510.00", "Monthly burn: $1,355.00",
                                 "lasts about 1.8 months", "399 units a month",
                                 "short $2,163.00 at opening"],
            "tutoring_service.json": ["Total one-time cost: $2,599.00", "Monthly burn: $495.00",
                                      "lasts about 4.9 months", "39 units a month"],
            "lawn_care.json": ["Total one-time cost: $9,845.00", "Monthly burn: $1,250.00",
                               "26 units a month", "short $1,783.00 at opening"],
        }
        for name, needles in expectations.items():
            code, out, _ = run_cli("report", str(ROOT / "examples" / name))
            self.assertEqual(code, 0)
            for needle in needles:
                with self.subTest(sample=name, needle=needle):
                    self.assertIn(needle, out)

    def test_edge_fixtures_report_without_crashing(self):
        for path in sorted(FIXTURES.glob("valid_*.json")):
            for fmt in ("text", "json", "html", "csv"):
                with self.subTest(path.name, fmt=fmt):
                    self.assertEqual(run_cli("report", str(path), "-f", fmt)[0], 0)

    def test_real_subprocess_module_entry_point(self):
        env = dict(os.environ, PYTHONPATH=str(SRC))
        proc = subprocess.run(
            [sys.executable, "-m", "startup_costs", "report", str(EXAMPLES[0]), "--format", "json"],
            capture_output=True, text=True, env=env, cwd=str(ROOT), check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["label"], LABEL)
        bad = subprocess.run(
            [sys.executable, "-m", "startup_costs", "validate", str(FIXTURES / "invalid_duplicates.json")],
            capture_output=True, text=True, env=env, cwd=str(ROOT), check=False,
        )
        self.assertEqual(bad.returncode, 1)
        self.assertIn("duplicate", bad.stderr)


if __name__ == "__main__":
    unittest.main()
