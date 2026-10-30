# Chapter: Entrepreneurship

## Thesis

> **Every idea has a price before it has a customer. Add it up first, while
> changing your mind still costs nothing.**

## Figure: "The crossing"

A single inline SVG that combines the two questions this project answers:
*how long does the cash last?* (a burn-down staircase) and *when do sales
pay for themselves?* (the break-even crossing).

### Specification

- **Canvas:** `viewBox="0 0 640 240"`, scales to 100% width, no fixed height.
  Transparent background so it sits on the chapter's surface color.
- **Baseline:** one 1px solid hairline at y = 200, from x = 40 to x = 600,
  in the muted-ink color `#52514e`. No other axes, no ticks, no gridlines.
- **Cash burn-down (background layer):** a descending step path in the muted
  ink at 35% opacity, 2px stroke, round joins. It starts at (40, 40) and drops
  32px every 80px across: steps at x = 120, 200, 280, 360, finishing at
  (440, 200) where it meets the baseline. That point is where the cash runs out.
  The months shown are illustrative, not a forecast.
- **Total-cost line:** a straight 2px line in orange `#eb6834` (dark mode
  `#d95926`) from (40, 120) to (600, 72). It starts high because fixed costs
  exist before the first sale, and rises gently because each sale adds a
  small variable cost.
- **Revenue line:** a straight 2px line in blue `#2a78d6` (dark mode `#3987e5`)
  from (40, 200) to (600, 24). It starts at zero and rises steeply.
- **The crossing:** the lines meet at (390, 90) (solve 200 − 176t = 120 − 48t
  for t = (x − 40) / 560: t = 0.625). Mark it with an 8px dot
  (r = 4) filled blue with a 2px ring in the surface color, plus a 1px muted
  vertical guide down to the baseline.
- **Labels (text ink, never the series color):** 13px system-ui, weight 600.
  "revenue" at the right end of the blue line, "total cost" under the right
  end of the orange line, "break-even" just above and left of the dot,
  "cash runs out" under the end of the staircase. A small colored line-key
  sits next to the two series labels so identity never depends on color alone.
- **Accessibility:** `role="img"` with `<title>` "Break-even crossing over a
  cash burn-down" and a `<desc>` describing the shapes (below). The palette
  pair passes the dataviz validator in light and dark mode (CVD ΔE 24.7,
  normal-vision ΔE 33.6, both ≥ 3:1 contrast on the surface).
- **Motion (optional):** draw the staircase first, then the two lines, then
  pop the dot. Use `stroke-dashoffset` over 1.2s, skipped when
  `prefers-reduced-motion: reduce`.

### Embed-ready markup

```html
<svg viewBox="0 0 640 240" width="100%" role="img" aria-labelledby="xing-t xing-d"
     xmlns="http://www.w3.org/2000/svg" font-family="system-ui, sans-serif">
  <title id="xing-t">Break-even crossing over a cash burn-down</title>
  <desc id="xing-d">A faint staircase falls from top left to the baseline, showing cash
    running out month by month. Over it, a blue revenue line rises steeply from zero and
    crosses an orange total-cost line that starts higher and rises gently. The crossing,
    marked with a dot, is break-even. Illustrative shape only, not data.</desc>
  <style>
    .ink { fill: #0b0b0b } .muted { stroke: #52514e } .rev { stroke: #2a78d6 } .cost { stroke: #eb6834 }
    .dot { fill: #2a78d6; stroke: #fcfcfb }
    @media (prefers-color-scheme: dark) {
      .ink { fill: #f0efec } .muted { stroke: #c3c2b7 } .rev { stroke: #3987e5 } .cost { stroke: #d95926 }
      .dot { fill: #3987e5; stroke: #1a1a19 }
    }
  </style>
  <line x1="40" y1="200" x2="600" y2="200" class="muted" stroke-width="1"/>
  <path d="M40 40 H120 V72 H200 V104 H280 V136 H360 V168 H440 V200" fill="none"
        class="muted" stroke-width="2" stroke-opacity=".35" stroke-linejoin="round"/>
  <line x1="40" y1="120" x2="600" y2="72" class="cost" stroke-width="2" stroke-linecap="round"/>
  <line x1="40" y1="200" x2="600" y2="24" class="rev" stroke-width="2" stroke-linecap="round"/>
  <line x1="390" y1="90" x2="390" y2="200" class="muted" stroke-width="1"/>
  <circle cx="390" cy="90" r="4" class="dot" stroke-width="2"/>
  <g font-size="13" font-weight="600" class="ink">
    <text x="300" y="80">break-even</text>
    <text x="596" y="20" text-anchor="end">revenue</text>
    <text x="596" y="92" text-anchor="end">total cost</text>
    <text x="440" y="218" text-anchor="middle">cash runs out</text>
  </g>
  <line x1="504" y1="16" x2="520" y2="16" class="rev" stroke-width="3"/>
  <line x1="490" y1="88" x2="506" y2="88" class="cost" stroke-width="3"/>
</svg>
```

## Project summary

**startup-cost-calculator** turns a list of costs and three guesses (price,
cost per unit, starting cash) into the numbers that decide whether a small
business survives: total opening cost with a contingency buffer, monthly burn,
runway, break-even and months to earn back the investment, compared across
lean, standard and premium plans. It is a standard-library Python CLI with
text, JSON, printable HTML and CSV reports, plus a static browser demo whose
JavaScript is tested to give exactly the same answers. Every sample business
is a **SYNTHETIC EXAMPLE — ILLUSTRATIVE FIGURES ONLY, NOT MARKET DATA**, and
the plain-English concepts guide teaches the arithmetic behind each figure.
