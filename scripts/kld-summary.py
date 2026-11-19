#!/usr/bin/env python3
"""Turn llama-perplexity --kl-divergence logs into a markdown table.

Usage: kld-summary.py <dir with <corpus>-<name>.log files>
"""
import re
import sys
from pathlib import Path

STATS = [("Mean KLD", r"Mean +KLD:\s+([0-9.]+)\s+±\s+([0-9.]+)"),
         ("Median KLD", r"Median +KLD:\s+([0-9.]+)"),
         ("99% KLD", r"99\.0% +KLD:\s+([0-9.]+)"),
         ("99.9% KLD", r"99\.9% +KLD:\s+([0-9.]+)"),
         ("Same top", r"Same top p:\s+([0-9.]+)"),
         ("RMS Δp", r"RMS Δp\s+:\s+([0-9.]+)"),
         ("PPL(Q)", r"Mean PPL\(Q\)\s+:\s+([0-9.]+)"),
         ("PPL(ref)", r"Mean PPL\(base\)\s+:\s+([0-9.]+)")]


def main(d):
    rows = []
    for f in sorted(Path(d).glob("*.log")):
        m = re.match(r"(prose|code)-(.+)\.log$", f.name)
        if not m or m.group(2) == "REF":
            continue
        t = f.read_text(errors="replace")
        vals = []
        for name, pat in STATS:
            x = re.search(pat, t)
            if not x:
                vals.append("")
            elif name == "Mean KLD":
                vals.append(f"{float(x.group(1)):.4f} ± {float(x.group(2)):.4f}")
            elif name in ("Same top", "RMS Δp"):
                vals.append(f"{float(x.group(1)):.2f}%")
            else:
                vals.append(f"{float(x.group(1)):.4f}")
        rows.append((m.group(1), m.group(2), vals))
    print("| Corpus | Quant | " + " | ".join(n for n, _ in STATS) + " |")
    print("|---|---|" + "---:|" * len(STATS))
    for corpus, name, vals in sorted(rows, key=lambda r: (r[0], float(r[2][0].split()[0] or 0))):
        print(f"| {corpus} | {name} | " + " | ".join(vals) + " |")


if __name__ == "__main__":
    main(sys.argv[1])
