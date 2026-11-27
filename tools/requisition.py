"""Generate purchasing-upload CSVs (one per supplier) from a product BOM.

Usage:
    python tools/requisition.py BOM.csv TOP_PN QTY [--repo PRODUCT_REPO] [--out DIR]
                                [--stock STOCK.csv] [--plan PLAN.csv] [--sheet SHEET.md]
                                [--build B00n] [--cart-link SUPPLIER=URL ...] [--skip-class C]

BOM.csv is a product repo's BOM: a build document's bom.csv (02_design/<assembly>/bom.csv) or an
older master bom.csv (parent_pn, parent_rev, pn, qty, ...). Parts are looked
up in this library (OTS, parts/CCC.csv) and in the product repo's 03_build_package/parts.csv (custom). The
product repo defaults to the folder above the BOM's folder. The BOM is expanded from TOP_PN,
multiplying quantities through sub-assemblies:
  - a PN with a supplier is ordered as one item (even if it has a BOM, e.g. a PCB ordered
    already assembled);
  - a PN without a supplier that is a parent in the BOM is expanded;
  - a custom part with a make method and no supplier (e.g. printed in-house) is listed
    as made in-house and not ordered;
  - anything else is an error.

STOCK.csv (optional) has columns pn, qty_on_hand (pieces); stock is subtracted.
The parts plan, one line per part (needed, on hand, to order, and where it comes from: order,
stock or made in house), is always printed for the human to review; --plan PLAN.csv also
writes it, e.g. to the product repo's builds/B00n/parts_plan.csv.
--sheet SHEET.md writes the order sheet: the document a person reviews before any req is sent.
It lists how many purchase reqs are needed (one per supplier), each req's lines, quantities,
prices and totals (also in CAD, from rates.csv), the parts taken from stock (marked where they
must be the exact part) and the parts made in house, and a short checklist. Each req section
names its upload file, which is what the organization's purchase-req tool reads.
--build B00n names the build in the sheet's title.
Parts sold in packs (pack_qty > 1) are ordered in whole packs: 12 screws from a pack of 100
is 1 item.
--cart-link SUPPLIER=URL puts one cart link on every row for that supplier.

Output: DIR/<supplier>-<YYYY-MM-DD>.csv with exactly the purchasing template's columns:
  Item Name, Prod No, # of Items, Price (Before Tax - Original Currency), Item Link
Prod No is the supplier part number, or the MPN if none. # of Items counts packs, and
Price is the price of one item (unit_price x pack_qty); Item Name ends ", pack of N" for
packs. price_date is not included. A warning is printed for missing prices and
prices older than 90 days.
"""
import csv
import math
import os
import re
import sys
from collections import defaultdict
from datetime import date

from lib import load_parts, load_product_parts, parts_by_pn, read_bom, read_csv

HEADER = ["Item Name", "Prod No", "# of Items", "Price (Before Tax - Original Currency)", "Item Link"]
STALE_DAYS = 90


def parse_args(argv):
    pos, opts, cart = [], {"out": ".", "stock": None, "plan": None, "sheet": None, "build": "",
                           "skip": set(), "repo": None}, {}
    it = iter(argv[1:])
    for a in it:
        if a == "--out":
            opts["out"] = next(it)
        elif a == "--repo":
            opts["repo"] = next(it)
        elif a == "--stock":
            opts["stock"] = next(it)
        elif a == "--plan":
            opts["plan"] = next(it)
        elif a == "--sheet":
            opts["sheet"] = next(it)
        elif a == "--build":
            opts["build"] = next(it)
        elif a == "--cart-link":
            k, v = next(it).split("=", 1)
            cart[k] = v
        elif a == "--skip-class":
            opts["skip"].add(next(it).upper())
        else:
            pos.append(a)
    return pos, opts, cart


def expand(bom, parts, top, qty, need, made, path=()):
    if top in path:
        raise SystemExit(f"error: BOM loop at {' > '.join(path + (top,))}")
    children = bom.get(top)
    if not children:
        raise SystemExit(f"error: {top} has no supplier and no BOM lines")
    for line in children:
        pn, q = line["pn"], float(line["qty"] or 0) * qty
        p = parts.get(pn)
        if p is None:
            raise SystemExit(f"error: {pn} (in {top}) is not in the library or the product's parts.csv")
        if p.get("supplier"):
            need[pn] += q
        elif pn in bom:
            expand(bom, parts, pn, q, need, made, path + (top,))
        elif p.get("make"):
            made[pn] += q
        else:
            raise SystemExit(f"error: {pn} has no supplier, no BOM lines and no make method")


RATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rates.csv")


def money(x):
    return f"{x:,.2f}"


def write_sheet(path, top, units, build, bom_path, by_supplier, files, plan, bom_line, warnings, today):
    """The order sheet (Markdown): what a person reviews before any purchase req is sent."""
    rates = {r["currency"]: float(r["cad_per_unit"]) for r in read_csv(RATES)} if os.path.exists(RATES) else {"CAD": 1.0}
    title = f"Order sheet: {top} x {units}" + (f", build {build}" if build else "")
    out = [f"# {title}", "",
           f"Date {today.isoformat()}. From the BOM `{os.path.basename(bom_path)}` of {top}. "
           "Prices before tax; CAD totals use rates.csv.", ""]
    reqs = []
    for supplier in sorted(by_supplier):
        rows = by_supplier[supplier]
        cur = rows[0]["_currency"]
        total = sum(float(r["Price (Before Tax - Original Currency)"] or 0) * r["# of Items"] for r in rows)
        cad = total * rates[cur] if cur in rates else None
        reqs.append((supplier, rows, cur, total, cad))
    grand = sum(c for *_, c in reqs if c is not None)
    stock = [r for r in plan if r["source"] in ("stock", "stock + order")]
    made = [r for r in plan if r["source"] == "made in house"]
    out += ["## Summary", "",
            f"- **Purchase reqs to send: {len(reqs)}** (one per supplier)",
            f"- **To order:** CA${money(grand)} before tax" + ("" if all(c is not None for *_, c in reqs) else " (some totals have no CAD rate)"),
            f"- **From stock:** {len(stock)} parts; **made in house:** {len(made)} parts", "",
            "| Req | Supplier | Lines | Total | Total CAD |", "|---|---|---|---|---|"]
    for i, (supplier, rows, cur, total, cad) in enumerate(reqs, 1):
        out.append(f"| {i} | {supplier} | {len(rows)} | {cur} {money(total)} | {money(cad) if cad is not None else '?'} |")
    for i, (supplier, rows, cur, total, cad) in enumerate(reqs, 1):
        out += ["", f"## Req {i}: {supplier}", "",
                f"Upload file for the purchase req: `{os.path.basename(files[supplier])}`", "",
                "| PN | Item | Supplier part | Qty to order | Price each | Line total | Link |",
                "|---|---|---|---|---|---|---|"]
        for r in rows:
            price = float(r["Price (Before Tax - Original Currency)"] or 0)
            out.append(f"| {r['_pn']} | {r['Item Name']} | {r['Prod No']} | {r['# of Items']} | "
                       f"{cur} {money(price)} | {cur} {money(price * r['# of Items'])} | {r['Item Link']} |")
        out.append(f"| | **Total** | | | | **{cur} {money(total)}** | |")
    out += ["", "## From stock (count before the build)", "",
            "| PN | Part | Needed | On hand | Still to order | Must be exactly this part |",
            "|---|---|---|---|---|---|"]
    for r in stock:
        exact = (bom_line.get(r["pn"], {}).get("exact_part", "") or "").lower() == "yes"
        mpn = bom_line.get(r["pn"], {}).get("manufacturer_pn", "") or bom_line.get(r["pn"], {}).get("mpn", "")
        out.append(f"| {r['pn']} | {r['description']} | {r['needed']} | {r['on_hand']} | {r['to_order']} | "
                   f"{'yes: ' + mpn if exact else 'no: any matching part'} |")
    if made:
        out += ["", "## Made in house", "", "| PN | Part | Quantity |", "|---|---|---|"]
        out += [f"| {r['pn']} | {r['description']} | {r['needed']} |" for r in made]
    if warnings:
        out += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    out += ["", "## Check before sending", "",
            "- [ ] Number of units is right.",
            "- [ ] Stock counted, and stock of an exact part is that exact part.",
            "- [ ] Each link opens the right part, in stock.",
            "- [ ] Quantities and packs are right; nothing ordered twice.", ""]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))


def main(argv):
    pos, opts, cart = parse_args(argv)
    if len(pos) != 3:
        print(__doc__)
        return 1
    bom_path, top, units = pos[0], pos[1], int(pos[2])
    repo = opts["repo"] or os.path.dirname(os.path.dirname(os.path.abspath(bom_path)))
    parts = parts_by_pn(load_parts() + load_product_parts(repo))
    bom = defaultdict(list)
    for parent, lines in read_bom(bom_path).items():
        bom[parent].extend(lines)
    bom_line = {ln["pn"]: ln for lines in bom.values() for ln in lines}  # for exact_part

    need, made = defaultdict(float), defaultdict(float)
    top_part = parts.get(top)
    if top_part and top_part.get("supplier"):
        need[top] = units
    else:
        expand(bom, parts, top, units, need, made)

    stock = {}
    if opts["stock"]:
        stock = {r["pn"]: float(r["qty_on_hand"] or 0) for r in read_csv(opts["stock"])}

    by_supplier = defaultdict(list)
    plan = []
    warnings = []
    today = date.today()
    for pn in sorted(need):
        p = parts[pn]
        on_hand = stock.get(pn, 0)
        pieces = max(0, math.ceil(need[pn] - on_hand))
        pack = int(p.get("pack_qty") or 1)
        skipped = p.get("class", "").upper() in opts["skip"]
        source = "skipped (class)" if skipped else ("order" if pieces and not on_hand else
                                                    "stock" if not pieces else "stock + order")
        plan.append({"pn": pn, "description": p.get("description", ""), "needed": f"{need[pn]:g}",
                     "on_hand": f"{on_hand:g}", "to_order": pieces if not skipped else 0,
                     "packs": math.ceil(pieces / pack) if pieces and not skipped else 0,
                     "supplier": p.get("supplier", ""), "source": source})
        if skipped or pieces <= 0:
            continue
        qty = math.ceil(pieces / pack)  # orderable items (packs)
        price = p.get("unit_price", "")
        if price:
            price = f"{float(price) * pack:.4f}".rstrip("0").rstrip(".")  # price per pack
        if not price:
            warnings.append(f"{pn}: no price")
        elif p.get("price_date"):
            age = (today - date.fromisoformat(p["price_date"])).days
            if age > STALE_DAYS:
                warnings.append(f"{pn}: price is {age} days old ({p['price_date']})")
        supplier = p["supplier"]
        by_supplier[supplier].append({
            "_pn": pn, "_currency": p.get("currency", "") or "CAD",
            "Item Name": p.get("description", "") + (f", pack of {pack}" if pack > 1 else ""),
            "Prod No": p.get("supplier_pn") or p.get("mpn", ""),
            "# of Items": qty,
            "Price (Before Tax - Original Currency)": price,
            "Item Link": cart.get(supplier) or p.get("link", ""),
        })

    for pn in sorted(made):
        plan.append({"pn": pn, "description": parts[pn].get("description", ""), "needed": f"{made[pn]:g}",
                     "on_hand": "", "to_order": 0, "packs": 0, "supplier": "", "source": "made in house"})
    cols = ["pn", "description", "needed", "on_hand", "to_order", "packs", "supplier", "source"]
    print(f"Parts plan: {top} x {units}")
    print(f"  {'pn':<11}{'needed':>7}{'on hand':>9}{'order':>7}{'packs':>7}  source / supplier")
    for r in plan:
        print(f"  {r['pn']:<11}{r['needed']:>7}{r['on_hand']:>9}{r['to_order']:>7}{r['packs']:>7}  "
              f"{r['source']}{' / ' + r['supplier'] if r['to_order'] else ''}")
    if opts["plan"]:
        os.makedirs(os.path.dirname(os.path.abspath(opts["plan"])), exist_ok=True)
        with open(opts["plan"], "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(plan)
        print(f"wrote {opts['plan']}")

    os.makedirs(opts["out"], exist_ok=True)
    files = {}
    for supplier, rows in sorted(by_supplier.items()):
        slug = re.sub(r"[^A-Za-z0-9]+", "-", supplier).strip("-").lower()
        out = os.path.join(opts["out"], f"{slug}-{today.isoformat()}.csv")
        files[supplier] = out
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {out} ({len(rows)} lines)")
    if opts["sheet"]:
        write_sheet(opts["sheet"], top, units, opts["build"], bom_path, by_supplier, files, plan,
                    bom_line, warnings, today)
        print(f"wrote {opts['sheet']}")
    for pn in sorted(made):
        print(f"made in-house, not ordered: {pn} x{made[pn]:g} ({parts[pn].get('make')})")
    for w in warnings:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
