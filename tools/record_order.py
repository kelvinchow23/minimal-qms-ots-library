"""Record a placed order in a product repo's purchases.csv (minimalQMS SOP-005).

Usage:
    python tools/record_order.py REQUISITION.csv SUPPLIER ORDER_REF PRODUCT_REPO [--date YYYY-MM-DD]

REQUISITION.csv is a file produced by requisition.py (and uploaded to the purchasing
system). Each row is mapped back to its internal PN through the library's parts/CCC.csv files and
the product's 03_release/parts.csv (supplier_pn, then mpn). Rows are appended to PRODUCT_REPO/purchasing/purchases.csv with new P-nnnn line IDs,
and the requisition file is copied to PRODUCT_REPO/purchasing/requisitions/ORDER_REF.csv.
The order date defaults to today; use the actual order date, never a backdated one.
"""
import os
import re
import shutil
import sys
from datetime import date

from lib import load_parts, load_product_parts, read_csv, write_csv

PURCHASE_FIELDS = ["line_id", "pn", "description", "qty", "supplier", "link", "order_ref",
                   "order_date", "received_date", "received_qty", "lot", "inspection", "notes"]


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    order_date = date.today().isoformat()
    if "--date" in argv:
        order_date = argv[argv.index("--date") + 1]
        args.remove(order_date)
    if len(args) != 4:
        print(__doc__)
        return 1
    req_path, supplier, order_ref, repo = args
    parts = load_parts() + load_product_parts(repo)
    lookup = {}
    for p in parts:
        if p.get("supplier") == supplier:
            for key in (p.get("supplier_pn"), p.get("mpn")):
                if key:
                    lookup.setdefault(key, p)

    purch_dir = os.path.join(repo, "purchasing")
    purch_path = os.path.join(purch_dir, "purchases.csv")
    existing = read_csv(purch_path) if os.path.exists(purch_path) else []
    if any(r.get("order_ref") == order_ref for r in existing):
        print(f"error: order {order_ref} is already recorded in {purch_path}")
        return 1
    nums = [int(m.group(1)) for r in existing if (m := re.match(r"P-(\d+)", r.get("line_id", "")))]
    nxt = max(nums, default=0) + 1

    new = []
    for row in read_csv(req_path):
        prod_no = row["Prod No"].strip()
        p = lookup.get(prod_no)
        if p is None:
            print(f"error: Prod No {prod_no} ({row['Item Name']}) has no {supplier} entry in the library or the product")
            return 1
        new.append({
            "line_id": f"P-{nxt:04d}", "pn": p["pn"], "description": p["description"],
            "qty": row["# of Items"], "supplier": supplier, "link": row["Item Link"],
            "order_ref": order_ref, "order_date": order_date, "inspection": "",
        })
        nxt += 1

    os.makedirs(os.path.join(purch_dir, "requisitions"), exist_ok=True)
    write_csv(purch_path, existing + new, PURCHASE_FIELDS)
    safe_ref = re.sub(r"[^A-Za-z0-9._-]+", "_", order_ref)
    shutil.copyfile(req_path, os.path.join(purch_dir, "requisitions", f"{safe_ref}.csv"))
    print(f"recorded {len(new)} lines ({new[0]['line_id']} to {new[-1]['line_id']}) for {order_ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
