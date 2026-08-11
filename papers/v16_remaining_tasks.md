# v16 Remaining Tasks (freeze tracker)

Last updated: session close, day 1 (post-dataset-reconstruction).

## Completed — Data & Reproducibility

- [x] Finite-model completeness claim corrected (session 1a, commit 426c4de)
- [x] Wilson "non-overlapping" claim removed (session 1a)
- [x] Outcome arithmetic fixed in 9.1: 5,400 not 7,200 (session 1b)
- [x] AN38 full-scale recalls corrected, 78.5/65.4 at n=400 (session 1b)
- [x] Provider description fixed and verified against artifacts (session 1b)
- [x] AN38 n=400 artifact recovered and published (session 1b)
- [x] McNemar paired-comparison analysis added: b=61, c=31, chi2=9.14,
      p=0.0025 (session 1b) — replaces reliance on marginal Wilson CIs
- [x] TRUE/FALSE asymmetry framing corrected in Introduction, grounded
      in tao2025etp only (session 1, final factual fix)
- [x] Ceiling scope bounded to explored prompt family throughout
      (abstract, introduction, sec:ceiling) (session 2)
- [x] Mixed-sample Pareto-front claim removed; replaced with full-scale
      (n=400) direct comparison (session 2)
- [x] Ordering effect reframed as hypothesis, not established cause
      (session 2)
- [x] Routing section retitled and stripped of unproven universals
      about how LLMs execute instructions (session 2)
- [x] Related Work: "cognitive load collapse" term removed; Llama vs.
      Gemma vs. GPT-OSS profiles separated (session 2)
- [x] Winning submission de-centered in 8.4 and 9: internal-mechanism
      descriptions removed, observation-then-interpretation structure
      applied (session 2)
- [x] 326 missing rows recovered (our GPT-OSS normal 1-126, our Gemma
      normal full) via re-extraction, SHA-256 verified
- [x] submission_id reconstructed via structural decomposition search
      (11,440 raw candidates -> 128 per-cell admissible -> 1 validated
      against all published official accuracies)
- [x] sair_matrix_extraction_v2.csv published: 4,200 rows, 0 duplicate
      keys, deterministic ordering, stable SHA-256
- [x] validate_matrix_reconstruction.py: regenerates candidate counts
      from data (not asserted constants); validates 18 scored per-model
      accuracies plus published research average (60.6%)
- [x] DATA_PROVENANCE.md: sources, hashes, transformation, encoding,
      scope, validation — full chain of custody
- [x] GPT-OSS normal disagreement 39.0% and Gemma normal 16.0%
      (tab:disagreement) now reproducible from the released dataset
- [x] Cross-board correlation analysis published (leaderboard_correlation.py,
      correlation_analysis.md): full-sample Pearson r=0.74; homogeneous-
      linear-null bootstrap (10,000 replicates, seed 42) shows the effect
      is directional — research-selected upper subsets fall outside the
      expected interval at all three cuts (33%/25%/10%), scored-selected
      subsets do not do so consistently

## Completed — Project Infrastructure

- [x] Permanent Cursor rules established (.cursor/rules/scientific-editing.mdc):
      venue (TMLR), paper objective, what this paper is NOT, primary
      contribution, narrative order, evidence hierarchy, competitor
      citation rule
- [x] Snapshot of sec:results (465-649), sec:analysis (650-762),
      sec:official (926-1264) with full structural map and all 51
      AN45c cross-references indexed by line

## Pending — Structural Reorganization (next session, priority order)

- [ ] **Section 8 restructure + AN45c relocation** (single task, two phases):
  - [ ] Phase A: map which lines in sec:official (940-1264) belong to
        Phenomenon A (AN45c local-hard3 -> official-hard3, our own
        experimental axis; relocates to sec:results/sec:analysis) vs.
        Phenomenon B (leaderboard research -> scored, external
        cross-distribution evidence; stays in sec:official)
  - [ ] Phase B: execute relocation; rewrite sec:official as bounded
        external validation (core: directional research->scored effect
        per correlation_analysis.md; no shared-mechanism claim with
        Phenomenon A)
  - [ ] Verify all 51 AN45c cross-references individually post-move
        (none broken, none duplicated)

- [ ] **Claim audit pass**: grep for demonstrates/shows/proves/confirms/
      establishes/indicates/causes/explains/generalizes/validates across
      the full document; classify each as observed fact / observed
      contrast / interpretation / hypothesis / external evidence; fix
      any direct jump from fact to external-evidence framing

- [ ] **Discussion / Threats to Validity**:
  - [ ] Leaderboard reconstruction threat (submission_id was not native
        to the original export; show the rigor via DATA_PROVENANCE.md,
        do not hide it)
  - [ ] Distinct-axes threat (AN45c local->official vs. leaderboard
        research->scored; explicitly not unified)
  - [ ] External-evidence-is-not-mechanism threat
  - [ ] Scope threat (bounded to explored prompt family)

- [ ] **Introduction rewrite**: lead with empirical-study framing per
      permanent rules, not framework framing; central question around
      capabilities/limits of heuristic guidance for algebraic implication
- [ ] **Title decision** (deferred from session 2)

- [ ] **Conclusion rewrite**: reflect exactly what was shown, no
      general-theory overclaim; add self-correction-as-strength
      paragraph (ceiling scope, Llama mechanism, cognitive load,
      disagreement interpretation — discussed, never written);
      Limitations synced with all prior changes

- [ ] **Related Work**: add pending citations from v1 — prompt
      sensitivity, DSPy/automatic prompt optimization, self-consistency/
      sampling variance literature

- [ ] **Reproducibility statement**: paragraph citing existing analysis
      scripts (mcnemar_an45c_an38.py, validate_matrix_reconstruction.py,
      leaderboard_correlation.py)

- [ ] **Final editorial pass**: tables, captions, labels, cross-references,
      terminology, numbering; abstract/intro/results/conclusion
      consistency; final compilation, PDF review, arXiv/TMLR submission prep

## Future Research (not v16)

- Analyze 61/31 discordant problem sets (AN45c vs AN38) for structural
  patterns
- Ordering ablation (same content, order-only manipulation)
- Cross-model disagreement analysis at leaderboard scale
- Prompt strategy taxonomy
- Disagreement rate as fragility predictor (requires per-run data for
  a larger submission sample)
- Investigate whether the research->scored transfer asymmetry and the
  AN45c local->official gap share any common cause (currently treated
  as distinct, unrelated-until-shown-otherwise phenomena)

## Frozen (do not reopen without new evidence)

- Section 9 structure and dataset (fully validated, do not re-audit
  bootstrap/Pearson/Spearman/Thorndike/hashes/validator again)
- Factual corrections from sessions 1a/1b
- Session 2 scope-calibration edits (Pareto front, ordering-as-hypothesis,
  routing, competitor de-centering)
