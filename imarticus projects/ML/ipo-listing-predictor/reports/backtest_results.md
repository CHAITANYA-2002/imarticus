# Backtest results

Code: `src/backtest.py`. Walkthrough with charts: `notebooks/05_backtest.ipynb`.

## Setup

- A retail investor applies for one minimum lot (₹15,000) in each IPO a strategy picks and sells
  at the listing-day open.
- Decisions use walk-forward predictions only: each was made by a model refit on IPOs known by then.
- **Allotment lottery:** a one-lot application in an oversubscribed IPO gets shares with odds of
  about 1 / retail subscription. Expected profit per application = gain × ₹15,000 × odds.
- Every threshold was picked on 2019–2023 (by expected profit). 2024–2026 was scored once.

Thresholds picked on 2019–2023:

| Strategy | Picked rule |
|---|---|
| Model | apply if predicted gain ≥ −2% |
| Subscription cutoff | ≥ 0x (no cutoff beat applying to everything) |
| Same-bucket lookup | ≥ −10% (applies to everything) |

## Out-of-sample: 2024–2026 (202 IPOs)

| Strategy | Applied | Listed with gain | Avg gain | Expected allotments | Expected profit |
|---|---|---|---|---|---|
| Apply to every IPO | 202 | 67.8% | 16.2% | 62.7 | ₹24,506 |
| Only if 30x+ subscribed | 98 | 89.8% | 31.7% | 5.5 | ₹21,505 |
| **Follow the model** | 187 | 70.6% | 17.8% | 52.6 | **₹30,588** |

The model skipped 15 IPOs: 9 listed below their offer price, 1 flat, and 5 above it, all by less than 6%.

## Is the edge real? (paired bootstrap, 10,000 resamples)

| Model vs | Extra profit | 95% interval |
|---|---|---|
| Apply to every IPO | ₹6,082 | ₹1,241 to ₹11,978 |
| Tuned subscription cutoff | ₹6,082 | ₹1,427 to ₹12,089 |
| Only if 30x+ subscribed | ₹9,083 | −₹10,927 to ₹28,821 |

- **Against applying to everything,** the edge holds in over 99% of resamples.
- **Against the 30x rule,** the model earns more on average, but that difference is not statistically clear.

## Findings

1. **The 30x rule has the best hit rate and the worst profit.** Hot IPOs list high, but a retail
   applicant expects about 5 allotments in 98 tries.
2. **Subscription alone could not improve on applying to everything** in 2019–2023. The model's
   edge comes from combining subscription with market conditions, and it held out of sample.
3. **Threshold sensitivity.** On 2019–2023 the chosen −2% sits on a sharp, noisy peak: −4% to 0%
   beat applying to everything, +1% and above did not. On 2024–2026, anything from −5% to about +17%
   beat it, and around +2% would have been best. The chosen threshold was cautious, not lucky.

## Caveats

- 1 / retail subscription is an approximation of allotment odds.
- Brokerage, taxes and slippage are ignored (small for one lot, next to listing moves).
- One out-of-sample period of 202 IPOs.
