# Data audit: Kaggle listing gains vs Yahoo Finance

Kaggle's listing gain is corroborated by the NSE open (within 10 pp) for **95.0%** of checkable IPOs (499 of 525).

Listing gain = listing-day open / offer price - 1. Yahoo back-adjusts history for splits and bonuses, so each bar is multiplied back by the split factor after the listing day. IPOs not on NSE's current list (delisted, merged, BSE-only) keep Kaggle's figure, marked unverified.

Where the two disagree by more than 10 pp, spot checks against the known NSE listing prices (CDSL 250, Paras Defence 475, Nazara 1,971, Bansal Wire 352) show Kaggle is right and Yahoo's split history is wrong or double-counted. Those rows therefore keep Kaggle's gain, marked unverified.

## Funnel

| Step | Count |
|---|---|
| IPOs in Kaggle file | 652 |
| Excluded (trusts, FPOs, missing values) | 18 |
| Kept for modelling | 634 |
|   matched to a current NSE symbol | 544 |
|   with a Yahoo price on the listing day | 525 |
|   agree within 2 pp | 390 |
|   within 10 pp (likely BSE vs NSE open) | 109 |
|   disagree by more than 10 pp | 26 |
| Target from NSE open (verified) | 499 |
| Target from Kaggle (unverified) | 135 |

## Verdict by listing year (kept IPOs)

| listing_date | agree | bar_not_listing_day | close | disagree | no_price | not_on_nse |
|---|---|---|---|---|---|---|
| 2010 | 12 | 0 | 18 | 10 | 0 | 34 |
| 2011 | 6 | 0 | 6 | 3 | 0 | 24 |
| 2012 | 7 | 0 | 1 | 0 | 0 | 3 |
| 2013 | 2 | 0 | 1 | 0 | 0 | 1 |
| 2014 | 2 | 0 | 3 | 0 | 0 | 1 |
| 2015 | 13 | 0 | 2 | 1 | 0 | 3 |
| 2016 | 18 | 2 | 1 | 2 | 0 | 4 |
| 2017 | 25 | 4 | 5 | 1 | 0 | 1 |
| 2018 | 13 | 3 | 3 | 1 | 1 | 3 |
| 2019 | 12 | 1 | 2 | 0 | 0 | 1 |
| 2020 | 10 | 1 | 2 | 0 | 0 | 2 |
| 2021 | 40 | 1 | 17 | 3 | 0 | 2 |
| 2022 | 31 | 1 | 5 | 1 | 0 | 1 |
| 2023 | 46 | 0 | 9 | 1 | 0 | 3 |
| 2024 | 55 | 0 | 19 | 2 | 1 | 3 |
| 2025 | 82 | 4 | 11 | 1 | 0 | 4 |
| 2026 | 16 | 0 | 4 | 0 | 0 | 0 |

## Disagreements (largest first)

| ipo_id | ipo_name | symbol | offer_price | list_price | open | listing_gain_pct | yf_open_gain_pct | diff_pp | bar_on_listing_date |
|---|---|---|---|---|---|---|---|---|---|
| IPO0469 | Bansal Wire Industries Limited | BANSALWIRE | 256.0 | 352.05 | 1780.0 | 37.52 | 595.31 | -557.79 | True |
| IPO0319 | Paras Defence and Space Technologies Limited | PARAS | 175.0 | 475.0 | 938.0 | 171.43 | 436.0 | -264.57 | True |
| IPO0194 | Central Depository Services Ltd | CDSL | 149.0 | 250.0 | 500.0 | 67.79 | 235.57 | -167.78 | True |
| IPO0293 | Nazara Technologies Limited | NAZARA | 1101.0 | 1971.0 | 995.0 | 79.02 | -9.63 | 88.65 | True |
| IPO0573 | Anlon Healthcare L | AHCL | 91.0 | 91.0 | 18.4 | 0.0 | -79.78 | 79.78 | True |
| IPO0287 | Easy Trip Planners Limited | EASEMYTRIP | 187.0 | 206.0 | 106.12 | 10.16 | -43.25 | 53.41 | True |
| IPO0229 | Dharan Infra EPC Ltd | DHARAN | 180.0 | 136.0 | 54.4 | -24.44 | -69.78 | 45.34 | True |
| IPO0057 | Ashoka Buildcon Ltd | ASHOKA | 324.0 | 333.55 | 228.0 | 2.95 | -29.63 | 32.58 | True |
| IPO0096 | Rushil Decor Ltd | RUSHIL | 72.0 | 81.25 | 57.85 | 12.85 | -19.65 | 32.5 | True |
| IPO0072 | A2Z Infra Engineering Ltd | A2ZINFRA | 400.0 | 390.0 | 500.0 | -2.5 | 25.0 | -27.5 | True |
| IPO0102 | Brooks Laboratories Ltd | BROOKS | 100.0 | 110.0 | 82.66 | 10.0 | -17.34 | 27.34 | True |
| IPO0068 | RPP Infra Projects Ltd | RPPINFRA | 75.0 | 75.0 | 56.59 | 0.0 | -24.55 | 24.55 | True |
| IPO0347 | Veranda Learning Solutions Limited | VERANDA | 137.0 | 157.0 | 125.0 | 14.6 | -8.76 | 23.36 | True |
| IPO0064 | Shah Metacorp Ltd | SHAH | 71.0 | 76.6 | 62.19 | 7.89 | -12.41 | 20.3 | True |
| IPO0178 | PNB Housing Finance Ltd | PNBHOUSING | 775.0 | 863.0 | 712.29 | 11.35 | -8.09 | 19.44 | True |
| IPO0023 | IL&FS Transportation Networks Limited | IL&FSTRANS | 258.0 | 287.0 | 246.61 | 11.24 | -4.41 | 15.65 | True |
| IPO0417 | Plaza Wires Limited | PLAZACABLE | 54.0 | 84.0 | 76.0 | 55.56 | 40.74 | 14.82 | True |
| IPO0456 | Mukka Proteins Ltd | MUKKA | 28.0 | 44.0 | 40.0 | 57.14 | 42.86 | 14.28 | True |
| IPO0054 | Cantabil Retail India Ltd | CANTABIL | 135.0 | 133.8 | 114.7 | -0.89 | -15.04 | 14.15 | True |
| IPO0066 | Gravita India Ltd | GRAVITA | 125.0 | 218.75 | 201.1 | 75.0 | 60.88 | 14.12 | True |
| IPO0073 | Ravikumar Distilleries Ltd | RKDL | 64.0 | 64.0 | 72.0 | 0.0 | 12.5 | -12.5 | True |
| IPO0025 | Persistent Systems Limited | PERSISTENT | 310.0 | 400.0 | 361.6 | 29.03 | 16.65 | 12.38 | True |
| IPO0056 | Va Tech Wabag Ltd | WABAG | 1310.0 | 1655.0 | 1500.0 | 26.34 | 14.5 | 11.84 | True |
| IPO0135 | Ortel Communications Ltd | ORTEL | 181.0 | 181.0 | 160.05 | 0.0 | -11.57 | 11.57 | True |
| IPO0171 | S P Apparels Ltd | SPAL | 268.0 | 305.0 | 275.0 | 13.81 | 2.61 | 11.2 | True |
| IPO0082 | Lovable Lingerie Ltd | LOVABLE | 205.0 | 261.5 | 240.0 | 27.56 | 17.07 | 10.49 | True |

## Excluded rows

| ipo_id | ipo_name | exclude_reason |
|---|---|---|
| IPO0150 | Coffee Day Enterprises Ltd | Missing subscription or listing gain |
| IPO0188 | IRB InvIT Fund | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0191 | IndiGrid Infrastructure Fund | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0247 | Embassy Office Parks REIT | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0264 | Mindspace Business Parks REIT | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0282 | Brookfield India Real Estate Trust | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0296 | Powergrid Infrastructure Investment Trust | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0388 | Nexus Select Trust | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0457 | Indus Infra Trust | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0465 | Vodafone Idea Ltd | Follow-on public offer (FPO) of a listed company, not an IPO |
| IPO0526 | Capital Infra Trust | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0565 | Knowledge Realty T | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0600 | Wework India Manag | Missing subscription or listing gain |
| IPO0603 | Anantam Highways T | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0624 | Wakefit Innovation | Missing subscription or listing gain |
| IPO0644 | RaajMarg Infra Inv | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0650 | Citius Transnet In | REIT/InvIT: trust units, no retail quota, different investor base |
| IPO0652 | Bagmane Prime Offi | REIT/InvIT: trust units, no retail quota, different investor base |
