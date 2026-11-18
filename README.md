# parts-library

The organisation-wide part number register and purchased-part data for
[minimalQMS](https://github.com/kelvinchow23/minimal-qms) product repos.

- **One register for every part number,** so `RES-0001` means the same resistor in every
  product, and made parts (`PCB-0001`, `SYS-A-0001`) never collide between products.
- **Purchased-part data in one place:** manufacturer, MPN, supplier, vendor number, link,
  and the last known price with its date.
- **Purchasing upload files generated from a BOM,** in the purchasing system's CSV format.
- **Orders recorded back** into the product repo's `purchases.csv` (minimalQMS SOP-005).

## Part numbers (minimalQMS SOP-002)

| Format | Used for | Examples |
|---|---|---|
| `CCC-NNNN` | Parts: single items, made or purchased | `PCB-0001` bare board, `MEC-0003` printed bracket, `RES-0002` |
| `CCC-A-NNNN` | Assemblies: items with sub-parts or an assembly instruction | `PCB-A-0001` assembled board, `SYS-A-0001` complete product |

Category codes are in `categories.csv`. Revisions of custom parts are tracked in the
product repo that owns them (`owner_repo`), not here.

## parts.csv

| Column | Meaning |
|---|---|
| `pn` | Internal part number |
| `description` | Used as "Item Name" on purchasing uploads |
| `class` | A / B / C traceability class (SOP-002) |
| `make_buy` | `make`: built or printed in-house. `buy`: ordered from a supplier, including custom parts made by a fabricator |
| `owner_repo` | Product repo that owns a custom part's design and revisions |
| `manufacturer`, `mpn` | Manufacturer and manufacturer part number |
| `supplier`, `supplier_pn` | Usual supplier and its part number ("Prod No" on uploads) |
| `link` | Product page |
| `unit_price`, `currency`, `price_date` | Last known unit price and the date it was checked |
| `lifecycle` | `draft` / `released` / `obsolete` |
| `notes` | Anything else |

When generating an order, anything with a `supplier` is ordered as one item, even if it
has its own BOM (e.g. a PCB ordered already assembled). Items without a supplier are
expanded through the product BOM.

## Tools

Standard-library Python. Run from the repo root.

```bash
# allocate a number (prints the new PN)
python tools/new_pn.py OPT "365 nm UV LED, 3535" make_buy=buy class=A \
    manufacturer=Lumileds mpn=L1F3-U365200014000 supplier=Mouser \
    supplier_pn=997-L1F3U36520001400 link=https://www.mouser.com/... unit_price=4.12 currency=CAD
python tools/new_pn.py PCB "LED driver board, assembled" --assembly --same-as=PCB-0001

# purchasing upload files for 3 units of a product (one CSV per supplier)
python tools/requisition.py ../photo-reactor/03_release/bom.csv SYS-A-0001 3 --out out/

# after ordering: record the order in the product repo
python tools/record_order.py out/mouser-2026-11-18.csv Mouser "PO 45012" ../photo-reactor

# check parts.csv (also runs in CI)
python tools/check.py
```

The upload files have exactly the purchasing template's columns: `Item Name`, `Prod No`,
`# of Items`, `Price (Before Tax - Original Currency)`, `Item Link`. `price_date` is not
included; the tool warns when a price is missing or older than 90 days.
`--cart-link SUPPLIER=URL` puts one cart link on every row for that supplier.
Quantities are rounded up to whole items, and `--stock stock.csv` subtracts stock on hand.

## License

MIT. Category codes adapted from [git-plm/parts](https://github.com/git-plm/parts) (see NOTICE).
