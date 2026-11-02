# Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning

**Author:** Manuel Israel Cázares, Bytepro AI, Mazatlán, Sinaloa, Mexico  
Contact: hello@bytepro.ai | israel.cazares@gmail.com  
arXiv: https://arxiv.org/abs/2604.18897

---

This repository is the companion codebase for the paper:

**"Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning"**

The repository includes the v15.2 release and a v16 manuscript. This branch
prepares the v16 data release; manuscript files are unchanged.
Previous TeX sources are kept in `papers/archive/` for historical traceability only.

## Context

This repo contains 76 prompt variants, evaluation pipelines, and released screening and full-scale results for the SAIR Foundation Mathematics Distillation Challenge: Equational Theories Stage 1 (April 2026, deadline April 20, 2026). The variant and result manifests document the available artifacts and their provenance.

- **Task:** Given two magma equations Eq1 and Eq2, determine if Eq1 implies Eq2 over ALL magmas (TRUE/FALSE binary classification).
- **Competition:** [SAIR Mathematics Distillation Challenge](https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview)
- **Official judge repo:** [SAIRcompetition/equational-theories-stage1-judge](https://github.com/SAIRcompetition/equational-theories-stage1-judge)

## April local results

| Variant                  | Dataset | n   | Accuracy | TRUE% | FALSE% |
|-------------------------|---------|-----|----------|-------|--------|
| AN45c (local variant)   | hard3   | 400 | 79.25%   | 95.9% | 63.4%  |
| AN38                    | hard3   | 400 | 71.8%    | 78.5% | 65.4%  |
| AN19c                   | hard3   | 50  | 62.0%    | 91.7% | 34.6%  |
| AN3c                    | hard1   | 69  | 78.3%    | 66.7% | 84.4%  |
| Baseline (no cheatsheet)| hard3   | 400 | 59.75%   | 82.6% | 38.0%  |

*Cross-provider validation:* the archived local AN45c run on OpenRouter/DeepInfra records 95% (19/20), in `results/AN45c_openrouter_deepinfra_hard3_20_20260413.txt:13–33`.

## Official submission EQT01-T00458

**AN38 body with self-contained output template (2,242 bytes)**.
The released reconstruction is
[`results/nov2026/T00458_cheatsheet.txt`](results/nov2026/T00458_cheatsheet.txt),
byte-identical to
[`cheatsheets/variants/cheat_sheet_variant_AN38_playground.txt`](cheatsheets/variants/cheat_sheet_variant_AN38_playground.txt).
Its local November evaluation is listed with the other 400-problem runs in
[`results/README.md`](results/README.md).

The **My Submission** page reports **“Size: 2,242 bytes”**, according to
row **A2** of the Chrome extraction reported by the author. The leaderboard's
Cheatsheet tab displays the rounded **“2.19 KB”**. The reconstructed file
also measures 2,242 bytes and matches AN38_playground with SHA-256
`e21d0de3300e367a04f4c741c1c324064df33d28e7290ec98473df224fbdd1e8`.
The referenced screenshot `12_my_submission.jpg` was not found locally.
The original uploaded binary is unavailable; byte-for-byte identity with
that binary remains **NO VERIFICADO**. The complete evidence chain
and unchanged leaderboard dataset hash are documented in
[`data/leaderboard/DATA_PROVENANCE.md`](data/leaderboard/DATA_PROVENANCE.md#submission-eqt01-t00458--prompt-identity).

## Files Description

- `cheatsheets/cheat_sheet_variant_AN45c.txt` — local AN45c prompt (2,252 bytes)
- `cheatsheets/cheat_sheet_variant_AN38.txt` — AN38 body (1,776 bytes)
- `cheatsheets/cheat_sheet_variant_AN19c.txt` — best multi-model (289 bytes)
- `cheatsheets/cheat_sheet_variant_AN3c.txt` — best on hard1 (FALSE-heavy distribution)

These four files are preserved at their original paths; their byte sizes match
the corresponding base variants in the paper. The other 72 files, including
playground versions, are in `cheatsheets/variants/`. Its `MANIFEST.csv` lists
all 76 variants, SHA-256 hashes, source modification times, manuscript mentions,
and associated released results. Historical prompt hashes are not stored in
the result JSONs.

- `scripts/eval_pipeline_together.py` — Together AI evaluation pipeline (used for all n=400 runs)
- `scripts/eval_pipeline_openrouter.py` — OpenRouter pipeline (used for cross-provider validation)
- `papers/paper-sair.tex` + `papers/references.bib` — paper source (v15.2 canonical)
- `papers/paper-sair.pdf` — compiled PDF
- `papers/archive/` — previous TeX versions (v13, v15) for historical traceability
- `results/README.md` — all released n=400 runs, dates, token-limit evidence and prompt construction
- `results/screening/` — screening and auxiliary results with a manifest
- `results/nov2026/` — three full-scale November runs, logs and T00458 reconstruction
- `data/leaderboard/official_baseline_matrix.csv` — official Baseline per-problem matrix
- `scripts/official_baseline_comparison.py` — paired comparison against EQT01-T00458

## Reproduction

**To reproduce AN45c full-scale result:**
```bash
pip install together python-dotenv
export TOGETHER_API_KEY=your_key
python scripts/eval_pipeline_together.py \
	--cheatsheet cheatsheets/cheat_sheet_variant_AN45c.txt \
	--raw-prompt \
	--problems hard3 \
	--model openai/gpt-oss-120b \
	--max 400 \
	--budget 5.00
```

**To reproduce cross-provider validation (official SAIR pipeline):**
```bash
export OPENROUTER_API_KEY=your_key
python scripts/eval_pipeline_openrouter.py \
	--cheatsheet cheatsheets/cheat_sheet_variant_AN45c.txt \
	--problems hard3 \
	--limit 20 \
	--model gpt-oss-120b
```

## Key Finding

AN45c achieves **+19.5pp** over the no-cheatsheet baseline (79.25% vs 59.75%) on 400 balanced hard problems. The baseline exhibits a structural TRUE bias (82.6% TRUE vs 38.0% FALSE recall); AN45c corrects FALSE recall by +25.4pp while maintaining 95.9% TRUE recall.

## Citation

If you use this work, please cite:

Manuel Israel Cázares (2026). *Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning*. Zenodo. https://doi.org/10.5281/zenodo.19598433

```bibtex
@misc{cazares2026sair,
	author    = {Cázares, Manuel Israel},
	title     = {Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning},
	year      = {2026},
	publisher = {Zenodo},
	doi       = {10.5281/zenodo.19598433},
	url       = {https://zenodo.org/records/19598433}
}
```

## License
MIT

## Related
- Official SAIR judge: https://github.com/SAIRcompetition/equational-theories-stage1-judge
- Competition: https://competition.sair.foundation
- Equational Theories Project: https://github.com/teorth/equational_theories
