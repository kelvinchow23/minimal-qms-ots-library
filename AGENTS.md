# AGENTS.md

Instructions for any AI agent working in this repo. `CLAUDE.md` imports this file.
This repo follows [minimalQMS](https://github.com/kelvinchow23/minimal-qms); its hard
rules apply here (never commit to `main`, never merge or approve, never backdate).

## Rules for this repo

1. **Allocate part numbers only with `tools/new_pn.py`.** Never type a new PN by hand,
   never reuse or renumber a PN, and never delete a row; set `lifecycle: obsolete` instead.
2. **Prices always carry a date.** When updating `unit_price`, also set `price_date` to the
   date the price was checked, and `currency`.
3. **Prefer the supplier's part number** for `supplier_pn` ("Prod No" on uploads). Use the
   MPN when the supplier has none.
4. **Custom parts** (`PCB-`, `MEC-`, `SYS-` …) need `owner_repo`. Their revisions live in
   that repo, not here.
5. **Run `python tools/check.py` before finishing** and report its result.
6. Commit format: `[PN] summary`, e.g. `[OPT-0001] add 365 nm LED`, or `[LIB] summary` for
   tools and repo-wide changes.

## Typical requests

- "Add these parts from my Mouser cart": create one `new_pn.py` row per item, with
  supplier data and today's price.
- "Make the order files for 3 photoreactors": run `requisition.py` on the product BOM and
  report any warnings (missing or old prices).
- "I placed the Mouser order, it's PO 45012": run `record_order.py` into the product repo,
  on a branch in that repo.
