"""Build the OTS library website into _site/ (published to GitHub Pages by CI).

Usage: python tools/build_site.py [OUT_DIR]

Copies site/index.html and writes data.json with the prefixes and every OTS part.
The site is read-only; changes go through the CSV files and a reviewed PR.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date

from lib import ROOT, categories, load_parts


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "_site")
    os.makedirs(out, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "site", "index.html"), os.path.join(out, "index.html"))
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    data = {
        "built": date.today().isoformat(),
        "commit": commit,
        "prefixes": [{"code": c, **{k: v for k, v in r.items() if k != "code"}}
                     for c, r in categories().items()],
        "parts": load_parts(),
    }
    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"built {out} ({len(data['parts'])} parts, {len(data['prefixes'])} prefixes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
