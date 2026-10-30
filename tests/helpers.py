"""Shared test helpers. Puts src/ on sys.path so tests run without installing."""

import contextlib
import copy
import io
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from startup_costs import cli  # noqa: E402
from startup_costs.model import LABEL, check  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*.json"))
FIXTURES = ROOT / "tests" / "fixtures"
VALID_FIXTURES = sorted(FIXTURES.glob("valid_*.json"))
INVALID_FIXTURES = sorted(FIXTURES.glob("invalid_*.json"))
NODE = shutil.which("node")

BASE = {
    "name": "Test stall",
    "label": LABEL,
    "starting_cash": 10000,
    "contingency_pct": 10,
    "one_time_costs": [
        {"name": "Oven", "amount": 3000, "category": "equipment"},
        {"name": "Permit", "amount": 500, "category": "licensing"},
    ],
    "monthly_costs": [
        {"name": "Rent", "amount": 800, "category": "facilities"},
        {"name": "Insurance", "amount": 100, "category": "insurance"},
    ],
    "revenue": {"unit_price": 10, "variable_cost_per_unit": 4, "monthly_units": 200},
}


def base(**changes):
    """A deep copy of BASE with top-level keys replaced (None deletes a key)."""
    data = copy.deepcopy(BASE)
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


def model_of(data):
    model, errors, _ = check(data)
    if errors:
        raise AssertionError("unexpected errors: " + "; ".join(errors))
    return model


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def run_cli(*argv):
    """Run the CLI in-process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            code = cli.main(list(argv), out=out, err=err)
    except SystemExit as exc:  # argparse usage errors
        code = exc.code
    return code, out.getvalue(), err.getvalue()
