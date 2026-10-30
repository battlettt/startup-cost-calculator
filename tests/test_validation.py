import math
import unittest

from tests.helpers import BASE, INVALID_FIXTURES, base, load_json

from startup_costs.model import (
    DEFAULT_SCENARIOS, ValidationError, check, load, parse_json_text,
)


def errors_of(data):
    return check(data)[1]


class ValidInput(unittest.TestCase):
    def test_base_is_valid_and_keeps_every_item(self):
        model, errors, warnings = check(base())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(len(model["one_time_costs"]), len(BASE["one_time_costs"]))
        self.assertEqual(len(model["monthly_costs"]), len(BASE["monthly_costs"]))

    def test_defaults_filled(self):
        model = load(base(contingency_pct=None, label=None))
        self.assertEqual(model["contingency_pct"], 10)
        self.assertEqual(model["currency"], "USD")
        self.assertEqual(model["label"], "")
        self.assertEqual(model["scenarios"], DEFAULT_SCENARIOS)
        self.assertEqual(model["revenue"]["fixed_cost_override"], None)

    def test_underscore_keys_are_comments(self):
        data = base(_comment="hello")
        data["one_time_costs"][0]["_note"] = "second-hand"
        self.assertEqual(errors_of(data), [])

    def test_names_are_trimmed(self):
        data = base()
        data["one_time_costs"][0]["name"] = "  Oven "
        self.assertEqual(load(data)["one_time_costs"][0]["name"], "Oven")

    def test_null_optional_means_unset(self):
        data = base(contingency_pct=None)
        data["contingency_pct"] = None
        self.assertEqual(load(data)["contingency_pct"], 10)

    def test_contingency_bounds_inclusive(self):
        self.assertEqual(errors_of(base(contingency_pct=0)), [])
        self.assertEqual(errors_of(base(contingency_pct=100)), [])


class Warnings(unittest.TestCase):
    def test_empty_lists_warn_not_fail(self):
        model, errors, warnings = check(base(one_time_costs=[], monthly_costs=[]))
        self.assertEqual(errors, [])
        self.assertIsNotNone(model)
        self.assertEqual(len(warnings), 2)
        self.assertIn("one_time_costs is empty", warnings[0])
        self.assertIn("monthly_costs is empty", warnings[1])

    def test_missing_revenue_warns(self):
        _, errors, warnings = check(base(revenue=None))
        self.assertEqual(errors, [])
        self.assertIn('No "revenue" section', warnings[0])

    def test_empty_scenarios_warns_and_uses_defaults(self):
        model, errors, warnings = check(base(scenarios=[]))
        self.assertEqual(errors, [])
        self.assertIn("scenarios is empty", warnings[0])
        self.assertEqual([s["name"] for s in model["scenarios"]], ["lean", "standard", "premium"])


class Errors(unittest.TestCase):
    def test_top_level_must_be_object(self):
        self.assertEqual(errors_of([1]), ["input: the top level must be a JSON object, got a list"])

    def test_missing_required_fields(self):
        errs = errors_of({})
        self.assertIn('input: missing required field "name"', errs)
        self.assertIn('input: missing required field "starting_cash"', errs)
        self.assertIn('input: missing required field "one_time_costs" (use [] if there are none)', errs)
        self.assertIn('input: missing required field "monthly_costs" (use [] if there are none)', errs)

    def test_negative_amount_is_numbered_and_named(self):
        data = base()
        data["monthly_costs"][1]["amount"] = -100
        self.assertEqual(errors_of(data), [
            'monthly_costs item 2 ("Insurance"): "amount" must not be negative (got -100)'
        ])

    def test_non_numeric_amount(self):
        data = base()
        data["one_time_costs"][0]["amount"] = "3,000"
        self.assertEqual(errors_of(data), [
            'one_time_costs item 1 ("Oven"): "amount" must be a number, got text "3,000"'
        ])

    def test_boolean_is_not_a_number(self):
        data = base()
        data["one_time_costs"][0]["amount"] = True
        self.assertIn("got true", errors_of(data)[0])

    def test_nan_and_infinity_rejected(self):
        for value, shown in ((math.nan, "NaN"), (math.inf, "Infinity")):
            errs = errors_of(base(starting_cash=value))
            self.assertEqual(errs, [f'input: "starting_cash" must be a number, got {shown}'])

    def test_missing_item_fields(self):
        data = base()
        data["one_time_costs"].append({"name": "Sign"})
        self.assertEqual(errors_of(data), [
            'one_time_costs item 3 ("Sign"): missing required field "amount"',
            'one_time_costs item 3 ("Sign"): missing required field "category"',
        ])

    def test_unknown_keys_listed_with_allowed(self):
        data = base(price=4)
        data["one_time_costs"][0]["cost"] = 5
        errs = errors_of(data)
        self.assertTrue(errs[0].startswith('input: unknown field "price" (allowed: name, label'))
        self.assertTrue(errs[1].startswith('one_time_costs item 1 ("Oven"): unknown field "cost"'))

    def test_contingency_out_of_range(self):
        self.assertEqual(errors_of(base(contingency_pct=150)),
                         ['input: "contingency_pct" must be between 0 and 100 (got 150)'])
        self.assertEqual(errors_of(base(contingency_pct=-1)),
                         ['input: "contingency_pct" must be between 0 and 100 (got -1)'])
        self.assertEqual(errors_of(base(contingency_pct=100.5)),
                         ['input: "contingency_pct" must be between 0 and 100 (got 100.5)'])

    def test_negative_starting_cash(self):
        self.assertEqual(errors_of(base(starting_cash=-5)),
                         ['input: "starting_cash" must not be negative (got -5)'])

    def test_invalid_item_is_reported_not_dropped(self):
        data = base()
        data["one_time_costs"].append("Sign: 200")
        model, errors, _ = check(data)
        self.assertIsNone(model)
        self.assertEqual(len(errors), 1)
        self.assertIn("one_time_costs item 3", errors[0])

    def test_duplicate_item_names(self):
        data = base()
        data["one_time_costs"].append({"name": "Oven", "amount": 1, "category": "x"})
        self.assertIn("duplicate name \"Oven\" (also item 1)", errors_of(data)[0])

    def test_revenue_requires_price_and_variable_cost(self):
        errs = errors_of(base(revenue={"monthly_units": 3}))
        self.assertEqual(errs, [
            'revenue: missing required field "unit_price"',
            'revenue: missing required field "variable_cost_per_unit"',
        ])

    def test_revenue_negative_volume(self):
        errs = errors_of(base(revenue={"unit_price": 1, "variable_cost_per_unit": 0, "monthly_units": -1}))
        self.assertEqual(errs, ['revenue: "monthly_units" must not be negative (got -1)'])

    def test_override_unknown_item(self):
        errs = errors_of(base(scenarios=[{"name": "x", "overrides": [{"item": "Van", "amount": 1}]}]))
        self.assertEqual(errs, [
            'scenarios item 1 ("x") override 1: no item named "Van" in one_time_costs or monthly_costs'
        ])

    def test_override_wrong_kind(self):
        errs = errors_of(base(scenarios=[{"name": "x", "overrides": [{"item": "Oven", "amount": 1, "kind": "monthly"}]}]))
        self.assertEqual(errs, ['scenarios item 1 ("x") override 1: no item named "Oven" in monthly_costs'])

    def test_ambiguous_override_needs_kind(self):
        data = base(scenarios=[{"name": "x", "overrides": [{"item": "Oven", "amount": 1}]}])
        data["monthly_costs"].append({"name": "Oven", "amount": 9, "category": "repairs"})
        self.assertIn('add "kind"', errors_of(data)[0])
        data["scenarios"][0]["overrides"][0]["kind"] = "monthly"
        self.assertEqual(errors_of(data), [])

    def test_negative_factor(self):
        errs = errors_of(base(scenarios=[{"name": "x", "monthly_factor": -0.5}]))
        self.assertEqual(errs, ['scenarios item 1 ("x"): "monthly_factor" must not be negative (got -0.5)'])

    def test_scenario_revenue_needs_base_or_full_section(self):
        errs = errors_of(base(revenue=None, scenarios=[{"name": "x", "revenue": {"unit_price": 5}}]))
        self.assertEqual(errs, [
            'scenarios item 1 ("x") revenue: "variable_cost_per_unit" is required here because '
            'the input has no top-level "revenue" section'
        ])

    def test_every_invalid_fixture_fails_with_errors(self):
        self.assertGreaterEqual(len(INVALID_FIXTURES), 10)
        for path in INVALID_FIXTURES:
            with self.subTest(path.name):
                model, errors, _ = check(load_json(path))
                self.assertIsNone(model)
                self.assertTrue(errors)
                for err in errors:
                    self.assertRegex(err, r"^(input|one_time_costs item \d+|monthly_costs item \d+|revenue|scenarios item \d+)")

    def test_errors_are_collected_not_first_only(self):
        errs = errors_of(load_json(INVALID_FIXTURES[0].parent / "invalid_bad_types.json"))
        self.assertEqual(len(errs), 12)


class LoadAndParse(unittest.TestCase):
    def test_load_raises_with_all_errors(self):
        with self.assertRaises(ValidationError) as ctx:
            load(base(starting_cash=-1, contingency_pct=500))
        self.assertEqual(len(ctx.exception.errors), 2)

    def test_parse_json_reports_position(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_json_text('{\n  "name": "x",\n  oops\n}', source="f.json")
        self.assertIn("f.json: not valid JSON (line 3, column 3)", ctx.exception.errors[0])


if __name__ == "__main__":
    unittest.main()
