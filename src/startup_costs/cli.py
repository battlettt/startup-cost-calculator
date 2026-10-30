"""Command-line interface.

    python -m startup_costs init [PATH] [--force]
    python -m startup_costs validate INPUT
    python -m startup_costs report INPUT [--format text|json|html|csv] [--output PATH]

Exit codes: 0 success, 1 invalid input or file problem, 2 bad command usage.
"""

import argparse
import json
import os
import sys

from .model import LABEL, ValidationError, check, parse_json_text
from .reports import RENDERERS, build_report

EXAMPLE_INPUT = {
    "_comment": [
        "Startup cost model. Keys starting with an underscore are comments and are ignored.",
        "Amounts are plain numbers (no currency symbols). Every cost item needs name, amount, category.",
        "Run: python -m startup_costs report this-file.json --format text",
    ],
    "name": "Weekend market stall",
    "label": LABEL,
    "currency": "USD",
    "_comment_starting_cash": "Cash you have before spending anything.",
    "starting_cash": 6000,
    "_comment_contingency_pct": "Buffer added to one-time costs for surprises, 0-100. Default 10.",
    "contingency_pct": 10,
    "_comment_one_time_costs": "Paid once, before or at opening.",
    "one_time_costs": [
        {"name": "Folding gazebo and table", "amount": 650, "category": "equipment"},
        {"name": "Card reader", "amount": 60, "category": "equipment"},
        {"name": "Market permit (season)", "amount": 400, "category": "licensing"},
        {"name": "Opening stock", "amount": 900, "category": "inventory"},
        {"name": "Banner and price cards", "amount": 180, "category": "marketing"},
    ],
    "_comment_monthly_costs": "Paid every month whether or not you sell anything.",
    "monthly_costs": [
        {"name": "Pitch fees (4 weekends)", "amount": 240, "category": "facilities"},
        {"name": "Public liability insurance", "amount": 35, "category": "insurance"},
        {"name": "Van share and fuel", "amount": 160, "category": "transport"},
        {"name": "Phone and card fees", "amount": 40, "category": "software"},
    ],
    "_comment_revenue": [
        "Optional. unit_price and variable_cost_per_unit are required if present.",
        "monthly_units is your assumed sales volume; fixed_cost_override replaces",
        "the monthly cost total in the break-even maths (e.g. to include your own pay).",
    ],
    "revenue": {
        "unit_price": 12,
        "variable_cost_per_unit": 4.5,
        "monthly_units": 160,
        "fixed_cost_override": None,
    },
    "_comment_scenarios": [
        "Optional. Factors scale every item; overrides set one item's amount exactly",
        "(overrides are not scaled). 'kind' is one_time or monthly and is only needed",
        "when the same name appears in both lists. Omit to get lean/standard/premium defaults.",
    ],
    "scenarios": [
        {"name": "lean", "description": "Borrowed gazebo, smaller opening stock.",
         "one_time_factor": 0.8, "monthly_factor": 0.9,
         "overrides": [{"item": "Folding gazebo and table", "amount": 150}]},
        {"name": "standard", "description": "The plan as entered.",
         "one_time_factor": 1, "monthly_factor": 1},
        {"name": "premium", "description": "Branded gazebo, extra weekend, higher price.",
         "one_time_factor": 1.3, "monthly_factor": 1.25,
         "revenue": {"unit_price": 14}},
    ],
}


def _read_input(path):
    """Load, parse and validate a file. Returns (model, warnings)."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise ValidationError([f"{path}: cannot read file ({exc.strerror})"]) from None
    data = parse_json_text(text, source=path)
    model, errors, warnings = check(data)
    if errors:
        raise ValidationError(errors, warnings)
    return model, warnings


def _print_problems(exc, stream):
    count = len(exc.errors)
    print(f"Invalid input: {count} error{'s' if count != 1 else ''} found.", file=stream)
    for err in exc.errors:
        print(f"  error: {err}", file=stream)
    for warn in exc.warnings:
        print(f"  warning: {warn}", file=stream)


def cmd_init(args, out, err):
    path = args.path
    if os.path.exists(path) and not args.force:
        print(f"{path} already exists; use --force to overwrite it.", file=err)
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(EXAMPLE_INPUT, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote example input to {path}. Edit it, then run:", file=out)
    print(f"  python -m startup_costs report {path}", file=out)
    return 0


def cmd_validate(args, out, err):
    try:
        model, warnings = _read_input(args.input)
    except ValidationError as exc:
        _print_problems(exc, err)
        return 1
    print(
        f"OK: {args.input} is valid ({len(model['one_time_costs'])} one-time items, "
        f"{len(model['monthly_costs'])} monthly items, {len(model['scenarios'])} scenarios).",
        file=out,
    )
    for warn in warnings:
        print(f"  warning: {warn}", file=err)
    return 0


def cmd_report(args, out, err):
    try:
        model, warnings = _read_input(args.input)
    except ValidationError as exc:
        _print_problems(exc, err)
        return 1
    for warn in warnings:
        print(f"warning: {warn}", file=err)
    text = RENDERERS[args.format](build_report(model, warnings))
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print(f"Wrote {args.format} report to {args.output}", file=err)
    else:
        out.write(text)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="startup-costs",
        description="Estimate startup costs, runway and break-even for a small business idea.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="write a commented example input file")
    p.add_argument("path", nargs="?", default="startup-costs.json")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("validate", help="check an input file and list every problem")
    p.add_argument("input")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("report", help="calculate and print or export a report")
    p.add_argument("input")
    p.add_argument("--format", "-f", choices=sorted(RENDERERS), default="text")
    p.add_argument("--output", "-o", help="write to this file instead of stdout")
    p.set_defaults(func=cmd_report)
    return parser


def main(argv=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_parser().parse_args(argv)
    return args.func(args, out, err)


if __name__ == "__main__":
    sys.exit(main())
