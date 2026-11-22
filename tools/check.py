"""Check the library, and optionally a product repo's custom parts. Exit code 1 on errors.

Usage:
    python tools/check.py                      # library: parts/*.csv, categories.csv, projects.csv
    python tools/check.py --repo PRODUCT_REPO  # also the product's 03_build_package/parts.csv
"""
import os
import sys
from datetime import date

from lib import (CUSTOM_FIELDS, FIELDS, PARTS_DIR, PN_RE, categories, load_product_parts,
                 prefix_files, product_parts_path, projects, read_csv)

LIFECYCLE = ("draft", "released", "obsolete")


def header(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.readline().strip().split(",")


def check_price(r, where, errors):
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


def check_library(errors):
    cats, projs = categories(), projects()
    families = {c.get("family", "") for c in cats.values()} - {""}
    clash = set(cats) & set(projs)
    if clash:
        errors.append(f"codes used as both prefix and project: {sorted(clash)}")
    for code in projs:
        if code[:2] in families:
            errors.append(f"project code {code} starts with a part family ({code[:2]})")
    for code in list(cats) + list(projs):
        if not (len(code) == 3 and code.isalpha() and code.isupper()):
            errors.append(f"code {code!r} must be 3 capital letters")
    seen = set()
    for name in prefix_files():
        code = name[:-4]
        path = os.path.join(PARTS_DIR, name)
        if code not in cats:
            errors.append(f"parts/{name}: {code} is not a prefix in categories.csv")
        if header(path) != FIELDS:
            errors.append(f"parts/{name}: header must be: {','.join(FIELDS)}")
        for i, r in enumerate(read_csv(path), start=2):
            pn = r.get("pn", "")
            where = f"parts/{name} line {i} ({pn or 'no pn'})"
            m = PN_RE.match(pn)
            if not m or m.group("asm"):
                errors.append(f"{where}: OTS part numbers are CCC-NNNN")
            elif m.group("code") != code:
                errors.append(f"{where}: belongs in parts/{m.group('code')}.csv")
            if pn in seen:
                errors.append(f"{where}: duplicate part number")
            seen.add(pn)
            if not r.get("description"):
                errors.append(f"{where}: description is required")
            if r.get("class") not in ("A", "B", "C"):
                errors.append(f"{where}: class must be A, B or C")
            if r.get("lifecycle") not in LIFECYCLE:
                errors.append(f"{where}: lifecycle must be draft, released or obsolete")
            if r.get("lifecycle") == "released":
                for k in ("supplier", "link"):
                    if not r.get(k):
                        errors.append(f"{where}: released part needs {k}")
                if not (r.get("supplier_pn") or r.get("mpn")):
                    errors.append(f"{where}: released part needs supplier_pn or mpn")
            check_price(r, where, errors)
    return len(seen)


def check_product(repo, errors):
    path = product_parts_path(repo)
    rows = load_product_parts(repo)
    if not rows:
        return 0
    if header(path) != CUSTOM_FIELDS:
        errors.append(f"{path} header must be: {','.join(CUSTOM_FIELDS)}")
    projs, seen = projects(), set()
    for i, r in enumerate(rows, start=2):
        pn = r.get("pn", "")
        where = f"{path} line {i} ({pn or 'no pn'})"
        m = PN_RE.match(pn)
        if not m:
            errors.append(f"{where}: custom part numbers are PPP-NNNN or PPP-A-NNNN")
        elif m.group("code") not in projs:
            errors.append(f"{where}: {m.group('code')} is not a project code in projects.csv")
        if pn in seen:
            errors.append(f"{where}: duplicate part number")
        seen.add(pn)
        for k in ("description", "rev"):
            if not r.get(k):
                errors.append(f"{where}: {k} is required")
        if r.get("class") not in ("A", "B", "C"):
            errors.append(f"{where}: class must be A, B or C")
        if r.get("lifecycle") not in LIFECYCLE:
            errors.append(f"{where}: lifecycle must be draft, released or obsolete")
        if r.get("lifecycle") == "released" and not r.get("source"):
            errors.append(f"{where}: released custom part needs source (CAD reference)")
        check_price(r, where, errors)
    return len(seen)


def main(argv):
    errors = []
    n = check_library(errors)
    msg = f"{n} library parts"
    if "--repo" in argv:
        repo = argv[argv.index("--repo") + 1]
        msg += f", {check_product(repo, errors)} custom parts in {repo}"
    for e in errors:
        print(f"error: {e}")
    print(f"{msg} checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
