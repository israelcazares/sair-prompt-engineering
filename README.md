# Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning

**Author:** Manuel Israel Cázares, Bytepro AI, Mazatlán, Sinaloa, Mexico  
Contact: hello@bytepro.ai | israel.cazares@gmail.com  
arXiv: https://arxiv.org/abs/2604.18897

---

This repository is the companion codebase for the paper:

**"Less Is More: Cognitive Load and the Single-Prompt Ceiling in LLM Mathematical Reasoning"**

The paper in this repo corresponds to **v15.2** (current arXiv / Zenodo version).
Previous TeX sources are kept in `papers/archive/` for historical traceability only.

## Context

This repo contains all prompt variants, evaluation pipelines, and results for the SAIR Foundation Mathematics Distillation Challenge: Equational Theories Stage 1 (April 2026, deadline April 20, 2026).

- **Task:** Given two magma equations Eq1 and Eq2, determine if Eq1 implies Eq2 over ALL magmas (TRUE/FALSE binary classification).
- **Competition:** [SAIR Mathematics Distillation Challenge](https://competition.sair.foundation/competitions/mathematics-distillation-challenge-equational-theories-stage1/overview)
- **Official judge repo:** [SAIRcompetition/equational-theories-stage1-judge](https://github.com/SAIRcompetition/equational-theories-stage1-judge)

## Key Results

| Variant                  | Dataset | n   | Accuracy | TRUE% | FALSE% |
|-------------------------|---------|-----|----------|-------|--------|
| AN45c (submitted)       | hard3   | 400 | 79.25%   | 95.9% | 63.4%  |
| AN38                    | hard3   | 400 | 71.8%    | 78.5% | 65.4%  |
| AN19c                   | hard3   | 50  | 62.0%    | 91.7% | 34.6%  |
| AN3c                    | hard1   | 69  | 78.3%    | 66.7% | 84.4%  |
| Baseline (no cheatsheet)| hard3   | 400 | 59.75%   | 82.6% | 38.0%  |

*Cross-provider validation:* AN45c achieved 95% (19/20) on OpenRouter/DeepInfra bf16 (official SAIR provider).

## Files Description

- `cheatsheets/cheat_sheet_variant_AN45c.txt` — submitted prompt (2,252 bytes)
- `cheatsheets/cheat_sheet_variant_AN38.txt` — runner-up, best stable full-scale
- `cheatsheets/cheat_sheet_variant_AN19c.txt` — best multi-model (289 bytes)
- `cheatsheets/cheat_sheet_variant_AN3c.txt` — best on hard1 (FALSE-heavy distribution)

These four files are exactly the prompts used in the gpt-oss runs reported in the paper (byte sizes match Table 1/2: AN45c 2,252; AN38 1,776; AN3c 4,306; AN19c 289). Playground wrappers used only in exploratory multi-model runs (Gemma, Llama) are not included in this curated repo.

- `scripts/eval_pipeline_together.py` — Together AI evaluation pipeline (used for all n=400 runs)
- `scripts/eval_pipeline_openrouter.py` — OpenRouter pipeline (used for cross-provider validation)
- `papers/paper-sair.tex` + `papers/references.bib` — paper source (v15.2 canonical)
- `papers/paper-sair.pdf` — compiled PDF
- `papers/archive/` — previous TeX versions (v13, v15) for historical traceability
- `results/` — all evaluation JSON outputs

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
