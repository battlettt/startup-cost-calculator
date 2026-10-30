"""Report renderers: text, JSON, HTML (self-contained, printable) and CSV."""

import csv
import html
import io
import json

from .calculations import format_money, format_number, format_quantity
from .model import LABEL
from .scenarios import runway_text

FOOTER = (
    "These figures are only as good as the assumptions entered. This is a "
    "planning estimate, not financial advice and not market data."
)

CSV_COLUMNS = [
    "scenario", "label", "currency", "one_time_factor", "monthly_factor", "overrides",
    "one_time_subtotal", "contingency_pct", "contingency_amount", "one_time_total",
    "monthly_burn", "starting_cash", "cash_after_one_time", "runway_status",
    "runway_months", "shortfall", "break_even_status", "contribution_margin",
    "break_even_units", "break_even_units_whole", "break_even_revenue",
    "months_to_break_even",
]


def build_report(model, warnings=()):
    """Everything a renderer needs, as plain JSON-able data."""
    from .calculations import analyze
    from .scenarios import compare

    return {
        "label": model["label"] or "",
        "analysis": analyze(model),
        "comparison": compare(model),
        "warnings": list(warnings),
    }


def _label_line(report):
    return report["label"] or "(no label given: treat every figure as an assumption)"


# ---------------------------------------------------------------- text

def _table(rows, aligns):
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    lines = []
    for n, row in enumerate(rows):
        cells = []
        for i, cell in enumerate(row):
            cell = str(cell)
            cells.append(cell.rjust(widths[i]) if aligns[i] == "r" else cell.ljust(widths[i]))
        lines.append("  " + "  ".join(cells).rstrip())
        if n == 0:
            lines.append("  " + "  ".join("-" * w for w in widths))
    return lines


def render_text(report):
    a = report["analysis"]
    cur = a["currency"]
    money = lambda v: format_money(v, cur)  # noqa: E731
    out = []
    title = f"Startup cost estimate: {a['name']}"
    out += [title, "=" * len(title), _label_line(report), ""]
    out.append(f"Starting cash: {money(a['starting_cash'])}")
    out.append("")

    out.append("ONE-TIME COSTS (paid once, before or at opening)")
    if a["one_time"]["items"]:
        rows = [["Item", "Category", "Amount"]]
        rows += [[i["name"], i["category"], money(i["amount"])] for i in a["one_time"]["items"]]
        out += _table(rows, "llr")
    else:
        out.append("  (none entered)")
    ot = a["one_time"]
    out.append(f"  Subtotal: {money(ot['subtotal'])}")
    out.append(
        f"  Contingency buffer ({format_quantity(ot['contingency_pct'])}%): "
        f"{money(ot['contingency_amount'])}"
    )
    out.append(f"  Total one-time cost: {money(ot['total'])}")
    out.append("")

    out.append("MONTHLY RECURRING COSTS (paid every month, sales or not)")
    if a["monthly"]["items"]:
        rows = [["Item", "Category", "Per month"]]
        rows += [[i["name"], i["category"], money(i["amount"])] for i in a["monthly"]["items"]]
        out += _table(rows, "llr")
    else:
        out.append("  (none entered)")
    out.append(f"  Monthly burn: {money(a['monthly']['total'])}")
    out.append("")

    out.append("RUNWAY")
    out.append("  " + a["runway"]["message"])
    if a["runway_with_revenue"]:
        out.append("  With the assumed sales: " + a["runway_with_revenue"]["message"])
    out.append("")

    out.append("BREAK-EVEN")
    be = a["break_even"]
    out.append("  " + be["message"])
    if be["months_message"]:
        out.append("  " + be["months_message"])
    out.append("")

    comp = report["comparison"]
    if comp["scenarios"]:
        out.append("SCENARIOS")
        rows = [["Scenario", "One-time total", "Monthly burn", "Runway", "Break-even units"]]
        for s in comp["scenarios"]:
            sa = s["analysis"]
            sbe = sa["break_even"]
            be_text = format_number(sbe["units_whole"], 0) if sbe["status"] == "ok" else sbe["status"].replace("_", " ")
            rows.append([
                s["name"], money(sa["one_time"]["total"]), money(sa["monthly"]["total"]),
                runway_text(sa["runway"], cur), be_text,
            ])
        out += _table(rows, "lrrrr")
        out.append("")
        for s in comp["scenarios"]:
            parts = [
                f"one-time x{format_quantity(s['one_time_factor'])}",
                f"monthly x{format_quantity(s['monthly_factor'])}",
            ]
            for o in s["overrides"]:
                parts.append(f"{o['item']} set to {money(o['amount'])}")
            if s["revenue_overrides"]:
                for k, v in s["revenue_overrides"].items():
                    parts.append(f"{k} = {format_quantity(v)}")
            desc = f" - {s['description']}" if s["description"] else ""
            out.append(f"  {s['name']}{desc} [{'; '.join(parts)}]")
        out.append("")
        out.append("WINNERS")
        for w in comp["winners"]:
            out.append("  " + w["statement"])
        out.append("")

    if report["warnings"]:
        out.append("WARNINGS")
        for w in report["warnings"]:
            out.append("  - " + w)
        out.append("")
    out.append(FOOTER)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- json

def render_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- csv

def scenario_rows(report):
    rows = []
    for s in report["comparison"]["scenarios"]:
        a = s["analysis"]
        r = a["runway"]
        be = a["break_even"]
        overrides = "; ".join(f"{o['kind']}:{o['item']}={o['amount']}" for o in s["overrides"])
        rows.append({
            "scenario": s["name"],
            "label": report["label"],
            "currency": a["currency"],
            "one_time_factor": s["one_time_factor"],
            "monthly_factor": s["monthly_factor"],
            "overrides": overrides,
            "one_time_subtotal": a["one_time"]["subtotal"],
            "contingency_pct": a["one_time"]["contingency_pct"],
            "contingency_amount": a["one_time"]["contingency_amount"],
            "one_time_total": a["one_time"]["total"],
            "monthly_burn": a["monthly"]["total"],
            "starting_cash": a["starting_cash"],
            "cash_after_one_time": r["cash_after_one_time"],
            "runway_status": r["status"],
            "runway_months": r["months"],
            "shortfall": r["shortfall"],
            "break_even_status": be["status"],
            "contribution_margin": be["contribution_margin"],
            "break_even_units": be["units"],
            "break_even_units_whole": be["units_whole"],
            "break_even_revenue": be["revenue"],
            "months_to_break_even": be["months_to_break_even"],
        })
    return rows


def render_csv(report):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in scenario_rows(report):
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return buf.getvalue()


# ---------------------------------------------------------------- html

HTML_CSS = """
:root { --ink:#1f2328; --muted:#57606a; --line:#d0d7de; --accent:#0b5cad;
        --warn:#8a4b00; --bad:#a40e26; --good:#1a7f37; --paper:#ffffff; }
* { box-sizing: border-box; }
body { font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       color: var(--ink); background: var(--paper); margin: 0 auto; max-width: 960px;
       padding: 24px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.15rem; margin: 28px 0 8px; border-bottom: 2px solid var(--line);
     padding-bottom: 4px; }
.label { display: inline-block; border: 2px solid var(--warn); color: var(--warn);
         font-weight: 700; padding: 4px 10px; border-radius: 4px; letter-spacing: .02em; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left;
         vertical-align: top; }
th { background: #f6f8fa; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.total td { font-weight: 700; }
.msg { padding: 8px 12px; border-left: 4px solid var(--accent); background: #f3f8fd;
       margin: 8px 0; }
.msg.shortfall, .msg.undefined, .msg.never { border-color: var(--bad); background: #fff5f5; }
.msg.unlimited { border-color: var(--good); background: #f3fbf5; }
.winners li { margin: 4px 0; }
.warnings li { color: var(--warn); }
figure { margin: 12px 0; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0);
      white-space: nowrap; }
figcaption { color: var(--muted); font-size: .9rem; }
footer { margin-top: 32px; color: var(--muted); font-size: .9rem;
         border-top: 1px solid var(--line); padding-top: 8px; }
@media print {
  body { padding: 0; max-width: none; font-size: 11pt; }
  h2 { break-after: avoid; }
  table, figure, .msg { break-inside: avoid; }
  .msg { background: none !important; }
}
"""


def _e(value):
    return html.escape(str(value), quote=True)


def _cash_points(runway, months_cap=24):
    """Cash balance at month 0 (after one-time costs) through the runway."""
    start = runway["cash_after_one_time"]
    burn = runway["monthly_burn"]
    if runway["status"] == "finite":
        horizon = min(months_cap, max(1, int(runway["months"]) + 2))
    else:
        horizon = 12
    return [(m, start - burn * m) for m in range(horizon + 1)]


def render_burn_svg(runway, currency):
    """Small inline SVG: cash remaining month by month."""
    pts = _cash_points(runway)
    w, h, pad = 640, 220, 44
    values = [v for _, v in pts] + [0, runway["starting_cash"]]
    hi, lo = max(values), min(values)
    span = (hi - lo) or 1
    months = pts[-1][0] or 1

    def x(m):
        return pad + (w - 2 * pad) * m / months

    def y(v):
        return pad / 2 + (h - pad * 1.5) * (hi - v) / span

    line = " ".join(f"{x(m):.1f},{y(v):.1f}" for m, v in pts)
    summary = (
        f"Cash after one-time costs starts at {format_money(pts[0][1], currency)} and "
        f"changes by {format_money(0 - runway['monthly_burn'], currency)} each month. "
        + runway["message"]
    )
    parts = [
        f'<svg role="img" aria-labelledby="burn-title burn-desc" viewBox="0 0 {w} {h}" '
        f'width="100%" xmlns="http://www.w3.org/2000/svg">',
        '<title id="burn-title">Cash runway burn-down</title>',
        f'<desc id="burn-desc">{_e(summary)}</desc>',
        f'<line x1="{pad}" y1="{y(0):.1f}" x2="{w - pad}" y2="{y(0):.1f}" '
        'stroke="#a40e26" stroke-dasharray="4 4" stroke-width="1.5"/>',
        f'<text x="{w - pad}" y="{y(0) - 6:.1f}" text-anchor="end" font-size="12" '
        'fill="#a40e26">cash = 0</text>',
        f'<line x1="{pad}" y1="{pad / 2}" x2="{pad}" y2="{h - pad}" stroke="#57606a"/>',
        f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#57606a"/>',
        f'<polyline points="{line}" fill="none" stroke="#0b5cad" stroke-width="3"/>',
        f'<text x="{pad}" y="{h - pad + 18}" font-size="12" fill="#57606a">month 0</text>',
        f'<text x="{w - pad}" y="{h - pad + 18}" font-size="12" text-anchor="end" '
        f'fill="#57606a">month {months}</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_html(report):
    a = report["analysis"]
    cur = a["currency"]
    money = lambda v: format_money(v, cur)  # noqa: E731
    ot, mo = a["one_time"], a["monthly"]
    p = []
    p.append("<!DOCTYPE html>")
    p.append('<html lang="en"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    p.append(f"<title>Startup cost estimate: {_e(a['name'])}</title>")
    p.append(f"<style>{HTML_CSS}</style></head><body>")
    p.append("<header>")
    p.append(f"<h1>Startup cost estimate: {_e(a['name'])}</h1>")
    p.append(f'<p class="label">{_e(_label_line(report))}</p>')
    p.append(f"<p>Starting cash: <strong>{money(a['starting_cash'])}</strong></p>")
    p.append("</header><main>")

    def items_table(caption, items, amount_head, total_rows):
        p.append(f"<table><caption class=\"sr\">{_e(caption)}</caption>")
        p.append(f'<thead><tr><th scope="col">Item</th><th scope="col">Category</th>'
                 f'<th scope="col" class="num">{amount_head}</th></tr></thead><tbody>')
        if not items:
            p.append('<tr><td colspan="3">(none entered)</td></tr>')
        for i in items:
            p.append(f"<tr><td>{_e(i['name'])}</td><td>{_e(i['category'])}</td>"
                     f'<td class="num">{money(i["amount"])}</td></tr>')
        for label, value, strong in total_rows:
            cls = ' class="total"' if strong else ""
            p.append(f'<tr{cls}><td colspan="2">{_e(label)}</td><td class="num">{money(value)}</td></tr>')
        p.append("</tbody></table>")

    p.append("<section><h2>One-time costs</h2>")
    items_table("One-time costs", ot["items"], "Amount", [
        ("Subtotal", ot["subtotal"], False),
        (f"Contingency buffer ({format_quantity(ot['contingency_pct'])}%)", ot["contingency_amount"], False),
        ("Total one-time cost", ot["total"], True),
    ])
    p.append("</section>")

    p.append("<section><h2>Monthly recurring costs</h2>")
    items_table("Monthly recurring costs", mo["items"], "Per month", [
        ("Monthly burn", mo["total"], True),
    ])
    p.append("</section>")

    p.append("<section><h2>Runway</h2>")
    p.append(f'<p class="msg {a["runway"]["status"]}">{_e(a["runway"]["message"])}</p>')
    if a["runway_with_revenue"]:
        rr = a["runway_with_revenue"]
        p.append(f'<p class="msg {rr["status"]}">With the assumed sales: {_e(rr["message"])}</p>')
    if a["runway"]["status"] != "shortfall":
        p.append("<figure>")
        p.append(render_burn_svg(a["runway"], cur))
        p.append("<figcaption>Cash left after one-time costs, month by month, with no "
                 "sales (dashed line = zero).</figcaption></figure>")
    p.append("</section>")

    be = a["break_even"]
    p.append("<section><h2>Break-even</h2>")
    p.append(f'<p class="msg {be["status"]}">{_e(be["message"])}</p>')
    if be["months_message"]:
        p.append(f'<p class="msg {be["months_status"]}">{_e(be["months_message"])}</p>')
    p.append("</section>")

    comp = report["comparison"]
    if comp["scenarios"]:
        p.append("<section><h2>Scenario comparison</h2><table>")
        p.append('<thead><tr><th scope="col">Scenario</th><th scope="col" class="num">One-time total</th>'
                 '<th scope="col" class="num">Monthly burn</th><th scope="col" class="num">Runway</th>'
                 '<th scope="col" class="num">Break-even units / month</th>'
                 '<th scope="col" class="num">Months to earn back</th></tr></thead><tbody>')
        for s in comp["scenarios"]:
            sa = s["analysis"]
            sbe = sa["break_even"]
            be_text = format_number(sbe["units_whole"], 0) if sbe["status"] == "ok" else sbe["status"].replace("_", " ")
            mt = sbe["months_to_break_even"]
            mt_text = format_number(mt, 1) if mt is not None else sbe["months_status"].replace("_", " ")
            p.append(
                f'<tr><th scope="row">{_e(s["name"])}'
                + (f'<br><small>{_e(s["description"])}</small>' if s["description"] else "")
                + f'</th><td class="num">{money(sa["one_time"]["total"])}</td>'
                f'<td class="num">{money(sa["monthly"]["total"])}</td>'
                f'<td class="num">{_e(runway_text(sa["runway"], cur))}</td>'
                f'<td class="num">{_e(be_text)}</td><td class="num">{_e(mt_text)}</td></tr>'
            )
        p.append("</tbody></table>")
        p.append('<ul class="winners">')
        for w in comp["winners"]:
            p.append(f"<li>{_e(w['statement'])}</li>")
        p.append("</ul></section>")

    if report["warnings"]:
        p.append('<section><h2>Warnings</h2><ul class="warnings">')
        for w in report["warnings"]:
            p.append(f"<li>{_e(w)}</li>")
        p.append("</ul></section>")
    p.append(f"</main><footer><p>{_e(FOOTER)}</p><p>The bundled samples are labelled {_e(LABEL)}.</p></footer>")
    p.append("</body></html>")
    return "\n".join(p) + "\n"


RENDERERS = {
    "text": render_text,
    "json": render_json,
    "html": render_html,
    "csv": render_csv,
}
