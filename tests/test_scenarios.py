import unittest

from tests.helpers import base, model_of

from startup_costs.scenarios import apply_scenario, compare, join_names, runway_text


def scenario(**kw):
    s = {"name": "s", "description": "", "one_time_factor": 1, "monthly_factor": 1,
         "overrides": [], "revenue": None}
    s.update(kw)
    return s


class ApplyScenario(unittest.TestCase):
    def setUp(self):
        self.model = model_of(base())

    def amounts(self, m, key):
        return [i["amount"] for i in m[key]]

    def test_factors_scale_every_item(self):
        m = apply_scenario(self.model, scenario(one_time_factor=0.8, monthly_factor=1.25))
        self.assertEqual(self.amounts(m, "one_time_costs"), [2400, 400])
        self.assertEqual(self.amounts(m, "monthly_costs"), [1000, 125])

    def test_override_replaces_and_is_not_scaled(self):
        m = apply_scenario(self.model, scenario(
            one_time_factor=0.5, monthly_factor=0.5,
            overrides=[{"item": "Oven", "kind": "one_time", "amount": 2500},
                       {"item": "Rent", "kind": "monthly", "amount": 0}]))
        self.assertEqual(self.amounts(m, "one_time_costs"), [2500, 250])
        self.assertEqual(self.amounts(m, "monthly_costs"), [0, 50])

    def test_base_model_is_not_mutated(self):
        apply_scenario(self.model, scenario(one_time_factor=3))
        self.assertEqual(self.amounts(self.model, "one_time_costs"), [3000, 500])

    def test_revenue_override_merges(self):
        m = apply_scenario(self.model, scenario(revenue={"unit_price": 12}))
        self.assertEqual(m["revenue"]["unit_price"], 12)
        self.assertEqual(m["revenue"]["variable_cost_per_unit"], 4)
        self.assertEqual(m["revenue"]["monthly_units"], 200)
        self.assertEqual(self.model["revenue"]["unit_price"], 10)

    def test_revenue_only_in_scenario(self):
        model = model_of(base(revenue=None, scenarios=[
            {"name": "x", "revenue": {"unit_price": 20, "variable_cost_per_unit": 5}}]))
        m = apply_scenario(model, model["scenarios"][0])
        self.assertEqual(m["revenue"], {"unit_price": 20, "variable_cost_per_unit": 5,
                                        "monthly_units": None, "fixed_cost_override": None})

    def test_zero_factor(self):
        m = apply_scenario(self.model, scenario(monthly_factor=0))
        self.assertEqual(self.amounts(m, "monthly_costs"), [0, 0])


class Compare(unittest.TestCase):
    def test_comparison_numbers_and_winners(self):
        model = model_of(base(scenarios=[
            {"name": "lean", "one_time_factor": 0.5, "monthly_factor": 0.5,
             "overrides": [{"item": "Oven", "amount": 2500}, {"item": "Rent", "amount": 0}]},
            {"name": "standard"},
            {"name": "premium", "one_time_factor": 1.5, "monthly_factor": 1.5,
             "revenue": {"unit_price": 14}},
        ]))
        comp = compare(model)
        rows = {r["name"]: r["analysis"] for r in comp["scenarios"]}
        self.assertEqual(rows["lean"]["one_time"]["total"], 3025)       # (2500 + 250) * 1.1
        self.assertEqual(rows["lean"]["monthly"]["total"], 50)
        self.assertEqual(rows["lean"]["runway"]["months"], 139.5)       # 6975 / 50
        self.assertEqual(rows["standard"]["one_time"]["total"], 3850)
        self.assertEqual(rows["premium"]["one_time"]["total"], 5775)    # 5250 * 1.1
        self.assertEqual(rows["premium"]["monthly"]["total"], 1350)
        self.assertEqual(rows["premium"]["break_even"]["units"], 135)    # 1350 / (14 - 4)
        w = {x["metric"]: x for x in comp["winners"]}
        self.assertEqual(w["one_time_total"]["winners"], ["lean"])
        self.assertEqual(w["one_time_total"]["statement"],
                         "Cheapest to launch: lean ($3,025.00 one-time, including contingency).")
        self.assertEqual(w["monthly_burn"]["winners"], ["lean"])
        self.assertEqual(w["runway"]["winners"], ["lean"])
        self.assertEqual(w["runway"]["statement"], "Longest runway: lean (139.5 months).")
        self.assertEqual(w["break_even_units"]["winners"], ["lean"])  # 50 / 6 = 8.33 units

    def test_ties_are_named(self):
        model = model_of(base(scenarios=[{"name": "a"}, {"name": "b"}, {"name": "c", "one_time_factor": 2}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["one_time_total"]["winners"], ["a", "b"])
        self.assertIn("a and b (tie)", w["one_time_total"]["statement"])
        self.assertEqual(w["monthly_burn"]["winners"], ["a", "b", "c"])
        self.assertIn("a, b and c (tie)", w["monthly_burn"]["statement"])

    def test_unlimited_runway_beats_finite(self):
        model = model_of(base(scenarios=[{"name": "busy"}, {"name": "free", "monthly_factor": 0}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["runway"]["winners"], ["free"])
        self.assertEqual(w["runway"]["statement"], "Longest runway: free (unlimited).")

    def test_finite_beats_shortfall_and_closest_shortfall_named(self):
        model = model_of(base(starting_cash=4000, scenarios=[
            {"name": "big", "one_time_factor": 2}, {"name": "ok"}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["runway"]["winners"], ["ok"])
        model = model_of(base(starting_cash=100, scenarios=[
            {"name": "x"}, {"name": "y", "one_time_factor": 0.5}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["runway"]["winners"], ["y"])
        self.assertIn("none of the scenarios can open", w["runway"]["statement"])
        self.assertIn("y comes closest (short $1,825.00 at opening)", w["runway"]["statement"])

    def test_break_even_winner_skips_undefined(self):
        model = model_of(base(scenarios=[
            {"name": "cheap price", "revenue": {"unit_price": 3}}, {"name": "normal"}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["break_even_units"]["winners"], ["normal"])

    def test_break_even_not_available_anywhere(self):
        model = model_of(base(revenue={"unit_price": 1, "variable_cost_per_unit": 2},
                              scenarios=[{"name": "x"}]))
        w = {x["metric"]: x for x in compare(model)["winners"]}
        self.assertEqual(w["break_even_units"]["winners"], [])
        self.assertIn("not available", w["break_even_units"]["statement"])

    def test_default_scenarios_used_when_absent(self):
        comp = compare(model_of(base()))
        self.assertEqual([s["name"] for s in comp["scenarios"]], ["lean", "standard", "premium"])
        self.assertEqual(comp["scenarios"][1]["analysis"]["one_time"]["total"], 3850)


class Helpers(unittest.TestCase):
    def test_join_names(self):
        self.assertEqual(join_names(["a"]), "a")
        self.assertEqual(join_names(["a", "b"]), "a and b (tie)")

    def test_runway_text(self):
        self.assertEqual(runway_text({"status": "finite", "months": 4.25}, "USD"), "4.3 months")
        self.assertEqual(runway_text({"status": "unlimited"}, "USD"), "unlimited")
        self.assertEqual(runway_text({"status": "shortfall", "shortfall": 10}, "USD"),
                         "short $10.00 at opening")


if __name__ == "__main__":
    unittest.main()
