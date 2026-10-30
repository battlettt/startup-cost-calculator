# Startup costs, in plain English

This page explains the ideas behind the calculator. It assumes no business or
accounting background. Every example number here is made up.

> **SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA.**
> The figures on this page and in the samples were invented to make the
> arithmetic easy to follow. They are not research into what anything costs.

## 1. One-time costs vs recurring costs

A **one-time cost** is paid once, usually before you open: a cart, a mower,
a laptop, a permit, your first batch of stock, a sign.

A **recurring cost** comes back every month whether you sell anything or not:
rent, insurance, software subscriptions, a phone plan, a loan payment.

Why it matters: people remember the big one-time purchases and forget the
small monthly ones. But a $60 subscription is $720 a year, and five of them
quietly become the biggest cost in the business.

## 2. Fixed vs variable costs

This is a different way of slicing the same money.

- A **fixed cost** stays the same no matter how much you sell. Rent is
  fixed: you pay it if you sell 10 coffees or 1,000.
- A **variable cost** goes up with every sale. For a coffee cart, the
  beans, milk, cup and lid in each drink are variable costs. Sell twice as
  many drinks, use twice as many cups.

In this calculator, your **monthly costs** are treated as the fixed costs,
and the **variable cost per unit** is what one sale costs you to make. (A
"unit" is whatever you sell one of: a drink, a lesson, a lawn mowed.)

## 3. Burn rate

Your **burn rate** (or *monthly burn*) is how much cash leaves the business
each month. In the calculator it is simply the total of your monthly costs,
because it assumes **no sales at all**. That's on purpose: it shows how
long you can survive while sales are slow, which they usually are at first.

If you also enter sales assumptions, the report shows a second figure, the
**net burn**: monthly costs minus what your sales contribute. If net burn is
zero or negative, your sales cover your costs and cash grows each month.

## 4. Runway

**Runway** is how many months your cash lasts before it runs out.

```
runway (months) = (starting cash − total one-time costs) ÷ monthly burn
```

Example: you have $10,000, opening costs $7,000, and monthly costs are $1,000.
After opening you have $3,000 left, so runway is 3,000 ÷ 1,000 = **3 months**.

Two special cases the calculator spells out instead of printing a strange number:

- **Shortfall.** If the one-time costs are more than your starting cash, you
  can't even open. Instead of a negative runway, the report tells you how much
  more cash you need. Example: $5,000 cash, $7,000 to open → "You need at least
  $2,000 more just to open."
- **Unlimited.** If monthly burn is zero (or sales more than cover costs),
  cash never runs out, so runway is "not limited" rather than a division by zero.

## 5. Break-even

**Break-even** is the number of sales each month where money in equals money
out: no profit, no loss.

First, work out the **contribution margin**: what each sale leaves over after
paying for its own variable cost.

```
contribution margin = price per unit − variable cost per unit
break-even units    = monthly fixed costs ÷ contribution margin   (round up)
break-even revenue  = break-even units × price per unit
```

**Worked example** (a candle stall, invented numbers):

- Each candle sells for **$18** and costs **$6** in wax, wick and jar.
- Contribution margin = 18 − 6 = **$12** per candle.
- Monthly fixed costs (stall fee, insurance, website) = **$900**.
- Break-even units = 900 ÷ 12 = **75 candles a month**.
- Break-even revenue = 75 × 18 = **$1,350 a month**.

Sell the 76th candle and you start making a profit: $12 for each extra candle.

If the answer comes out as a fraction (say 398.5 drinks), round **up**,
because 398 isn't quite enough.

**When break-even is impossible.** If the price is at or below the variable
cost, every sale loses money (or earns nothing), so no number of sales ever
covers the fixed costs. The calculator reports break-even as **undefined** and
says why. It never shows a negative or infinite number of units.

### Months to earn back the opening costs

If you enter an assumed monthly volume, the calculator also estimates how long
it takes for profit to pay back the one-time costs:

```
monthly profit = (units per month × contribution margin) − monthly fixed costs
months to earn back = total one-time costs ÷ monthly profit
```

Candle stall again: selling 150 candles a month gives 150 × 12 − 900 = $900
profit a month. If opening cost $2,700, that's 2,700 ÷ 900 = **3 months**.
If monthly profit is zero or negative, the answer is "never at this volume".

### Paying yourself

Break-even with only the business's costs means the business survives, but
you work for free. The `fixed_cost_override` field lets you use a bigger
fixed-cost figure, for example monthly costs plus the pay you need, so
break-even means "the business pays me too". The tutoring sample does this.

## 6. Contingency: why a buffer exists

A **contingency** is extra money added to your one-time costs for things you
didn't plan for: a permit that costs more than expected, a part that breaks
in week one, a delivery fee nobody mentioned. Something like this almost always
happens, even when you can't say in advance what it will be.

The calculator adds a percentage (10% by default) on top of the one-time
subtotal. With $8,000 of opening costs and 10% contingency, you plan for
$8,800.

**What happens without one?** Say you have exactly $8,000, spend it all, and a
$500 surprise turns up. You either can't open or you open with no cash at all
for the first month's rent. A 0% contingency is allowed (it's your plan), but
the runway it shows is the best case, not a likely one. Setting 100% doubles
the one-time costs, a very cautious plan that can be useful as a stress test.

## 7. Common beginner mistakes

1. **Forgetting recurring costs.** Listing the equipment but not insurance,
   subscriptions, phone, fuel or card-processing fees. Go through a typical
   month and write down every payment.
2. **Confusing revenue with profit.** $5,000 of sales is not $5,000 earned.
   Take away the variable cost of every sale and the fixed costs first. The
   break-even panel shows the difference.
3. **Pricing below variable cost.** If a drink costs $1.60 to make and sells
   for $1.50, selling more makes things worse. Check the contribution margin
   before anything else.
4. **Ignoring runway.** A business can be profitable "on paper" at full volume
   and still run out of cash while it builds up customers. Runway shows how
   long you can wait.
5. **No contingency.** Planning to spend every dollar you have. Leave a buffer.
6. **Treating sample numbers as real.** The figures in this project are
   invented. Get real quotes for your area before deciding anything.

## 8. Try it yourself

- **Demo:** open [`index.html`](index.html), load the *Mobile coffee cart*
  sample, then:
  - set the price to `1.20` and watch break-even become undefined;
  - set contingency to `0`, then `100`, and watch the runway change;
  - pick the *premium* scenario and read the shortfall message;
  - delete the commissary rent row and see how far the runway stretches.
- **CLI:** from the repository root,
  ```sh
  PYTHONPATH=src python3 -m startup_costs report examples/tutoring_service.json
  PYTHONPATH=src python3 -m startup_costs report examples/lawn_care.json --format html -o lawn.html
  PYTHONPATH=src python3 -m startup_costs init my-idea.json
  ```
  then edit `my-idea.json` with your own costs and run the report on it.
- **Break something on purpose:** give an item a negative amount or type
  `"lots"` as the starting cash, and read the error. Each one names the item
  and says what's wrong.
