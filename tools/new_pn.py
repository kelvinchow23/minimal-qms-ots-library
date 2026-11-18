"""Allocate the next free part number and add it to parts.csv.

Usage:
    python tools/new_pn.py CCC "description" [--assembly] [field=value ...]

Examples:
    python tools/new_pn.py RES "10k 0603 1% resistor" make_buy=buy class=B \
        manufacturer=Yageo mpn=RC0603FR-0710KL supplier=Mouser supplier_pn=603-RC0603FR-0710KL \
        link=https://www.mouser.com/... unit_price=0.10 currency=CAD
    python tools/new_pn.py PCB "Photoreactor LED driver board" --assembly make_buy=buy \
        owner_repo=kelvinchow23/photo-reactor

Numbers are shared between parts and assemblies in a category: PCB-0001 and PCB-A-0001
are the bare and assembled versions of the same board. --same-as PCB-0001 reuses that
number for the assembly. Otherwise the next number not used by either form is issued.
The new row starts as lifecycle=draft. price_date defaults to today when a price is given.
"""
import sys
from datetime import date

from lib import FIELDS, PN_RE, categories, load_parts, write_csv, PARTS


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--") and "=" not in a]
    flags = [a for a in argv[1:] if a.startswith("--")]
    fields = dict(a.split("=", 1) for a in argv[1:] if "=" in a and not a.startswith("--"))
    if len(args) < 2:
        print(__doc__)
        return 1
    cat, description = args[0].upper(), args[1]
    if cat not in categories():
        print(f"error: unknown category {cat}; add it to categories.csv first")
        return 1
    assembly = "--assembly" in flags
    same_as = next((f.split("=", 1)[1] for f in flags if f.startswith("--same-as=")), None)

    rows = load_parts()
    used = {(m.group("cat"), m.group("num")) for m in (PN_RE.match(r["pn"]) for r in rows) if m}
    existing = {r["pn"] for r in rows}

    if same_as:
        m = PN_RE.match(same_as)
        if not m or m.group("cat") != cat:
            print(f"error: --same-as {same_as} is not a {cat} part number")
            return 1
        num = m.group("num")
    else:
        taken = sorted(int(n) for c, n in used if c == cat)
        num = f"{(taken[-1] + 1) if taken else 1:04d}"
    pn = f"{cat}-A-{num}" if assembly else f"{cat}-{num}"
    if pn in existing:
        print(f"error: {pn} already exists")
        return 1

    row = {k: "" for k in FIELDS}
    row.update(pn=pn, description=description, lifecycle="draft",
               **{"class": categories()[cat]["typical_class"] if categories()[cat]["typical_class"] != "-" else ""})
    unknown = set(fields) - set(FIELDS)
    if unknown:
        print(f"error: unknown fields {sorted(unknown)}")
        return 1
    row.update(fields)
    if row["unit_price"] and not row["price_date"]:
        row["price_date"] = date.today().isoformat()
    rows.append(row)
    write_csv(PARTS, rows, FIELDS)
    print(pn)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
