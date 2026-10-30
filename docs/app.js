/* startup-cost-calculator demo.
 *
 * Part 1 (Calc) is a line-for-line port of src/startup_costs/{model,
 * calculations,scenarios}.py. It performs the same floating-point
 * operations in the same order, so the demo and the CLI agree exactly; the
 * parity tests (tests/test_parity.py, run under Node) prove it on every
 * sample. Part 2 is the browser UI and only runs when a document exists.
 * No dependencies, no build step, no network calls.
 */
(function (root) {
  "use strict";

  // ------------------------------------------------------------ model.py
  var LABEL = "SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA";
  var DEFAULT_CURRENCY = "USD";
  var DEFAULT_CONTINGENCY_PCT = 10;
  var TOP_FIELDS = ["name", "label", "currency", "starting_cash", "contingency_pct",
    "one_time_costs", "monthly_costs", "revenue", "scenarios"];
  var ITEM_FIELDS = ["name", "amount", "category"];
  var REVENUE_FIELDS = ["unit_price", "variable_cost_per_unit", "monthly_units", "fixed_cost_override"];
  var SCENARIO_FIELDS = ["name", "description", "one_time_factor", "monthly_factor", "overrides", "revenue"];
  var OVERRIDE_FIELDS = ["item", "amount", "kind"];
  var LIST_FOR_KIND = { one_time: "one_time_costs", monthly: "monthly_costs" };
  var KINDS = ["one_time", "monthly"];
  var DEFAULT_SCENARIOS = [
    { name: "lean", description: "Second-hand equipment, fewer paid tools, owner does more.",
      one_time_factor: 0.8, monthly_factor: 0.85, overrides: [], revenue: null },
    { name: "standard", description: "The plan as entered.",
      one_time_factor: 1, monthly_factor: 1, overrides: [], revenue: null },
    { name: "premium", description: "New equipment, stronger branding, more paid help.",
      one_time_factor: 1.35, monthly_factor: 1.25, overrides: [], revenue: null }
  ];

  function own(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }
  function isObject(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function isNumber(v) { return typeof v === "number" && isFinite(v); }
  function isText(v) { return typeof v === "string" && v.trim() !== ""; }
  function quote(s) { return JSON.stringify(s); }
  function clone(v) { return JSON.parse(JSON.stringify(v)); }

  function plainNumber(v) { return String(v); }

  function describe(v) {
    if (v === null || v === undefined) return "null";
    if (typeof v === "boolean") return v ? "true" : "false";
    if (typeof v === "number") return plainNumber(v);
    if (typeof v === "string") return "text " + quote(v);
    if (Array.isArray(v)) return "a list";
    if (typeof v === "object") return "an object";
    return typeof v;
  }

  function present(obj, key, required) {
    if (!own(obj, key)) return false;
    return obj[key] !== null || required;
  }

  function unknown(errors, where, obj, allowed) {
    var extra = Object.keys(obj).filter(function (k) {
      return allowed.indexOf(k) < 0 && k.charAt(0) !== "_";
    }).sort();
    extra.forEach(function (k) {
      errors.push(where + ": unknown field " + quote(k) + " (allowed: " + allowed.join(", ") + ")");
    });
  }

  function number(errors, where, obj, key, required, high) {
    if (!present(obj, key, required)) {
      if (required) errors.push(where + ": missing required field " + quote(key));
      return null;
    }
    var v = obj[key];
    if (!isNumber(v)) {
      errors.push(where + ": " + quote(key) + " must be a number, got " + describe(v));
      return null;
    }
    if (high !== undefined && high !== null && (v < 0 || v > high)) {
      errors.push(where + ": " + quote(key) + " must be between 0 and " + high + " (got " + describe(v) + ")");
      return null;
    }
    if (v < 0) {
      errors.push(where + ": " + quote(key) + " must not be negative (got " + describe(v) + ")");
      return null;
    }
    return v;
  }

  function text(errors, where, obj, key, required) {
    if (!present(obj, key, required)) {
      if (required) errors.push(where + ": missing required field " + quote(key));
      return null;
    }
    var v = obj[key];
    if (!isText(v)) {
      errors.push(where + ": " + quote(key) + " must be non-empty text, got " + describe(v));
      return null;
    }
    return v.trim();
  }

  function items(errors, warnings, data, listKey) {
    if (!own(data, listKey)) {
      errors.push("input: missing required field " + quote(listKey) + " (use [] if there are none)");
      return { items: [], names: [] };
    }
    var raw = data[listKey];
    if (!Array.isArray(raw)) {
      errors.push("input: " + quote(listKey) + " must be a list, got " + describe(raw));
      return { items: [], names: [] };
    }
    if (raw.length === 0) {
      var kind = listKey === "one_time_costs" ? "one-time" : "monthly";
      warnings.push(listKey + " is empty: no " + kind + " costs will be counted. " +
        "Double-check that nothing was forgotten.");
      return { items: [], names: [] };
    }
    var out = [], names = [], seen = new Map();
    raw.forEach(function (item, i) {
      var index = i + 1;
      if (!isObject(item)) {
        errors.push(listKey + " item " + index + ': must be an object with "name", "amount" ' +
          'and "category", got ' + describe(item));
        return;
      }
      var where = listKey + " item " + index;
      if (own(item, "name") && isText(item.name)) where += " (" + quote(item.name.trim()) + ")";
      unknown(errors, where, item, ITEM_FIELDS);
      var name = text(errors, where, item, "name", true);
      var amount = number(errors, where, item, "amount", true);
      var category = text(errors, where, item, "category", true);
      if (name !== null) {
        if (seen.has(name)) {
          errors.push(where + ": duplicate name " + quote(name) + " (also item " + seen.get(name) + "); " +
            "names must be unique within " + listKey + " so scenarios can refer to them");
        } else {
          seen.set(name, index);
          names.push(name);
        }
      }
      if (name !== null && amount !== null && category !== null) {
        out.push({ name: name, amount: amount, category: category });
      }
    });
    return { items: out, names: names };
  }

  function revenueSection(errors, where, raw, partial) {
    if (!isObject(raw)) {
      errors.push(where + ": must be an object, got " + describe(raw));
      return null;
    }
    unknown(errors, where, raw, REVENUE_FIELDS);
    var out = {};
    REVENUE_FIELDS.forEach(function (key) {
      var required = !partial && (key === "unit_price" || key === "variable_cost_per_unit");
      var v = number(errors, where, raw, key, required);
      if (v !== null) out[key] = v;
    });
    return out;
  }

  function overridesList(errors, where, raw, names) {
    if (!Array.isArray(raw)) {
      errors.push(where + ': "overrides" must be a list, got ' + describe(raw));
      return [];
    }
    var out = [], targeted = new Map();
    raw.forEach(function (ov, i) {
      var index = i + 1;
      var ow = where + " override " + index;
      if (!isObject(ov)) {
        errors.push(ow + ': must be an object with "item" and "amount", got ' + describe(ov));
        return;
      }
      unknown(errors, ow, ov, OVERRIDE_FIELDS);
      var item = text(errors, ow, ov, "item", true);
      var amount = number(errors, ow, ov, "amount", true);
      var kind = null;
      if (present(ov, "kind", false)) {
        if (KINDS.indexOf(ov.kind) < 0) {
          errors.push(ow + ': "kind" must be "one_time" or "monthly", got ' + describe(ov.kind));
          return;
        }
        kind = ov.kind;
      }
      if (item === null) return;
      var kinds = kind !== null ? [kind] : KINDS.slice();
      var found = kinds.filter(function (k) { return names[LIST_FOR_KIND[k]].indexOf(item) >= 0; });
      if (found.length === 0) {
        var place = kind !== null ? LIST_FOR_KIND[kind] : "one_time_costs or monthly_costs";
        errors.push(ow + ": no item named " + quote(item) + " in " + place);
        return;
      }
      if (found.length > 1) {
        errors.push(ow + ": " + quote(item) + " exists in both one_time_costs and monthly_costs; " +
          'add "kind": "one_time" or "monthly"');
        return;
      }
      var key = found[0] + ":" + item;
      if (targeted.has(key)) {
        errors.push(ow + ": " + quote(item) + " is already overridden by override " + targeted.get(key));
        return;
      }
      targeted.set(key, index);
      if (amount !== null) out.push({ item: item, kind: found[0], amount: amount });
    });
    return out;
  }

  function scenarioList(errors, warnings, data, names, hasRevenue) {
    if (!present(data, "scenarios", false)) return clone(DEFAULT_SCENARIOS);
    var raw = data.scenarios;
    if (!Array.isArray(raw)) {
      errors.push('input: "scenarios" must be a list, got ' + describe(raw));
      return [];
    }
    if (raw.length === 0) {
      warnings.push("scenarios is empty: the built-in lean / standard / premium scenarios will be used.");
      return clone(DEFAULT_SCENARIOS);
    }
    var out = [], seen = new Map();
    raw.forEach(function (sc, i) {
      var index = i + 1;
      if (!isObject(sc)) {
        errors.push("scenarios item " + index + ': must be an object with at least a "name", ' +
          "got " + describe(sc));
        return;
      }
      var where = "scenarios item " + index;
      if (own(sc, "name") && isText(sc.name)) where += " (" + quote(sc.name.trim()) + ")";
      unknown(errors, where, sc, SCENARIO_FIELDS);
      var name = text(errors, where, sc, "name", true);
      if (name !== null) {
        if (seen.has(name)) {
          errors.push(where + ": duplicate scenario name " + quote(name) + " (also item " + seen.get(name) + ")");
        } else {
          seen.set(name, index);
        }
      }
      var description = text(errors, where, sc, "description", false);
      var otf = number(errors, where, sc, "one_time_factor", false);
      var mf = number(errors, where, sc, "monthly_factor", false);
      var overrides = [];
      if (present(sc, "overrides", false)) overrides = overridesList(errors, where, sc.overrides, names);
      var revenue = null;
      if (present(sc, "revenue", false)) {
        revenue = revenueSection(errors, where + " revenue", sc.revenue, true);
        if (revenue !== null && !hasRevenue) {
          ["unit_price", "variable_cost_per_unit"].forEach(function (key) {
            if (!own(sc.revenue, key)) {
              errors.push(where + " revenue: " + quote(key) + " is required here because the " +
                'input has no top-level "revenue" section');
            }
          });
        }
      }
      out.push({
        name: name !== null ? name : "scenario " + index,
        description: description !== null ? description : "",
        one_time_factor: otf !== null ? otf : 1,
        monthly_factor: mf !== null ? mf : 1,
        overrides: overrides,
        revenue: revenue
      });
    });
    return out;
  }

  function check(data) {
    var errors = [], warnings = [];
    if (!isObject(data)) {
      errors.push("input: the top level must be a JSON object, got " + describe(data));
      return { model: null, errors: errors, warnings: warnings };
    }
    unknown(errors, "input", data, TOP_FIELDS);
    var name = text(errors, "input", data, "name", true);
    var label = text(errors, "input", data, "label", false);
    var currency = text(errors, "input", data, "currency", false);
    var startingCash = number(errors, "input", data, "starting_cash", true);
    var contingency = number(errors, "input", data, "contingency_pct", false, 100);
    var ot = items(errors, warnings, data, "one_time_costs");
    var mo = items(errors, warnings, data, "monthly_costs");
    var revenue = null;
    if (present(data, "revenue", false)) {
      revenue = revenueSection(errors, "revenue", data.revenue, false);
      if (revenue !== null) {
        if (!own(revenue, "monthly_units")) revenue.monthly_units = null;
        if (!own(revenue, "fixed_cost_override")) revenue.fixed_cost_override = null;
      }
    } else {
      warnings.push('No "revenue" section: break-even will not be calculated. Add unit_price ' +
        "and variable_cost_per_unit to see it.");
    }
    var names = { one_time_costs: ot.names, monthly_costs: mo.names };
    var scenarios = scenarioList(errors, warnings, data, names, present(data, "revenue", false));
    if (errors.length) return { model: null, errors: errors, warnings: warnings };
    return {
      model: {
        name: name,
        label: label !== null ? label : "",
        currency: currency !== null ? currency : DEFAULT_CURRENCY,
        starting_cash: startingCash,
        contingency_pct: contingency !== null ? contingency : DEFAULT_CONTINGENCY_PCT,
        one_time_costs: ot.items,
        monthly_costs: mo.items,
        revenue: revenue,
        scenarios: scenarios
      },
      errors: errors,
      warnings: warnings
    };
  }

  // ----------------------------------------------------- calculations.py
  var CURRENCY_SYMBOLS = { USD: "$", CAD: "$", AUD: "$", NZD: "$", GBP: "£", EUR: "€" };

  function roundTo(value, places) {
    var factor = Math.pow(10, places);
    return Math.floor(value * factor + 0.5 + 1e-9) / factor;
  }
  function round2(value) { return roundTo(value, 2); }

  function group(digits) {
    var out = "";
    while (digits.length > 3) {
      out = "," + digits.slice(-3) + out;
      digits = digits.slice(0, -3);
    }
    return digits + out;
  }

  function formatNumber(value, decimals) {
    if (decimals === undefined) decimals = 2;
    var factor = Math.pow(10, decimals);
    var scaled = Math.floor(Math.abs(value) * factor + 0.5 + 1e-9);
    var whole = Math.floor(scaled / factor);
    var frac = scaled % factor;
    var s = group(String(whole));
    if (decimals > 0) s += "." + String(frac).padStart(decimals, "0");
    var sign = value < 0 && scaled !== 0 ? "-" : "";
    return sign + s;
  }

  function formatMoney(value, currency) {
    if (currency === undefined) currency = "USD";
    var symbol = own(CURRENCY_SYMBOLS, currency) ? CURRENCY_SYMBOLS[currency] : currency + " ";
    var s = formatNumber(value, 2);
    if (s.charAt(0) === "-") return "-" + symbol + s.slice(1);
    return symbol + s;
  }

  function formatQuantity(value) {
    if (Number.isInteger(value)) return formatNumber(value, 0);
    return formatNumber(value, 2);
  }

  function sumAmounts(list) {
    var total = 0;
    list.forEach(function (item) { total += item.amount; });
    return round2(total);
  }

  function categoryTotals(list) {
    var order = [], sums = new Map();
    list.forEach(function (item) {
      if (!sums.has(item.category)) { order.push(item.category); sums.set(item.category, 0); }
      sums.set(item.category, sums.get(item.category) + item.amount);
    });
    return order.map(function (c) { return { category: c, amount: round2(sums.get(c)) }; });
  }

  function computeRunway(startingCash, oneTimeTotal, burn, currency, net) {
    function money(v) { return formatMoney(v, currency); }
    var after = round2(startingCash - oneTimeTotal);
    var r = {
      basis: net ? "net_of_revenue" : "costs_only",
      starting_cash: startingCash,
      one_time_total: oneTimeTotal,
      monthly_burn: burn,
      cash_after_one_time: after,
      status: "",
      months: null,
      shortfall: 0,
      message: ""
    };
    if (after < 0) {
      var shortfall = round2(0 - after);
      r.status = "shortfall";
      r.shortfall = shortfall;
      r.message = "Not enough cash: the one-time costs (" + money(oneTimeTotal) + " including " +
        "contingency) are more than the starting cash (" + money(startingCash) + "). " +
        "You need at least " + money(shortfall) + " more just to open, before paying " +
        "any monthly costs.";
    } else if (burn <= 0) {
      r.status = "unlimited";
      if (burn < 0) {
        r.message = "Sales cover the monthly costs (net burn " + money(burn) + " a month), so " +
          "cash grows instead of shrinking. Runway is not limited while these " +
          "assumptions hold; " + money(after) + " is left after one-time costs.";
      } else {
        r.message = "Monthly burn is " + money(0) + ", so nothing drains cash each month. " +
          "Runway is not limited; " + money(after) + " is left after one-time costs.";
      }
    } else {
      var months = round2(after / burn);
      r.status = "finite";
      r.months = months;
      var spending = net ? "Losing " + money(burn) + " a month after sales"
        : "Spending " + money(burn) + " a month with no sales";
      r.message = "After one-time costs you have " + money(after) + " left. " + spending + ", that " +
        "lasts about " + formatNumber(months, 1) + " months.";
    }
    return r;
  }

  function computeBreakEven(revenue, recurringTotal, oneTimeTotal, currency) {
    function money(v) { return formatMoney(v, currency); }
    var r = {
      status: "no_revenue",
      unit_price: null,
      variable_cost_per_unit: null,
      fixed_costs: null,
      fixed_cost_source: null,
      contribution_margin: null,
      margin_pct: null,
      units: null,
      units_whole: null,
      revenue: null,
      monthly_units: null,
      monthly_contribution: null,
      monthly_profit: null,
      months_status: "no_volume",
      months_to_break_even: null,
      message: "No revenue assumptions were given, so break-even was not calculated. " +
        'Add a "revenue" section with unit_price and variable_cost_per_unit.',
      months_message: ""
    };
    if (revenue === null) return r;
    var price = revenue.unit_price;
    var variable = revenue.variable_cost_per_unit;
    var override = own(revenue, "fixed_cost_override") ? revenue.fixed_cost_override : null;
    var fixed;
    if (override !== null && override !== undefined) {
      fixed = round2(override);
      r.fixed_cost_source = "override";
    } else {
      fixed = recurringTotal;
      r.fixed_cost_source = "recurring_total";
    }
    var margin = round2(price - variable);
    r.unit_price = price;
    r.variable_cost_per_unit = variable;
    r.fixed_costs = fixed;
    r.contribution_margin = margin;
    if (price > 0) r.margin_pct = round2(margin / price * 100);
    if (margin <= 0) {
      r.status = "undefined";
      if (margin === 0) {
        r.message = "Break-even is undefined: each unit sells for " + money(price) + " and costs " +
          money(variable) + " to make, so every sale earns " + money(0) + " toward fixed " +
          "costs. No number of sales can cover " + money(fixed) + " a month. Raise the " +
          "price or lower the variable cost per unit.";
      } else {
        r.message = "Break-even is undefined: each unit sells for " + money(price) + " but costs " +
          money(variable) + " to make, so every sale loses " + money(0 - margin) + ". " +
          "Selling more only loses more, so no number of sales can cover " +
          money(fixed) + " a month. Raise the price or lower the variable cost per unit.";
      }
    } else {
      var units = fixed / margin;
      var whole = Math.ceil(roundTo(units, 6));
      var sales = round2(units * price);
      r.status = "ok";
      r.units = round2(units);
      r.units_whole = whole;
      r.revenue = sales;
      r.message = "Each unit earns " + money(margin) + " toward fixed costs (" +
        formatNumber(r.margin_pct, 1) + "% of the price). To cover " +
        money(fixed) + " of fixed costs a month you need " + formatNumber(whole, 0) +
        " units a month, about " + money(sales) + " in sales.";
    }
    var volume = own(revenue, "monthly_units") ? revenue.monthly_units : null;
    if (volume === null || volume === undefined) {
      r.months_message = 'Add "monthly_units" to the revenue section to estimate how many months ' +
        "it takes to earn back the one-time costs.";
      return r;
    }
    var contribution = round2(volume * margin);
    var profit = round2(contribution - fixed);
    r.monthly_units = volume;
    r.monthly_contribution = contribution;
    r.monthly_profit = profit;
    var qty = formatQuantity(volume);
    if (profit <= 0) {
      r.months_status = "never";
      var t = "At " + qty + " units a month you bring in " + money(contribution) + " toward fixed " +
        "costs of " + money(fixed) + ", a shortfall of " + money(0 - profit) + " a month. At this " +
        "volume the one-time costs (" + money(oneTimeTotal) + ") are never earned back";
      if (r.status === "ok") {
        t += "; you need about " + formatNumber(r.units_whole, 0) + " units a " +
          "month just to cover fixed costs.";
      } else {
        t += " because every sale loses money or breaks even.";
      }
      r.months_message = t;
    } else {
      var months = round2(oneTimeTotal / profit);
      r.months_status = "ok";
      r.months_to_break_even = months;
      r.months_message = "At " + qty + " units a month you make " + money(profit) + " a month after fixed " +
        "costs, which earns back the " + money(oneTimeTotal) + " one-time cost in " +
        "about " + formatNumber(months, 1) + " months.";
    }
    return r;
  }

  function copyItems(list) {
    return list.map(function (i) { return { name: i.name, amount: i.amount, category: i.category }; });
  }

  function analyze(model) {
    var currency = model.currency;
    var subtotal = sumAmounts(model.one_time_costs);
    var pct = model.contingency_pct;
    var contingency = round2(subtotal * pct / 100);
    var oneTimeTotal = round2(subtotal + contingency);
    var burn = sumAmounts(model.monthly_costs);
    var runway = computeRunway(model.starting_cash, oneTimeTotal, burn, currency, false);
    var be = computeBreakEven(model.revenue, burn, oneTimeTotal, currency);
    var withRevenue = null;
    if (be.monthly_contribution !== null) {
      var netBurn = round2(burn - be.monthly_contribution);
      withRevenue = computeRunway(model.starting_cash, oneTimeTotal, netBurn, currency, true);
    }
    return {
      name: model.name,
      label: model.label,
      currency: currency,
      starting_cash: model.starting_cash,
      one_time: {
        items: copyItems(model.one_time_costs),
        subtotal: subtotal,
        contingency_pct: pct,
        contingency_amount: contingency,
        total: oneTimeTotal,
        by_category: categoryTotals(model.one_time_costs)
      },
      monthly: {
        items: copyItems(model.monthly_costs),
        total: burn,
        by_category: categoryTotals(model.monthly_costs)
      },
      runway: runway,
      runway_with_revenue: withRevenue,
      break_even: be
    };
  }

  // -------------------------------------------------------- scenarios.py
  function hasKeys(obj) { return isObject(obj) && Object.keys(obj).length > 0; }

  function scale(list, kind, factor, overrides) {
    return list.map(function (item) {
      var key = kind + ":" + item.name;
      var amount = overrides.has(key) ? overrides.get(key) : round2(item.amount * factor);
      return { name: item.name, amount: amount, category: item.category };
    });
  }

  function applyScenario(model, scenario) {
    var overrides = new Map();
    scenario.overrides.forEach(function (o) { overrides.set(o.kind + ":" + o.item, o.amount); });
    var revenue = model.revenue;
    if (hasKeys(scenario.revenue)) {
      var merged = { monthly_units: null, fixed_cost_override: null };
      if (revenue !== null) Object.keys(revenue).forEach(function (k) { merged[k] = revenue[k]; });
      Object.keys(scenario.revenue).forEach(function (k) { merged[k] = scenario.revenue[k]; });
      revenue = merged;
    } else if (revenue !== null) {
      revenue = Object.assign({}, revenue);
    }
    return {
      name: model.name + " (" + scenario.name + ")",
      label: model.label,
      currency: model.currency,
      starting_cash: model.starting_cash,
      contingency_pct: model.contingency_pct,
      one_time_costs: scale(model.one_time_costs, "one_time", scenario.one_time_factor, overrides),
      monthly_costs: scale(model.monthly_costs, "monthly", scenario.monthly_factor, overrides),
      revenue: revenue,
      scenarios: []
    };
  }

  function joinNames(names) {
    if (names.length === 1) return names[0];
    return names.slice(0, -1).join(", ") + " and " + names[names.length - 1] + " (tie)";
  }

  function runwayText(runway, currency) {
    if (runway.status === "finite") return formatNumber(runway.months, 1) + " months";
    if (runway.status === "unlimited") return "unlimited";
    return "short " + formatMoney(runway.shortfall, currency) + " at opening";
  }

  function runwayScore(runway) {
    if (runway.status === "shortfall") return [0, 0 - runway.shortfall];
    if (runway.status === "finite") return [1, runway.months];
    return [2, runway.cash_after_one_time];
  }

  function cmp(a, b) {
    for (var i = 0; i < Math.min(a.length, b.length); i++) {
      if (a[i] < b[i]) return -1;
      if (a[i] > b[i]) return 1;
    }
    return a.length - b.length;
  }

  function best(rows, score, preferLow) {
    var top = null, names = [];
    rows.forEach(function (row) {
      var v = score(row);
      var better = top === null || (preferLow ? cmp(v, top) < 0 : cmp(v, top) > 0);
      if (better) { top = v; names = [row.name]; }
      else if (cmp(v, top) === 0) names.push(row.name);
    });
    return { best: top, names: names };
  }

  function findRow(rows, name) {
    for (var i = 0; i < rows.length; i++) if (rows[i].name === name) return rows[i];
    return null;
  }

  function winnersFor(rows, currency) {
    function money(v) { return formatMoney(v, currency); }
    var out = [], b;

    b = best(rows, function (r) { return [r.analysis.one_time.total]; }, true);
    out.push({
      metric: "one_time_total",
      title: "Cheapest to launch",
      winners: b.names,
      statement: "Cheapest to launch: " + joinNames(b.names) + " (" + money(b.best[0]) + " one-time, " +
        "including contingency)."
    });

    b = best(rows, function (r) { return [r.analysis.monthly.total]; }, true);
    out.push({
      metric: "monthly_burn",
      title: "Lowest monthly burn",
      winners: b.names,
      statement: "Lowest monthly burn: " + joinNames(b.names) + " (" + money(b.best[0]) + " a month)."
    });

    b = best(rows, function (r) { return runwayScore(r.analysis.runway); }, false);
    var t = runwayText(findRow(rows, b.names[0]).analysis.runway, currency);
    var statement;
    if (b.best[0] === 0) {
      statement = "Longest runway: none of the scenarios can open with the starting cash; " +
        joinNames(b.names) + " comes closest (" + t + ").";
    } else {
      statement = "Longest runway: " + joinNames(b.names) + " (" + t + ").";
    }
    out.push({ metric: "runway", title: "Longest runway", winners: b.names, statement: statement });

    var defined = rows.filter(function (r) { return r.analysis.break_even.status === "ok"; });
    var names;
    if (defined.length) {
      b = best(defined, function (r) { return [r.analysis.break_even.units]; }, true);
      names = b.names;
      var whole = findRow(defined, names[0]).analysis.break_even.units_whole;
      statement = "Fewest sales needed to break even: " + joinNames(names) +
        " (" + formatNumber(whole, 0) + " units a month).";
    } else {
      names = [];
      statement = "Fewest sales needed to break even: not available, because break-even is " +
        "undefined or not calculated in every scenario.";
    }
    out.push({ metric: "break_even_units", title: "Fewest sales to break even", winners: names, statement: statement });
    return out;
  }

  function compare(model) {
    var rows = model.scenarios.map(function (sc) {
      return {
        name: sc.name,
        description: sc.description,
        one_time_factor: sc.one_time_factor,
        monthly_factor: sc.monthly_factor,
        overrides: sc.overrides.map(function (o) { return { item: o.item, kind: o.kind, amount: o.amount }; }),
        revenue_overrides: hasKeys(sc.revenue) ? Object.assign({}, sc.revenue) : null,
        analysis: analyze(applyScenario(model, sc))
      };
    });
    return { scenarios: rows, winners: rows.length ? winnersFor(rows, model.currency) : [] };
  }

  var Calc = {
    LABEL: LABEL,
    DEFAULT_SCENARIOS: DEFAULT_SCENARIOS,
    check: check,
    analyze: analyze,
    applyScenario: applyScenario,
    compare: compare,
    computeRunway: computeRunway,
    computeBreakEven: computeBreakEven,
    roundTo: roundTo,
    round2: round2,
    formatNumber: formatNumber,
    formatMoney: formatMoney,
    formatQuantity: formatQuantity,
    runwayText: runwayText
  };

  if (typeof module !== "undefined" && module.exports) module.exports = Calc;
  root.Calc = Calc;

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () { startUI(Calc); });
    } else {
      startUI(Calc);
    }
  }

  // ================================================================ UI
  function startUI(C) {
    var samples = root.STARTUP_SAMPLES || [];
    var state = { data: null, scenario: "__base__" };
    var $ = function (id) { return document.getElementById(id); };
    var SVGNS = "http://www.w3.org/2000/svg";

    function el(tag, attrs, children) {
      var node = document.createElement(tag);
      Object.keys(attrs || {}).forEach(function (k) {
        if (k === "text") node.textContent = attrs[k];
        else if (k === "className") node.className = attrs[k];
        else node.setAttribute(k, attrs[k]);
      });
      (children || []).forEach(function (c) { node.appendChild(c); });
      return node;
    }
    function svg(tag, attrs, textContent) {
      var node = document.createElementNS(SVGNS, tag);
      Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
      if (textContent !== undefined) node.textContent = textContent;
      return node;
    }

    // Number inputs: blank -> field missing; non-numeric text stays text so
    // validation reports it exactly as the CLI would.
    function readNumber(str) {
      var s = String(str).trim();
      if (s === "") return undefined;
      var n = Number(s);
      return isFinite(n) ? n : s;
    }
    function setField(obj, key, value) {
      if (value === undefined) delete obj[key]; else obj[key] = value;
    }
    function showValue(v) { return v === undefined || v === null ? "" : String(v); }

    // ---------------------------------------------------------- samples
    var sel = $("sample-select");
    samples.forEach(function (s, i) {
      sel.appendChild(el("option", { value: String(i), text: s.name + " (synthetic)" }));
    });
    $("load-sample").addEventListener("click", function () { loadData(clone(samples[Number(sel.value)])); });
    $("start-blank").addEventListener("click", function () {
      loadData({
        name: "My business idea", currency: "USD", starting_cash: 0, contingency_pct: 10,
        one_time_costs: [], monthly_costs: []
      });
    });
    $("export-json").addEventListener("click", function () {
      var blob = new Blob([JSON.stringify(state.data, null, 2) + "\n"], { type: "application/json" });
      var a = el("a", { href: URL.createObjectURL(blob), download: "startup-costs.json" });
      document.body.appendChild(a); a.click(); a.remove();
    });
    $("import-json").addEventListener("change", function (ev) {
      var file = ev.target.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        try { loadData(JSON.parse(reader.result)); }
        catch (e) { showProblems(["file: not valid JSON (" + e.message + ")"], []); }
      };
      reader.readAsText(file);
      ev.target.value = "";
    });

    function loadData(data) {
      state.data = data;
      state.scenario = "__base__";
      renderEditor();
      update();
    }

    // ----------------------------------------------------------- editor
    function bindBasics() {
      var d = state.data;
      $("biz-name").value = showValue(d.name);
      $("starting-cash").value = showValue(d.starting_cash);
      $("contingency").value = showValue(d.contingency_pct);
      $("currency").value = d.currency || "USD";
      var rev = isObject(d.revenue) ? d.revenue : null;
      $("has-revenue").checked = !!rev;
      $("revenue-fields").hidden = !rev;
      ["unit_price", "variable_cost_per_unit", "monthly_units", "fixed_cost_override"].forEach(function (k) {
        $("rev-" + k).value = rev ? showValue(rev[k]) : "";
      });
      var label = d.label || "";
      $("sample-label").textContent = label || "Your own figures: every number here is an assumption you entered.";
    }

    $("biz-name").addEventListener("input", function (e) { state.data.name = e.target.value; update(); });
    $("starting-cash").addEventListener("input", function (e) { setField(state.data, "starting_cash", readNumber(e.target.value)); update(); });
    $("contingency").addEventListener("input", function (e) { setField(state.data, "contingency_pct", readNumber(e.target.value)); update(); });
    $("currency").addEventListener("change", function (e) { state.data.currency = e.target.value; update(); });
    $("has-revenue").addEventListener("change", function (e) {
      if (e.target.checked) state.data.revenue = { unit_price: 10, variable_cost_per_unit: 4, monthly_units: 100 };
      else delete state.data.revenue;
      bindBasics(); update();
    });
    ["unit_price", "variable_cost_per_unit", "monthly_units", "fixed_cost_override"].forEach(function (k) {
      $("rev-" + k).addEventListener("input", function (e) {
        if (!isObject(state.data.revenue)) state.data.revenue = {};
        setField(state.data.revenue, k, readNumber(e.target.value));
        update();
      });
    });

    function renderRows(listKey, tbodyId, amountLabel) {
      var body = $(tbodyId);
      body.textContent = "";
      var list = Array.isArray(state.data[listKey]) ? state.data[listKey] : (state.data[listKey] = []);
      list.forEach(function (item, i) {
        var n = i + 1;
        var tr = el("tr");
        function cell(key, type, label) {
          var input = el("input", {
            type: type, value: showValue(item[key]), "aria-label": label + " (row " + n + ")"
          });
          if (type === "text" && key === "amount") input.setAttribute("inputmode", "decimal");
          input.addEventListener("input", function () {
            setField(item, key, key === "amount" ? readNumber(input.value) : input.value);
            update();
          });
          return el("td", {}, [input]);
        }
        tr.appendChild(el("td", { className: "rownum", text: String(n) }));
        tr.appendChild(cell("name", "text", "Item name"));
        tr.appendChild(cell("amount", "text", amountLabel));
        tr.appendChild(cell("category", "text", "Category"));
        var rm = el("button", { type: "button", className: "remove", text: "Remove",
          "aria-label": "Remove row " + n + (item.name ? " (" + item.name + ")" : "") });
        rm.addEventListener("click", function () {
          list.splice(i, 1); renderEditor(); update();
          // keep keyboard focus in the table instead of dropping it to <body>
          var rows = document.querySelectorAll("#" + tbodyId + " tr");
          var next = rows[Math.min(i, rows.length - 1)];
          if (next) next.querySelector("button").focus();
          else $(listKey === "one_time_costs" ? "add-one-time" : "add-monthly").focus();
        });
        tr.appendChild(el("td", {}, [rm]));
        body.appendChild(tr);
      });
    }
    $("add-one-time").addEventListener("click", function () { addRow("one_time_costs"); });
    $("add-monthly").addEventListener("click", function () { addRow("monthly_costs"); });
    function addRow(listKey) {
      state.data[listKey].push({ name: "", amount: 0, category: "" });
      renderEditor(); update();
      var rows = document.querySelectorAll("#" + (listKey === "one_time_costs" ? "one-time-rows" : "monthly-rows") + " tr");
      var last = rows[rows.length - 1];
      if (last) last.querySelector("input").focus();
    }

    function renderEditor() {
      bindBasics();
      renderRows("one_time_costs", "one-time-rows", "Amount");
      renderRows("monthly_costs", "monthly-rows", "Amount per month");
    }

    // ------------------------------------------------------- scenarios
    function renderScenarioSwitcher(model) {
      var box = $("scenario-switcher");
      box.textContent = "";
      var options = [{ value: "__base__", text: "As entered" }].concat(model.scenarios.map(function (s) {
        return { value: s.name, text: s.name };
      }));
      if (!options.some(function (o) { return o.value === state.scenario; })) state.scenario = "__base__";
      options.forEach(function (o, i) {
        var id = "scn-" + i;
        var input = el("input", { type: "radio", name: "scenario", id: id, value: o.value });
        input.checked = o.value === state.scenario;
        input.addEventListener("change", function () { state.scenario = o.value; update(); });
        box.appendChild(el("span", { className: "radio" }, [input, el("label", { "for": id, text: o.text })]));
      });
      var detail = $("scenario-detail");
      var sc = model.scenarios.filter(function (s) { return s.name === state.scenario; })[0];
      if (!sc) {
        detail.textContent = "Showing the costs exactly as entered (no scaling).";
        return;
      }
      var parts = ["One-time costs ×" + C.formatQuantity(sc.one_time_factor),
        "monthly costs ×" + C.formatQuantity(sc.monthly_factor)];
      sc.overrides.forEach(function (o) { parts.push(o.item + " set to " + C.formatMoney(o.amount, model.currency)); });
      if (hasKeys(sc.revenue)) Object.keys(sc.revenue).forEach(function (k) { parts.push(k + " = " + C.formatQuantity(sc.revenue[k])); });
      detail.textContent = (sc.description ? sc.description + " " : "") + "(" + parts.join("; ") + ")";
    }

    // --------------------------------------------------------- results
    function showProblems(errors, warnings) {
      var box = $("problems");
      box.textContent = "";
      if (errors.length) {
        box.appendChild(el("h3", { text: errors.length + " problem" + (errors.length === 1 ? "" : "s") + " to fix (nothing is calculated until they are fixed)" }));
        box.appendChild(el("ul", { className: "errors" }, errors.map(function (e) { return el("li", { text: e }); })));
      }
      if (warnings.length) {
        box.appendChild(el("h3", { text: "Warnings" }));
        box.appendChild(el("ul", { className: "warnings" }, warnings.map(function (w) { return el("li", { text: w }); })));
      }
      box.hidden = !errors.length && !warnings.length;
    }

    function setMsg(id, text, status) {
      var p = $(id);
      p.textContent = text || "";
      p.className = "msg " + (status || "");
      p.hidden = !text;
    }

    function stat(label, value) {
      return el("div", { className: "stat" }, [el("dt", { text: label }), el("dd", { text: value })]);
    }

    function all(selector, scope) {
      return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
    }
    var TOP_INPUTS = { name: "biz-name", starting_cash: "starting-cash", contingency_pct: "contingency" };
    function markInvalid(errors) {
      all("#one-time-rows input").concat(all("#monthly-rows input"))
        .concat(["biz-name", "starting-cash", "contingency", "rev-unit_price", "rev-variable_cost_per_unit",
          "rev-monthly_units", "rev-fixed_cost_override"].map($))
        .forEach(function (input) { input.removeAttribute("aria-invalid"); });
      errors.forEach(function (e) {
        var m = e.match(/^(one_time_costs|monthly_costs) item (\d+)[^:]*: (?:missing required field |)"(name|amount|category)"/);
        if (m) {
          var row = all("#" + (m[1] === "one_time_costs" ? "one-time-rows" : "monthly-rows") + " tr")[Number(m[2]) - 1];
          if (row) all("input", row)[["name", "amount", "category"].indexOf(m[3])].setAttribute("aria-invalid", "true");
          return;
        }
        m = e.match(/^input: (?:missing required field |)"(\w+)"/);
        if (m && TOP_INPUTS[m[1]]) { $(TOP_INPUTS[m[1]]).setAttribute("aria-invalid", "true"); return; }
        m = e.match(/^revenue: (?:missing required field |)"(\w+)"/);
        if (m && document.getElementById("rev-" + m[1])) $("rev-" + m[1]).setAttribute("aria-invalid", "true");
      });
    }

    function update() {
      var res = C.check(state.data);
      showProblems(res.errors, res.warnings);
      markInvalid(res.errors);
      $("results").hidden = !!res.errors.length;
      if (res.errors.length) return;
      var model = res.model;
      renderScenarioSwitcher(model);
      var sc = model.scenarios.filter(function (s) { return s.name === state.scenario; })[0];
      var a = C.analyze(sc ? C.applyScenario(model, sc) : model);
      var cur = model.currency;
      var m = function (v) { return C.formatMoney(v, cur); };

      var totals = $("totals");
      totals.textContent = "";
      [stat("One-time subtotal", m(a.one_time.subtotal)),
        stat("Contingency (" + C.formatQuantity(a.one_time.contingency_pct) + "%)", m(a.one_time.contingency_amount)),
        stat("One-time total", m(a.one_time.total)),
        stat("Monthly burn", m(a.monthly.total)),
        stat("Cash after opening", m(a.runway.cash_after_one_time)),
        stat("Runway (no sales)", C.runwayText(a.runway, cur))
      ].forEach(function (n) { totals.appendChild(n); });

      setMsg("runway-msg", a.runway.message, a.runway.status);
      setMsg("runway-rev-msg", a.runway_with_revenue ? "With the assumed sales: " + a.runway_with_revenue.message : "",
        a.runway_with_revenue ? a.runway_with_revenue.status : "");
      drawBurn(a, cur);

      var be = a.break_even;
      setMsg("be-msg", be.message, be.status);
      setMsg("be-months-msg", be.months_message, be.months_status);
      drawBreakEven(be, cur);

      renderComparison(C.compare(model), cur);
    }

    function renderComparison(comp, cur) {
      var body = $("compare-rows");
      body.textContent = "";
      comp.scenarios.forEach(function (s) {
        var a = s.analysis, be = a.break_even;
        var beText = be.status === "ok" ? C.formatNumber(be.units_whole, 0) : be.status.replace("_", " ");
        var mt = be.months_to_break_even !== null ? C.formatNumber(be.months_to_break_even, 1) : be.months_status.replace("_", " ");
        var tr = el("tr", s.name === state.scenario ? { className: "current" } : {});
        tr.appendChild(el("th", { scope: "row", text: s.name }));
        [C.formatMoney(a.one_time.total, cur), C.formatMoney(a.monthly.total, cur), C.runwayText(a.runway, cur), beText, mt]
          .forEach(function (t) { tr.appendChild(el("td", { className: "num", text: t })); });
        body.appendChild(tr);
      });
      var ul = $("winners");
      ul.textContent = "";
      comp.winners.forEach(function (w) { ul.appendChild(el("li", { text: w.statement })); });
    }

    // ----------------------------------------------------------- charts
    var W = 640, H = 240, PAD_L = 72, PAD_R = 24, PAD_T = 16, PAD_B = 40;

    function axes(g, x0, x1, y0, y1, xLabel, yTicks, yFmt, sx, sy) {
      yTicks.forEach(function (v) {
        g.appendChild(svg("line", { x1: x0, x2: x1, y1: sy(v), y2: sy(v), "class": "gridline" }));
        g.appendChild(svg("text", { x: x0 - 8, y: sy(v) + 4, "text-anchor": "end", "class": "tick" }, yFmt(v)));
      });
      g.appendChild(svg("line", { x1: x0, x2: x1, y1: y0, y2: y0, "class": "axis" }));
      g.appendChild(svg("text", { x: x1, y: y0 + 30, "text-anchor": "end", "class": "tick" }, xLabel));
    }

    function niceTicks(lo, hi, count) {
      var span = hi - lo || 1;
      var step = Math.pow(10, Math.floor(Math.log10(span / count)));
      [1, 2, 2.5, 5, 10].some(function (f) { if (span / (step * f) <= count) { step *= f; return true; } return false; });
      var out = [];
      for (var v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6);
      return out;
    }

    function hoverDot(g, x, y, cls, label) {
      // Pointer tooltip only: the chart is one role="img" whose <desc> and the
      // text panels beside it carry the same numbers for keyboard and screen readers.
      var hit = svg("circle", { cx: x, cy: y, r: 10, "class": "hit" });
      hit.appendChild(svg("title", {}, label));
      g.appendChild(svg("circle", { cx: x, cy: y, r: 4, "class": "dot " + cls }));
      g.appendChild(hit);
    }

    function drawBurn(a, cur) {
      var box = $("burn-chart");
      box.textContent = "";
      var r = a.runway;
      if (r.status === "shortfall") {
        box.appendChild(el("p", { className: "chart-note", text: "No burn-down chart: the business cannot open with this much starting cash." }));
        return;
      }
      var horizon = r.status === "finite" ? Math.min(24, Math.max(1, Math.floor(r.months) + 2)) : 12;
      var pts = [];
      for (var mth = 0; mth <= horizon; mth++) pts.push([mth, C.round2(r.cash_after_one_time - r.monthly_burn * mth)]);
      var vals = pts.map(function (p) { return p[1]; }).concat([0]);
      var hi = Math.max.apply(null, vals), lo = Math.min.apply(null, vals);
      var ticks = niceTicks(lo, hi, 4);
      lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
      var sx = function (v) { return PAD_L + (W - PAD_L - PAD_R) * v / horizon; };
      var sy = function (v) { return PAD_T + (H - PAD_T - PAD_B) * (hi - v) / ((hi - lo) || 1); };
      var root = svg("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-labelledby": "burn-t burn-d", "class": "chart" });
      root.appendChild(svg("title", { id: "burn-t" }, "Cash left each month with no sales"));
      root.appendChild(svg("desc", { id: "burn-d" }, r.message));
      var g = svg("g");
      axes(g, PAD_L, W - PAD_R, sy(lo), sy(hi), "months after opening →", ticks, function (v) { return C.formatMoney(v, cur).replace(/\.00$/, ""); }, sx, sy);
      g.appendChild(svg("line", { x1: PAD_L, x2: W - PAD_R, y1: sy(0), y2: sy(0), "class": "zero" }));
      g.appendChild(svg("text", { x: W - PAD_R, y: sy(0) - 6, "text-anchor": "end", "class": "zero-label" }, "cash runs out"));
      g.appendChild(svg("path", { d: pts.map(function (p, i) { return (i ? "L" : "M") + sx(p[0]).toFixed(1) + " " + sy(p[1]).toFixed(1); }).join(" "), "class": "line s1" }));
      pts.forEach(function (p) {
        hoverDot(g, sx(p[0]), sy(p[1]), "s1", "Month " + p[0] + ": " + C.formatMoney(p[1], cur) + " left");
      });
      if (r.status === "finite") {
        var xz = sx(Math.min(r.months, horizon));
        g.appendChild(svg("text", { x: xz, y: sy(0) + 16, "text-anchor": "middle", "class": "callout" }, "≈ " + C.formatNumber(r.months, 1) + " months"));
      }
      root.appendChild(g);
      box.appendChild(root);
    }

    function drawBreakEven(be, cur) {
      var box = $("be-chart");
      box.textContent = "";
      if (be.status !== "ok") {
        box.appendChild(el("p", { className: "chart-note", text: be.status === "undefined"
          ? "No break-even chart: the revenue line never rises above the cost line because each sale does not cover its own variable cost."
          : "No break-even chart: add revenue assumptions to see one." }));
        return;
      }
      var maxU = Math.max(be.units * 2, (be.monthly_units || 0) * 1.15, 1);
      var steps = 20;
      var rev = [], cost = [];
      for (var i = 0; i <= steps; i++) {
        var u = maxU * i / steps;
        rev.push([u, u * be.unit_price]);
        cost.push([u, be.fixed_costs + u * be.variable_cost_per_unit]);
      }
      var hi = Math.max(rev[steps][1], cost[steps][1]);
      var ticks = niceTicks(0, hi, 4);
      hi = Math.max(hi, ticks[ticks.length - 1]);
      var sx = function (v) { return PAD_L + (W - PAD_L - PAD_R) * v / maxU; };
      var sy = function (v) { return PAD_T + (H - PAD_T - PAD_B) * (hi - v) / (hi || 1); };
      var root = svg("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-labelledby": "be-t be-d", "class": "chart" });
      root.appendChild(svg("title", { id: "be-t" }, "Break-even: monthly sales revenue versus total monthly cost"));
      root.appendChild(svg("desc", { id: "be-d" }, be.message));
      var g = svg("g");
      axes(g, PAD_L, W - PAD_R, sy(0), sy(hi), "units sold per month →", ticks, function (v) { return C.formatMoney(v, cur).replace(/\.00$/, ""); }, sx, sy);
      function path(points, cls) {
        g.appendChild(svg("path", { d: points.map(function (p, j) { return (j ? "L" : "M") + sx(p[0]).toFixed(1) + " " + sy(p[1]).toFixed(1); }).join(" "), "class": "line " + cls }));
      }
      path(cost, "s2");
      path(rev, "s1");
      g.appendChild(svg("text", { x: sx(maxU) - 4, y: sy(rev[steps][1]) - 8, "text-anchor": "end", "class": "direct" }, "Revenue"));
      g.appendChild(svg("text", { x: sx(maxU) - 4, y: sy(cost[steps][1]) + 18, "text-anchor": "end", "class": "direct" }, "Total cost"));
      var bx = sx(be.units), by = sy(be.revenue);
      g.appendChild(svg("line", { x1: bx, x2: bx, y1: by, y2: sy(0), "class": "guide" }));
      hoverDot(g, bx, by, "s1", "Break-even: " + C.formatNumber(be.units_whole, 0) + " units, " + C.formatMoney(be.revenue, cur) + " in sales");
      g.appendChild(svg("text", { x: bx + 8, y: by - 10, "class": "callout" }, "break-even ≈ " + C.formatNumber(be.units_whole, 0) + " units"));
      if (be.monthly_units) {
        var vx = sx(be.monthly_units);
        g.appendChild(svg("line", { x1: vx, x2: vx, y1: sy(hi), y2: sy(0), "class": "guide" }));
        g.appendChild(svg("text", { x: vx - 4, y: sy(hi) + 12, "text-anchor": "end", "class": "tick" }, "assumed volume"));
      }
      root.appendChild(g);
      box.appendChild(root);
    }

    // ---------------------------------------------------------- start
    if (samples.length) loadData(clone(samples[0]));
  }
})(typeof window !== "undefined" ? window : globalThis);
