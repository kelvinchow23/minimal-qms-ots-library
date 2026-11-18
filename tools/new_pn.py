"""Allocate the next free part number.

OTS part (written to this library's parts.csv):
    python tools/new_pn.py CCC "description" [field=value ...]

Custom part or assembly (written to the product repo's 03_release/parts.csv):
    python tools/new_pn.py PPP "description" --repo PATH [--assembly] [field=value ...]

CCC is a category code (categories.csv). PPP is a project code (projects.csv).
Custom parts are numbered PPP-NNNN and assemblies PPP-A-NNNN; parts and assemblies share
one number sequence per project, so PRX-0003 and PRX-A-0003 never mean different things.

Examples:
    python tools/new_pn.py FST "M3x8 SHCS, stainless, pack of 100" class=B \\
        manufacturer=McMaster-Carr mpn=91292A112 supplier=McMaster-Carr \\
        supplier_pn=91292A112 link=https://www.mcmaster.com/91292A112/ unit_price=9.85 currency=USD
    python tools/new_pn.py PRX "Housing lid" --repo ../photo-reactor make=print \\
        "source=Fusion: Photoreactor/Housing lid v12"
    python tools/new_pn.py PRX "LED driver board, assembled" --repo ../photo-reactor --assembly \\
        make=fab supplier=JLCPCB link=https://jlcpcb.com

New rows start as lifecycle=draft (custom parts also rev=A). price_date defaults to today
when a price is given.
"""
import sys
from datetime import date

from lib import (CUSTOM_FIELDS, FIELDS, PARTS, PN_RE, categories, load_parts,
                 load_product_parts, product_parts_path, projects, write_csv)


def next_number(rows, code):
    taken = [int(m.group("num")) for m in (PN_RE.match(r["pn"]) for r in rows)
             if m and m.group("code") == code]
    return max(taken, default=0) + 1


def main(argv):
    args, fields, repo, assembly = [], {}, None, False
    it = iter(argv[1:])
    for a in it:
        if a == "--repo":
            repo = next(it)
        elif a == "--assembly":
            assembly = True
        elif "=" in a and not a.startswith("--"):
            k, v = a.split("=", 1)
            fields[k] = v
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__)
        return 1
    code, description = args[0].upper(), args[1]
    cats, projs = categories(), projects()

    if code in cats:
        if repo or assembly:
            print("error: OTS parts are single items in this library; --repo/--assembly are for custom parts")
            return 1
        path, cols, rows = PARTS, FIELDS, load_parts()
        pn = f"{code}-{next_number(rows, code):04d}"
        row = {"class": cats[code]["typical_class"]}
    elif code in projs:
        if not repo:
            print("error: custom parts need --repo (the product repo that owns them)")
            return 1
        path, cols, rows = product_parts_path(repo), CUSTOM_FIELDS, load_product_parts(repo)
        num = next_number(rows, code)
        pn = f"{code}-A-{num:04d}" if assembly else f"{code}-{num:04d}"
        row = {"rev": "A", "class": "A"}
    else:
        print(f"error: {code} is neither a category (categories.csv) nor a project (projects.csv)")
        return 1

    unknown = set(fields) - set(cols)
    if unknown:
        print(f"error: unknown fields {sorted(unknown)}; allowed: {', '.join(cols)}")
        return 1
    row.update(pn=pn, description=description, lifecycle="draft")
    row.update(fields)
    if row.get("unit_price") and not row.get("price_date"):
        row["price_date"] = date.today().isoformat()
    write_csv(path, rows + [row], cols)
    print(pn)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
