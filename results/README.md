# Evaluation result provenance

This inventory covers all seven released 400-problem JSON runs, including the
auxiliary April 13 run in `screening/`. Every row records
`model=openai/gpt-oss-120b`, `provider=together`, and 400 hard3 problem IDs.
Counts, accuracy, and dates below come from each file's `metrics` and
`results` fields. Dates use the stored timestamp; the JSONs do not specify
a timezone.

| File (relative to `results/`) | Prompt body | Template | max_tokens and evidence | Date | k/400 | Accuracy |
|---|---|---|---|---|---|---|
| `AN38_gptoss_hard3_full_gpt-oss-120b_20260404_170146.json` | AN38, 1,776 bytes | Wrapper inferred; exact historical version **NO VERIFICADO** | 4,096 inferred: observed maximum, 268 responses exactly there | 2026-04-04 | 287/400 | 71.75% |
| `screening/AN45c_gptoss_hard3_400_final_gpt-oss-120b_20260413_134539.json` | AN45c label, 2,252 bytes | **NO VERIFICADO** | 8,192 inferred: observed maximum, 3 responses exactly there | 2026-04-13 | 224/400 | 56.00% |
| `AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json` | AN45c, 2,252 bytes | Self-contained/raw, attributed by experiment name and paper pipeline note | 8,192 inferred: observed maximum, 25 responses exactly there | 2026-04-14 | 317/400 | 79.25% |
| `baseline_nocheatsheet_gptoss_hard3_gpt-oss-120b_20260414_162038.json` | No cheatsheet, 0 bytes | Wrapper; exact historical version **NO VERIFICADO** | 8,192 inferred: observed maximum, 12 responses exactly there | 2026-04-14 | 239/400 | 59.75% |
| `nov2026/T00458_rawprompt_gptoss_hard3_full.json` | AN38 with self-contained output template, 2,242 bytes | Self-contained/raw | 8,192 in documented configuration; observed maximum, 42 responses exactly there | 2026-11-01 | 330/400 | 82.50% |
| `nov2026/AN45c_rerun_gptoss_hard3_full.json` | AN45c, 2,252 bytes | Self-contained/raw | 8,192 in documented configuration; observed maximum, 29 responses exactly there | 2026-11-01 | 318/400 | 79.50% |
| `nov2026/AN38_wrapper8192_gptoss_hard3_full.json` | AN38, 1,776 bytes | Wrapper | 8,192 in documented configuration; observed maximum, 15 responses exactly there | 2026-11-01 | 323/400 | 80.75% |

## Prompt construction and token-limit evidence

The Together wrapper is defined in `scripts/eval_pipeline_together.py:119–132`.
Raw mode substitutes the two equation placeholders in the supplied prompt
(`:428–433`). Its current GPT-OSS request uses `max_tokens=8192` (`:198–206`).
These JSONs do not store `max_tokens`, a raw/wrapper flag, the full request,
or a cheatsheet hash. Exact historical request configuration is therefore
**NO VERIFICADO** from the JSONs alone. Repeated output-token maxima are
reported as an inference, not as proof that every such answer was truncated.

The April AN45c raw attribution also appears in
`papers/paper-sair-v16.tex:508–530`. For April AN38, the current body has no
equation placeholders; the prior audit suggests wrapper mode but does not
recover its original invocation. The 56% AN45c result does not by itself
establish wrapper mode.

November files and logs were extracted byte-for-byte using `git show` from
commit `1b2a3896290272e4332f26093ca8b5412c9402e7` on
`origin/work/t00458-local`. Prompt modes and configuration are documented in
that commit's `fase1/t00458-local/report.md:196–203,217–226`; the original
filenames and log paths are preserved in that history. The release includes:

- `nov2026/run.log` for T00458;
- `nov2026/rerun_an45c.log` for the AN45c repeat;
- `nov2026/run_an38_wrapper8192.log` for AN38 with the wrapper;
- `nov2026/T00458_cheatsheet.txt`, the reconstructed 2,242-byte prompt.

All three logs identify the cheatsheet byte count and report
`[OK] Cargados 400 problemas (hard3)` at lines 4–5. The logs retain their
original paths, including references to `fase1/t00458-local/`.
No smoke outputs or analysis scripts were imported with this release.

## Screening and official results

`screening/MANIFEST.csv` links the released screening and auxiliary records
to matching manuscript passages. Its README documents repeated runs,
sample-size discrepancies, prompt-size differences, and unverified limits.
`cheatsheets/variants/MANIFEST.csv` lists the 76 source variants.

Official leaderboard data are in `data/leaderboard/`. Their submission
identifiers, encoding, and provenance are documented in
`data/leaderboard/DATA_PROVENANCE.md`. The local 400-problem runs above
are not official leaderboard evaluations.
