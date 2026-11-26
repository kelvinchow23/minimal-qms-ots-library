# AGENTS.md

Instructions for any AI agent working in this repo. `CLAUDE.md` imports this file.
This repo follows [minimalQMS](https://github.com/kelvinchow23/minimal-qms); its hard
rules apply here (never commit to `main`, never merge or approve, never backdate).

## Related repos

The minimalQMS repos are cloned side by side in one parent folder. Agent sessions in
different repos do not share memory; they coordinate through these files. Local folder
names may differ from the GitHub names (e.g. `minimal-qms` may be cloned as `mini-qms-ai`).

| Repo | What to read there |
|---|---|
| `minimal-qms` | `docs/INTERFACES.md`: the authority on shared names, IDs, columns and the product repo layout. `docs/ROADMAP.md`: what is planned. `sops/SOP-002-*` (part numbers) and `sops/SOP-005-*` (purchasing) govern this library. |
| `minimal-qms-ots-library` (this repo) | OTS parts, project codes, part number allocation and purchasing tools. |
| `minimal-qms-playbook` | Public work instructions and agent skills, `skills/<name>/SKILL.md` (Fusion, Onshape, KiCad, assembly instructions, purchasing). Read the relevant skill before doing that kind of work. |
| `minimal-qms-playbook-private` | Private organization add-ons, `skills/<name>/<name>-private-addon.md`. Not every user has it. Never copy its contents into a public repo. |

- Read the relevant file in the other repo before changing anything that crosses repos.
- A change to a column or name that product repos rely on (e.g. the `parts.csv` header)
  also updates `docs/INTERFACES.md` and the SOP that cites it in `minimal-qms`, through a
  separate PR there.

## Rules for this repo

1. **This library holds OTS parts only.** Custom parts and assemblies (`PPP-NNNN`,
   `PPP-A-NNNN`) are written to the owning product repo with `new_pn.py --repo`.
2. **Allocate part numbers only with `tools/new_pn.py`.** Never type a new PN by hand,
   never reuse or renumber a PN, and never delete a row; set `lifecycle: obsolete` instead.
   OTS parts go in `parts/CCC.csv`, one file per prefix. A new project needs a line in
   `projects.csv` first; codes are 3 capital letters and must not start with a part
   family (`EC`, `HW`). A new prefix needs a line in `categories.csv` and an
   empty `parts/CCC.csv` with the standard header.
3. **Prices always carry a date.** When updating `unit_price`, also set `price_date` to the
   date the price was checked, and `currency`. `unit_price` is per piece; set `pack_qty`
   for parts sold in packs. Exchange rates in `rates.csv` follow the same rule: update
   `rate_date` with `cad_per_unit` (Bank of Canada daily rate).
4. **Prefer the supplier's part number** for `supplier_pn` ("Prod No" on uploads). Use the
   manufacturer PN when the supplier has none.
   **McMaster-Carr hides the manufacturer and MPN: for a McMaster part, leave
   `manufacturer` and `manufacturer_pn` blank** (never fill them with "McMaster-Carr" or the McMaster
   number). The McMaster number goes in `supplier_pn` only. `check.py` enforces this.
5. **One value per column.** `description` is one line in the README's pattern (fasteners:
   `Type, size, [style, ]material`). `notes` hold only what a buyer needs that has no
   column, under 120 characters: no prices, dates, PNs that have a column, CAD-model
   sources or project decisions (those go in the product repo or the Fusion design).
6. **Run `python tools/check.py` before finishing** (add `--repo` when custom parts changed) and report its result.
7. Commit format: `[PN] summary`, e.g. `[ECE-0001] add 365 nm LED`, or `[LIB] summary` for
   tools and repo-wide changes.

8. **Canadian English spelling** in prose (organization, colour, centre, licence as the
   noun). Proper names and code identifiers stay as they are.

## Typical requests

- A "Part request" issue: read the links, choose the prefix, add the part with
  `new_pn.py` on a branch, and open a PR that closes the issue.
- "Add these parts from my Mouser cart": create one `new_pn.py` row per item, with
  supplier data and today's price.
- "Make the order files for 3 photoreactors": run `requisition.py` on the product BOM and
  report any warnings (missing or old prices).
- "Cost the photoreactor BOM for 3 units": run `bom_cost.py` and report the CAD total and
  any warnings (missing or old prices, old rates).
- "I placed the Mouser order, it's PO 45012": run `record_order.py` into the product repo,
  on a branch in that repo.
