# Cross-Board Correlation Analysis

- Analysis date: 2026-08-05
- Git HEAD: `ed8de6ce6f279fda202943c2c112602eb5848d7e`
- Root seed: `42`
- Resamples per bootstrap/simulation: `10,000`
- Top-subset rule: `ceil(fraction × n)` observations define the cutoff;
  all observations tied at the cutoff are included.

## Source Integrity

- Scored export SHA-256: `2d0998d47bfb2a80bf473c61f2bcf388711e78345130f7cbd15f280d40277aae`
- Research export SHA-256: `467d7532b8ce22aab445536378277a660953381069226b43c9c534a285251303`
- Scored-details export SHA-256: `1cf8ee574d22690d8d949c4467865810ef3bcb0bd92ca265c108600c4d1a8bfb`

## Unit-of-Analysis Validation

- Scored rows: `310`
- Scored unique team IDs: `310`
- Scored duplicate team IDs: `0`
- Research rows: `310`
- Research unique team IDs: `310`
- Research duplicate team IDs: `0`
- Cross-board ID intersection: `310`
- Scored-only IDs: `0`
- Research-only IDs: `0`

The exported boards therefore contain 310 rows corresponding to 310
unique team IDs on each board, with an exact 310-ID intersection.

## Full Sample

| Metric | Estimate | Bootstrap 95% CI | Fisher 95% CI |
|---|---:|---:|---:|
| Pearson r | 0.7409 | [0.5318, 0.8441] | [0.6862, 0.7873] |
| Spearman rho | 0.5731 | [0.4712, 0.6638] | [0.4932, 0.6434] |

Degenerate full-sample correlation bootstrap replicates: `0`.
The Fisher interval for Spearman rho is included only as an
approximation for comparison; the bootstrap interval is primary.

## Conditioned Subsets and Range Restriction

| Selector | Cut | Target n | Cutoff | Actual n | Pearson r | Pearson bootstrap 95% CI | Spearman rho | Spearman bootstrap 95% CI | SD ratio u | Thorndike expected r | Observed - expected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| scored | 33% | 103 | 56.9% | 109 | 0.2318 | [0.0172, 0.4198] | 0.2980 | [0.0967, 0.4767] | 0.3973 | 0.4014 | -0.1696 |
| research | 33% | 103 | 64.9% | 104 | -0.0724 | [-0.2762, 0.1319] | 0.0469 | [-0.1610, 0.2596] | 0.4851 | 0.4718 | -0.5442 |
| scored | 25% | 78 | 58.1% | 79 | 0.1552 | [-0.0904, 0.3632] | 0.1517 | [-0.0952, 0.3824] | 0.3871 | 0.3927 | -0.2375 |
| research | 25% | 78 | 65.9% | 80 | -0.2136 | [-0.4124, 0.0062] | -0.1158 | [-0.3347, 0.1221] | 0.4854 | 0.4721 | -0.6857 |
| scored | 10% | 31 | 60.1% | 32 | 0.1267 | [-0.1715, 0.4176] | 0.1108 | [-0.2598, 0.4579] | 0.3750 | 0.3823 | -0.2556 |
| research | 10% | 31 | 69.7% | 32 | -0.2970 | [-0.5737, 0.0156] | -0.3360 | [-0.6361, 0.0333] | 0.4429 | 0.4390 | -0.7360 |

Thorndike Case II is reported as an analytic reference under direct
range restriction and a homogeneous linear relationship. It is not
used as a standalone hypothesis test.

## Empirical Pair-Selection Bootstrap

This bootstrap follows the requested pair-resampling algorithm. It
preserves heterogeneity present in the observed pairs and therefore
is not a homogeneous null simulation.

| Selector | Cut | Observed r | Bootstrap p2.5 | Median | Bootstrap p97.5 | Observed percentile | Interval verdict | Valid | Degenerate |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| scored | 33% | 0.2318 | 0.0324 | 0.2490 | 0.4426 | 42.90% | inside | 10000 | 0 |
| research | 33% | -0.0724 | -0.2753 | -0.0681 | 0.1387 | 48.27% | inside | 10000 | 0 |
| scored | 25% | 0.1552 | -0.0813 | 0.1702 | 0.3878 | 45.06% | inside | 10000 | 0 |
| research | 25% | -0.2136 | -0.4124 | -0.2050 | 0.0484 | 47.28% | inside | 10000 | 0 |
| scored | 10% | 0.1267 | -0.1671 | 0.1376 | 0.4243 | 46.93% | inside | 10000 | 0 |
| research | 10% | -0.2970 | -0.5738 | -0.2913 | 0.0481 | 48.73% | inside | 10000 | 0 |

## Homogeneous Linear Null Bootstrap

For each selector, an ordinary least-squares model is fit on the full
sample with the other board as outcome. Each replicate independently
resamples selector values and centered residuals, reconstructs 310
pairs under one homogeneous linear relationship, and reapplies the
same cutoff and tie rule. This is the simulation used for the
inside/outside homogeneity verdict.

| Selector | Cut | Observed r | Null p2.5 | Null median | Null p97.5 | Observed percentile | Homogeneity verdict | Valid | Degenerate |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| scored | 33% | 0.2318 | 0.2186 | 0.3992 | 0.5685 | 3.62% | inside expected interval | 10000 | 0 |
| research | 33% | -0.0724 | 0.2734 | 0.4818 | 0.6410 | 0.00% | outside expected interval | 10000 | 0 |
| scored | 25% | 0.1552 | 0.1776 | 0.3927 | 0.5882 | 1.63% | outside expected interval | 10000 | 0 |
| research | 25% | -0.2136 | 0.2478 | 0.4827 | 0.6641 | 0.00% | outside expected interval | 10000 | 0 |
| scored | 10% | 0.1267 | 0.0385 | 0.3893 | 0.6755 | 6.59% | inside expected interval | 10000 | 0 |
| research | 10% | -0.2970 | 0.0757 | 0.4671 | 0.7313 | 0.03% | outside expected interval | 10000 | 0 |

## Fisher Intervals for Conditioned Subsets

| Selector | Cut | n | Pearson Fisher 95% CI | Spearman Fisher approximation 95% CI | Degenerate correlation bootstrap replicates |
|---|---:|---:|---:|---:|---:|
| scored | 33% | 109 | [0.0457, 0.4024] | [0.1164, 0.4603] | 0 |
| research | 33% | 104 | [-0.2614, 0.1219] | [-0.1471, 0.2373] | 0 |
| scored | 25% | 79 | [-0.0682, 0.3639] | [-0.0719, 0.3607] | 0 |
| research | 25% | 80 | [-0.4139, 0.0064] | [-0.3272, 0.1066] | 0 |
| scored | 10% | 32 | [-0.2323, 0.4553] | [-0.2474, 0.4424] | 0 |
| research | 10% | 32 | [-0.5851, 0.0576] | [-0.6129, 0.0144] | 0 |

## Parameters

- Pair alignment key: exact `EQT01-Txxxxx` team ID.
- Correlations use leaderboard `Avg Accuracy` percentages.
- Bootstrap confidence intervals use percentile endpoints.
- Pair bootstrap resamples paired scored/research observations.
- Named pseudorandom streams are deterministically derived from the
  root seed `42` using SHA-256.
- Sensitivity cuts: top 33%, top 25%, and top 10% by each board.
- Ties use average ranks for Spearman rho.
