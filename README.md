# startup-cost-calculator

**Price an idea before you build it.** A small, offline startup cost estimator
for small business ideas: what it costs to open, what it costs to stay open,
how long your cash lasts, and how many sales it takes to break even.

- **Python CLI** (standard library only) is the source of truth.
- **Static demo** in [`docs/`](docs/index.html) (vanilla JS, no build step, no
  dependencies) runs the same calculations in the browser and deploys as-is
  to GitHub Pages.
- **Parity tests** run the demo's JavaScript under Node and check that it
  produces exactly the same numbers, messages and validation errors as the CLI.
- No API keys, no paid services, no network calls.

> **SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA.**
> Every sample business and every figure in this README was invented for
> teaching. None of it is research into real prices. Use your own quotes.

New to the ideas (burn rate, runway, break-even, contingency)? Read
[`docs/concepts.md`](docs/concepts.md) first. It assumes no background.

## Why it matters

Most small businesses that run out of money don't do it because the idea was
bad. They do it because nobody added up the monthly costs, or the price was
below what each sale costs to make, or the cash ran out a month before sales
picked up. Ten minutes with a list of costs and three numbers (price, cost per
unit, starting cash) shows those problems before you spend anything.

## Run it

Needs Python 3.8+ and nothing else. From the repository root:

```sh
# write a commented example input you can edit
PYTHONPATH=src python3 -m startup_costs init my-idea.json

# check an input and list every problem, numbered by item
PYTHONPATH=src python3 -m startup_costs validate my-idea.json

# full report (text by default)
PYTHONPATH=src python3 -m startup_costs report examples/coffee_cart.json

# other formats: json, html (self-contained, printable), csv (scenario comparison)
PYTHONPATH=src python3 -m startup_costs report examples/lawn_care.json --format html -o lawn.html
PYTHONPATH=src python3 -m startup_costs report examples/lawn_care.json -f csv -o lawn.csv
```

If you prefer an installed command, run `pip install -e .` and use
`startup-costs report ...` instead.

Exit codes: `0` success, `1` invalid input (every error is listed, nothing is
silently dropped), `2` wrong command usage.

### The demo

Open `docs/index.html` straight from disk, or publish the `docs/` folder with
GitHub Pages (Settings → Pages → branch, folder `/docs`). You can:

- load one of the synthetic sample businesses,
- edit, add and remove one-time and monthly cost rows,
- set starting cash, contingency and sales assumptions,
- switch between the *as entered*, lean, standard and premium scenarios,
- read the runway and break-even panels (each with a chart),
- compare all scenarios side by side, with a stated winner per metric,
- download your figures as JSON and feed them to the CLI.

Errors in the demo are the same messages, word for word, as the CLI's.

### Input format

```jsonc
{
  "_comment": "keys starting with _ are comments",
  "name": "Mobile coffee cart",
  "label": "SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA",
  "currency": "USD",                 // optional; USD CAD AUD NZD GBP EUR get symbols
  "starting_cash": 18000,            // required, >= 0
  "contingency_pct": 10,             // optional, 0-100, default 10
  "one_time_costs": [ {"name": "Cart and build-out", "amount": 7500, "category": "equipment"} ],
  "monthly_costs":  [ {"name": "Commissary kitchen rent", "amount": 450, "category": "facilities"} ],
  "revenue": {                       // optional; needed for break-even
    "unit_price": 4.75,
    "variable_cost_per_unit": 1.35,
    "monthly_units": 1200,           // optional assumed volume
    "fixed_cost_override": null      // optional; replaces the monthly total in break-even
  },
  "scenarios": [                     // optional; defaults to lean / standard / premium
    {"name": "lean", "one_time_factor": 0.8, "monthly_factor": 0.9,
     "overrides": [{"item": "Espresso machine and grinder", "amount": 2500, "kind": "one_time"}]},
    {"name": "premium", "one_time_factor": 1.3, "monthly_factor": 1.2,
     "revenue": {"unit_price": 5.5}}
  ]
}
```

(The real files are plain JSON; the `//` notes above are only for this README.)

Rules worth knowing:

- Factors multiply every item. An **override** sets one item's amount
  exactly and is *not* multiplied by the factor. `kind` (`one_time` or
  `monthly`) is only needed when the same name appears in both lists.
- Item names must be unique within a list, so overrides are never ambiguous.
- Validation catches negative amounts, missing fields, unknown keys, text
  where a number belongs, contingency outside 0–100, overrides that name a
  missing item, and more. Each error says which item, for example
  `monthly_costs item 2 ("Insurance"): "amount" must not be negative (got -100)`.
- Empty cost lists are a **warning**, not a crash.

## Worked example: the mobile coffee cart

> **SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA.**
> These are the invented figures in `examples/coffee_cart.json`.

`PYTHONPATH=src python3 -m startup_costs report examples/coffee_cart.json`
produces every number below. Here is how each one is worked out.

**1. One-time costs (paid once, to open)**

| Item | Amount |
|---|---:|
| Cart and build-out | $7,500 |
| Espresso machine and grinder | $4,200 |
| POS tablet and card reader | $350 |
| Permits and health inspection | $650 |
| Opening inventory | $800 |
| Branding and signage | $600 |
| **Subtotal** | **$14,100** |

Contingency is 10% of the subtotal: 14,100 × 10 / 100 = **$1,410**.
Total one-time cost = 14,100 + 1,410 = **$15,510**.

**2. Monthly burn (recurring costs)**

450 rent + 300 event fees + 120 insurance + 60 POS software + 55 phone
+ 220 fuel + 150 marketing = **$1,355 a month**.

**3. Runway**

Cash left after opening = 18,000 − 15,510 = **$2,490**.
Runway = 2,490 / 1,355 = 1.84 → **about 1.8 months** if nothing sells.
That is thin: one slow month and the cart is out of cash.

**4. Break-even**

Each drink sells for $4.75 and costs $1.35 to make (beans, milk, cup).
Contribution margin = 4.75 − 1.35 = **$3.40** per drink (71.6% of the price).
Break-even units = fixed costs / margin = 1,355 / 3.40 = 398.53 → **399 drinks
a month** (you can't sell part of a drink, so round up).
Break-even revenue = 398.53 × 4.75 = **$1,893.01** a month.

**5. Months to earn back the one-time cost**

At the assumed 1,200 drinks a month: 1,200 × 3.40 = $4,080 contribution,
minus $1,355 fixed costs = **$2,725 profit a month**.
15,510 / 2,725 = 5.69 → **about 5.7 months** to earn back the opening costs.

**6. Scenarios**

| Scenario | One-time total | Monthly burn | Runway (no sales) | Break-even units |
|---|---:|---:|---:|---:|
| lean | $11,462.00 | $1,219.50 | 5.4 months | 359 |
| standard | $15,510.00 | $1,355.00 | 1.8 months | 399 |
| premium | $20,163.00 | $1,626.00 | short $2,163.00 at opening | 417 |

Lean scales one-time costs by 0.8 and monthly costs by 0.9, but sets the
espresso machine to a refurbished $2,500 (not scaled):
6,000 + 2,500 + 280 + 520 + 640 + 480 = 10,420, plus 10% = $11,462.
Premium costs more than the $18,000 starting cash, so the report says
plainly that it is **$2,163 short** instead of printing a negative runway.

The report ends with the winners, in plain words:

```
Cheapest to launch: lean ($11,462.00 one-time, including contingency).
Lowest monthly burn: lean ($1,219.50 a month).
Longest runway: lean (5.4 months).
Fewest sales needed to break even: lean (359 units a month).
```

## Samples

All three are **SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA.**

| File | Business | What it teaches |
|---|---|---|
| `examples/coffee_cart.json` | Mobile coffee cart | Thin runway; premium can't open on the starting cash |
| `examples/tutoring_service.json` | Neighbourhood tutoring | Low start-up cost; `fixed_cost_override` adds owner pay to break-even; overrides set items to zero |
| `examples/lawn_care.json` | Lawn-care service | Equipment-heavy; premium shortfall; per-item override in lean |

`docs/samples.js` is generated from these files by `python3 tools/sync_samples.py`,
and a test fails if the two drift apart.

## Tests

```sh
python3 -m unittest discover -s tests -t . -v
```

Standard library `unittest` only. Node is used **only** by the tests (parity
and demo smoke test); if `node` is missing, those tests are skipped and
reported as skipped. See [`TESTS.txt`](TESTS.txt) for the latest verified count.

What is covered: calculations (with hand-checked numbers), edge cases (zero
and negative burn, price at or below variable cost, cash shortfall, 0% and
100% contingency, scenario overrides, ties), validation errors, all four
report formats, the CLI end to end on every sample and fixture, JS/CLI parity
on every sample and fixture (numbers, messages and errors), the demo UI booting
and reacting to edits under a fake DOM, and the synthetic labels.

## Layout

```
src/startup_costs/   model.py (validation), calculations.py, scenarios.py, reports.py, cli.py
tests/               unittest suites, fixtures/, js/ (Node parity runner + UI smoke test)
examples/            three synthetic sample businesses
docs/                index.html, app.js, style.css, samples.js (the demo), concepts.md
tools/               sync_samples.py
CHAPTER.md           portfolio chapter text and figure
```

## How the numbers stay identical in Python and JavaScript

Both sides round money to cents after each step using the same
"round half up" rule, `floor(x × 100 + 0.5 + 1e-9) / 100`. Python's built-in
`round()` rounds halves to even and would disagree with JavaScript on values
like 0.125, so it is never used. Sums are added in the same order and
messages are built from the same formatter, so even the sentences match.

## License

MIT. See [LICENSE](LICENSE).
