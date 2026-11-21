"""Generate purchasing-upload CSVs (one per supplier) from a product BOM.

Usage:
    python tools/requisition.py BOM.csv TOP_PN QTY [--repo PRODUCT_REPO] [--out DIR]
                                [--stock STOCK.csv] [--cart-link SUPPLIER=URL ...] [--skip-class C]

BOM.csv is a product repo's bom.csv (parent_pn, parent_rev, pn, qty, ...). Parts are looked
up in this library (OTS, parts/CCC.csv) and in the product repo's 03_build_package/parts.csv (custom). The
product repo defaults to the folder above the BOM's folder. The BOM is expanded from TOP_PN,
multiplying quantities through sub-assemblies:
  - a PN with a supplier is ordered as one item (even if it has a BOM, e.g. a PCB ordered
    already assembled);
  - a PN without a supplier that is a parent in the BOM is expanded;
  - a custom part with a make method and no supplier (e.g. printed in-house) is listed
    as made in-house and not ordered;
  - anything else is an error.

STOCK.csv (optional) has columns pn, qty_on_hand; stock is subtracted.
--cart-link SUPPLIER=URL puts one cart link on every row for that supplier.

Output: DIR/<supplier>-<YYYY-MM-DD>.csv with exactly the purchasing template's columns:
  Item Name, Prod No, # of Items, Price (Before Tax - Original Currency), Item Link
Prod No is the supplier part number, or the MPN if none. Price is the unit price from
parts.csv; price_date is not included. A warning is printed for missing prices and
prices older than 90 days.
"""
import csv
import math
import os
import re
import sys
from collections import defaultdict
from datetime import date

from lib import load_parts, load_product_parts, parts_by_pn, read_csv

HEADER = ["Item Name", "Prod No", "# of Items", "Price (Before Tax - Original Currency)", "Item Link"]
STALE_DAYS = 90


def parse_args(argv):
    pos, opts, cart = [], {"out": ".", "stock": None, "skip": set(), "repo": None}, {}
    it = iter(argv[1:])
    for a in it:
        if a == "--out":
            opts["out"] = next(it)
        elif a == "--repo":
            opts["repo"] = next(it)
        elif a == "--stock":
            opts["stock"] = next(it)
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


def main(argv):
    pos, opts, cart = parse_args(argv)
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

    stock = {}
    if opts["stock"]:
        stock = {r["pn"]: float(r["qty_on_hand"] or 0) for r in read_csv(opts["stock"])}

    by_supplier = defaultdict(list)
    warnings = []
    today = date.today()
    for pn in sorted(need):
        p = parts[pn]
        if p.get("class", "").upper() in opts["skip"]:
            continue
        qty = math.ceil(need[pn] - stock.get(pn, 0))
        if qty <= 0:
            continue
        price = p.get("unit_price", "")
        if not price:
            warnings.append(f"{pn}: no price")
        elif p.get("price_date"):
            age = (today - date.fromisoformat(p["price_date"])).days
            if age > STALE_DAYS:
                warnings.append(f"{pn}: price is {age} days old ({p['price_date']})")
        supplier = p["supplier"]
        by_supplier[supplier].append({
            "Item Name": p.get("description", ""),
            "Prod No": p.get("supplier_pn") or p.get("mpn", ""),
            "# of Items": qty,
            "Price (Before Tax - Original Currency)": price,
            "Item Link": cart.get(supplier) or p.get("link", ""),
        })

    os.makedirs(opts["out"], exist_ok=True)
    for supplier, rows in sorted(by_supplier.items()):
        slug = re.sub(r"[^A-Za-z0-9]+", "-", supplier).strip("-").lower()
        out = os.path.join(opts["out"], f"{slug}-{today.isoformat()}.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {out} ({len(rows)} lines)")
    for pn in sorted(made):
        print(f"made in-house, not ordered: {pn} x{made[pn]:g} ({parts[pn].get('make')})")
    for w in warnings:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
