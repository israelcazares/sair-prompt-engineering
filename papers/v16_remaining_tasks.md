# v16 Remaining Tasks (freeze tracker)

## Completed
- [x] Finite-model completeness claim (session 1a, commit 426c4de)
- [x] Wilson "non-overlapping" removed (session 1a)
- [x] Outcome arithmetic 5,400 (session 1b)
- [x] AN38 full-scale recalls corrected (session 1b)
- [x] Provider description fixed, verified vs artifacts (session 1b)
- [x] AN38 n=400 artifact recovered and published (session 1b)
- [x] McNemar paired-comparison test computed: b=61, c=31, p≈0.0025
      (session 1b)

## Pending — Session 2 (scope recalibration)
- [ ] Ceiling scope: family-bounded language throughout
- [ ] Title: remove "cognitive load" (decide final title last)
- [ ] Ordering claim -> hypothesis (or run ablation; decision pending)
- [ ] Trade-off section: rewrite with correlation analysis
      (r=0.74 global, 0.12/-0.23 at frontier)
- [ ] Disagreement -> observed metric; delegation -> labeled interpretation
- [ ] De-center winner in 8.4 and 9 (observable behavior only)
- [ ] Semi-decidable sentence (lines ~106-109): rewrite asymmetry
      with correct direction; needs bibliography check
- [ ] Competitor mechanism details: decision pending (Heath/Dufius)

## Pending — Session 3 (final sync)
- [ ] Abstract rewrite (incl. McNemar result)
- [ ] Contributions rewrite
- [ ] Conclusion + self-correction narrative paragraph
- [ ] Limitations rewrite
- [ ] Related Work: add prompt sensitivity, DSPy, self-consistency cites
- [ ] Reproducibility statement citing analysis scripts
- [ ] Release extraction dataset + scripts + checksums (leaderboard n=310)
- [ ] Verify winner sheet exact byte size
- [ ] Confirm GPT-OSS normal disagreement 39.0% vs merged dataset
- [ ] Decide: publish winner's extracted matrix or own only (provenance note)

## Future Research (not v16)
- Analyze 61/31 discordant problem sets for structural patterns
- Ordering ablation (same content, order-only manipulation)
- Cross-model disagreement analysis at leaderboard scale
- Prompt strategy taxonomy
- Disagreement rate as fragility predictor (requires per-run data
  for larger submission sample)

## Frozen (do not reopen without new evidence)
- Section 8 structure; Section 9 structure
- Factual corrections from sessions 1a/1b
