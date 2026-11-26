"""Write a costed BOM (one row per part, costs in CAD) from a product BOM.

Usage:
    python tools/bom_cost.py BOM.csv TOP_PN UNITS [--repo PRODUCT_REPO] [--out FILE.csv]

The BOM is expanded from TOP_PN exactly as requisition.py does (a part with a supplier is
one line, even if it has its own BOM; assemblies without a supplier are expanded; parts made
in-house are listed with no cost). Costs are per piece, so packs do not affect them: 12
screws cost 12 x unit_price, whatever the pack size.

Output columns (one value per cell, so it pastes cleanly into a spreadsheet):
  PN, Description, Qty per unit, Qty, Supplier, Supplier PN, Unit cost, Currency,
  Unit cost (CAD), Extended (CAD), Price date, Link
followed by a TOTAL row in CAD. Foreign currencies are converted with rates.csv
(currency, cad_per_unit, rate_date). Warnings are printed for missing prices, prices older
than 90 days, and missing or old exchange rates. The output defaults to
<TOP_PN>_x<UNITS>_cost_<YYYY-MM-DD>.csv in the current folder.
"""
import csv
import os
import sys
from collections import defaultdict
from datetime import date

from lib import ROOT, load_parts, load_product_parts, parts_by_pn, read_csv
from requisition import STALE_DAYS, expand

RATES = os.path.join(ROOT, "rates.csv")
RATE_STALE_DAYS = 30
COLUMNS = ["PN", "Description", "Qty per unit", "Qty", "Supplier", "Supplier PN", "Unit cost",
           "Currency", "Unit cost (CAD)", "Extended (CAD)", "Price date", "Link"]


def num(v, places):
    return f"{v:.{places}f}".rstrip("0").rstrip(".") if v is not None else ""


def main(argv):
    pos, opts = [], {"repo": None, "out": None}
    it = iter(argv[1:])
    for a in it:
        if a in ("--repo", "--out"):
            opts[a[2:]] = next(it)
        else:
            pos.append(a)
    if len(pos) != 3:
        print(__doc__)
        return 1
    bom_path, top, units = pos[0], pos[1], int(pos[2])
    repo = opts["repo"] or os.path.dirname(os.path.dirname(os.path.abspath(bom_path)))
    parts = parts_by_pn(load_parts() + load_product_parts(repo))
    bom = defaultdict(list)
    for line in read_csv(bom_path):
        bom[line["parent_pn"]].append(line)

    need, made = defaultdict(float), defaultdict(float)
    top_part = parts.get(top)
    if top_part and top_part.get("supplier"):
        need[top] = units
    else:
        expand(bom, parts, top, units, need, made)

    rates = {r["currency"]: r for r in read_csv(RATES)}
    today, warnings, rows, total, priced = date.today(), [], [], 0.0, True
    for pn in sorted(set(need) | set(made)):
        p, qty = parts[pn], need.get(pn) or made.get(pn)
        cur, price = p.get("currency", ""), p.get("unit_price", "")
        unit = cad_unit = ext = None
        if pn in made:
            note = "made in-house"
        elif not price:
            warnings.append(f"{pn}: no price")
            priced = False
        else:
            unit = float(price)
            if p.get("price_date"):
                age = (today - date.fromisoformat(p["price_date"])).days
                if age > STALE_DAYS:
                    warnings.append(f"{pn}: price is {age} days old ({p['price_date']})")
            rate = rates.get(cur)
            if not rate:
                warnings.append(f"{pn}: no CAD rate for currency {cur!r} in rates.csv")
                priced = False
            else:
                cad_unit = unit * float(rate["cad_per_unit"])
                ext = cad_unit * qty
                total += ext
        rows.append({
            "PN": pn, "Description": p.get("description", ""),
            "Qty per unit": num(qty / units, 4), "Qty": num(qty, 4),
            "Supplier": p.get("supplier", "") if pn not in made else "(made in-house)",
            "Supplier PN": p.get("supplier_pn") or p.get("manufacturer_pn", ""),
            "Unit cost": num(unit, 6), "Currency": cur if unit is not None else "",
            "Unit cost (CAD)": num(cad_unit, 4), "Extended (CAD)": num(ext, 2),
            "Price date": p.get("price_date", "") if unit is not None else "",
            "Link": p.get("link", ""),
        })
    for cur, r in sorted(rates.items()):
        if cur != "CAD" and r.get("rate_date") and any(x["Currency"] == cur for x in rows):
            age = (today - date.fromisoformat(r["rate_date"])).days
            if age > RATE_STALE_DAYS:
                warnings.append(f"rates.csv: {cur} rate is {age} days old ({r['rate_date']})")

    out = opts["out"] or f"{top}_x{units}_cost_{today.isoformat()}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        w.writerow({"PN": "TOTAL", "Description": f"{top} x {units}" + ("" if priced else " (incomplete: see warnings)"),
                    "Currency": "CAD", "Extended (CAD)": f"{total:.2f}"})
    print(f"wrote {out} ({len(rows)} parts, total {total:.2f} CAD for {units} x {top})")
    for wmsg in warnings:
        print(f"warning: {wmsg}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
