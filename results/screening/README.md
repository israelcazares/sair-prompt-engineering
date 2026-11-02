# Screening and auxiliary results

`MANIFEST.csv` indexes 35 byte-preserved artifacts: the 25 result files retained
by the private-repository audit and 10 additional JSON files covering repeated
runs and the cross-dataset table. This includes runs with 20–50 problems and
auxiliary runs with 69, 100, 200, or 400 problems. Files were scanned before
copying; SHA-256 equality with each source was checked.

## Manifest conventions

- `file` is relative to this directory.
- `variant` follows the experiment filename; `model` and `provider` follow the
  JSON metadata (or per-problem log records). A filename containing `gptoss`
  can still have Llama as its recorded model.
- `split` and `problem_id_range` come from the stored problem IDs. The range
  records the first and last ID; it is not a statement about an external split.
- `n`, `correct`, and `accuracy` are recomputed from the per-problem records
  and checked against JSON metrics. Accuracy is a fraction, not a percentage.
- `inferred_max_tokens` is the observed maximum when that maximum is one of
  512, 1,024, 2,048, 4,096, or 8,192 and at least two responses reach it;
  otherwise it is `NO VERIFICADO`. This is an inference from `tokens_out`,
  not a recovered request parameter or proof of truncation.
- `cited_in_paper` identifies matching numerical entries in
  `papers/paper-sair-v16.tex` at release time. It does not prove which repeat
  the author originally selected, nor that every other metric in that row
  matches. `no` identifies an auxiliary record without such an attribution.

## Repeated runs and provenance limits

Both AN35 hard3 runs are retained. `...20260403_010402.json` records 36/50
(72%) and matches `papers/paper-sair-v16.tex:516`; `...20260403_010112.json`
records 39/50 (78%) and is marked `no`.

Both AN19c/Llama runs record 30/50, and both AN45c/Llama runs record 11/20.
The manuscript alone does not distinguish the repeats.

The two AN3c hard1 GPT-OSS runs both record 54/69, but their TRUE recalls
differ: the April 3 run has 66.7%, matching the cross-dataset row, while the
March 26 run has 62.5%. Their accuracy match is recorded without changing
either file.

The AN19c/Gemma 55% record contains 20 problems, while the multi-model table's
caption generally assigns 50 to non-AN45c rows. Its recorded cheatsheet size
is 455 bytes; the published AN19c body has 289 bytes. AN38/Gemma and
AN38/Llama record 2,242 bytes, while the base AN38 body has 1,776 bytes.
Historical prompt hashes and exact wrapper choices are **NO VERIFICADO**.

The AN3c/Llama files `AN3c_llama_test_...` and `AN3c_agnostic_llama_...`
contain hard1 IDs, 16/20 correct, and 0/4 TRUE recall. They are auxiliary
records marked `no`: this does not establish the hard3 claim in the
multi-model table.

The Gemma files with observed maxima of 512 and 2,048 are retained as
auxiliary records; their presence alone does not reproduce the manuscript's
claim of 100% truncation-caused errors.

The 400-problem `AN45c_gptoss_hard3_400_final_...` record is retained with
224/400 correct (56%). Its exact historical prompt construction is
**NO VERIFICADO**; its filename and accuracy do not establish wrapper mode.

The DeepInfra text log preserves 19/20 correct responses and an original
command referring to an external judge repository. It is an archival log,
not a runnable setup recipe. No evaluation commands were executed during
this release preparation.

Still **NO VERIFICADO** from the releasable artifacts: AN45d/GPT-OSS 70%,
DeepSeek 80%/60%, the AN45c/GPT-OSS 90% endpoint, the Gemma/OpenRouter ~53%
denominator, and a Gemma run at 1,024 tokens. The private mixed transcript
`output-april10-2026.txt` is excluded from this release.
