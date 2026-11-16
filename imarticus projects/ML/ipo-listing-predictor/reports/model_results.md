# Model results

Code: `src/models/train.py` (tuning), `src/models/evaluate.py` (walk-forward and final models).
Walkthrough with charts: `notebooks/04_modeling.ipynb`.

## Setup

- 634 IPOs. Development period 2010–2023 (432 IPOs), out-of-sample period 2024–2026 (202 IPOs).
- Tuning: yearly folds on 2010–2023. Each validation year (2019 to 2023) is predicted by a model
  trained only on IPOs that listed before it (with a 7-day gap at the year boundary).
  Selection metric: mean absolute error (MAE).
- Candidates: two baselines (median of all past IPOs; median of past IPOs in the same
  subscription bucket), ridge regression, random forest, LightGBM. Each ML model also chose
  between the base features and the base plus relative-subscription features, and between no
  recency weighting and a 4-year half-life.
- **Nothing was chosen using 2024–2026.**

## 1. Tuning result (2019–2023 yearly folds)

| Model | MAE | Median AE | Spearman |
|---|---|---|---|
| Random forest | 16.03 | 9.59 | 0.76 |
| LightGBM | 16.45 | 9.73 | 0.74 |
| Same-bucket median | 17.21 | 10.12 | 0.71 |
| Ridge | 18.71 | 11.61 | 0.73 |
| Median of all IPOs | 26.74 | 13.10 | −0.02 |

All ML winners used the base features with no recency weighting.

## 2. A model frozen at the end of 2023 failed

Trained once on 2010–2023 and scored on 2024–2026:

| Model | MAE 2024–26 | Spearman |
|---|---|---|
| Same-bucket median | 17.94 | 0.69 |
| Median of all IPOs | 18.98 | 0.00 |
| Ridge | 21.29 | 0.65 |
| Random forest | 22.03 | 0.69 |
| LightGBM | 24.61 | 0.67 |

The cause is **subscription inflation**. Median subscription rose from 4.9x (2010–19) to 28x
(2024–26), and the gain for the same demand roughly halved: 100x+ issues listed at a 75% median
gain in 2020–23 but 36.5% in 2024–26. Models frozen in 2023 over-predicted 2025 IPOs by 20+ points.
Relative-subscription features and recency weighting did not remove this bias.

## 3. Walk-forward: refit every quarter (the realistic setup)

Each quarter, the model is refit on every IPO that listed before (quarter start − 7 days).

| Model | MAE 2019–23 | MAE 2024–26 | Median AE 2024–26 | Spearman 2019–23 | Spearman 2024–26 |
|---|---|---|---|---|---|
| **Random forest** (chosen) | **16.13** | 19.52 | 12.13 | **0.76** | **0.71** |
| LightGBM | 16.23 | 20.92 | 12.21 | 0.75 | 0.68 |
| Same-bucket median | 17.27 | **17.26** | 11.83 | 0.70 | 0.67 |
| Ridge | 18.69 | 20.08 | 15.84 | 0.73 | 0.65 |
| Median of all IPOs | 26.70 | 19.06 | 9.73 | 0.03 | −0.17 |

MAE by year (random forest vs same-bucket median): 2024 21.7 vs 22.2, **2025 19.5 vs 14.5**,
2026 11.2 vs 11.7. The gap comes from 2025.

**Honest reading:**
- The random forest was chosen on 2019–2023 and is the best model there on every metric.
- Out of sample, it **ranks IPOs best** (Spearman 0.71), which is what an apply-or-skip decision needs.
- It does **not** beat the simple same-bucket lookup on absolute error in 2024–2026, because 2025
  listed lower across the board than any history suggested.
- A rolling bias correction (adding the recent median error) was tested and made 2019–2023 worse,
  so it was not used.

## 4. The 80% range

LightGBM quantile models (P10, P50, P90), refit quarterly, then widened by **rolling conformal
calibration**: each new range is widened by the 80th-percentile miss distance of the last 60 IPOs.

| Period | Raw P10–P90 coverage | Calibrated coverage | Avg width (pp) |
|---|---|---|---|
| 2019–2023 | 67% | 78% | 48 |
| 2024–2026 | 56% | **79%** | 57 |

The 80% target was fixed up front, not tuned. The calibrated range does what it says out of sample.

## 5. What drives predictions (SHAP, final random forest)

Mean |SHAP| in percentage points: total subscription 8.9, QIB 5.4, HNI 2.8, retail 1.8, recent
IPO count 1.1, issue size 0.8, QIB vs retail 0.8, NIFTY 3-month return 0.8, India VIX 0.7.

A crowded IPO calendar (many IPOs in the last 90 days) pushes predictions down: investors'
money and attention are spread thin.

## Final models (used by the app)

Refit on all 634 IPOs and saved to `models/deploy.pkl`: the random forest for the expected gain,
and the quantile set plus the latest conformal margin (6.43 pp) for the 80% range.
