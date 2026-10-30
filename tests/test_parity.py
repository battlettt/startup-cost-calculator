"""JS/CLI parity: run docs/app.js under Node and compare with the Python package.

Compares validation errors, warnings, the normalised model, the full analysis
(every number and every message) and the scenario comparison, on every sample,
every valid edge-case fixture and every invalid fixture.
"""

import json
import subprocess
import unittest

from tests.helpers import EXAMPLES, INVALID_FIXTURES, NODE, ROOT, VALID_FIXTURES, load_json

from startup_costs.calculations import analyze, format_money, format_number, round2
from startup_costs.cli import EXAMPLE_INPUT
from startup_costs.model import check
from startup_costs.scenarios import compare

RUNNER = ROOT / "tests" / "js" / "parity_runner.js"


def run_node(paths):
    proc = subprocess.run(
        [NODE, str(RUNNER)] + [str(p) for p in paths],
        capture_output=True, text=True, check=True, cwd=str(ROOT),
    )
    return json.loads(proc.stdout)


def node_eval(expr):
    script = (
        "const C = require(" + json.dumps(str(ROOT / "docs" / "app.js")) + ");"
        "process.stdout.write(JSON.stringify(" + expr + "));"
    )
    proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def python_result(path):
    model, errors, warnings = check(load_json(path))
    out = {"errors": errors, "warnings": warnings, "model": model}
    if model:
        out["analysis"] = analyze(model)
        out["comparison"] = compare(model)
    # normalise through JSON exactly like the Node side
    return json.loads(json.dumps(out))


@unittest.skipUnless(NODE, "node is required for the JS/CLI parity tests")
class Parity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = EXAMPLES + VALID_FIXTURES + INVALID_FIXTURES
        cls.js = run_node(cls.paths)

    def assert_same(self, path):
        py = python_result(path)
        js = self.js[str(path)]
        for key in ("errors", "warnings", "model", "analysis", "comparison"):
            with self.subTest(file=path.name, part=key):
                self.assertEqual(js.get(key), py.get(key))

    def test_samples_identical(self):
        self.assertGreaterEqual(len(EXAMPLES), 3)
        for path in EXAMPLES:
            self.assertIsNotNone(self.js[str(path)]["analysis"])
            self.assert_same(path)

    def test_edge_case_fixtures_identical(self):
        self.assertGreaterEqual(len(VALID_FIXTURES), 15)
        for path in VALID_FIXTURES:
            self.assert_same(path)

    def test_validation_errors_identical(self):
        self.assertGreaterEqual(len(INVALID_FIXTURES), 10)
        for path in INVALID_FIXTURES:
            self.assertTrue(self.js[str(path)]["errors"], path.name)
            self.assert_same(path)

    def test_headline_numbers_spelled_out(self):
        # A readable spot check on top of the deep comparison above.
        for path in EXAMPLES:
            py = python_result(path)["analysis"]
            js = self.js[str(path)]["analysis"]
            for getter in (
                lambda a: a["one_time"]["total"],
                lambda a: a["monthly"]["total"],
                lambda a: a["runway"]["months"],
                lambda a: a["break_even"]["units_whole"],
                lambda a: a["break_even"]["revenue"],
                lambda a: a["break_even"]["months_to_break_even"],
            ):
                self.assertEqual(getter(js), getter(py), path.name)

    def test_init_example_identical(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "init.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(EXAMPLE_INPUT, fh, ensure_ascii=False)
            js = run_node([p])[p]
            py = python_result(p)
            self.assertEqual(js, py)

    def test_rounding_and_formatting_helpers_identical(self):
        values = [0.125, 2.675, 1.005, -1.5, 1234567.891, 999.995, -0.001, 0, 0.1 + 0.2, 7.777e6]
        js = node_eval("[" + ",".join(
            f"[C.round2({v!r}), C.formatNumber({v!r}, 2), C.formatNumber({v!r}, 1), C.formatMoney({v!r}, 'GBP')]"
            for v in values) + "]")
        py = [[round2(v), format_number(v, 2), format_number(v, 1), format_money(v, "GBP")] for v in values]
        self.assertEqual(js, py)


class SamplesInSync(unittest.TestCase):
    def test_demo_samples_match_examples_exactly(self):
        proc = subprocess.run(
            ["python3", str(ROOT / "tools" / "sync_samples.py"), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)

    @unittest.skipUnless(NODE, "node is required")
    def test_samples_js_loads_to_the_example_files(self):
        script = (
            "global.window = {}; require(" + json.dumps(str(ROOT / "docs" / "samples.js")) + ");"
            "process.stdout.write(JSON.stringify(window.STARTUP_SAMPLES));"
        )
        proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(proc.stdout), [load_json(p) for p in EXAMPLES])


if __name__ == "__main__":
    unittest.main()
