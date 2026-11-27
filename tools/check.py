"""Check the library, and optionally a product repo's custom parts. Exit code 1 on errors.

Usage:
    python tools/check.py                      # library: parts/*.csv, categories.csv, projects.csv
    python tools/check.py --repo PRODUCT_REPO  # also the product's custom parts (BOM sources,
                                               # or 03_build_package/parts.csv in older repos)
"""
import os
import re
import sys
from datetime import date

from lib import (CUSTOM_FIELDS, FIELDS, PARTS_DIR, PN_RE, ROOT, categories, load_product_parts,
                 prefix_files, product_parts_path, projects, read_csv)

LIFECYCLE = ("draft", "released", "obsolete")
# fastener prefixes whose descriptions follow "Type, size, [style, ]material"
FASTENER_PREFIXES = {"HWB", "HWN", "HWW", "HWS"}
THREAD_RE = re.compile(r"(M\d+(\.\d+)?|#\d+-\d+|\d+/\d+\"?-\d+)( x \d+(\.\d+)? mm)?")
MATERIAL_RE = re.compile(r"stainless|steel|brass|nylon|alumin|zinc|titanium|peek|plastic|copper", re.I)
NOTES_MAX = 120
NOTE_PRICE_RE = re.compile(r"[$€£]\s*\d|\b\d+(\.\d+)?\s*(USD|CAD|EUR)\b|\b(USD|CAD|US\$)\s*\d")
NOTE_DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


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


def check_text(r, code, where, errors):
    """One value per column: the description follows the pattern, notes hold only extras."""
    d, n = r.get("description", ""), r.get("notes", "")
    if "\n" in d or "\n" in n:
        errors.append(f"{where}: description and notes are one line")
    if code in FASTENER_PREFIXES and d:
        segs = d.split(", ")
        if len(segs) < 3 or not THREAD_RE.fullmatch(segs[1]) or not MATERIAL_RE.search(segs[-1]):
            errors.append(f"{where}: fastener description must be 'Type, size, [style, ]material', "
                          f"e.g. 'Screw, M3 x 6 mm, button head hex drive, 18-8 stainless'")
        elif code == "HWB" and " x " not in segs[1]:
            errors.append(f"{where}: screw size needs a length, e.g. 'M3 x 6 mm'")
    if len(n) > NOTES_MAX:
        errors.append(f"{where}: notes are {len(n)} characters; keep them under {NOTES_MAX} "
                      "(only what a buyer needs that has no column)")
    if NOTE_PRICE_RE.search(n) or NOTE_DATE_RE.search(n):
        errors.append(f"{where}: notes must not hold prices or dates; they have their own columns")


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
    seen, all_rows = set(), []
    for name in prefix_files():
        code = name[:-4]
        path = os.path.join(PARTS_DIR, name)
        if code not in cats:
            errors.append(f"parts/{name}: {code} is not a prefix in categories.csv")
        if header(path) != FIELDS:
            errors.append(f"parts/{name}: header must be: {','.join(FIELDS)}")
        for i, r in enumerate(read_csv(path), start=2):
            all_rows.append(r)
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
                if not (r.get("supplier_pn") or r.get("manufacturer_pn")):
                    errors.append(f"{where}: released part needs supplier_pn or manufacturer_pn")
            pq = r.get("pack_qty", "")
            if not (pq.isdigit() and int(pq) >= 1):
                errors.append(f"{where}: pack_qty must be a whole number, 1 or more")
            if r.get("supplier", "").strip().lower() == "mcmaster-carr" and (
                    r.get("manufacturer") or r.get("manufacturer_pn")):
                errors.append(f"{where}: McMaster-Carr parts leave manufacturer and manufacturer_pn blank")
            check_text(r, code, where, errors)
            check_price(r, where, errors)
    check_rates({r.get("currency") for r in all_rows if r.get("unit_price")}, errors)
    return len(seen)


def check_rates(used, errors):
    """rates.csv: currency, cad_per_unit, rate_date; every currency with a price needs a rate."""
    path = os.path.join(ROOT, "rates.csv")
    if not os.path.exists(path):
        errors.append("rates.csv is missing")
        return
    if header(path)[:3] != ["currency", "cad_per_unit", "rate_date"]:
        errors.append("rates.csv: header must start currency,cad_per_unit,rate_date")
    have = set()
    for i, r in enumerate(read_csv(path), start=2):
        cur = r.get("currency", "")
        have.add(cur)
        try:
            if float(r.get("cad_per_unit", "")) <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"rates.csv line {i} ({cur}): cad_per_unit must be a positive number")
        if cur != "CAD":
            try:
                if date.fromisoformat(r.get("rate_date", "")) > date.today():
                    errors.append(f"rates.csv line {i} ({cur}): rate_date is in the future")
            except ValueError:
                errors.append(f"rates.csv line {i} ({cur}): rate_date must be YYYY-MM-DD")
    for cur in sorted(used - have - {None, ""}):
        errors.append(f"rates.csv: no rate for {cur}, which parts are priced in")


def check_product(repo, errors):
    path = product_parts_path(repo)
    legacy = os.path.exists(path)  # older repos keep a parts.csv; newer ones use the BOM sources
    rows = load_product_parts(repo)
    if not rows:
        return 0
    if legacy and header(path) != CUSTOM_FIELDS:
        errors.append(f"{path} header must be: {','.join(CUSTOM_FIELDS)}")
    if not legacy:
        path = "BOM sources"
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
        for k in ("description", "rev") if legacy or not PN_RE.match(pn) or not PN_RE.match(pn).group("asm") else ("description",):
            if not r.get(k):
                errors.append(f"{where}: {k} is required")
        if r.get("class") not in ("A", "B", "C"):
            errors.append(f"{where}: class must be A, B or C")
        if legacy and r.get("lifecycle") not in LIFECYCLE:
            errors.append(f"{where}: lifecycle must be draft, released or obsolete")
        if legacy and r.get("lifecycle") == "released" and not r.get("source"):
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
