# AN45c vs AN38 Paired Partitions

Generated: 2026-07-27T12:37:14Z
Generated at commit: `e58cc15bf460041a2d018f1795cd1a30b25660fd`
Paper version: `paper-sair-v16.tex`

## Sources
- AN45c path: `results/AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json`
- AN45c filename: `AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json`
- AN38 path: `results/AN38_gptoss_hard3_full_gpt-oss-120b_20260404_170146.json`
- AN38 filename: `AN38_gptoss_hard3_full_gpt-oss-120b_20260404_170146.json`

## Partition Counts
- Aligned problems: 400
- `an45c_only_correct.csv`: 61
- `an38_only_correct.csv`: 31
- `both_correct.csv`: 256
- `both_wrong.csv`: 52

## McNemar Test
- b (AN45c correct, AN38 incorrect): 61
- c (AN45c incorrect, AN38 correct): 31
- Chi-square statistic (continuity-corrected): 9.1413043478
- p-value: 0.00249902885761
- Method: chi-square(1 df), continuity-corrected
