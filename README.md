# minimal-qms-ots-library

Off-the-shelf (OTS) parts and the naming registers for
[minimalQMS](https://github.com/kelvinchow23/minimal-qms) product repos.

**Browse and search:** https://kelvinchow23.github.io/minimal-qms-ots-library/ — one tab per prefix,
search across every field, flags prices older than 90 days. Fastener tabs split descriptions
into Type / Thread / Length / Material with filters, and prices show per piece and per pack. To add or change a part, use
**Request a part** on the site (a GitHub issue that an agent turns into a reviewed PR).

- **Off-the-shelf (OTS) parts only:** manufacturer, MPN, supplier, vendor number, link,
  pack size, and the last known price per piece with its date. Custom parts and assemblies live in the product repo that owns them.
- **Naming registers:** OTS prefix codes (`categories.csv`) and project codes
  (`projects.csv`).
- **Purchasing upload files generated from a product BOM,** in the purchasing system's
  CSV format, covering both OTS parts and custom parts bought from fabricators.
- **Orders recorded back** into the product repo's `purchases.csv` (minimalQMS SOP-005).

## Part numbers (minimalQMS SOP-002)

| Type | Format | Lives in | Example |
|---|---|---|---|
| OTS part | `CCC-NNNN` (prefix) | this library, `parts/CCC.csv` | `HWB-0001` M3x8 screws |
| Custom part | `PPP-NNNN` (project) | product repo `03_build_package/parts.csv` | `PRX-0004` housing lid |
| Custom assembly | `PPP-A-NNNN` (project) | product repo `03_build_package/parts.csv` | `PRX-A-0003` assembled PCB |

Custom parts and assemblies share one number sequence per project. Prefix and project
codes are 3 capital letters. Project codes never start with a part family (`EC`, `HW`),
so a number shows at a glance whether a part is off the shelf or custom.

## OTS prefixes

Prefixes are grouped in two families, `EC` electrical and `HW` hardware. The full list is
in `categories.csv`:

- **EC:** `ECJ` connectors (J for jack), `ECW` wire, `ECP` power, `ECS` safety devices,
  `ECM` modules and boards, `ECE` electronic components bought loose, `ECA` motors and
  actuators, `ECF` fans and thermal, `ECX` other electrical.
- **HW:** `HWB` screws and bolts, `HWN` nuts and inserts, `HWW` washers, `HWS` spacers and
  standoffs, `HWM` motion (bearings, belts, pulleys, shafts), `HWP` plumbing, `HWA`
  adhesives and sealants, `HWT` tape, `HWF` 3D-printer filament and resin, `HWX` other
  hardware (extrusion, brackets).

Boards and breakouts (a Raspberry Pi, a sensor board) are `ECM`. Chips and passives on a
custom PCB are not numbered here: the PCB is a custom assembly in the product repo, and
its KiCad BOM keeps their MPN and LCSC numbers. Use `ECE` only for components bought loose.

## parts/CCC.csv (OTS)

One file per prefix, like one tab per prefix in a workbook. Every file has the same columns:

`pn, description, class, manufacturer, mpn, supplier, supplier_pn, link, unit_price,
pack_qty, currency, price_date, lifecycle, notes`

- `unit_price` is the price of **one piece**; `pack_qty` is how many pieces you buy at once
  (`1` if sold singly). A pack of 100 screws for 6.98 USD is `unit_price=0.0698`,
  `pack_qty=100`. The pack price is not stored: it is always `unit_price × pack_qty`.
- `supplier_pn` is the supplier's own number. **McMaster-Carr parts leave `manufacturer` and
  `mpn` blank**: McMaster hides them, and `check.py` enforces this.
- Write fastener descriptions as `Type, size, style, material`, e.g.
  `Screw, M3 x 6 mm, button head hex drive, 18-8 stainless` or `Hex nut, M3, 18-8 stainless`.
  The site splits them into Type / Thread / Length / Material columns with filters.

## Product repo parts.csv (custom)

`pn, rev, description, class, lifecycle, make, source, drawing, supplier, supplier_pn,
link, unit_price, currency, price_date, notes`

- `make`: `print`, `machine`, `fab` (made by an outside fabricator), `assemble`, …
- `source`: where the design lives, e.g. `Fusion: Housing lid v12` or a KiCad path.
- The purchasing columns match the OTS file (without `pack_qty`: a custom part is ordered
  one piece per item), so custom parts bought from a fabricator (e.g. a PCB) appear on the
  same upload files.

When generating an order, anything with a `supplier` is ordered as one item, even if it
has its own BOM (e.g. a PCB ordered already assembled). Assemblies without a supplier are
expanded; custom parts made in-house are listed but not ordered.

## Tools

Standard-library Python. Run from the repo root.

```bash
# OTS part (prints the new PN)
python tools/new_pn.py ECE "365 nm UV LED, 3535" class=A \
    manufacturer=Lumileds mpn=L1F3-U365200014000 supplier=Mouser \
    supplier_pn=997-L1F3U36520001400 link=https://www.mouser.com/... unit_price=4.12 currency=CAD

# custom part or assembly, written to the product repo's 03_build_package/parts.csv
python tools/new_pn.py PRX "Housing lid" --repo ../photo-reactor make=print "source=Fusion: Housing lid v12"
python tools/new_pn.py PRX "LED driver board, assembled" --repo ../photo-reactor --assembly \
    make=fab supplier=JLCPCB link=https://jlcpcb.com

# purchasing upload files for 3 units of a product (one CSV per supplier)
python tools/requisition.py ../photo-reactor/03_build_package/bom.csv PRX-A-0001 3 --out out/

# after ordering: record the order in the product repo
python tools/record_order.py out/mouser-2026-11-18.csv Mouser "PO 45012" ../photo-reactor

# check the library (also runs in CI), optionally a product's custom parts
python tools/check.py --repo ../photo-reactor

# build the website locally into _site/ (CI publishes it to GitHub Pages on every merge)
python tools/build_site.py
```

The upload files have exactly the purchasing template's columns: `Item Name`, `Prod No`,
`# of Items`, `Price (Before Tax - Original Currency)`, `Item Link`. `price_date` is not
included; the tool warns when a price is missing or older than 90 days.
`--cart-link SUPPLIER=URL` puts one cart link on every row for that supplier.
Quantities are rounded up to whole items, and `--stock stock.csv` subtracts stock on hand
(in pieces). Parts sold in packs are ordered in whole packs: 36 screws from packs of 100 is
`# of Items` 1 at the pack price, and the `Item Name` ends `, pack of 100`.
`record_order.py` records `qty` in pieces (1 pack of 100 is 100).

## Licence

MIT. The `CCC-NNNN` part number format is adapted from [git-plm/parts](https://github.com/git-plm/parts) (see NOTICE).
