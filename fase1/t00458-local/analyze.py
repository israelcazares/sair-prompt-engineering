#!/usr/bin/env python3
"""analyze.py — analysis for the T00458 local n=400 run.
Usage: python3 analyze.py [--t00458 PATH]
Stdlib only. Without --t00458 it runs only the McNemar control AN45c vs AN38.
"""
import argparse, csv, json, math
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
AN38 = REPO / "results" / "AN38_gptoss_hard3_full_gpt-oss-120b_20260404_170146.json"
AN45C = REPO / "results" / "AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json"


def load(path):
    d = json.load(open(path))
    return {r["id"]: r for r in d["results"]}, d.get("metrics", {})


def wilson(k, n, z=1.959964):
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def mcnemar(a, b, label_a, label_b):
    ids = sorted(set(a) & set(b))
    both_ok = only_a = only_b = both_bad = 0
    for i in ids:
        ca, cb = a[i]["correct"], b[i]["correct"]
        both_ok += ca and cb
        only_a += ca and not cb
        only_b += cb and not ca
        both_bad += (not ca) and (not cb)
    disc = only_a + only_b
    stat = (abs(only_a - only_b) - 1) ** 2 / disc if disc else 0.0
    if disc < 25:
        method = "exact two-sided binomial"
        from math import comb
        p = sum(comb(disc, k) for k in range(0, min(only_a, only_b) + 1)) / 2 ** (disc - 1) if disc else 1.0
    else:
        method = "chi-square(1 df), continuity-corrected"
        p = math.erfc(math.sqrt(stat / 2.0))
    print(f"\n{label_a} vs {label_b} (n={len(ids)} paired problems)")
    print(f"  2x2: both correct={both_ok}  only {label_a}={only_a}  "
          f"only {label_b}={only_b}  both wrong={both_bad}")
    print(f"  b={only_a}  c={only_b}  chi2={stat:.4f}  p={p:.6g}  [{method}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t00458", type=Path, default=None)
    args = ap.parse_args()

    a38, m38 = load(AN38)
    a45, m45 = load(AN45C)
    print(f"ID sets AN38 vs AN45c identical: {set(a38) == set(a45)}")
    mcnemar(a45, a38, "AN45c", "AN38")  # control: expect b=61 c=31 chi2=9.14 p=0.0025

    if not args.t00458:
        print("\n(no --t00458 JSON provided; control only)")
        return
    t, mt = load(args.t00458)
    ids_t, ids_38 = set(t), set(a38)
    print(f"\nT00458 ID set == AN38/AN45c ID set: {ids_t == ids_38}")
    if ids_t != ids_38:
        print("STOP: ID sets differ.")
        print("  only in T00458:", sorted(ids_t - ids_38)[:10])
        print("  missing:", sorted(ids_38 - ids_t)[:10])
        return

    n = len(t)
    ncorr = sum(r["correct"] for r in t.values())
    preds = Counter(r["predicted"] for r in t.values())
    parsed = preds.get("TRUE", 0) + preds.get("FALSE", 0)
    tp = sum(r["correct"] for r in t.values() if r["label"] == "TRUE")
    nt = sum(1 for r in t.values() if r["label"] == "TRUE")
    fp = sum(r["correct"] for r in t.values() if r["label"] == "FALSE")
    nf = n - nt
    # F1 over predicted-TRUE class
    pred_true = preds.get("TRUE", 0)
    precision = tp / pred_true if pred_true else 0.0
    recall_t = tp / nt
    f1 = 2 * precision * recall_t / (precision + recall_t) if (precision + recall_t) else 0.0
    lo, hi = wilson(ncorr, n)
    print(f"\nT00458 n={n}: accuracy={ncorr/n:.4f} ({ncorr}/{n})  "
          f"Wilson95=[{lo:.4f},{hi:.4f}]")
    print(f"  TRUE recall={recall_t:.4f} ({tp}/{nt})  FALSE recall={fp/nf:.4f} ({fp}/{nf})")
    print(f"  F1(TRUE)={f1:.4f}  parse rate={parsed/n:.4f} ({parsed}/{n})")
    print(f"  metrics.size_bytes={mt.get('size_bytes')}  provider={mt.get('provider')}")
    print(f"  cost=${mt.get('total_cost_usd')}  minutes={mt.get('total_minutes')}")

    mcnemar(t, a45, "T00458", "AN45c")
    mcnemar(t, a38, "T00458", "AN38")

    # Drift control: AN45c re-run vs April AN45c
    rerun_path = REPO / "fase1" / "t00458-local" / "AN45c_rerun_gptoss_hard3_full.json"
    if rerun_path.exists():
        ar, mr = load(rerun_path)
        if set(ar) != set(a45):
            print("\nSTOP: AN45c re-run ID set differs from April AN45c")
            return
        nr = len(ar)
        nrc = sum(r["correct"] for r in ar.values())
        lo, hi = wilson(nrc, nr)
        print(f"\nAN45c re-run n={nr}: accuracy={nrc/nr:.4f} ({nrc}/{nr})  "
              f"Wilson95=[{lo:.4f},{hi:.4f}]")
        print(f"  (April AN45c: 0.7925 = 317/400)")
        mcnemar(a45, ar, "AN45c_apr", "AN45c_rerun")  # drift control
        mcnemar(t, ar, "T00458", "AN45c_rerun")
    else:
        print("\n(no AN45c re-run JSON found; drift control skipped)")


if __name__ == "__main__":
    main()
