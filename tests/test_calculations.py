import unittest

from tests.helpers import base, model_of

from startup_costs.calculations import (
    analyze, category_totals, compute_break_even, compute_runway, format_money,
    format_number, format_quantity, round2, round_to, sum_amounts,
)


class RoundingAndFormatting(unittest.TestCase):
    def test_round_half_up_not_bankers(self):
        self.assertEqual(round2(0.125), 0.13)   # built-in round() gives 0.12
        self.assertEqual(round2(2.675), 2.68)   # binary 2.67499999... still rounds up
        self.assertEqual(round2(1.005), 1.01)
        self.assertEqual(round2(-1.5), -1.5)
        self.assertEqual(round2(10), 10)

    def test_round_to_places(self):
        self.assertEqual(round_to(1.23456789, 6), 1.234568)
        self.assertEqual(round_to(2.5, 0), 3)

    def test_format_number_groups_thousands(self):
        self.assertEqual(format_number(1234567.891), "1,234,567.89")
        self.assertEqual(format_number(0), "0.00")
        self.assertEqual(format_number(-1200.5), "-1,200.50")
        self.assertEqual(format_number(-0.001), "0.00")
        self.assertEqual(format_number(999.995, 2), "1,000.00")
        self.assertEqual(format_number(1.25, 1), "1.3")
        self.assertEqual(format_number(42, 0), "42")

    def test_format_money_symbols(self):
        self.assertEqual(format_money(1500, "USD"), "$1,500.00")
        self.assertEqual(format_money(-20, "USD"), "-$20.00")
        self.assertEqual(format_money(3, "GBP"), "£3.00")
        self.assertEqual(format_money(3, "EUR"), "€3.00")
        self.assertEqual(format_money(3, "JPY"), "JPY 3.00")

    def test_format_quantity(self):
        self.assertEqual(format_quantity(1200), "1,200")
        self.assertEqual(format_quantity(37.5), "37.50")


class Totals(unittest.TestCase):
    def test_sum_amounts_handles_float_noise(self):
        items = [{"amount": 0.1}, {"amount": 0.2}]
        self.assertEqual(sum_amounts(items), 0.3)
        self.assertEqual(sum_amounts([]), 0)

    def test_category_totals_keep_first_seen_order(self):
        items = [
            {"amount": 5, "category": "b"},
            {"amount": 1, "category": "a"},
            {"amount": 2.5, "category": "b"},
        ]
        self.assertEqual(
            category_totals(items),
            [{"category": "b", "amount": 7.5}, {"category": "a", "amount": 1}],
        )


class AnalyzeBase(unittest.TestCase):
    """Hand-checked numbers for tests.helpers.BASE."""

    def setUp(self):
        self.a = analyze(model_of(base()))

    def test_one_time_with_contingency(self):
        ot = self.a["one_time"]
        self.assertEqual(ot["subtotal"], 3500)        # 3000 + 500
        self.assertEqual(ot["contingency_amount"], 350)  # 10% of 3500
        self.assertEqual(ot["total"], 3850)

    def test_monthly_burn(self):
        self.assertEqual(self.a["monthly"]["total"], 900)

    def test_runway(self):
        r = self.a["runway"]
        self.assertEqual(r["status"], "finite")
        self.assertEqual(r["cash_after_one_time"], 6150)  # 10000 - 3850
        self.assertEqual(r["months"], 6.83)               # 6150 / 900
        self.assertIn("6.8 months", r["message"])

    def test_break_even(self):
        be = self.a["break_even"]
        self.assertEqual(be["status"], "ok")
        self.assertEqual(be["contribution_margin"], 6)    # 10 - 4
        self.assertEqual(be["margin_pct"], 60)
        self.assertEqual(be["fixed_cost_source"], "recurring_total")
        self.assertEqual(be["units"], 150)                # 900 / 6
        self.assertEqual(be["units_whole"], 150)
        self.assertEqual(be["revenue"], 1500)

    def test_months_to_break_even(self):
        be = self.a["break_even"]
        self.assertEqual(be["monthly_contribution"], 1200)  # 200 * 6
        self.assertEqual(be["monthly_profit"], 300)          # 1200 - 900
        self.assertEqual(be["months_status"], "ok")
        self.assertEqual(be["months_to_break_even"], 12.83)  # 3850 / 300

    def test_runway_with_revenue_is_unlimited(self):
        rr = self.a["runway_with_revenue"]
        self.assertEqual(rr["monthly_burn"], -300)
        self.assertEqual(rr["status"], "unlimited")
        self.assertIn("cash grows", rr["message"])


class Contingency(unittest.TestCase):
    def test_zero_percent(self):
        ot = analyze(model_of(base(contingency_pct=0)))["one_time"]
        self.assertEqual(ot["contingency_amount"], 0)
        self.assertEqual(ot["total"], 3500)

    def test_hundred_percent_doubles(self):
        ot = analyze(model_of(base(contingency_pct=100)))["one_time"]
        self.assertEqual(ot["contingency_amount"], 3500)
        self.assertEqual(ot["total"], 7000)

    def test_default_is_ten_percent(self):
        ot = analyze(model_of(base(contingency_pct=None)))["one_time"]
        self.assertEqual(ot["contingency_pct"], 10)
        self.assertEqual(ot["total"], 3850)

    def test_fractional_percent(self):
        ot = analyze(model_of(base(contingency_pct=12.5)))["one_time"]
        self.assertEqual(ot["contingency_amount"], 437.5)


class Runway(unittest.TestCase):
    def test_zero_burn_is_unlimited_not_a_crash(self):
        r = compute_runway(5000, 1000, 0, "USD")
        self.assertEqual(r["status"], "unlimited")
        self.assertIsNone(r["months"])
        self.assertIn("not limited", r["message"])

    def test_negative_burn_is_unlimited(self):
        r = compute_runway(5000, 1000, -50, "USD", net=True)
        self.assertEqual(r["status"], "unlimited")
        self.assertIn("cash grows", r["message"])

    def test_shortfall_says_how_much_more_is_needed(self):
        r = compute_runway(2000, 3850, 900, "USD")
        self.assertEqual(r["status"], "shortfall")
        self.assertEqual(r["shortfall"], 1850)
        self.assertIsNone(r["months"])
        self.assertIn("$1,850.00 more", r["message"])

    def test_shortfall_wins_over_zero_burn(self):
        r = compute_runway(100, 200, 0, "USD")
        self.assertEqual(r["status"], "shortfall")
        self.assertEqual(r["shortfall"], 100)

    def test_exactly_enough_cash_gives_zero_months(self):
        r = compute_runway(3850, 3850, 900, "USD")
        self.assertEqual(r["status"], "finite")
        self.assertEqual(r["months"], 0)

    def test_net_wording(self):
        r = compute_runway(5000, 1000, 400, "USD", net=True)
        self.assertEqual(r["months"], 10)
        self.assertIn("after sales", r["message"])

    def test_shortfall_from_model(self):
        r = analyze(model_of(base(starting_cash=2000)))["runway"]
        self.assertEqual(r["status"], "shortfall")
        self.assertEqual(r["cash_after_one_time"], -1850)


class BreakEven(unittest.TestCase):
    def rev(self, **kw):
        r = {"unit_price": 10, "variable_cost_per_unit": 4, "monthly_units": None,
             "fixed_cost_override": None}
        r.update(kw)
        return r

    def test_price_below_variable_is_undefined(self):
        be = compute_break_even(self.rev(unit_price=3, variable_cost_per_unit=3.5), 900, 3850, "USD")
        self.assertEqual(be["status"], "undefined")
        self.assertIsNone(be["units"])
        self.assertIsNone(be["units_whole"])
        self.assertIsNone(be["revenue"])
        self.assertEqual(be["contribution_margin"], -0.5)
        self.assertIn("every sale loses $0.50", be["message"])
        self.assertNotIn("inf", be["message"].lower())

    def test_price_equal_to_variable_is_undefined(self):
        be = compute_break_even(self.rev(unit_price=4, variable_cost_per_unit=4), 900, 3850, "USD")
        self.assertEqual(be["status"], "undefined")
        self.assertIn("earns $0.00", be["message"])

    def test_undefined_with_volume_never_earns_back(self):
        be = compute_break_even(self.rev(unit_price=3, variable_cost_per_unit=3.5, monthly_units=100), 900, 3850, "USD")
        self.assertEqual(be["months_status"], "never")
        self.assertIsNone(be["months_to_break_even"])
        self.assertIn("every sale loses money", be["months_message"])

    def test_zero_price_zero_variable(self):
        be = compute_break_even(self.rev(unit_price=0, variable_cost_per_unit=0), 900, 0, "USD")
        self.assertEqual(be["status"], "undefined")
        self.assertIsNone(be["margin_pct"])

    def test_fractional_units_round_up_to_whole_units(self):
        be = compute_break_even(self.rev(fixed_cost_override=1500.5), 900, 3850, "USD")
        self.assertEqual(be["fixed_cost_source"], "override")
        self.assertEqual(be["fixed_costs"], 1500.5)
        self.assertEqual(be["units"], 250.08)
        self.assertEqual(be["units_whole"], 251)

    def test_float_noise_does_not_add_a_unit(self):
        # 3000 / 0.3 = 10000.000000000002 in binary floating point
        be = compute_break_even(self.rev(unit_price=1.3, variable_cost_per_unit=1), 3000, 0, "USD")
        self.assertEqual(be["units_whole"], 10000)

    def test_zero_fixed_costs_break_even_at_zero(self):
        be = compute_break_even(self.rev(), 0, 0, "USD")
        self.assertEqual(be["units"], 0)
        self.assertEqual(be["units_whole"], 0)

    def test_volume_below_break_even_never_pays_back(self):
        be = compute_break_even(self.rev(monthly_units=100), 900, 3850, "USD")
        self.assertEqual(be["monthly_profit"], -300)
        self.assertEqual(be["months_status"], "never")
        self.assertIn("about 150 units", be["months_message"])

    def test_exactly_break_even_volume_never_pays_back(self):
        be = compute_break_even(self.rev(monthly_units=150), 900, 3850, "USD")
        self.assertEqual(be["monthly_profit"], 0)
        self.assertEqual(be["months_status"], "never")

    def test_no_one_time_costs_pays_back_immediately(self):
        be = compute_break_even(self.rev(monthly_units=200), 900, 0, "USD")
        self.assertEqual(be["months_to_break_even"], 0)

    def test_no_volume_explains_what_to_add(self):
        be = compute_break_even(self.rev(), 900, 3850, "USD")
        self.assertEqual(be["months_status"], "no_volume")
        self.assertIn("monthly_units", be["months_message"])

    def test_no_revenue(self):
        be = compute_break_even(None, 900, 3850, "USD")
        self.assertEqual(be["status"], "no_revenue")
        self.assertIn("not calculated", be["message"])
        a = analyze(model_of(base(revenue=None)))
        self.assertIsNone(a["runway_with_revenue"])
        self.assertEqual(a["break_even"]["status"], "no_revenue")


class EmptyLists(unittest.TestCase):
    def test_empty_lists_compute_zeroes(self):
        a = analyze(model_of(base(one_time_costs=[], monthly_costs=[])))
        self.assertEqual(a["one_time"]["total"], 0)
        self.assertEqual(a["monthly"]["total"], 0)
        self.assertEqual(a["runway"]["status"], "unlimited")
        self.assertEqual(a["break_even"]["units"], 0)


if __name__ == "__main__":
    unittest.main()
