#!/usr/bin/env python3
"""analyze_official_baseline.py — paired comparison EQT01-T00458 vs SAIR Baseline,
problem by problem, over the 12 model x set cells. Stdlib only.

Encodings:
  baseline CSV: run1..run3 in {C,I}; U counts as not correct (rule).
  v2 CSV: `runs` single char = 3 identical runs; 3 chars = per-run; G=correct.
"""
import csv, math, random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "data" / "leaderboard" / "official_baseline_matrix.csv"
V2 = REPO / "data" / "leaderboard" / "sair_matrix_extraction_v2.csv"
SUB = "EQT01-T00458"
NREP, SEED = 10000, 42

BOARD_MAP = {"Evaluation (Scored)": "scored", "Order-5 (Research)": "research"}
EXPECTED_BASE = {
    ("GPT-OSS 120B", "normal"): 54.83, ("GPT-OSS 120B", "hard"): 51.17,
    ("GPT-OSS 120B", "extra_hard"): 48.83, ("GPT-OSS 120B", "order5"): 50.83,
    ("Gemma 4 31B IT", "normal"): 65.17, ("Gemma 4 31B IT", "hard"): 55.67,
    ("Gemma 4 31B IT", "extra_hard"): 50.00, ("Gemma 4 31B IT", "order5"): 74.00,
    ("Llama 3.3 70B Instruct", "normal"): 50.00,
    ("Llama 3.3 70B Instruct", "hard"): 50.00,
    ("Llama 3.3 70B Instruct", "extra_hard"): 49.83,
    ("Llama 3.3 70B Instruct", "order5"): 50.00,
}
EXPECTED_T = {
    ("GPT-OSS 120B", "normal"): 62.2, ("GPT-OSS 120B", "hard"): 53.8,
    ("GPT-OSS 120B", "extra_hard"): 59.0, ("GPT-OSS 120B", "order5"): 62.3,
    ("Gemma 4 31B IT", "normal"): 65.7, ("Gemma 4 31B IT", "hard"): 62.8,
    ("Gemma 4 31B IT", "extra_hard"): 43.5, ("Gemma 4 31B IT", "order5"): 69.7,
    ("Llama 3.3 70B Instruct", "normal"): 49.7,
    ("Llama 3.3 70B Instruct", "hard"): 50.5,
    ("Llama 3.3 70B Instruct", "extra_hard"): 50.0,
    ("Llama 3.3 70B Instruct", "order5"): 49.8,
}
MODELS = ["GPT-OSS 120B", "Gemma 4 31B IT", "Llama 3.3 70B Instruct"]
SETS = {"scored": ["normal", "hard", "extra_hard"], "research": ["order5"]}


def expand_runs(r):
    return list(r * 3) if len(r) == 1 else list(r)


def load_baseline():
    # cells[(board,model,set)][problem_id] = (k_correct, single_block)
    cells = defaultdict(dict)
    with BASE.open() as f:
        for row in csv.DictReader(f):
            k = sum(1 for r in (row["run1"], row["run2"], row["run3"]) if r == "C")
            cells[(BOARD_MAP[row["board"]], row["model"], row["set"])][
                row["problem_id"]] = (k, int(row["single_block"]))
    return cells


def load_t():
    cells = defaultdict(dict)
    with V2.open() as f:
        for row in csv.DictReader(f):
            if row["submission_id"] != SUB:
                continue
            runs = expand_runs(row["runs"])
            k = sum(1 for r in runs if r == "G")
            sb = 1 if len(set(runs)) == 1 else 0
            cells[(row["board"], row["model"], row["problem_set"])][
                row["problem_id"]] = (k, sb)
    return cells


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def boot_ci(diffs, rng, nrep=NREP):
    n = len(diffs)
    bs = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(nrep))
    return bs[int(0.025 * nrep)], bs[int(0.975 * nrep)]


def perm_test(diffs, rng, nrep=NREP):
    obs = abs(sum(diffs) / len(diffs))
    cnt = 0
    for _ in range(nrep):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs)
        if abs(s / len(diffs)) >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (nrep + 1)


def mcnemar(t_ids, a, b):
    bb = cc = 0
    for i in t_ids:
        ca = a[i][0] >= 2
        cb = b[i][0] >= 2
        bb += ca and not cb
        cc += cb and not ca
    disc = bb + cc
    stat = (abs(bb - cc) - 1) ** 2 / disc if disc else 0.0
    p = math.erfc(math.sqrt(stat / 2)) if disc >= 25 else float("nan")
    return bb, cc, stat, p


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        adj[i] = max(prev, min(1.0, pvals[i] * (m - rank)))
        prev = adj[i]
    return adj


def main():
    rng = random.Random(SEED)
    base = load_baseline()
    t = load_t()

    # Paso 1 validation
    print("## Paso 1 — baseline validation")
    bad = []
    for (model, s), exp in EXPECTED_BASE.items():
        board = "research" if s == "order5" else "scored"
        cell = base[(board, model, s)]
        n = len(cell)
        acc = 100 * sum(k for k, _ in cell.values()) / (n * 3)
        flag = "OK" if abs(acc - exp) < 0.005 + 0.05 else "FAIL"
        if flag == "FAIL":
            bad.append((model, s, acc, exp))
        print(f"  {model:25s} {s:10s} n={n} acc={acc:6.2f} exp={exp:6.2f} {flag}")
    if bad:
        print("STOP: baseline cell mismatch", bad)
        return

    # Paso 2 validation
    print("\n## Paso 2 — T00458 validation")
    map_ok = True
    for (model, s), exp in EXPECTED_T.items():
        board = "research" if s == "order5" else "scored"
        cell = t[(board, model, s)]
        n = len(cell)
        acc = 100 * sum(k for k, _ in cell.values()) / (n * 3)
        ok = abs(acc - exp) <= 0.05
        bcell = base[(board, model, s)]
        ids_ok = set(cell) == set(bcell)
        if not (ok and ids_ok):
            map_ok = False
        print(f"  {model:25s} {s:10s} n={n} acc={acc:6.2f} exp={exp:5.1f} "
              f"acc_ok={ok} ids_1to1={ids_ok}")
    if not map_ok:
        print("STOP: T00458 cell/ID mismatch")
        return

    # Paso 3 paired comparison
    print("\n## Paso 3 — paired per-problem comparison")
    rows = []
    per_cell = {}
    for board in ("scored", "research"):
        for model in MODELS:
            for s in SETS[board]:
                a = t[(board, model, s)]
                b = base[(board, model, s)]
                ids = sorted(set(a) & set(b))
                d_i = [(a[i][0] - b[i][0]) / 3 for i in ids]
                acc_a = 100 * sum(a[i][0] for i in ids) / (3 * len(ids))
                acc_b = 100 * sum(b[i][0] for i in ids) / (3 * len(ids))
                lo, hi = boot_ci(d_i, rng)
                p = perm_test(d_i, rng)
                bb, cc, stat, pm = mcnemar(ids, a, b)
                sb_a = sum(a[i][1] for i in ids) / len(ids)
                sb_b = sum(b[i][1] for i in ids) / len(ids)
                rows.append([model, s, acc_a, acc_b, acc_a - acc_b,
                             lo * 100, hi * 100, p, bb, cc, pm,
                             sb_a, sb_b])
                per_cell[(model, s)] = dict(d_i=d_i, a=a, b=b, ids=ids)
    p_adj = holm([r[7] for r in rows])
    print("| model | set | T00458 | Base | Δpp | CI95 | p_perm | p_Holm | McNemar p | sbT | sbB |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r, pa in zip(rows, p_adj):
        pm = f"{r[10]:.4f}" if r[10] == r[10] else "exact(<25 disc)"
        print(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:+.2f} | "
              f"[{r[5]:+.2f},{r[6]:+.2f}] | {r[7]:.4f} | {pa:.4f} | "
              f"{pm} (b={r[8]},c={r[9]}) | {r[11]:.2f} | {r[12]:.2f} |")

    # Paso 4 aggregates
    print("\n## Paso 4 — aggregates")
    scored = [(m, s) for m in MODELS for s in SETS["scored"]]
    tot_t = sum(sum(t[("scored", m, s)][i][0] for i in t[("scored", m, s)])
                for m, s in scored)
    tot_b = sum(sum(base[("scored", m, s)][i][0] for i in base[("scored", m, s)])
                for m, s in scored)
    denom = sum(len(t[("scored", m, s)]) * 3 for m, s in scored)
    print(f"  Scored mean T00458: {100*tot_t/denom:.1f}% (exp 55.2)   "
          f"Baseline: {100*tot_b/denom:.1f}% (exp 52.8)")
    for m in MODELS:
        ds, groups = [], defaultdict(list)
        for s in SETS["scored"]:
            e = per_cell[(m, s)]
            for i in e["ids"]:
                d_i = (e["a"][i][0] - e["b"][i][0]) / 3
                ds.append(d_i)
                groups[s].append(d_i)
        obs = sum(ds) / len(ds)
        bs = []
        for _ in range(NREP):
            tot = 0.0
            for s, g in groups.items():
                tot += sum(rng.choice(g) for _ in range(len(g)))
            bs.append(tot / len(ds))
        bs.sort()
        print(f"  {m}: Δ={100*obs:+.2f}pp CI95=[{100*bs[250]:+.2f},"
              f"{100*bs[9750]:+.2f}] (n=600 problems, stratified by set)")

    # Paso 5 Llama descriptive
    print("\n## Paso 5 — Llama descriptive")
    for s in ["normal", "hard", "extra_hard", "order5"]:
        board = "scored" if s != "order5" else "research"
        a = t[(board, "Llama 3.3 70B Instruct", s)]
        b = base[(board, "Llama 3.3 70B Instruct", s)]
        for tag, cell in (("T00458", a), ("Baseline", b)):
            ids = sorted(cell)
            same3 = sum(1 for i in ids if cell[i][0] in (0, 3))
            seq = "".join("C" if cell[i][0] >= 2 else "I" for i in ids[:20])
            runs_c, runs_i, cur = [], [], 1
            for j in range(1, len(ids)):
                same = (cell[ids[j]][0] >= 2) == (cell[ids[j - 1]][0] >= 2)
                cur += 1 if same else 0
                if not same:
                    (runs_c if cell[ids[j - 1]][0] >= 2 else runs_i).append(cur)
                    cur = 1
            (runs_c if cell[ids[-1]][0] >= 2 else runs_i).append(cur)
            mc = sum(runs_c) / len(runs_c) if runs_c else 0
            mi = sum(runs_i) / len(runs_i) if runs_i else 0
            print(f"  {s:10s} {tag:8s} 3-equal={same3}/200  "
                  f"first20={seq}  meanCrun={mc:.1f} meanIrun={mi:.1f}")


if __name__ == "__main__":
    main()
