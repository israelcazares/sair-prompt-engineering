#!/usr/bin/env python3
"""supplement_an38w8192.py — token cap, metrics and McNemar for the AN38 wrapper
run with max_tokens=8192. Stdlib only; reuses analyze.py and supplement.py."""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import AN38, load, wilson, mcnemar  # noqa: E402
from supplement import pct  # noqa: E402

NEW = HERE / "AN38_wrapper8192_gptoss_hard3_full.json"
T00458 = HERE / "T00458_rawprompt_gptoss_hard3_full.json"
RERUN = HERE / "AN45c_rerun_gptoss_hard3_full.json"


def main():
    w, m = load(NEW)
    a38, _ = load(AN38)
    t, _ = load(T00458)
    ar, _ = load(RERUN)
    print("n_total:", m.get("n_total"), "provider:", m.get("provider"), "model:", m.get("model"),
          "size_bytes:", m.get("size_bytes"), "cost:", m.get("total_cost_usd"),
          "minutes:", m.get("total_minutes"), "budget_exceeded:", m.get("budget_exceeded"))
    print("ID set == AN38_apr:", set(w) == set(a38), "== T00458:", set(w) == set(t),
          "== AN45c_rerun:", set(w) == set(ar))
    tk = [int(x["tokens_out"]) for x in w.values()]
    print(f"tokens_out max={max(tk)} p99={pct(tk, .99)} p95={pct(tk, .95)} "
          f"==4096={sum(v == 4096 for v in tk)} ==8192={sum(v == 8192 for v in tk)} "
          f">4096={sum(v > 4096 for v in tk)}")
    n = len(w)
    k = sum(bool(x["correct"]) for x in w.values())
    nt = sum(x["label"] == "TRUE" for x in w.values())
    tp = sum(x["label"] == "TRUE" and x["predicted"] == "TRUE" for x in w.values())
    tn = sum(x["label"] == "FALSE" and x["predicted"] == "FALSE" for x in w.values())
    pt = sum(x["predicted"] == "TRUE" for x in w.values())
    preds = Counter(x["predicted"] for x in w.values())
    parsed = preds.get("TRUE", 0) + preds.get("FALSE", 0)
    prec = tp / pt if pt else 0.0
    rec = tp / nt
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    lo, hi = wilson(k, n)
    print(f"accuracy={k}/{n}={k/n:.4f} Wilson95=[{lo:.4f}, {hi:.4f}] TRUE recall={tp}/{nt}={rec:.4f} "
          f"FALSE recall={tn}/{n-nt}={tn/(n-nt):.4f} F1(TRUE)={f1:.4f} parse={parsed}/{n}={parsed/n:.4f}")
    mcnemar(w, a38, "AN38_wrapper8192", "AN38_apr")
    mcnemar(w, t, "AN38_wrapper8192", "T00458")
    mcnemar(w, ar, "AN38_wrapper8192", "AN45c_rerun")


if __name__ == "__main__":
    main()
