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
PRODUCT_PARTS = os.path.join("03_build_package", "parts.csv")

PN_RE = re.compile(r"^(?P<code>[A-Z]{3})-(?P<asm>A-)?(?P<num>\d{4})$")

# OTS parts in this library (same columns in every parts/CCC.csv)
FIELDS = [
    "pn", "description", "class", "manufacturer", "manufacturer_pn", "supplier", "supplier_pn",
    "link", "unit_price", "pack_qty", "currency", "price_date", "lifecycle", "notes",
]
# unit_price is per piece; pack_qty is how many pieces one orderable item holds (1 if sold
# singly). The price of one orderable item is unit_price x pack_qty.
# Custom parts and assemblies in a product repo; the purchasing columns match FIELDS
# (no pack_qty: a custom part is ordered one piece per item)
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


def product_bom_paths(repo):
    """BOM sources of a product repo (minimalQMS build documents): 02_design/<folder>/bom.csv."""
    base = os.path.join(repo, "02_design")
    if not os.path.isdir(base):
        return []
    return sorted(os.path.join(base, d, "bom.csv") for d in os.listdir(base)
                  if os.path.exists(os.path.join(base, d, "bom.csv")))


def bom_assembly(path):
    """The assembly a BOM source belongs to: 'assembly' in the steps.json beside it."""
    steps = os.path.join(os.path.dirname(path), "steps.json")
    if os.path.exists(steps):
        import json
        return json.load(open(steps, encoding="utf-8")).get("assembly", "")
    return ""


def read_bom(path):
    """{assembly PN: [lines]} from a BOM. Reads the old master BOM (parent_pn column) and the
    per-assembly BOM (no parent_pn; PN column 'pn' or 'internal_pn'); each line gets 'pn'."""
    out = {}
    for line in read_csv(path):
        line = dict(line, pn=line.get("pn") or line.get("internal_pn", ""))
        parent = line.get("parent_pn") or bom_assembly(path)
        out.setdefault(parent, []).append(line)
    return out


def load_product_parts(repo):
    """Custom parts and assemblies of a product repo, or [] if it has none yet. From
    03_build_package/parts.csv when a repo still has one, else from its BOM sources: each
    assembly, and every custom line (category 'Custom ...')."""
    path = product_parts_path(repo)
    if os.path.exists(path):
        return read_csv(path)
    rows = {}
    for bom_path in product_bom_paths(repo):
        for asm, lines in read_bom(bom_path).items():
            if asm:
                rows.setdefault(asm, {"pn": asm, "rev": "", "description": "assembly", "class": "A", "make": "assemble"})
            for ln in lines:
                if ln.get("category", "").startswith("Custom"):
                    rows.setdefault(ln["pn"], {"pn": ln["pn"], "rev": ln.get("rev", ""), "description": ln.get("description", ""),
                                               "class": ln.get("class", "A"), "make": ln.get("make") or "custom",
                                               "notes": ln.get("notes", "")})
    return list(rows.values())


def categories(path=CATEGORIES):
    return {r["code"]: r for r in read_csv(path)}


def projects(path=PROJECTS):
    return {r["code"]: r for r in read_csv(path)}
