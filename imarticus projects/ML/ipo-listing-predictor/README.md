# IPO Listing Day Predictor

Predicts an Indian mainboard IPO's **listing-day gain** the moment subscription closes, before it lists.
It gives an expected gain, a calibrated 80% range, a **SUBSCRIBE / AVOID** call and the reasons behind it,
and it was backtested the way a retail investor would really use it: one lot per IPO, with the allotment lottery.

Built on real data (Kaggle + NSE + Yahoo Finance), 634 IPOs from Jan 2010 to May 2026, plus a one-time forward
test on 78 IPOs from Jun to Nov 2026. Ends in a Streamlit app.

> **In simple words:** a company sells shares to the public for the first time (an IPO). People queue up to buy.
> On the first trading day the price can jump or fall. This project looks at how long the queue was, who stood in
> it, and how the market feels, and guesses that jump before day one. Then it checks whether following those
> guesses would really have made money.

---

## Contents

1. [The project in 1 minute](#1-the-project-in-1-minute)
2. [Results at a glance](#2-results-at-a-glance)
3. [Words you need](#3-words-you-need)
4. [Data: sources, cleaning, checking](#4-data-sources-cleaning-checking)
5. [EDA: seven findings](#5-eda-seven-findings)
6. [The no-peeking rule (data leakage)](#6-the-no-peeking-rule-data-leakage)
7. [Features](#7-features)
8. [The model](#8-the-model)
9. [Backtest: does it make money?](#9-backtest-does-it-make-money)
10. [Forward test on new IPOs](#10-forward-test-on-new-ipos)
11. [The app: Primary Desk](#11-the-app-primary-desk)
12. [How to run it](#12-how-to-run-it)
13. [Interview kit](#13-interview-kit)
14. [Limits and next steps](#14-limits-and-next-steps)
15. [Where is the code?](#15-where-is-the-code)

---

## 1. The project in 1 minute

| Step | What happened |
|---|---|
| **1. Collect** | 652 real IPOs from Kaggle, the NSE company list, listing prices from Yahoo Finance |
| **2. Clean and check** | Fixed names and types, dropped 18 rows, verified 499 listing prices against the NSE open |
| **3. Explore (EDA)** | Subscription is the strongest signal, but it has inflated over time |
| **4. Features** | 18 inputs, all known before listing (13 used by the final model) |
| **5. Model** | Random Forest, tuned with time-series cross-validation, retrained every quarter |
| **6. Money test** | Backtest with the allotment lottery, a bootstrap, a forward test, then the app |

**Say it in 1 minute:**

> "I built a model that predicts an Indian IPO's listing-day gain the moment subscription closes. I took 652 real
> IPOs from Kaggle, matched each one to its NSE symbol, and checked Kaggle's listing prices against the NSE open
> from Yahoo, after fixing Yahoo's split adjustment: 95% agreed. EDA showed subscription is the strongest signal,
> but it has inflated over time, so a model trained once and frozen failed on 2024 to 2026. I switched to
> retraining every quarter. The random forest ranks IPOs best (Spearman 0.71 on unseen years), though a simple
> subscription lookup is as good on the exact number, which I report openly. Its real value is the apply / skip
> call: following it, a retail investor's expected profit was ₹30,588 vs ₹24,506 for applying to everything, and a
> bootstrap shows that edge is real. A one-time forward test on 78 newer IPOs told the same story. It all runs in a
> Streamlit app that gives a Subscribe / Avoid call with a calibrated 80% range and the reasons."

---

## 2. Results at a glance

| | |
|---|---|
| **Data** | 634 mainboard IPOs, Jan 2010 – May 2026 (652 in the raw file); listing prices cross-checked against the NSE open, 95% agree |
| **Typical IPO** | Median listing gain 6.6%; 1 in 4 IPOs list below the offer price |
| **Testing** | Tuned on 2010–2023 with time-series cross-validation (year folds); evaluated walk-forward, refit every quarter; 2024–2026 never used to choose anything |
| **Ranking quality, 2024–26** | Spearman **0.71**, best of all models (subscription lookup 0.67) |
| **Average miss, 2024–26** | MAE 19.52 pp (subscription lookup 17.26 pp) |
| **80% range, 2024–26** | Actual gain fell inside the range for **79%** of IPOs |
| **Backtest, 2024–26** | Following the model: **₹30,588** expected profit vs ₹24,506 applying to every IPO; bootstrap 95% interval for the difference ₹1,241 to ₹11,978 |
| **Forward test, Jun–Nov 2026** | 78 IPOs collected after the model was frozen, scored once: Spearman 0.72, range covered 87%, model ₹13,781 vs ₹12,064 apply-all vs ₹8,122 for the 30x rule |
| **Honest limit** | A simple subscription-bucket lookup matched or beat the model on exact-gain error in both test periods (2024–26: 17.3 vs 19.5 pp; forward: 14.5 vs 15.4 pp). The model's value is ranking and the apply / skip call, not the exact number |

<details>
<summary><b>The whole project in eight numbers</b></summary>

| Number | Meaning |
|---|---|
| **634** | mainboard IPOs used, Jan 2010 to May 2026 (652 in the raw file) |
| **499** | listing prices verified against the NSE open (95% of the ones that could be checked) |
| **6.6%** | median listing gain of an IPO |
| **1 in 4** | IPOs list below the offer price (25.2%) |
| **18** | features, all known before the IPO lists (13 used) |
| **0.71** | ranking score (Spearman) on 2024 to 2026, years the model never saw |
| **₹30,588** | expected profit following the model, vs ₹24,506 applying to every IPO (2024 to 2026) |
| **78** | brand-new IPOs (Jun to Nov 2026) used as a final, one-time exam |

</details>

---

## 3. Words you need

IRCTC's IPO (October 2019) is used as the example everywhere in this README.

| Word | Plain English | Technical meaning | Example (IRCTC) |
|---|---|---|---|
| IPO | A company sells its shares to the public for the first time | Initial Public Offering | IRCTC, Oct 2019 |
| Offer price | The price you pay when you apply | Issue price (upper end of the price band) | ₹320 |
| Listing day | First day the share trades on the exchange | Listing date | 14 Oct 2019 |
| **Listing gain** | How much the price jumped (or fell) at the start of day one | (listing-day open ÷ offer price − 1) × 100. **This is the target** | opened ₹626 → **+95.6%** |
| Subscription | How many times more shares were asked for than offered | Bids ÷ shares offered, per investor group | 111.95x overall |
| QIB | Big professional investors: mutual funds, banks, foreign funds | Qualified Institutional Buyers | 108.8x |
| HNI / NII | Rich individuals applying for more than ₹2 lakh | Non-Institutional Investors | 354.5x |
| Retail (RII) | Normal people applying for up to ₹2 lakh | Retail Individual Investors | 14.9x |
| Lot | The smallest packet you can apply for | Minimum bid lot, ~₹15,000 | – |
| Allotment | Actually getting shares. When too many apply, it is a lottery | Odds ≈ 1 ÷ retail subscription | ~1 in 15 |
| NSE / BSE | India's two big stock exchanges | National / Bombay Stock Exchange | NSE open ₹626, BSE ₹644 |
| NIFTY 50 | Shows if India's 50 biggest companies are going up or down | Stock market index | – |
| India VIX | The market's "fear meter" | Volatility index | 17.8 a week before IRCTC listed |
| 200-DMA | Average price of the last 200 trading days; above it = good mood | 200-day moving average | NIFTY 1.2% below it |
| REIT / InvIT | Not a company: a trust that owns buildings or roads | Real estate / infrastructure investment trust | removed |
| FPO | An already listed company selling more shares | Follow-on Public Offer | Vodafone Idea 2024, removed |
| GMP | Unofficial "street price" before listing | Grey Market Premium | **not used**: unofficial, not verifiable |
| pp | Difference between two percentages | Percentage points | 101.3% vs 95.6% = 5.6 pp |

---

## 4. Data: sources, cleaning, checking

Notebook: [`notebooks/01_data_cleaning.ipynb`](notebooks/01_data_cleaning.ipynb)

> **In simple words:** I didn't trust one source. Kaggle has the subscription numbers but no stock symbol, and
> some of its listing prices looked wrong. So I found each IPO on NSE's own list and checked its price on Yahoo,
> like asking two friends the same question.

### 4.1 Sources

| Need | Source | Rows |
|---|---|---|
| IPO list, issue size, QIB / HNI / RII subscription, listing gain | Kaggle: [IPO Data India 2010–2026](https://www.kaggle.com/datasets/karanammithul/ipo-data-india-2010-2025) | 652 |
| Symbol, ISIN, listing date, mainboard vs SME | NSE `EQUITY_L.csv` (2,646) and `SME_EQUITY_L.csv` (584) | 3,230 |
| Listing-day prices | Yahoo Finance (`<SYMBOL>.NS`), split-restored | 547 |
| Market mood | Yahoo Finance: NIFTY 50 (`^NSEI`), India VIX (`^INDIAVIX`) | ~4,380 days each |
| New IPOs, Jun–Nov 2026 | Collected by hand from news and broker pages, two sources each | 127 candidates, 78 usable |

Rules: every raw file is logged with its source, date and SHA-256 in `data/raw/manifest.json`; raw files are never
edited; mainboard only; **GMP is not used** (unofficial, no checkable history); no scraping of sites whose terms forbid it.

### 4.2 Columns

| # | Raw column | Plain English | IRCTC | What I did |
|---|---|---|---|---|
| 1 | Date | Listing date | 2019-10-14 | → `listing_date`, real date |
| 2 | IPO_Name | Company name | Indian Railway Catering… | → `ipo_name`, fixed 69 cut-off names |
| 3 | Issue_Size(crores) | Money raised | 637.97 | → `issue_size_cr` |
| 4 | QIB | Institutions' subscription | 108.79 | → `sub_qib` |
| 5 | HNI | Rich individuals' subscription | 354.52 | → `sub_hni` |
| 6 | RII | Retail subscription | 14.94 | → `sub_rii` |
| 7 | Total | Overall subscription | 111.95 | → `sub_total` |
| 8 | Offer Price | Price paid in the IPO | 320 | → `offer_price` |
| 9 | List Price | First price on listing day | 644 (BSE open) | → `list_price`, checked against NSE |
| 10 | Listing Gain | Kaggle's listing gain % | 101.25 | → `listing_gain_pct`, checked against NSE |
| 11–13 | CMP(BSE), CMP(NSE), Current Gains | Today's price | 726.65 … | **dropped**: nobody knows today's price on listing day (**data leakage**) |

### 4.3 Cleaning

| # | What I did | How | Why |
|---|---|---|---|
| 1 | Renamed columns | `Issue_Size(crores)` → `issue_size_cr`, … | Short, consistent names |
| 2 | Fixed cut-off names | 69 names ended in "..."; removed it, kept a `name_truncated` flag | The name is needed to find the NSE symbol |
| 3 | Fixed datatypes | `pd.to_datetime`, numbers → `float` | Can't sort or average text |
| 4 | Duplicates | `df.duplicated().sum()` → **0** | – |
| 5 | Missing values | `missing_info(df)`: 3 IPOs miss subscription or listing gain → dropped | A row with no answer can't teach anything |
| 6 | Outliers: checked, **kept** | `out_info(df)` + boxplots; used log scale and MAE instead | 300x subscriptions and Hyundai's ₹27,859 cr IPO are real and matter most |
| 7 | Marked REITs / InvITs | By name or retail subscription = 0: 14 rows | Trusts have no retail quota |
| 8 | Dropped rows | 14 REITs / InvITs + 1 FPO + 3 missing = **18**; reason kept in `exclude_reason` | First-time company IPOs only; nothing disappears silently |
| 9 | Sorted and gave ids | By date, then name; `IPO0001`, `IPO0002`, … | Time order matters for everything later |

| Step | IPOs |
|---|---|
| Raw Kaggle file | 652 |
| − REITs / InvITs | −14 |
| − FPO (Vodafone Idea) | −1 |
| − missing subscription or listing gain | −3 |
| **Clean IPOs for the model** | **634** |

### 4.4 Finding each IPO's NSE symbol

| # | What I did | Why |
|---|---|---|
| 1 | Cleaned both names: lowercase, "&" → "and", removed Ltd / Limited / Pvt / the / IPO | "Larsen & Toubro Infotech Ltd." and "Larsen and Toubro Infotech Limited" become the same |
| 2 | Only looked at NSE companies listed within **±7 days** of the Kaggle date | Fewer candidates, fewer wrong matches |
| 3 | Scored name similarity with `rapidfuzz` (best of word-order, start-of-name, shared-words scores) | Handles word order and cut-off names |
| 4 | Accepted only a score of **85+** | Better no symbol than a wrong one |
| 5 | Fixed a bad match: "VMS Industries" matched "PI Industries"; shared words now count only if the first word also matches | Found by checking the lowest-score matches by eye |

Result: **547** IPOs matched, **105** not matched (mostly delisted, merged, or BSE-only).

### 4.5 The split problem

> **In simple words:** cut a pizza into 5 slices and each slice is worth one fifth. Companies do this with shares
> (a split or bonus). Yahoo then quietly divides all old prices too, so IRCTC's first-day price shows as ~₹125
> instead of ₹626.

For each IPO, the first-day prices were multiplied by every split ratio after the listing day (`split_factor`).
90 of the 545 IPOs with a price had a later split or bonus. **Before the fix only ~63% of prices agreed; after it, 95%.**

### 4.6 Checking Kaggle's numbers

| Difference between Kaggle's gain and the NSE-open gain | Label | IPOs |
|---|---|---|
| 2 pp or less | agree | 390 |
| 2 to 10 pp | close (Kaggle often used BSE's open) | 109 |
| more than 10 pp | disagree | 26 |
| **Agree or close, out of 525 checkable** | | **499 (95.0%)** |

Disagreements were checked by hand against news (CDSL ₹250, Paras Defence ₹475, Nazara ₹1,971, Bansal Wire ₹352):
**Kaggle was right**, Yahoo's split history was wrong.

| Case | Target used | Marked as | IPOs |
|---|---|---|---|
| agree or close | gain from the NSE open | `nse_open_yahoo` | 499 |
| disagree, not on NSE, no price | Kaggle's listing gain | `kaggle_unverified` | 135 |

**IRCTC before and after:** Kaggle listing price 644 (BSE open), gain 101.25% → NSE open 626 (split-corrected),
check = close (5.6 pp apart) → **target 95.6%**.

---

## 5. EDA: seven findings

Notebooks: [`02_eda.ipynb`](notebooks/02_eda.ipynb), [`03_feature_engineering.ipynb`](notebooks/03_feature_engineering.ipynb)

> **In simple words:** before building the guessing machine, I looked at the old IPOs with tables and charts to see
> what usually happens. Each finding became a decision for the model.

### Summary

| # | Question | What the data showed | Decision for the model |
|---|---|---|---|
| 1 | How do IPOs usually list? | Median **+6.6%**, mean 16.8%; **1 in 4** list below offer | MAE as main score; also predict an 80% range |
| 2 | Is every year the same? | 4 IPOs in 2013, 102 in 2025; median gain −2.8% to +23.4% | Split by **time**, never randomly |
| 3 | Longer queue = bigger jump? | Below 3x: under half list up; above 30x: **9 in 10** do | Log of subscription; **bucket median** as the baseline |
| 4 | Whose demand matters most? | Total 0.71, HNI 0.67, QIB 0.64, retail 0.58 (Spearman) | Keep all four groups + `qib_to_rii`; Ridge for the linear model |
| 5 | Do big IPOs list differently? | Size groups all ~5–8% median | Keep size (log); not a signal alone |
| 6 | Does market mood help? | NIFTY above 200-DMA: 7.9% vs 2.9% | Add NIFTY, VIX and recent-IPO features |
| 7 | Does 50x mean the same in 2012 and 2025? | Typical IPO 4.9x → 28x; 100x+ gain 75% → 36.5% | **Retrain every quarter** (walk-forward) |

### Finding 1: most IPOs list a little up; a few list hugely up

| Measure | Value |
|---|---|
| Median gain | 6.6% |
| Mean gain | 16.8% |
| Skew | 2.5 (long right tail) |
| Listed below offer price | 25.2% |
| Listed flat (0%) | 6.3% |
| Gain above 15% | 34.2% |
| Gain above 50% | 11.5% |

![Listing gain distribution](reports/figures/01_gain_distribution.png)

### Finding 2: IPOs come in waves

| Year | IPOs | Median gain | % listed below offer |
|---|---|---|---|
| 2010 | 74 | 5.4% | 21.6% |
| 2013 | 4 | 4.9% | 25.0% |
| 2020 | 15 | 23.4% | 26.7% |
| 2021 | 63 | 16.0% | 25.4% |
| 2023 | 59 | 17.1% | 10.2% |
| 2024 | 80 | 15.8% | 20.0% |
| 2025 | 102 | 5.7% | 20.6% |
| 2026 (to May) | 20 | −2.8% | 55.0% |

![IPOs and median gain by year](reports/figures/02_by_year.png)

### Finding 3: subscription is the strongest signal

> **In simple words:** 100 laddoos, 10,000 people in the queue. 9,900 go home empty-handed and will pay more
> the next day. That is why a long queue pushes the listing price up.

| Total subscription | IPOs | Median gain | % listed with a gain |
|---|---|---|---|
| less than 1x | 26 | 0.0% | 38% |
| 1 to 3x | 177 | 0.0% | 41% |
| 3 to 10x | 104 | 3.9% | 62% |
| 10 to 30x | 90 | 9.9% | 70% |
| 30 to 100x | 164 | 23.3% | **92%** |
| 100x and more | 73 | **56.6%** | **100%** |

![Subscription vs gain](reports/figures/03_subscription_vs_gain.png)
![Hit rate by subscription](reports/figures/04_hit_rate_by_subscription.png)

### Finding 4: rich individuals and institutions matter more than retail

| Column | Spearman with gain |
|---|---|
| Total subscription | 0.71 |
| HNI subscription | 0.67 |
| QIB subscription | 0.64 |
| Retail subscription | 0.58 |
| Offer price | 0.03 |
| Issue size | −0.02 |

The four subscription columns move together (0.64 to 0.93 with each other): **multicollinearity**. Trees don't mind;
the linear model uses Ridge.

### Finding 5: issue size alone says little

| Size group | Range (₹ cr) | Median gain | Median subscription |
|---|---|---|---|
| Smallest 25% | 23 – 257 | 6.3% | 6.3x |
| Small-mid | 260 – 583 | 7.2% | 21.0x |
| Mid-large | 583 – 1,204 | 8.4% | 20.3x |
| Largest 25% | 1,210 – 27,859 | 5.3% | 7.8x |

### Finding 6: market mood helps a little

| Situation | Median gain |
|---|---|
| NIFTY above its 200-day average | 7.9% |
| NIFTY below its 200-day average | 2.9% |
| Recent IPOs cold / normal / hot | 5.2% / 5.1% / 9.9% |

![Feature correlation](reports/figures/05_feature_correlation.png)
![Market mood](reports/figures/06_market_mood.png)

### Finding 7: subscription has inflated

| Subscription | 2010–2019 | 2020–2023 | 2024–2026 |
|---|---|---|---|
| less than 3x | −0.1% | 0.1% | −1.0% |
| 3 to 10x | 4.2% | 3.8% | 0.0% |
| 10 to 30x | 11.3% | 12.7% | 6.5% |
| 30 to 100x | 25.1% | 36.9% | 14.1% |
| 100x and more | 59.2% | **75.0%** | **36.5%** |
| Median subscription | 4.9x | 22.6x | 28.0x |

> **In simple words:** when everyone starts standing in every queue, a long queue means less. Queues got 6 times
> longer, and the jump for the same queue got about half as big. A model trained once will expect too much.

---

## 6. The no-peeking rule (data leakage)

> **In simple words:** in an exam you can't look at tomorrow's newspaper. The model may only use what a person could
> know **before** the IPO lists. If it peeks at the future, it looks clever in testing and fails in real life.

| Day | What happens | For the model |
|---|---|---|
| **−7 (cutoff)** | – | Last day of market data the model may use |
| −6 to −4 | IPO open for applications (3 working days) | – |
| −3 | Applications close, subscription known | The model makes its call |
| **0** | Listing day | The answer. Never an input |

**Why 7 days?** Since Dec 2023 an IPO lists 3 working days after applications close (T+3); before that the gap was up
to 6 days. 3 working days can be 5–6 calendar days with a weekend or holiday, so 7 calendar days puts the cutoff before
applications close for every IPO. Small loss of signal, but no future information can slip in.

**Every guard against leakage:**

| # | What I did | What it stops |
|---|---|---|
| 1 | Market data only up to the cutoff, 7 days before listing | Seeing the market around listing day |
| 2 | Dropped CMP (BSE), CMP (NSE), Current Gains | Using today's price |
| 3 | "Recent IPOs" counts only IPOs listed before the cutoff | Seeing how later IPOs did |
| 4 | 7-day gap between training and validation in every fold | A test IPO's neighbour sitting in training |
| 5 | Walk-forward: each quarter predicted by a model trained only on earlier IPOs | Any guess made with later results |
| 6 | Missing values filled inside the pipeline, from training rows only | Test data leaking through the fill value |
| 7 | Automated test: adding later IPOs never changes an earlier IPO's features | Future data creeping into past rows |

---

## 7. Features

Notebook: [`03_feature_engineering.ipynb`](notebooks/03_feature_engineering.ipynb). 18 built, **13 used** by the final model.

| Group | Feature | Plain English | How it is made | IRCTC |
|---|---|---|---|---|
| The queue | `log_sub_total` | How long the whole queue was | log(1 + total) | 4.73 (111.95x) |
| | `log_sub_qib` | Institutions' queue | log(1 + QIB) | 4.70 |
| | `log_sub_hni` | Rich individuals' queue | log(1 + HNI) | 5.87 |
| | `log_sub_rii` | Retail queue | log(1 + retail) | 2.77 |
| | `qib_to_rii` | Professionals keener than retail? | log QIB − log retail | 1.93 |
| | `fully_subscribed` | At least 1x? | 1 / 0 | 1 |
| The issue | `log_issue_size` | How big the IPO was | log(₹ crore) | 6.46 |
| | `log_offer_price` | Price of one share | log(offer price) | 5.77 |
| Queue vs last year | `sub_total_vs_recent` | Longer than usual for its time? | log sub − median log sub of IPOs in the 365 days before the cutoff (needs 5+) | 3.69 |
| | `sub_qib_vs_recent`, `sub_hni_vs_recent` | Same for QIB, HNI | same | 3.29, 4.88 |
| Market mood (at cutoff) | `nifty_ret_1w`, `_1m`, `_3m` | Market up last week / month / 3 months? | % change over 5 / 21 / 63 trading days | −3.35%, +2.60%, −6.63% |
| | `nifty_vs_200dma` | Long-term mood | % above / below 200-day average | −1.15% |
| | `vix` | How scared is the market? | India VIX close | 17.83 |
| Recent IPOs (90 days before cutoff) | `recent_ipo_count` | How many listed recently | count | 3 |
| | `recent_ipo_mean_gain` | Did they do well? | average listing gain | 3.90% |

**Used by the final model (13):** `log_sub_qib, log_sub_hni, log_sub_rii, log_sub_total, qib_to_rii, log_issue_size,
log_offer_price, nifty_ret_1m, nifty_ret_3m, nifty_vs_200dma, vix, recent_ipo_mean_gain, recent_ipo_count`.
The 3 "vs recent" features were tried and did not help on validation; `fully_subscribed` and `nifty_ret_1w` were built but not used.

**Why log?** Queues go from 1x to 300x+. A log ruler puts 1x → 0.7, 10x → 2.4, 100x → 4.6, 300x → 5.7, so every size gets a fair say.

**Missing values:** `recent_ipo_mean_gain` (12, no IPO in the 90 days) and `sub_*_vs_recent` (10, fewer than 5 IPOs
in the year) are filled with the median **inside the model pipeline**, so the median comes from training data only.

---

## 8. The model

Notebook: [`04_modeling.ipynb`](notebooks/04_modeling.ipynb) (scripts: `src/models/train.py`, `walk_forward.py`, `evaluate.py`)

> **In simple words:** the model is a student. Old IPOs are practice questions with answers. It practises on old
> years, then sits an exam on newer years it has never seen. If it only does well on practice questions, it just
> memorised them.

### 8.1 The model in one table: simple words and the technical name

| # | Step | In simple words | Technical name (say this) | In the project |
|---|---|---|---|---|
| 1 | The job | Look at the subscription and guess the listing gain in % | **Regression** | Target `target_gain_pct` |
| 2 | Splitting | Learn from old IPOs; hide the newest for the final test | **Time-based train-test split**, hold-out test | 2010–23: 432 IPOs · 2024–26: 202 IPOs |
| 3 | Practice tests | Learn up to 2018, test 2019; … five tests, 7-day gap | **Time-series cross-validation** (expanding window) | `year_folds()` |
| 4 | What to beat | "Median gain of past IPOs in the same subscription group" | **Baseline models** | `MedianModel`, `BucketMedian` |
| 5 | Models tried | Straight line / 400 trees that vote / trees built one after another | **Ridge, Random Forest, LightGBM** | `make_model()` |
| 6 | Problem 1 | Miss of ~4 on practice years, ~15 on new years | **Overfitting** | `time_eval()` |
| 7 | Fix 1 | Smaller trees, few settings | **Regularization + hyperparameter tuning** (grid search) | `max_depth=8`, `min_samples_leaf=5`, 94 combos |
| 8 | Problem 2 | Trained once and left alone, it failed on 2024–26 | **Concept drift** (subscription inflation) | RF 22.03 vs bucket median 17.94 |
| 9 | Fix 2 | Re-teach every 3 months with the newest IPOs | **Walk-forward validation**, quarterly refit | `walk_forward()` |
| 10 | Choosing | Smallest miss on 2019–23 | **Model selection** without the test set | Random Forest 16.13 |
| 11 | Judging | Average miss + right order | **MAE + Spearman rank correlation** | MAE 19.52, Spearman 0.71 |
| 12 | Range | Bad case and good case that catch ~8 in 10 | **Quantile regression + conformal calibration** | coverage 79% |
| 13 | Reasons | What pushed each guess up or down | **SHAP** | top: total subscription |
| 14 | Final | Re-trained once on every IPO, used by the app | **Final refit** | Random Forest on 712 IPOs |

### 8.2 Every decision: the options, what I chose, and why

| # | Decision | Options I had | Chosen | Why |
|---|---|---|---|---|
| 1 | Kind of problem | Classification (apply / skip) · Regression | **Regression** | A number gives both the expected gain and a ranking; apply / skip comes from it with a threshold |
| 2 | Train / test split | Random `train_test_split` · time split | **Time split**: 2010–23 dev, 2024–26 hold-out | IPOs come in waves; random would learn from 2025 to predict 2019 |
| 3 | Validation | `KFold(shuffle=True)` · `TimeSeriesSplit` · year folds | **Time-series CV by year + 7-day gap** | KFold leaks the future; `TimeSeriesSplit` cuts by row count, not years, and its gap counts rows, not days |
| 4 | What to beat | No baseline · median · bucket median | **Both baselines** | ML must beat what an investor does by eye (MAE 17.21) |
| 5 | Models | Ridge · Random Forest · LightGBM | **All three compared** | From simple to strong, same folds |
| 6 | Overfitting (train 3.70 vs valid 14.88) | No limit · large grid · limited trees + small grid | **`max_depth=8`, `min_samples_leaf=5`, 94 combos** | Gap shrank to 7.02 vs 15.39; small grid = less chance of a lucky winner. Honest note: the no-limit forest was slightly better on valid (14.88), a next step to test |
| 7 | Features | +3 "vs last year" · down-weight old years · 13 base | **13 base** | Both extras did not lower validation error |
| 8 | Train once or retrain? | Freeze at end of 2023 · retrain every quarter | **Retrain every quarter** | Frozen model lost to the bucket median on 2024–26 (22.03 vs 17.94): concept drift |
| 9 | Final model | Ridge 18.69 · LightGBM 16.23 · Random Forest 16.13 | **Random Forest** | Lowest walk-forward MAE on 2019–23, chosen before looking at 2024–26 |
| 10 | Main score | RMSE / R² · MAE · Spearman | **MAE + Spearman** | A few 200% IPOs dominate RMSE; apply / skip is a ranking question |
| 11 | Uncertainty | One number · raw quantile range (56–67%) · quantile + conformal | **Quantile LightGBM + rolling conformal** | An "80% range" must really catch ~80%: 79% after calibration |
| 12 | Explanations | Feature importance (overall) · SHAP (per IPO) | **SHAP** (importance kept as a check) | The app needs a reason for each IPO |

### 8.3 Validation: time-series cross-validation (it is not KFold)

Its name is **time-series cross-validation** with an **expanding window**, also called **forward chaining**.
The scikit-learn version of the idea is `TimeSeriesSplit`; here it is written by hand so each fold is one calendar year with a 7-day gap.

```python
def year_folds(d):
    for year in range(2019, 2024):
        cutoff = pd.Timestamp(year, 1, 1) - pd.Timedelta(days=7)
        yield d.index[d["listing_date"] < cutoff], d.index[d["year"] == year]
```

| Test year | Learnt from (IPOs) | Tested on (IPOs) |
|---|---|---|
| 2019 | 240 (up to 25 Dec 2018) | 16 |
| 2020 | 255 | 15 |
| 2021 | 271 | 63 |
| 2022 | 331 | 39 |
| 2023 | 371 | 59 |

The training set grows every year (the "expanding window"). The same folds are used by `time_eval()` (train vs valid
table, in the style of the class helper `regression_eval`) and by `cv_predict()` (tuning the 94 settings).

### 8.4 Why LightGBM?

| Job | Why LightGBM | Result |
|---|---|---|
| Candidate for the main guess | Often the strongest on tabular data; handles missing values itself; fast | Slightly behind Random Forest (16.23 vs **16.13**), not chosen |
| **The 80% range** | **Quantile loss is built in** (`objective="quantile"`); scikit-learn's Random Forest has no such option | Three models at alpha 0.1 / 0.5 / 0.9 + conformal → coverage **79%** |

### 8.5 What the scores mean

| Score | In simple words | Better when |
|---|---|---|
| **MAE** | Average miss in percentage points. Real +30%, guess +10% = miss of 20 | lower |
| Median miss | The miss on a typical IPO | lower |
| RMSE | Like MAE, but big misses count extra (squared) | lower |
| **R²** | How much better than "always guess the average". 1 = perfect, 0 = no better, below 0 = worse | higher |
| **Spearman** | Are IPOs in the right order, best to worst? 1 = perfect, 0 = random | higher |
| Within ±10 pp | % of IPOs where the guess was within 10 points | higher |
| Direction right | % where it correctly said "lists up" / "does not list up" | higher |

<details>
<summary><b>MAE and R² with a 3-IPO example</b></summary>

| IPO | Real gain | Guess | Miss |
|---|---|---|---|
| A | +30% | +20% | 10 |
| B | +10% | +12% | 2 |
| C | −5% | +5% | 10 |

- **MAE** = (10 + 2 + 10) ÷ 3 = **7.3** points.
- **R²:** the average real gain is 11.7%. Guessing 11.7% for all three gives squared misses totalling 617; the model's
  squared misses total 204. R² = 1 − 204 ÷ 617 = **0.67**: the model explains 67% of the ups and downs.
- Because R² squares the misses, a few IPOs that jump 150–250% swing it a lot. That is why **MAE** is the main
  error score and **Spearman** is used for the apply / skip decision.

</details>

### 8.6 Scorecard: every model, every number

Best number in each column in **bold**.

**1. First try and tuned: train vs valid** (average of the five year folds, 2019–23)

| Model | Train MAE | Valid MAE | Train R² | Valid R² | Reading |
|---|---|---|---|---|---|
| Median baseline | 16.06 | 27.26 | −0.10 | −0.34 | knows nothing |
| Bucket median baseline | 10.23 | 16.26 | 0.55 | 0.51 | the line to beat |
| Ridge, alpha 1 | 11.80 | 18.50 | 0.53 | 0.38 | small gap, but weak |
| Random Forest, no limit | 3.70 | **14.88** | 0.94 | **0.56** | memorises (3.7 vs 14.9) |
| LightGBM, 500 trees, 31 leaves | 3.85 | 15.85 | 0.92 | 0.50 | memorises (3.9 vs 15.9) |
| Ridge, tuned (alpha 30) | 11.64 | 18.39 | 0.51 | 0.41 | slightly better |
| **Random Forest, tuned (depth 8, leaf 5)** | 7.02 | 15.39 | 0.76 | **0.56** | gap shrunk to 7.0 vs 15.4 |
| LightGBM, tuned | 6.91 | 15.75 | 0.76 | 0.53 | gap shrunk to 6.9 vs 15.8 |

**2. Tuning: best setting of each model** (year folds 2019–23, 94 combinations)

| Model | Best setting | MAE | Median miss | RMSE | Spearman |
|---|---|---|---|---|---|
| **Random Forest** | depth 8, min leaf 5, 400 trees | **16.03** | **9.59** | **26.62** | **0.76** |
| LightGBM | 200 trees, 15 leaves, min child 25 | 16.45 | 9.73 | 27.07 | 0.74 |
| Bucket median | – | 17.21 | 10.12 | 27.95 | 0.71 |
| Ridge | alpha 30 | 18.71 | 11.61 | 29.32 | 0.73 |
| Median | – | 26.74 | 13.10 | 43.60 | −0.02 |

All winners used the 13 base features and no old-year down-weighting.

**3. Exam 1: frozen at the end of 2023, scored on 2024–26** (202 IPOs, the failed exam)

| Model | MAE | Median miss | RMSE | Spearman |
|---|---|---|---|---|
| Bucket median | **17.94** | 12.51 | **25.64** | **0.69** |
| Median | 18.98 | **9.30** | 32.12 | 0.00 |
| Ridge | 21.29 | 16.65 | 27.86 | 0.65 |
| Random Forest | 22.03 | 13.54 | 31.29 | **0.69** |
| LightGBM | 24.61 | 14.25 | 34.29 | 0.67 |

Why it failed: subscription inflation (Finding 7). The frozen model still expected 2021-style jumps.

**4. Walk-forward, retrained every quarter: 2019–23** (192 IPOs, used to choose the model)

| Model | MAE | Median miss | RMSE | R² | Spearman | Within ±10 pp | Direction right |
|---|---|---|---|---|---|---|---|
| **Random Forest** | **16.13** | **9.15** | **27.01** | **0.50** | **0.76** | **53.6%** | **77.1%** |
| LightGBM | 16.23 | 9.96 | 27.20 | **0.50** | 0.75 | 50.5% | 75.0% |
| Bucket median | 17.27 | 10.12 | 28.22 | 0.46 | 0.70 | 49.0% | 75.0% |
| Ridge | 18.69 | 12.01 | 29.31 | 0.42 | 0.73 | 45.8% | 70.8% |
| Median | 26.70 | 12.92 | 43.47 | −0.28 | 0.03 | 38.5% | 73.4% |

**5. Walk-forward, retrained every quarter: 2024–26** (202 IPOs, the final exam)

| Model | MAE | Median miss | RMSE | R² | Spearman | Within ±10 pp | Direction right |
|---|---|---|---|---|---|---|---|
| **Random Forest** (chosen) | 19.52 | 12.13 | 27.99 | 0.15 | **0.71** | 44.6% | 72.8% |
| LightGBM | 20.92 | 12.21 | 29.65 | 0.05 | 0.68 | 41.1% | 70.3% |
| Bucket median | **17.26** | 11.83 | **24.78** | **0.34** | 0.67 | 43.6% | **74.8%** |
| Ridge | 20.08 | 15.84 | 26.65 | 0.23 | 0.65 | 34.2% | 74.3% |
| Median | 19.06 | **9.73** | 31.97 | −0.10 | −0.17 | **51.5%** | 67.8% |

**6. Forward test: 78 new IPOs, Jun–Nov 2026** (scored once)

| Model | MAE | Median miss | RMSE | R² | Spearman | Within ±10 pp | Direction right |
|---|---|---|---|---|---|---|---|
| **Random Forest** | 15.44 | 11.20 | 20.84 | 0.21 | 0.72 | **48.7%** | 78.2% |
| Bucket median | **14.54** | 11.16 | **19.49** | **0.31** | **0.73** | 47.4% | **80.8%** |
| Median | 17.65 | **10.62** | 26.19 | −0.25 | −0.05 | **48.7%** | 78.2% |

![MAE by year](reports/figures/07_error_by_year.png)
![Predicted vs actual](reports/figures/08_pred_vs_actual.png)

> **Honest reading**
> - **2019–23** (where the model was chosen): Random Forest is best on every number.
> - **2024–26 and the forward test:** the simple bucket median is as good or better on most error numbers. The forest
>   is best on ranking in 2024–26 (Spearman 0.71), and ranking is what apply / skip uses: ₹30,588 vs ₹24,506.
> - **R² is low on new years** (0.15): a handful of 100–250% IPOs make it swing, so MAE and Spearman are the main scores.
> - **The median baseline** looks good on "median miss" only because many IPOs list near a small gain; it cannot rank
>   (Spearman ≈ 0). Its "direction right" is just the share that listed up, since it always guesses "up".

### 8.7 The 80% range

Three LightGBM quantile models (10th, 50th, 90th percentile) were too confident. **Rolling conformal calibration**
looks at how far the last 60 results fell outside their ranges and widens the next range by that much.

| Period | Inside the range, before | After calibration | Average width |
|---|---|---|---|
| 2019–23 | 67% | 78% | 48 pp |
| 2024–26 | 56% | **79%** | 57 pp |
| Forward test | – | **87%** | – |

![Range coverage](reports/figures/09_range_coverage.png)

### 8.8 What the model looks at (SHAP)

| Feature | Average push on the guess (mean \|SHAP\|, pp) |
|---|---|
| Total subscription | 8.85 |
| QIB subscription | 5.38 |
| HNI subscription | 2.76 |
| Retail subscription | 1.81 |
| IPOs in the last 90 days | 1.05 |
| Issue size | 0.82 |
| QIB vs retail | 0.80 |
| NIFTY 3-month return | 0.79 |
| India VIX | 0.67 |

Subscription drives the guess; market features adjust it by about 1 pp. This matches the EDA.

![SHAP importance](reports/figures/10_shap_importance.png)
![SHAP beeswarm](reports/figures/11_shap_beeswarm.png)

### 8.9 One real example: IRCTC (Oct 2019)

| What | Value |
|---|---|
| Bucket median guess (100x+ bucket) | +58.7% |
| Random Forest guess, made before listing | +48.9% |
| 80% range | +9.7% to +65.9% |
| Real listing gain | **+95.6%** |

The model correctly said "big jump, apply", but the real jump was bigger than the top of its range: one of the
~1 in 5 IPOs that fall outside an 80% range, which is what "80%" means.

### 8.10 What I paid attention to

| Care point | What I did |
|---|---|
| No peeking | Market data stops 7 days before listing; folds keep a 7-day gap; walk-forward trains only on earlier IPOs |
| Exam never used to choose | Settings, model, threshold and range method all chosen on 2019–23 |
| Outliers kept | Log scale and MAE instead of deleting hot IPOs |
| Overfitting checked | Train vs valid table before tuning; shallow trees chosen |
| Missing values | `SimpleImputer` inside each model pipeline |
| Simple baselines | Median and bucket median scored the same way |
| Failure reported | The frozen model's loss is shown, not hidden |
| Same results every run | Fixed seed (42); rebuilding from raw files gives the same data files |
| Notebook = pipeline | Notebooks and `python -m src.pipeline` produce the same numbers (checked file by file) |
| Tested code | 83 automated tests (`pytest`) |

---

## 9. Backtest: does it make money?

Notebook: [`05_backtest.ipynb`](notebooks/05_backtest.ipynb)

> **In simple words:** applying for an IPO is like buying a raffle ticket. If 15 people want each prize, you win
> 1 time in 15. A super-popular IPO may jump a lot, but you almost never get it. The best plan is not "only the
> hottest ones", it is "skip the ones likely to fall".

**Setup**

| | |
|---|---|
| Investor | Normal retail investor, 1 lot (~₹15,000) per IPO, sells at the listing-day open |
| Chance of getting shares | 1 ÷ retail subscription (100% if retail ≤ 1x) |
| Expected profit of one application | listing gain × ₹15,000 × chance of getting shares |
| Example | IRCTC: 95.6% × ₹15,000 = ₹14,344 if allotted; chance 1 in 14.94 → expected **₹960** |
| Fairness | Uses walk-forward guesses (made before listing); threshold chosen on 2019–23 only |

**Strategies**

| Strategy | Rule | Threshold (picked on 2019–23) |
|---|---|---|
| Apply to every IPO | always | – |
| Popular rule | only if 30x or more | – |
| Tuned subscription cutoff | subscription ≥ best cutoff | 0x (= everything) |
| Bucket median | bucket median ≥ best threshold | −10% (= everything) |
| **Follow the model** | **model's guess ≥ −2%** | **−2%** |

**Results on 2024–26**

| Strategy | Applications | Listed with a gain | Expected allotments | Expected profit |
|---|---|---|---|---|
| Apply to every IPO | 202 | 67.8% | 62.7 | ₹24,506 |
| Only if 30x+ | 98 | **89.8%** | 5.5 | ₹21,505 |
| **Follow the model** | 187 | 70.6% | 52.6 | **₹30,588** |

On 2019–23 (where the threshold was picked, so less fair): model ₹67,632 vs apply-all ₹57,367 vs 30x rule ₹34,679.

The 30x rule has the best hit rate and the **worst** profit: about 5 allotments from 98 applications.

![Strategy comparison](reports/figures/12_strategy_comparison.png)
![Cumulative profit](reports/figures/13_cumulative_profit.png)

**Is the edge real? Paired bootstrap, 10,000 resamples**

| Model vs | Extra profit | 95% range | Model loses in | Verdict |
|---|---|---|---|---|
| Apply to every IPO | ₹6,082 | ₹1,241 to ₹11,978 | 0.4% | **real edge** |
| Only if 30x+ | ₹9,083 | −₹10,927 to ₹28,821 | 18.5% | not proven |

**What did it skip?** In 2024–26 the model said AVOID to 15 IPOs: 9 listed below offer, 1 flat, 5 above (the best only
+5.6%). All 15 had low subscription (1.0x to 3.2x). Examples: ACME Solar (−13.1%), Godavari Biorefineries (−12.5%),
Afcons (−8.0%). It said SUBSCRIBE to 187; high-conviction calls (83 IPOs) listed up 95% of the time.

**Does it only work at exactly −2%?** On 2024–26 every threshold from −5% to about +17% beats applying to everything;
on 2019–23 anything from −4% to 0% does. The exact −2% should not be over-read.

![Threshold sensitivity](reports/figures/14_threshold_sensitivity.png)

---

## 10. Forward test on new IPOs

After the model was finished and locked, new IPOs kept coming. They were collected later and scored **once**; nothing was changed after seeing the result. Report: [`reports/forward_test.md`](reports/forward_test.md)

| Step | Count |
|---|---|
| Candidates: new listings, 2 Jun to 13 Nov 2026 | 127 |
| − not a mainboard IPO | −39 |
| − two sources disagreed | −9 |
| − reported listing price did not match the NSE open (within 3%) | −1 |
| **Usable IPOs (10 Jun to 4 Nov 2026)** | **78** |

| Strategy | Applications | Listed with a gain | Expected profit |
|---|---|---|---|
| Apply to every IPO | 78 | 78.2% | ₹12,064 |
| Only if 30x+ | 46 | 91.3% | ₹8,122 |
| **Follow the model** | 69 | 82.6% | **₹13,781** |

| Model vs | Extra profit | 95% range | Model loses in | Verdict |
|---|---|---|---|---|
| Apply to every IPO | ₹1,718 | −₹1,988 to ₹6,333 | 20% | not proven |
| Only if 30x+ | ₹5,659 | −₹161 to ₹11,773 | 3% | likely real |

Same story as 2024–26: best ranking (0.72), range caught 87%, model earned the most. Only 78 IPOs, so the edge over
"apply to everything" is not proven here.

---

## 11. The app: Primary Desk

`app/streamlit_app.py`, styled as an IPO research desk with a live NIFTY / India VIX bar and a ticker of recent listings.

| Page | What it shows | Question it answers |
|---|---|---|
| **Research Note** | Pick a past IPO or enter a new one → verdict, conviction, expected gain, bear and bull case (80% range), allotment odds, expected value of one lot, drivers for and against (SHAP), key risks, 5 most similar past IPOs. For a past IPO, the call made **before** it listed | Should I apply? |
| Market Monitor | Every IPO since 2010, filters, charts, full table | How is the IPO market doing? |
| Strategy Performance | Backtest for 2019–23, 2024–26 and the forward test; threshold slider; equity curve | Has following the desk paid off? |
| Methodology | Data, testing, scores, forward test, limits | Can I trust it? |

**How the verdict is decided**

| Condition | Verdict | Conviction |
|---|---|---|
| expected gain below −7% | AVOID | High |
| −7% to below −2% | AVOID | Low |
| ≥ −2% and even the bad case (P10) is above 0 | SUBSCRIBE | High |
| ≥ 10% (bad case below 0) | SUBSCRIBE | Medium |
| −2% to below 10% (bad case below 0) | SUBSCRIBE | Low |

The app's model is the same configuration refit on all **712** IPOs up to 4 Nov 2026 (634 + 78).

**Demo, step by step**

1. **Research Note** → pick **IRCTC** → SUBSCRIBE (High), range, and the "Track record" line (call before listing vs what happened).
2. Scroll to **Investment thesis**: long QIB and HNI queues support it; weak market weighs a little.
3. Pick **ACME Solar** → **AVOID**: 2.8x subscription pulled the guess down; it really listed −13.1%.
4. **Strategy Performance** → the model's line above "apply to every IPO", the 30x rule's low line.
5. **Methodology** → forward test and honest limits.

The first load after a restart takes 20–30 seconds (libraries, model, live market data).

---

## 12. How to run it

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt          # or requirements-lock.txt for the exact versions used
python -m src.pipeline                   # download data, build features, tune, evaluate, backtest
streamlit run app/streamlit_app.py       # open http://localhost:8501
```

- `python -m src.pipeline --no-download` rebuilds everything from the files already in `data/raw/`.
- Seeds are fixed, so a rebuild reproduces the same numbers.
- Tests: `pytest -q` (83 tests).

**Notebooks** (run from the `notebooks/` folder, in order; they write the same files as `src/`):

| Notebook | What it does | Saves |
|---|---|---|
| `01_data_cleaning` | Load Kaggle, clean, match NSE symbols, check prices against Yahoo | `data/interim/ipos_verified.csv` |
| `02_eda` | Target, years, subscription, investor groups, size | figures 01–04 |
| `03_feature_engineering` | Market and recent-IPO features as of 7 days before listing | `data/processed/ipo_features.csv` |
| `04_modeling` | Baselines, time-series CV tuning, frozen failure, walk-forward, range, SHAP | results, `models/best_configs.json` |
| `05_backtest` | One lot per IPO with the allotment lottery, thresholds, bootstrap | `models/decision_rule.json` |

<details>
<summary><b>Adding newer IPOs later</b></summary>

1. `python -m src.data.new_listings` writes `data/manual/new_ipos_template.csv`, pre-filled from NSE's listed-company
   file (symbol, name, listing date) and the listing-day open from Yahoo. NSE's 17 Aug 2026 bulk addition of ~150 old
   BSE companies is left out.
2. Save it as `data/manual/new_ipos.csv`. For each row mark `is_mainboard_ipo` yes / no (demergers and migrations are
   not IPOs) and fill offer price, issue size and final-day QIB / HNI / retail / total subscription from the NSE or BSE
   bid details page, with that page in `source_url`.
3. `python -m src.forward_test` validates every row, predicts walk-forward with the settings frozen on 2010–2023, and
   writes `reports/forward_test.md`. Nothing is re-tuned.

`python -m src.data.new_ipos_merge data/manual/research` rebuilds `data/manual/new_ipos.csv` from the research files.
The forward test also writes `models/deploy_live.pkl` and `data/processed/ipo_features_live.csv`, which the app uses.

</details>

---

## 13. Interview kit

<details>
<summary><b>Why not a normal random train_test_split?</b></summary>

IPOs come in waves and subscription has inflated. A random split would train on 2025 and test on 2019, which leaks the
future. I split by time: tune on 2010–2023, test on 2024–2026, and retrain every quarter.
</details>

<details>
<summary><b>What is your validation method called?</b></summary>

Time-series cross-validation with an expanding window (forward chaining). For each year 2019–2023 the model trains only
on IPOs before that year, with a 7-day gap, and is tested on that year. Same idea as `TimeSeriesSplit`, written by hand
as `year_folds()` so each fold is one calendar year.
</details>

<details>
<summary><b>Why didn't you use the class helper regression_eval?</b></summary>

It uses `KFold(shuffle=True)`, which mixes years. I kept the same idea (one table of train vs valid MAE and R²) but with
year folds and a 7-day gap: `time_eval()`.
</details>

<details>
<summary><b>Why not use GMP?</b></summary>

It is unofficial, quoted by informal dealers, with no reliable, checkable history. Everything I used comes from official
or checkable sources.
</details>

<details>
<summary><b>Your model loses to a simple lookup on MAE. So why use it?</b></summary>

On the exact number the bucket median is as good or slightly better (17.3 vs 19.5 pp in 2024–26). But the model ranks
IPOs better (Spearman 0.71 vs 0.67), and apply / skip is a ranking question. In the backtest the model made more
expected profit than every simple rule. I report both.
</details>

<details>
<summary><b>Is your model overfitting?</b></summary>

I checked with a train vs valid table. Untuned trees missed by ~4 pp on training years and ~15 on new years, so I
limited depth and leaf size (~7 vs ~15). Every score I quote is on years the model never saw, and a forward test on 78
later IPOs gave similar results (Spearman 0.72).
</details>

<details>
<summary><b>How do you know there is no data leakage?</b></summary>

Market data stops 7 days before listing; CMP / current-gain columns were dropped; folds keep a 7-day gap; walk-forward
only trains on earlier IPOs; missing values are filled inside the pipeline; and an automated test checks that adding
later IPOs never changes an earlier IPO's features.
</details>

<details>
<summary><b>You must apply before subscription closes. How can the model use the final subscription?</b></summary>

By the evening of the last day the numbers are almost final, and that is when most people apply. The market data is
from 7 days earlier, so it is safely in the past either way.
</details>

<details>
<summary><b>Why MAE and not R² or RMSE?</b></summary>

The target has a long right tail: a few IPOs jump 150–250%. RMSE and R² square the misses, so those few dominate. MAE is
the plain average miss. For the decision I use Spearman, which measures ranking.
</details>

<details>
<summary><b>Why Random Forest, and where did you use LightGBM?</b></summary>

Random Forest had the lowest walk-forward MAE on 2019–2023 (16.13 vs 16.23), chosen before looking at 2024–26. LightGBM
is used for the 80% range because quantile loss is built in: three models at alpha 0.1 / 0.5 / 0.9, then conformal
calibration to 79% coverage.
</details>

<details>
<summary><b>Why did you keep outliers?</b></summary>

They are real IPOs (300x subscriptions, ₹20,000+ crore issues) and the most important to get right. I used a log scale
and MAE so they don't dominate.
</details>

<details>
<summary><b>What is conformal calibration?</b></summary>

The quantile models said "80% range" but caught only 56–67%. Rolling conformal looks at how far the last 60 results fell
outside their ranges and widens the next range by that amount: 78–79% after, 87% in the forward test.
</details>

<details>
<summary><b>How is the allotment lottery handled?</b></summary>

Expected profit = gain × ₹15,000 × (1 ÷ retail subscription). That is why the 30x rule has the best hit rate (89.8%) but
the worst profit: about 5 allotments from 98 applications.
</details>

<details>
<summary><b>Is the profit difference just luck?</b></summary>

Paired bootstrap, 10,000 resamples: against applying to everything, the extra ₹6,082 has a 95% range of ₹1,241 to
₹11,978 (model loses in 0.4%). Against the 30x rule it is not proven.
</details>

<details>
<summary><b>Where does the model go wrong?</b></summary>

Example: Shree Ram Twistex, 44x total subscription but only 3.9x from institutions (QIB); demand came from HNI (220x).
The model guessed +35%; it listed −34.6%. The model has no company financials or valuation data, only subscription and
market data.
</details>

<details>
<summary><b>What would you do next?</b></summary>

Test "no depth limit" in the forest's grid; add a QIB-share feature and company financials / valuation from the offer
document (RHP); use actual allotment ratios instead of 1 ÷ subscription; keep adding new IPOs. Every change would be
chosen on 2019–2023 only, to avoid overfitting.
</details>

**Easy-to-get-wrong numbers**

| Number | Correct | Common mistake |
|---|---|---|
| IPOs used | **634** (652 raw, 18 removed) | saying 652 |
| Verified targets | **499** verified, 135 Kaggle-only; 95% of 525 checkable agree | "all prices verified" |
| Target | listing-day **open** vs offer price | closing price |
| Typical gain | median **6.6%**, mean 16.8% | "IPOs gain 17% on average" |
| Exam period | **2024 to May 2026**, 202 IPOs | not saying it ends in May |
| MAE 2024–26 | model **19.52**, bucket median 17.26 | claiming the model has the lowest error |
| Spearman 2024–26 | **0.71** (forward 0.72) | calling it accuracy |
| Range coverage | **79%** (forward 87%) | "80% accurate" |
| Backtest profit | **₹30,588** vs ₹24,506 (expected, 202 IPOs, 1 lot each) | "I made ₹30,000" |
| Threshold | apply if the guess is **≥ −2%** | "≥ 0%" |
| Features | 18 built, **13** used | "18 used" |
| Tests | **83** automated tests | – |

---

## 14. Limits and next steps

| Limit | What it means |
|---|---|
| Exact gain is hard | Average miss ~16–20 pp; a subscription lookup is as good on the exact number. The value is ranking |
| The market keeps changing | Subscription has inflated; the model adapts only as new IPOs are added and it is retrained |
| No company information | No financials, valuation, sector or offer-for-sale share; big company-specific drops are missed |
| Allotment odds are estimated | 1 ÷ retail subscription is an approximation |
| Costs ignored | Brokerage, tax and slippage not included (small for 1 lot) |
| 135 targets unverified | Mostly 2010–11 IPOs no longer on NSE's list; kept with Kaggle's number, marked |
| History ends 4 Nov 2026 | Newer IPOs must be added for the "recent IPO" features to stay current |
| Not investment advice | A study project |

**Next steps (each chosen on 2019–23 only, then checked once on later data):** add "no depth limit" to the forest's
grid; a QIB-share-of-demand feature; financials and valuation from the RHP; real allotment ratios; keep adding IPOs.

---

## 15. Where is the code?

| What | Notebook (step by step) | Script (used by the app) |
|---|---|---|
| Load, clean, match NSE, check prices | `notebooks/01_data_cleaning.ipynb` | `src/data/kaggle_ipo.py`, `nse.py`, `matching.py`, `market.py`, `listing_prices.py`, `audit.py` |
| EDA | `notebooks/02_eda.ipynb` | – |
| Features | `notebooks/03_feature_engineering.ipynb` | `src/features/build.py` |
| Models, tuning, walk-forward, range, SHAP | `notebooks/04_modeling.ipynb` | `src/models/train.py`, `walk_forward.py`, `evaluate.py` |
| Backtest | `notebooks/05_backtest.ipynb` | `src/backtest.py` |
| Forward test (Jun–Nov 2026) | – | `src/forward_test.py` → `reports/forward_test.md` |
| Everything in one go | – | `python -m src.pipeline` |
| App | – | `streamlit run app/streamlit_app.py` |
| Tests | – | `pytest -q` (83 tests) |
| Class helpers | `notebooks/useful_func.py` (`missing_info`, `out_info`) | – |

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
notebooks/       cleaning, EDA, features, modelling, backtest (01-05)
reports/         write-ups and figures
docs/            IPO_guide.html (the same content as a styled page)
tests/           pytest (83 tests)
```

Written reports: [data audit](reports/data_audit.md) · [EDA findings](reports/eda_findings.md) ·
[model results](reports/model_results.md) · [backtest](reports/backtest_results.md) · [forward test](reports/forward_test.md)

Not investment advice.
