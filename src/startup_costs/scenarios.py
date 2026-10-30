"""Scenarios: scale and override a base model, compare side by side.

Mirrored by Calc.applyScenario / Calc.compare in docs/app.js.
"""

from .calculations import analyze, format_money, format_number, round2


def _scale(items, kind, factor, overrides):
    out = []
    for item in items:
        key = kind + ":" + item["name"]
        if key in overrides:
            amount = overrides[key]
        else:
            amount = round2(item["amount"] * factor)
        out.append({"name": item["name"], "amount": amount, "category": item["category"]})
    return out


def apply_scenario(model, scenario):
    """Return a new model with the scenario's factors and overrides applied.

    Factors multiply every item; an override replaces one item's amount
    outright (it is *not* scaled by the factor). Scenario revenue fields
    replace the matching base revenue fields.
    """
    overrides = {o["kind"] + ":" + o["item"]: o["amount"] for o in scenario["overrides"]}
    revenue = model["revenue"]
    if scenario.get("revenue"):
        merged = {"monthly_units": None, "fixed_cost_override": None}
        if revenue is not None:
            merged.update(revenue)
        merged.update(scenario["revenue"])
        revenue = merged
    elif revenue is not None:
        revenue = dict(revenue)
    return {
        "name": model["name"] + " (" + scenario["name"] + ")",
        "label": model["label"],
        "currency": model["currency"],
        "starting_cash": model["starting_cash"],
        "contingency_pct": model["contingency_pct"],
        "one_time_costs": _scale(
            model["one_time_costs"], "one_time", scenario["one_time_factor"], overrides
        ),
        "monthly_costs": _scale(
            model["monthly_costs"], "monthly", scenario["monthly_factor"], overrides
        ),
        "revenue": revenue,
        "scenarios": [],
    }


def join_names(names):
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1] + " (tie)"


def runway_text(runway, currency):
    if runway["status"] == "finite":
        return format_number(runway["months"], 1) + " months"
    if runway["status"] == "unlimited":
        return "unlimited"
    return "short " + format_money(runway["shortfall"], currency) + " at opening"


def _runway_score(runway):
    """Larger is better: shortfall < finite < unlimited."""
    if runway["status"] == "shortfall":
        return [0, 0 - runway["shortfall"]]
    if runway["status"] == "finite":
        return [1, runway["months"]]
    return [2, runway["cash_after_one_time"]]


def _best(rows, score, prefer_low):
    """Names of the rows with the best score (lists compare element-wise)."""
    best = None
    names = []
    for row in rows:
        value = score(row)
        better = best is None or (value < best if prefer_low else value > best)
        if better:
            best = value
            names = [row["name"]]
        elif value == best:
            names.append(row["name"])
    return best, names


def _winners(rows, currency):
    money = lambda v: format_money(v, currency)  # noqa: E731
    winners = []

    best, names = _best(rows, lambda r: [r["analysis"]["one_time"]["total"]], True)
    winners.append({
        "metric": "one_time_total",
        "title": "Cheapest to launch",
        "winners": names,
        "statement": f"Cheapest to launch: {join_names(names)} ({money(best[0])} one-time, "
                     "including contingency).",
    })

    best, names = _best(rows, lambda r: [r["analysis"]["monthly"]["total"]], True)
    winners.append({
        "metric": "monthly_burn",
        "title": "Lowest monthly burn",
        "winners": names,
        "statement": f"Lowest monthly burn: {join_names(names)} ({money(best[0])} a month).",
    })

    best, names = _best(rows, lambda r: _runway_score(r["analysis"]["runway"]), False)
    first = next(r for r in rows if r["name"] == names[0])
    text = runway_text(first["analysis"]["runway"], currency)
    if best[0] == 0:
        statement = (
            "Longest runway: none of the scenarios can open with the starting cash; "
            f"{join_names(names)} comes closest ({text})."
        )
    else:
        statement = f"Longest runway: {join_names(names)} ({text})."
    winners.append({
        "metric": "runway",
        "title": "Longest runway",
        "winners": names,
        "statement": statement,
    })

    defined = [r for r in rows if r["analysis"]["break_even"]["status"] == "ok"]
    if defined:
        best, names = _best(defined, lambda r: [r["analysis"]["break_even"]["units"]], True)
        whole = next(r for r in defined if r["name"] == names[0])["analysis"]["break_even"]["units_whole"]
        statement = (
            f"Fewest sales needed to break even: {join_names(names)} "
            f"({format_number(whole, 0)} units a month)."
        )
    else:
        names = []
        statement = (
            "Fewest sales needed to break even: not available, because break-even is "
            "undefined or not calculated in every scenario."
        )
    winners.append({
        "metric": "break_even_units",
        "title": "Fewest sales to break even",
        "winners": names,
        "statement": statement,
    })
    return winners


def compare(model):
    """Analyse every scenario of a model and pick a winner per metric."""
    rows = []
    for scenario in model["scenarios"]:
        rows.append({
            "name": scenario["name"],
            "description": scenario["description"],
            "one_time_factor": scenario["one_time_factor"],
            "monthly_factor": scenario["monthly_factor"],
            "overrides": [dict(o) for o in scenario["overrides"]],
            "revenue_overrides": dict(scenario["revenue"]) if scenario.get("revenue") else None,
            "analysis": analyze(apply_scenario(model, scenario)),
        })
    winners = _winners(rows, model["currency"]) if rows else []
    return {"scenarios": rows, "winners": winners}
