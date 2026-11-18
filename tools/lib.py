"""Shared helpers for minimal-qms-ots-library tools. Standard library only.

Part numbers (minimalQMS SOP-002):
  OTS part         CCC-NNNN     CCC = prefix code (categories.csv)    kept in parts/CCC.csv
  Custom part      PPP-NNNN     PPP = project code (projects.csv)     kept in the product repo
  Custom assembly  PPP-A-NNNN                                         kept in the product repo
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS_DIR = os.path.join(ROOT, "parts")
CATEGORIES = os.path.join(ROOT, "categories.csv")
PROJECTS = os.path.join(ROOT, "projects.csv")
PRODUCT_PARTS = os.path.join("03_release", "parts.csv")

PN_RE = re.compile(r"^(?P<code>[A-Z]{3})-(?P<asm>A-)?(?P<num>\d{4})$")

# OTS parts in this library (same columns in every parts/CCC.csv)
FIELDS = [
    "pn", "description", "class", "manufacturer", "mpn", "supplier", "supplier_pn",
    "link", "unit_price", "currency", "price_date", "lifecycle", "notes",
]
# Custom parts and assemblies in a product repo; the purchasing columns match FIELDS
CUSTOM_FIELDS = [
    "pn", "rev", "description", "class", "lifecycle", "make", "source", "drawing",
    "supplier", "supplier_pn", "link", "unit_price", "currency", "price_date", "notes",
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def prefix_path(code):
    return os.path.join(PARTS_DIR, f"{code}.csv")


def load_prefix(code):
    path = prefix_path(code)
    return read_csv(path) if os.path.exists(path) else []


def prefix_files():
    return sorted(n for n in os.listdir(PARTS_DIR) if n.endswith(".csv"))


def load_parts():
    """All OTS parts, from every parts/CCC.csv."""
    rows = []
    for name in prefix_files():
        rows.extend(read_csv(os.path.join(PARTS_DIR, name)))
    return rows


def parts_by_pn(rows):
    return {r["pn"]: r for r in rows}


def product_parts_path(repo):
    return os.path.join(repo, PRODUCT_PARTS)


def load_product_parts(repo):
    """Custom parts of a product repo, or [] if it has none yet."""
    path = product_parts_path(repo)
    return read_csv(path) if os.path.exists(path) else []


def categories(path=CATEGORIES):
    return {r["code"]: r for r in read_csv(path)}


def projects(path=PROJECTS):
    return {r["code"]: r for r in read_csv(path)}
