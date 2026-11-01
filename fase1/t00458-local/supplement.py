#!/usr/bin/env python3
"""supplement.py — per-run metrics, artifact checks, token-cap table and the
five McNemar comparisons for the five n=400 runs. Stdlib only; reuses analyze.py."""
import json, math, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import REPO, AN38, AN45C, load, wilson, mcnemar  # noqa: E402

RUNS = [
    ("baseline_apr", REPO / "results" / "baseline_nocheatsheet_gptoss_hard3_gpt-oss-120b_20260414_162038.json"),
    ("AN38_apr", AN38),
    ("AN45c_apr", AN45C),
    ("AN45c_rerun", HERE / "AN45c_rerun_gptoss_hard3_full.json"),
    ("T00458", HERE / "T00458_rawprompt_gptoss_hard3_full.json"),
]


def pct(xs, q):
    s = sorted(xs)
    k = max(0, math.ceil(q * len(s)) - 1)  # nearest-rank
    return s[k]


def main():
    data = {name: load(p) for name, p in RUNS}
    ref = set(data["AN38_apr"][0])
    print("== Artifacts ==")
    print("run | n_total | provider | model | size_bytes | parsed | unparsed | cost_usd | minutes | IDs==AN38_apr")
    for name, (r, m) in data.items():
        preds = Counter(x["predicted"] for x in r.values())
        parsed = preds.get("TRUE", 0) + preds.get("FALSE", 0)
        print(f"{name} | {m.get('n_total')} | {m.get('provider')} | {m.get('model')} | "
              f"{m.get('size_bytes')} | {parsed} | {len(r) - parsed} | {m.get('total_cost_usd')} | "
              f"{m.get('total_minutes')} | {set(r) == ref}")
    print("ID sets identical across all 5:", all(set(r) == ref for r, _ in data.values()))

    print("\n== Output tokens ==")
    print("run | max | p99 | p95 | ==4096 | ==8192")
    for name, (r, _) in data.items():
        t = [int(x["tokens_out"]) for x in r.values()]
        print(f"{name} | {max(t)} | {pct(t, .99)} | {pct(t, .95)} | "
              f"{sum(v == 4096 for v in t)} | {sum(v == 8192 for v in t)}")

    print("\n== Metrics ==")
    print("run | accuracy | Wilson95 | TRUE recall | FALSE recall | F1(TRUE) | parse rate")
    for name, (r, _) in data.items():
        n = len(r)
        k = sum(bool(x["correct"]) for x in r.values())
        nt = sum(x["label"] == "TRUE" for x in r.values())
        tp = sum(x["label"] == "TRUE" and x["predicted"] == "TRUE" for x in r.values())
        tn = sum(x["label"] == "FALSE" and x["predicted"] == "FALSE" for x in r.values())
        pt = sum(x["predicted"] == "TRUE" for x in r.values())
        parsed = sum(x["predicted"] in ("TRUE", "FALSE") for x in r.values())
        prec = tp / pt if pt else 0.0
        rec = tp / nt
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        lo, hi = wilson(k, n)
        print(f"{name} | {k}/{n} = {k/n:.4f} | [{lo:.4f}, {hi:.4f}] | {tp}/{nt} = {rec:.4f} | "
              f"{tn}/{n-nt} = {tn/(n-nt):.4f} | {f1:.4f} | {parsed}/{n} = {parsed/n:.4f}")

    print("\n== McNemar (continuity-corrected) ==")
    g = lambda nm: data[nm][0]
    for a, b in [("AN45c_apr", "AN38_apr"), ("AN45c_apr", "AN45c_rerun"),
                 ("T00458", "AN45c_rerun"), ("T00458", "AN45c_apr"), ("T00458", "AN38_apr")]:
        mcnemar(g(a), g(b), a, b)


if __name__ == "__main__":
    main()
