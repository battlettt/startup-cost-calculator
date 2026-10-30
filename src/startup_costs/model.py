"""Input model: validation and normalisation of a cost-model JSON document.

Every check here is mirrored line-for-line in docs/app.js (``Calc.check``) so
the demo reports exactly the same errors and warnings as the CLI. If you
change a message here, change it there too; the parity tests will tell you.

Keys that start with an underscore (for example ``"_comment"``) are treated
as comments and ignored everywhere, because JSON has no comment syntax.
"""

import copy
import json
import math

LABEL = "SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA"

DEFAULT_CURRENCY = "USD"
DEFAULT_CONTINGENCY_PCT = 10

TOP_FIELDS = (
    "name", "label", "currency", "starting_cash", "contingency_pct",
    "one_time_costs", "monthly_costs", "revenue", "scenarios",
)
ITEM_FIELDS = ("name", "amount", "category")
REVENUE_FIELDS = (
    "unit_price", "variable_cost_per_unit", "monthly_units", "fixed_cost_override",
)
SCENARIO_FIELDS = (
    "name", "description", "one_time_factor", "monthly_factor", "overrides", "revenue",
)
OVERRIDE_FIELDS = ("item", "amount", "kind")

COST_LISTS = ("one_time_costs", "monthly_costs")
LIST_FOR_KIND = {"one_time": "one_time_costs", "monthly": "monthly_costs"}
KINDS = ("one_time", "monthly")

DEFAULT_SCENARIOS = [
    {
        "name": "lean",
        "description": "Second-hand equipment, fewer paid tools, owner does more.",
        "one_time_factor": 0.8,
        "monthly_factor": 0.85,
        "overrides": [],
        "revenue": None,
    },
    {
        "name": "standard",
        "description": "The plan as entered.",
        "one_time_factor": 1,
        "monthly_factor": 1,
        "overrides": [],
        "revenue": None,
    },
    {
        "name": "premium",
        "description": "New equipment, stronger branding, more paid help.",
        "one_time_factor": 1.35,
        "monthly_factor": 1.25,
        "overrides": [],
        "revenue": None,
    },
]


class ValidationError(Exception):
    """Raised by :func:`load` when the input has one or more errors."""

    def __init__(self, errors, warnings=()):
        self.errors = list(errors)
        self.warnings = list(warnings)
        super().__init__("\n".join(self.errors))


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def quote(text):
    return json.dumps(text, ensure_ascii=False)


def plain_number(value):
    """Format a number the same way JavaScript's String() would."""
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if float(value).is_integer() and abs(value) < 1e15:
        return str(int(value))
    return repr(float(value))


def describe(value):
    """Describe a bad value for an error message."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return plain_number(value)
    if isinstance(value, str):
        return "text " + quote(value)
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return type(value).__name__


def _present(obj, key, required):
    """True if the key should be checked (optional keys may be null = unset)."""
    if key not in obj:
        return False
    return obj[key] is not None or required


def _unknown(errors, where, obj, allowed):
    extra = sorted(k for k in obj if k not in allowed and not k.startswith("_"))
    for key in extra:
        errors.append(
            f"{where}: unknown field {quote(key)} (allowed: {', '.join(allowed)})"
        )


def _number(errors, where, obj, key, required, high=None):
    if not _present(obj, key, required):
        if required:
            errors.append(f"{where}: missing required field {quote(key)}")
        return None
    value = obj[key]
    if not is_number(value):
        errors.append(f"{where}: {quote(key)} must be a number, got {describe(value)}")
        return None
    if high is not None and (value < 0 or value > high):
        errors.append(
            f"{where}: {quote(key)} must be between 0 and {high} (got {describe(value)})"
        )
        return None
    if value < 0:
        errors.append(f"{where}: {quote(key)} must not be negative (got {describe(value)})")
        return None
    return value


def _text(errors, where, obj, key, required):
    if not _present(obj, key, required):
        if required:
            errors.append(f"{where}: missing required field {quote(key)}")
        return None
    value = obj[key]
    if not is_text(value):
        errors.append(f"{where}: {quote(key)} must be non-empty text, got {describe(value)}")
        return None
    return value.strip()


def _items(errors, warnings, data, list_key):
    """Validate one cost list. Returns (valid_items, all_names_seen)."""
    if list_key not in data:
        errors.append(
            f"input: missing required field {quote(list_key)} (use [] if there are none)"
        )
        return [], []
    raw = data[list_key]
    if not isinstance(raw, list):
        errors.append(f"input: {quote(list_key)} must be a list, got {describe(raw)}")
        return [], []
    if len(raw) == 0:
        kind = "one-time" if list_key == "one_time_costs" else "monthly"
        warnings.append(
            f"{list_key} is empty: no {kind} costs will be counted. "
            "Double-check that nothing was forgotten."
        )
        return [], []
    items = []
    names = []
    seen = {}
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            errors.append(
                f'{list_key} item {index}: must be an object with "name", "amount" '
                f"and \"category\", got {describe(item)}"
            )
            continue
        where = f"{list_key} item {index}"
        if is_text(item.get("name")):
            where += f" ({quote(item['name'].strip())})"
        _unknown(errors, where, item, ITEM_FIELDS)
        name = _text(errors, where, item, "name", True)
        amount = _number(errors, where, item, "amount", True)
        category = _text(errors, where, item, "category", True)
        if name is not None:
            if name in seen:
                errors.append(
                    f"{where}: duplicate name {quote(name)} (also item {seen[name]}); "
                    f"names must be unique within {list_key} so scenarios can refer to them"
                )
            else:
                seen[name] = index
                names.append(name)
        if name is not None and amount is not None and category is not None:
            items.append({"name": name, "amount": amount, "category": category})
    return items, names


def _revenue(errors, where, raw, partial):
    if not isinstance(raw, dict):
        errors.append(f"{where}: must be an object, got {describe(raw)}")
        return None
    _unknown(errors, where, raw, REVENUE_FIELDS)
    out = {}
    for key in REVENUE_FIELDS:
        required = not partial and key in ("unit_price", "variable_cost_per_unit")
        value = _number(errors, where, raw, key, required)
        if value is not None:
            out[key] = value
    return out


def _overrides(errors, where, raw, names):
    if not isinstance(raw, list):
        errors.append(f'{where}: "overrides" must be a list, got {describe(raw)}')
        return []
    out = []
    targeted = {}
    for index, ov in enumerate(raw, start=1):
        ow = f"{where} override {index}"
        if not isinstance(ov, dict):
            errors.append(f'{ow}: must be an object with "item" and "amount", got {describe(ov)}')
            continue
        _unknown(errors, ow, ov, OVERRIDE_FIELDS)
        item = _text(errors, ow, ov, "item", True)
        amount = _number(errors, ow, ov, "amount", True)
        kind = None
        if _present(ov, "kind", False):
            if ov["kind"] not in KINDS:
                errors.append(
                    f'{ow}: "kind" must be "one_time" or "monthly", got {describe(ov["kind"])}'
                )
                continue
            kind = ov["kind"]
        if item is None:
            continue
        kinds = [kind] if kind is not None else list(KINDS)
        found = [k for k in kinds if item in names[LIST_FOR_KIND[k]]]
        if len(found) == 0:
            place = LIST_FOR_KIND[kind] if kind is not None else "one_time_costs or monthly_costs"
            errors.append(f"{ow}: no item named {quote(item)} in {place}")
            continue
        if len(found) > 1:
            errors.append(
                f"{ow}: {quote(item)} exists in both one_time_costs and monthly_costs; "
                'add "kind": "one_time" or "monthly"'
            )
            continue
        key = found[0] + ":" + item
        if key in targeted:
            errors.append(f"{ow}: {quote(item)} is already overridden by override {targeted[key]}")
            continue
        targeted[key] = index
        if amount is not None:
            out.append({"item": item, "kind": found[0], "amount": amount})
    return out


def _scenarios(errors, warnings, data, names, has_revenue):
    if not _present(data, "scenarios", False):
        return copy.deepcopy(DEFAULT_SCENARIOS)
    raw = data["scenarios"]
    if not isinstance(raw, list):
        errors.append(f'input: "scenarios" must be a list, got {describe(raw)}')
        return []
    if len(raw) == 0:
        warnings.append(
            "scenarios is empty: the built-in lean / standard / premium scenarios will be used."
        )
        return copy.deepcopy(DEFAULT_SCENARIOS)
    out = []
    seen = {}
    for index, sc in enumerate(raw, start=1):
        if not isinstance(sc, dict):
            errors.append(
                f'scenarios item {index}: must be an object with at least a "name", '
                f"got {describe(sc)}"
            )
            continue
        where = f"scenarios item {index}"
        if is_text(sc.get("name")):
            where += f" ({quote(sc['name'].strip())})"
        _unknown(errors, where, sc, SCENARIO_FIELDS)
        name = _text(errors, where, sc, "name", True)
        if name is not None:
            if name in seen:
                errors.append(f"{where}: duplicate scenario name {quote(name)} (also item {seen[name]})")
            else:
                seen[name] = index
        description = _text(errors, where, sc, "description", False)
        one_time_factor = _number(errors, where, sc, "one_time_factor", False)
        monthly_factor = _number(errors, where, sc, "monthly_factor", False)
        overrides = []
        if _present(sc, "overrides", False):
            overrides = _overrides(errors, where, sc["overrides"], names)
        revenue = None
        if _present(sc, "revenue", False):
            revenue = _revenue(errors, where + " revenue", sc["revenue"], True)
            if revenue is not None and not has_revenue:
                for key in ("unit_price", "variable_cost_per_unit"):
                    if key not in sc["revenue"]:
                        errors.append(
                            f"{where} revenue: {quote(key)} is required here because the "
                            'input has no top-level "revenue" section'
                        )
        out.append({
            "name": name if name is not None else f"scenario {index}",
            "description": description if description is not None else "",
            "one_time_factor": one_time_factor if one_time_factor is not None else 1,
            "monthly_factor": monthly_factor if monthly_factor is not None else 1,
            "overrides": overrides,
            "revenue": revenue,
        })
    return out


def check(data):
    """Validate a parsed JSON document.

    Returns ``(model, errors, warnings)``. ``model`` is the normalised input
    (defaults filled in) when there are no errors, otherwise ``None``.
    """
    errors = []
    warnings = []
    if not isinstance(data, dict):
        errors.append(f"input: the top level must be a JSON object, got {describe(data)}")
        return None, errors, warnings
    _unknown(errors, "input", data, TOP_FIELDS)
    name = _text(errors, "input", data, "name", True)
    label = _text(errors, "input", data, "label", False)
    currency = _text(errors, "input", data, "currency", False)
    starting_cash = _number(errors, "input", data, "starting_cash", True)
    contingency = _number(errors, "input", data, "contingency_pct", False, high=100)
    one_time, one_time_names = _items(errors, warnings, data, "one_time_costs")
    monthly, monthly_names = _items(errors, warnings, data, "monthly_costs")
    revenue = None
    if _present(data, "revenue", False):
        revenue = _revenue(errors, "revenue", data["revenue"], False)
        if revenue is not None:
            revenue.setdefault("monthly_units", None)
            revenue.setdefault("fixed_cost_override", None)
    else:
        warnings.append(
            'No "revenue" section: break-even will not be calculated. Add unit_price '
            "and variable_cost_per_unit to see it."
        )
    names = {"one_time_costs": one_time_names, "monthly_costs": monthly_names}
    scenarios = _scenarios(errors, warnings, data, names, _present(data, "revenue", False))
    if errors:
        return None, errors, warnings
    model = {
        "name": name,
        "label": label if label is not None else "",
        "currency": currency if currency is not None else DEFAULT_CURRENCY,
        "starting_cash": starting_cash,
        "contingency_pct": contingency if contingency is not None else DEFAULT_CONTINGENCY_PCT,
        "one_time_costs": one_time,
        "monthly_costs": monthly,
        "revenue": revenue,
        "scenarios": scenarios,
    }
    return model, errors, warnings


def load(data):
    """Return the normalised model or raise :class:`ValidationError`."""
    model, errors, warnings = check(data)
    if errors:
        raise ValidationError(errors, warnings)
    return model


def parse_json_text(text, source="input"):
    """Parse JSON text, turning syntax errors into a readable ValidationError."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            [f"{source}: not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}"]
        ) from None
