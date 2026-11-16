# Forward test: IPOs listed after the training data

78 mainboard IPOs listed 10 Jun 2026 – 04 Nov 2026. Settings, threshold and range method were frozen before these IPOs were added; scored once.

## Accuracy

| model | mae | median_ae | rmse | spearman |
|---|---|---|---|---|
| random_forest | 15.44 | 11.2 | 20.84 | 0.72 |
| bucket_median | 14.54 | 11.16 | 19.49 | 0.73 |
| median | 17.65 | 10.62 | 26.19 | -0.05 |

80% range coverage: **87%** (average width 50 pp).

## Backtest (one lot, allotment lottery)

| strategy | applied | hit_rate | avg_gain | expected_profit |
|---|---|---|---|---|
| Apply to every IPO | 78 | 78.2 | 18.5 | 12063.5 |
| Only if 30x+ subscribed | 46 | 91.3 | 29.9 | 8121.9 |
| Model (gain >= -2%) | 69 | 82.6 | 21.3 | 13781.0 |

Paired bootstrap (10,000 resamples of the IPOs):

| model vs | extra profit | 95% low | 95% high | resamples where model loses |
|---|---|---|---|---|
| Apply to every IPO | 1718 | -1988 | 6333 | 20% |
| Only if 30x+ subscribed | 5659 | -161 | 11773 | 3% |
