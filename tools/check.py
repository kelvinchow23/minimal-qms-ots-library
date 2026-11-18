"""Check parts.csv against the library rules. Exit code 1 on any error. Used by CI.

Usage: python tools/check.py
"""
import sys
from datetime import date

from lib import FIELDS, PARTS, PN_RE, categories, read_csv

with open(PARTS, encoding="utf-8-sig") as f:
    header = f.readline().strip().split(",")


def main():
    errors = []
    if header != FIELDS:
        errors.append(f"parts.csv header must be: {','.join(FIELDS)}")
    cats = categories()
    seen = set()
    for i, r in enumerate(read_csv(PARTS), start=2):
        pn = r.get("pn", "")
        where = f"line {i} ({pn or 'no pn'})"
        m = PN_RE.match(pn)
        if not m:
            errors.append(f"{where}: part number must be CCC-NNNN or CCC-A-NNNN")
        elif m.group("cat") not in cats:
            errors.append(f"{where}: unknown category {m.group('cat')}")
        if pn in seen:
            errors.append(f"{where}: duplicate part number")
        seen.add(pn)
        if not r.get("description"):
            errors.append(f"{where}: description is required")
        if r.get("class") not in ("A", "B", "C", ""):
            errors.append(f"{where}: class must be A, B or C")
        if r.get("make_buy") not in ("make", "buy"):
            errors.append(f"{where}: make_buy must be make or buy")
        if r.get("lifecycle") not in ("draft", "released", "obsolete"):
            errors.append(f"{where}: lifecycle must be draft, released or obsolete")
        if r.get("make_buy") == "buy" and r.get("lifecycle") == "released":
            for k in ("class", "supplier", "link"):
                if not r.get(k):
                    errors.append(f"{where}: released purchased part needs {k}")
            if not (r.get("supplier_pn") or r.get("mpn")):
                errors.append(f"{where}: released purchased part needs supplier_pn or mpn")
        if r.get("make_buy") == "make" and not r.get("owner_repo"):
            errors.append(f"{where}: made part needs owner_repo")
        if r.get("unit_price"):
            try:
                float(r["unit_price"])
            except ValueError:
                errors.append(f"{where}: unit_price must be a number")
            if not r.get("currency"):
                errors.append(f"{where}: unit_price needs currency")
            if not r.get("price_date"):
                errors.append(f"{where}: unit_price needs price_date")
        if r.get("price_date"):
            try:
                if date.fromisoformat(r["price_date"]) > date.today():
                    errors.append(f"{where}: price_date is in the future")
            except ValueError:
                errors.append(f"{where}: price_date must be YYYY-MM-DD")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(seen)} parts checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
