# EDA findings

Source: `notebooks/01_eda.ipynb`, run on 634 Indian mainboard IPOs (Jan 2010 – May 2026).
Target: listing-day gain = listing-day open / offer price − 1. Figures are in `reports/figures/`.

## 1. The target is skewed

| Statistic | Value |
|---|---|
| Median gain | 6.6% |
| Mean gain | 16.8% |
| Listed below offer price | 25.2% |
| Listed exactly flat | 6.3% |
| Gain above 15% | 34.2% |
| Gain above 50% | 11.5% |

Most IPOs list a few percent up, but a long tail of hot issues (up to +250%) pulls the mean far
above the median. **Implication:** predict a range with quantile models, and report MAE alongside RMSE.

## 2. The IPO market moves in waves

| Year | IPOs | Median gain | Listed below offer |
|---|---|---|---|
| 2018 | 24 | 1.4% | 45.8% |
| 2020 | 15 | 23.4% | 26.7% |
| 2023 | 59 | 17.1% | 10.2% |
| 2025 | 102 | 5.7% | 20.6% |
| 2026 (Jan–May) | 20 | −2.8% | 55.0% |

2026 so far is the coldest stretch in the data: more than half the IPOs listed below their offer
price. **Implication:** split by time (train on the past, test on the most recent years), never at random.

## 3. Subscription is the strongest signal

| Total subscription | IPOs | Median gain | Listed with a gain |
|---|---|---|---|
| under 1x | 26 | 0.0% | 38% |
| 1–3x | 177 | 0.0% | 41% |
| 3–10x | 104 | 3.9% | 62% |
| 10–30x | 90 | 9.9% | 70% |
| 30–100x | 164 | 23.3% | 92% |
| 100x+ | 73 | 56.6% | 100% |

Below 3x, an IPO is close to a coin toss. Above 30x, 92–100% listed with a gain. The popular
"apply if over 30x" rule holds up, so **it is the baseline the model must beat**, together with
"always predict the median".

## 4. Which investors matter (Spearman correlation with gain)

| Feature | Correlation |
|---|---|
| Total subscription | +0.71 |
| HNI / NII subscription | +0.67 |
| QIB subscription | +0.64 |
| Retail subscription | +0.58 |
| QIB relative to retail | +0.31 |
| NIFTY return, 3 months | +0.23 |
| NIFTY vs 200-day average | +0.20 |
| Recent IPOs' mean gain (90 days) | +0.12 |
| India VIX | −0.11 |
| Issue size | −0.02 |

HNI and QIB demand track gains more closely than retail demand. The subscription
features are strongly correlated with each other, so the model sees overlapping information.

## 5. Market mood adds a second, weaker signal

| Condition | IPOs | Median gain | Listed with a gain |
|---|---|---|---|
| NIFTY above its 200-day average | 518 | 7.9% | 70% |
| NIFTY below its 200-day average | 116 | 2.9% | 61% |
| Hot IPO market (top third of recent IPO gains) | 206 | 9.9% | 69% |
| Cold IPO market (bottom third) | 207 | 5.2% | 68% |

Among IPOs subscribed 100x+, the median gain was 57.3% in an up-trending market and 27.6% in a
down-trending one. That second figure comes from only 9 IPOs, so it is a hint rather than a finding.
Tree models can pick up this kind of interaction.

## 6. Issue size barely matters on its own

Median gain by issue-size quartile ranges only from 5.3% (largest) to 8.4% (mid-large). The largest
issues draw lower subscription (median 7.8x versus 20x for mid-sized issues), which explains most of
their lower gains.

## 7. Data caveat

The 135 targets without NSE verification are mostly from 2010–2011 (median year 2011), the IPOs
that have since been delisted or merged. Their median gain (5.2%) is close to the verified set (6.9%),
so they are kept, flagged by `target_source`, and can be dropped in a robustness check.

## Modelling decisions carried forward

1. Subscription on a log scale; keep total, QIB, HNI and retail plus the QIB-to-retail ratio.
2. Market mood features: NIFTY 1-month and 3-month return, distance from the 200-day average,
   India VIX, recent IPO gains.
3. Baselines: median gain, and the "over 30x" rule.
4. Time split: train 2010–2022, validate 2023, test 2024–2026.
5. Quantile models (P10 / P50 / P90) for a range, not just one number.
