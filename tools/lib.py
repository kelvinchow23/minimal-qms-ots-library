"""Shared helpers for parts-library tools. Standard library only."""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, "parts.csv")
CATEGORIES = os.path.join(ROOT, "categories.csv")

PN_RE = re.compile(r"^(?P<cat>[A-Z]{3})-(?P<asm>A-)?(?P<num>\d{4})$")
FIELDS = [
    "pn", "description", "class", "make_buy", "owner_repo", "manufacturer", "mpn",
    "supplier", "supplier_pn", "link", "unit_price", "currency", "price_date",
    "lifecycle", "notes",
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def load_parts(path=PARTS):
    return read_csv(path)


def parts_by_pn(rows):
    return {r["pn"]: r for r in rows}


def categories(path=CATEGORIES):
    return {r["code"]: r for r in read_csv(path)}
