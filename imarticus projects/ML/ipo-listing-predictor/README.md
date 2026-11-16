# IPO Listing Day Predictor

Predicts an Indian mainboard IPO's listing-day gain the moment subscription closes, before it lists.
It gives an expected gain, a calibrated 80% range, an Apply/Skip call and the reasons behind it,
and it was backtested the way a retail investor would actually use it: one lot per IPO, with the
allotment lottery.

## Results at a glance

| | |
|---|---|
| Data | 634 mainboard IPOs, Jan 2010 – May 2026, listing prices cross-checked against the NSE open (95% agree) |
| Testing | Tuned on 2010–2023 with yearly folds; evaluated walk-forward (refit every quarter); 2024–2026 never used to choose anything |
| Ranking quality, 2024–26 | Spearman 0.71 (best of all models; simple subscription lookup 0.67) |
| 80% range, 2024–26 | Actual gain fell inside the range for 79% of IPOs |
| Backtest, 2024–26 | Following the model: ₹30,588 expected profit vs ₹24,506 applying to every IPO (bootstrap 95% interval for the difference ₹1,241 to ₹11,978) |
| Forward test, Jun–Nov 2026 | 78 IPOs collected after the model was frozen, scored once: Spearman 0.72, 80% range covered 87%, model ₹13,781 vs ₹12,064 apply-all vs ₹8,122 for the 30x rule ([report](reports/forward_test.md)) |
| Honest limit | A simple subscription-bucket lookup matched or beat the model on exact-gain error in both test periods (2024–26: 17.3 vs 19.5 pp; forward: 14.5 vs 15.4 pp). The model's value is ranking and the Apply/Skip call, not the exact number |

Full write-ups: [data audit](reports/data_audit.md) · [EDA findings](reports/eda_findings.md) ·
[model results](reports/model_results.md) · [backtest](reports/backtest_results.md)

## What makes it more than a notebook

- **Real, traceable data.** Every raw file is logged with its source, time and SHA-256 in
  `data/raw/manifest.json`. Kaggle's listing gains are recomputed from exchange prices, after
  undoing Yahoo's split/bonus adjustments (IRCTC's ₹626 listing shows up as ~₹125 otherwise).
- **No look-ahead.** Market features stop 7 days before listing; tuning folds keep a 7-day gap;
  a test checks that adding later IPOs never changes an earlier IPO's features.
- **A failure, found and explained.** A model frozen in 2023 lost to a simple lookup on 2024–26.
  The cause was subscription inflation (median IPO 5x → 28x, gain per unit of demand halved),
  which is why the final setup refits quarterly.
- **Calibrated uncertainty.** Quantile models were overconfident (56–67% coverage); rolling
  conformal calibration brought the 80% range to 78–79%.
- **Money, not just metrics.** The "apply if 30x+ subscribed" rule has the best hit rate (90%) and
  the worst profit, because hot IPOs almost never allot to retail.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt          # or requirements-lock.txt for the exact versions used
python -m src.pipeline                   # download data, build features, tune, evaluate, backtest
streamlit run app/streamlit_app.py
```

`python -m src.pipeline --no-download` rebuilds everything from the files already in `data/raw/`.
Seeds are fixed, so a rebuild reproduces the same numbers. Tests: `pytest -q`.

Notebooks (`notebooks/01_eda`, `02_modeling`, `03_backtest`) read the pipeline's outputs and explain them;
rerun one with `jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb`.

## The app

- **Predict:** enter the final-day subscription (or pick a past IPO). Shows expected gain, the 80%
  range, Apply/Skip, allotment odds, SHAP reasons and the most similar past IPOs. For a past IPO
  it also shows what the walk-forward model said before that IPO listed.
- **Explore:** every IPO, filterable by year and subscription.
- **Backtest:** strategies compared, with a threshold slider.
- **Model card:** data, testing, accuracy and limitations.

NIFTY and India VIX are fetched live. The IPO history ends in May 2026, so for a live call enter
the recent IPO count and average gain under *Market context*.

## Forward test on IPOs after May 2026

The Kaggle file stops at 14 May 2026. The 78 IPOs from June to November 2026 in
`data/manual/research/` were researched from news and broker pages after the model was frozen.
Every row keeps two source links; 87 of 88 reported listing prices matched the NSE open within 3%,
and the 10 rows with conflicting sources or a price mismatch are kept in the file but not used.
`python -m src.data.new_ipos_merge data/manual/research` rebuilds `data/manual/new_ipos.csv`.

The forward test also writes `models/deploy_live.pkl` and `data/processed/ipo_features_live.csv`:
the same frozen settings refit on all 712 IPOs, which the app uses so its recent-IPO features are current.

To add more IPOs later:

1. `python -m src.data.new_listings` writes `data/manual/new_ipos_template.csv`, pre-filled from
   official sources: NSE's listed-company file (symbol, name, listing date) and the listing-day
   open from Yahoo. NSE's 17 Aug 2026 bulk addition of ~150 old BSE companies is left out.
2. Save it as `data/manual/new_ipos.csv`. For each row, mark `is_mainboard_ipo` yes/no (demergers
   and migrations are not IPOs) and fill offer price, issue size and final-day QIB/HNI/retail/total
   subscription from the NSE or BSE bid details page, with that page in `source_url`.
3. `python -m src.forward_test` validates every row (for example, total subscription must lie
   between the category figures), predicts walk-forward with the settings frozen on 2010–2023, and
   writes `reports/forward_test.md`. Nothing is re-tuned, and the main pipeline's outputs are untouched.

## Data sources

| Need | Source |
|---|---|
| IPO list, issue size, QIB/HNI/RII subscription, listing gain | Kaggle: [IPO Data India 2010–2026](https://www.kaggle.com/datasets/karanammithul/ipo-data-india-2010-2025) |
| Symbol, ISIN, listing date, mainboard vs SME | NSE `EQUITY_L.csv` and `SME_EQUITY_L.csv` |
| Listing-day prices | Yahoo Finance (`<SYMBOL>.NS`), split-restored |
| Market mood | Yahoo Finance: NIFTY 50 (`^NSEI`), India VIX (`^INDIAVIX`) |

Rules: raw files are never edited; mainboard only (SME, REITs, InvITs and FPOs excluded); GMP is
not used (unofficial, and a proxy for the target); no scraping of sites whose terms forbid it.

## Project layout

```
data/raw/        untouched downloads + manifest.json
data/manual/     hand-filled data for IPOs after May 2026 (with source links)
data/interim/    joined and cross-checked tables
data/processed/  features, predictions, results
src/data/        downloads, matching, cross-check
src/features/    pre-listing features
src/models/      tuning, walk-forward evaluation, quantile range
src/backtest.py  strategy backtest with the allotment lottery
src/pipeline.py  runs everything in order
app/             Streamlit app
notebooks/       EDA, modelling, backtest walkthroughs
reports/         write-ups and figures
tests/           pytest (71 tests)
```

Not investment advice.
