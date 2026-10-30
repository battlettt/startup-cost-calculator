"""Core arithmetic: totals, contingency, runway and break-even.

Every function here has a twin in docs/app.js that performs the same
floating-point operations in the same order, so the CLI and the demo produce
identical numbers. Money is rounded to cents after each step with
:func:`round_to`, which rounds halves up (unlike Python's built-in ``round``,
which rounds halves to even and would disagree with JavaScript).
"""

import math

CURRENCY_SYMBOLS = {"USD": "$", "CAD": "$", "AUD": "$", "NZD": "$", "GBP": "£", "EUR": "€"}


def round_to(value, places):
    factor = 10 ** places
    return math.floor(value * factor + 0.5 + 1e-9) / factor


def round2(value):
    return round_to(value, 2)


def _group(digits):
    out = ""
    while len(digits) > 3:
        out = "," + digits[-3:] + out
        digits = digits[:-3]
    return digits + out


def format_number(value, decimals=2):
    """1234.5 -> '1,234.50'. Same output as Calc.formatNumber in app.js."""
    factor = 10 ** decimals
    scaled = math.floor(abs(value) * factor + 0.5 + 1e-9)
    whole = scaled // factor
    frac = scaled % factor
    text = _group(str(whole))
    if decimals > 0:
        text += "." + str(frac).zfill(decimals)
    sign = "-" if value < 0 and scaled != 0 else ""
    return sign + text


def format_money(value, currency="USD"):
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    text = format_number(value, 2)
    if text.startswith("-"):
        return "-" + symbol + text[1:]
    return symbol + text


def format_quantity(value):
    """Whole quantities without decimals, fractional ones with two."""
    if float(value).is_integer():
        return format_number(value, 0)
    return format_number(value, 2)


def sum_amounts(items):
    total = 0
    for item in items:
        total += item["amount"]
    return round2(total)


def category_totals(items):
    order = []
    sums = {}
    for item in items:
        cat = item["category"]
        if cat not in sums:
            order.append(cat)
            sums[cat] = 0
        sums[cat] += item["amount"]
    return [{"category": cat, "amount": round2(sums[cat])} for cat in order]


def compute_runway(starting_cash, one_time_total, burn, currency, net=False):
    """Months of runway = (starting cash - one-time total) / monthly burn.

    ``status`` is one of:
      * ``"shortfall"`` - cash does not even cover the one-time costs;
      * ``"unlimited"`` - burn is zero or negative, so cash never runs out;
      * ``"finite"``    - ``months`` holds the runway.
    """
    def money(v):
        return format_money(v, currency)

    after = round2(starting_cash - one_time_total)
    result = {
        "basis": "net_of_revenue" if net else "costs_only",
        "starting_cash": starting_cash,
        "one_time_total": one_time_total,
        "monthly_burn": burn,
        "cash_after_one_time": after,
        "status": "",
        "months": None,
        "shortfall": 0,
        "message": "",
    }
    if after < 0:
        shortfall = round2(0 - after)
        result["status"] = "shortfall"
        result["shortfall"] = shortfall
        result["message"] = (
            f"Not enough cash: the one-time costs ({money(one_time_total)} including "
            f"contingency) are more than the starting cash ({money(starting_cash)}). "
            f"You need at least {money(shortfall)} more just to open, before paying "
            "any monthly costs."
        )
    elif burn <= 0:
        result["status"] = "unlimited"
        if burn < 0:
            result["message"] = (
                f"Sales cover the monthly costs (net burn {money(burn)} a month), so "
                "cash grows instead of shrinking. Runway is not limited while these "
                f"assumptions hold; {money(after)} is left after one-time costs."
            )
        else:
            result["message"] = (
                f"Monthly burn is {money(0)}, so nothing drains cash each month. "
                f"Runway is not limited; {money(after)} is left after one-time costs."
            )
    else:
        months = round2(after / burn)
        result["status"] = "finite"
        result["months"] = months
        spending = (
            f"Losing {money(burn)} a month after sales"
            if net
            else f"Spending {money(burn)} a month with no sales"
        )
        result["message"] = (
            f"After one-time costs you have {money(after)} left. {spending}, that "
            f"lasts about {format_number(months, 1)} months."
        )
    return result


def compute_break_even(revenue, recurring_total, one_time_total, currency):
    """Break-even units/revenue and months to earn back the one-time costs."""
    def money(v):
        return format_money(v, currency)

    result = {
        "status": "no_revenue",
        "unit_price": None,
        "variable_cost_per_unit": None,
        "fixed_costs": None,
        "fixed_cost_source": None,
        "contribution_margin": None,
        "margin_pct": None,
        "units": None,
        "units_whole": None,
        "revenue": None,
        "monthly_units": None,
        "monthly_contribution": None,
        "monthly_profit": None,
        "months_status": "no_volume",
        "months_to_break_even": None,
        "message": (
            "No revenue assumptions were given, so break-even was not calculated. "
            'Add a "revenue" section with unit_price and variable_cost_per_unit.'
        ),
        "months_message": "",
    }
    if revenue is None:
        return result
    price = revenue["unit_price"]
    variable = revenue["variable_cost_per_unit"]
    override = revenue.get("fixed_cost_override")
    if override is not None:
        fixed = round2(override)
        result["fixed_cost_source"] = "override"
    else:
        fixed = recurring_total
        result["fixed_cost_source"] = "recurring_total"
    margin = round2(price - variable)
    result.update({
        "unit_price": price,
        "variable_cost_per_unit": variable,
        "fixed_costs": fixed,
        "contribution_margin": margin,
    })
    if price > 0:
        result["margin_pct"] = round2(margin / price * 100)
    if margin <= 0:
        result["status"] = "undefined"
        if margin == 0:
            result["message"] = (
                f"Break-even is undefined: each unit sells for {money(price)} and costs "
                f"{money(variable)} to make, so every sale earns {money(0)} toward fixed "
                f"costs. No number of sales can cover {money(fixed)} a month. Raise the "
                "price or lower the variable cost per unit."
            )
        else:
            result["message"] = (
                f"Break-even is undefined: each unit sells for {money(price)} but costs "
                f"{money(variable)} to make, so every sale loses {money(0 - margin)}. "
                f"Selling more only loses more, so no number of sales can cover "
                f"{money(fixed)} a month. Raise the price or lower the variable cost per unit."
            )
    else:
        units = fixed / margin
        whole = math.ceil(round_to(units, 6))
        sales = round2(units * price)
        result.update({
            "status": "ok",
            "units": round2(units),
            "units_whole": whole,
            "revenue": sales,
        })
        result["message"] = (
            f"Each unit earns {money(margin)} toward fixed costs "
            f"({format_number(result['margin_pct'], 1)}% of the price). To cover "
            f"{money(fixed)} of fixed costs a month you need {format_number(whole, 0)} "
            f"units a month, about {money(sales)} in sales."
        )

    volume = revenue.get("monthly_units")
    if volume is None:
        result["months_message"] = (
            'Add "monthly_units" to the revenue section to estimate how many months '
            "it takes to earn back the one-time costs."
        )
        return result
    contribution = round2(volume * margin)
    profit = round2(contribution - fixed)
    result["monthly_units"] = volume
    result["monthly_contribution"] = contribution
    result["monthly_profit"] = profit
    qty = format_quantity(volume)
    if profit <= 0:
        result["months_status"] = "never"
        text = (
            f"At {qty} units a month you bring in {money(contribution)} toward fixed "
            f"costs of {money(fixed)}, a shortfall of {money(0 - profit)} a month. At this "
            f"volume the one-time costs ({money(one_time_total)}) are never earned back"
        )
        if result["status"] == "ok":
            text += (
                f"; you need about {format_number(result['units_whole'], 0)} units a "
                "month just to cover fixed costs."
            )
        else:
            text += " because every sale loses money or breaks even."
        result["months_message"] = text
    else:
        months = round2(one_time_total / profit)
        result["months_status"] = "ok"
        result["months_to_break_even"] = months
        result["months_message"] = (
            f"At {qty} units a month you make {money(profit)} a month after fixed "
            f"costs, which earns back the {money(one_time_total)} one-time cost in "
            f"about {format_number(months, 1)} months."
        )
    return result


def analyze(model):
    """Full analysis of one normalised model (see model.check)."""
    currency = model["currency"]
    one_time_items = model["one_time_costs"]
    monthly_items = model["monthly_costs"]
    subtotal = sum_amounts(one_time_items)
    pct = model["contingency_pct"]
    contingency = round2(subtotal * pct / 100)
    one_time_total = round2(subtotal + contingency)
    burn = sum_amounts(monthly_items)
    runway = compute_runway(model["starting_cash"], one_time_total, burn, currency)
    break_even = compute_break_even(model["revenue"], burn, one_time_total, currency)
    runway_with_revenue = None
    if break_even["monthly_contribution"] is not None:
        net_burn = round2(burn - break_even["monthly_contribution"])
        runway_with_revenue = compute_runway(
            model["starting_cash"], one_time_total, net_burn, currency, net=True
        )
    return {
        "name": model["name"],
        "label": model["label"],
        "currency": currency,
        "starting_cash": model["starting_cash"],
        "one_time": {
            "items": [dict(i) for i in one_time_items],
            "subtotal": subtotal,
            "contingency_pct": pct,
            "contingency_amount": contingency,
            "total": one_time_total,
            "by_category": category_totals(one_time_items),
        },
        "monthly": {
            "items": [dict(i) for i in monthly_items],
            "total": burn,
            "by_category": category_totals(monthly_items),
        },
        "runway": runway,
        "runway_with_revenue": runway_with_revenue,
        "break_even": break_even,
    }
