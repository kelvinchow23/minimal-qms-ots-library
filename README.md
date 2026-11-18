# parts-library

Off-the-shelf (OTS) parts and the naming registers for
[minimalQMS](https://github.com/kelvinchow23/minimal-qms) product repos.

- **OTS parts only:** manufacturer, MPN, supplier, vendor number, link, and the last known
  price with its date. Custom parts and assemblies live in the product repo that owns them.
- **Naming registers:** OTS category codes (`categories.csv`) and project codes
  (`projects.csv`).
- **Purchasing upload files generated from a product BOM,** in the purchasing system's
  CSV format, covering both OTS parts and custom parts bought from fabricators.
- **Orders recorded back** into the product repo's `purchases.csv` (minimalQMS SOP-005).

## Part numbers (minimalQMS SOP-002)

| Type | Format | Lives in | Example |
|---|---|---|---|
| OTS part | `CCC-NNNN` (category) | this library | `FST-0001` M3x8 screws |
| Custom part | `PPP-NNNN` (project) | product repo `03_release/parts.csv` | `PRX-0004` housing lid |
| Custom assembly | `PPP-A-NNNN` (project) | product repo `03_release/parts.csv` | `PRX-A-0003` assembled PCB |

Custom parts and assemblies share one number sequence per project. Category and project
codes are 3 capital letters and never overlap.

## parts.csv (OTS)

`pn, description, class, manufacturer, mpn, supplier, supplier_pn, link, unit_price,
currency, price_date, lifecycle, notes`

## Product repo parts.csv (custom)

`pn, rev, description, class, lifecycle, make, source, drawing, supplier, supplier_pn,
link, unit_price, currency, price_date, notes`

- `make`: `print`, `machine`, `fab` (made by an outside fabricator), `assemble`, …
- `source`: where the design lives, e.g. `Fusion: Housing lid v12` or a KiCad path.
- The purchasing columns match the OTS file, so custom parts bought from a fabricator
  (e.g. a PCB) appear on the same upload files.

When generating an order, anything with a `supplier` is ordered as one item, even if it
has its own BOM (e.g. a PCB ordered already assembled). Assemblies without a supplier are
expanded; custom parts made in-house are listed but not ordered.

## Tools

Standard-library Python. Run from the repo root.

```bash
# OTS part (prints the new PN)
python tools/new_pn.py OPT "365 nm UV LED, 3535" class=A \
    manufacturer=Lumileds mpn=L1F3-U365200014000 supplier=Mouser \
    supplier_pn=997-L1F3U36520001400 link=https://www.mouser.com/... unit_price=4.12 currency=CAD

# custom part or assembly, written to the product repo's 03_release/parts.csv
python tools/new_pn.py PRX "Housing lid" --repo ../photo-reactor make=print "source=Fusion: Housing lid v12"
python tools/new_pn.py PRX "LED driver board, assembled" --repo ../photo-reactor --assembly \
    make=fab supplier=JLCPCB link=https://jlcpcb.com

# purchasing upload files for 3 units of a product (one CSV per supplier)
python tools/requisition.py ../photo-reactor/03_release/bom.csv PRX-A-0001 3 --out out/

# after ordering: record the order in the product repo
python tools/record_order.py out/mouser-2026-11-18.csv Mouser "PO 45012" ../photo-reactor

# check the library (also runs in CI), optionally a product's custom parts
python tools/check.py --repo ../photo-reactor
```

The upload files have exactly the purchasing template's columns: `Item Name`, `Prod No`,
`# of Items`, `Price (Before Tax - Original Currency)`, `Item Link`. `price_date` is not
included; the tool warns when a price is missing or older than 90 days.
`--cart-link SUPPLIER=URL` puts one cart link on every row for that supplier.
Quantities are rounded up to whole items, and `--stock stock.csv` subtracts stock on hand.

## License

MIT. OTS category codes adapted from [git-plm/parts](https://github.com/git-plm/parts) (see NOTICE).
