"""Link each IPO to its NSE symbol by company name + listing date."""

import re

import pandas as pd
from rapidfuzz import fuzz

from src.config import LISTING_DATE_TOLERANCE_DAYS, NAME_MATCH_MIN_SCORE

STOP_WORDS = {"limited", "ltd", "pvt", "private", "ipo", "the"}


def normalize_name(name):
    if not isinstance(name, str):
        return ""
    words = re.sub(r"[^a-z0-9]+", " ", name.lower().replace("&", " and ")).split()
    return " ".join(w for w in words if w not in STOP_WORDS)


def listing_gain_pct(issue_price, listing_price):
    if pd.isna(issue_price) or pd.isna(listing_price) or issue_price <= 0:
        return float("nan")
    return (listing_price / issue_price - 1) * 100


def name_score(ipo_name, listed_name):
    """0-100 similarity of two normalised names.

    token_sort handles word order, the prefix ratio handles names cut off in the
    Kaggle file ("Highway Infrastruc"), and the lenient token_set only counts when
    the first words agree - otherwise "VMS Industries" matches "PI Industries".
    """
    if not ipo_name or not listed_name:
        return 0.0
    sort_score = fuzz.token_sort_ratio(ipo_name, listed_name)
    prefix_score = fuzz.ratio(ipo_name, listed_name[:len(ipo_name)])
    same_start = fuzz.ratio(ipo_name.split()[0], listed_name.split()[0]) >= 85
    set_score = fuzz.token_set_ratio(ipo_name, listed_name) if same_start else 0.0
    return float(max(sort_score, prefix_score, set_score))


NO_MATCH = {"symbol": None, "nse_company_name": None, "segment": None, "nse_listing_date": pd.NaT,
            "match_score": 0.0, "match_method": "unmatched"}


def best_candidate(ipo_name, listing_date, listed):
    if pd.isna(listing_date) or not ipo_name:
        return NO_MATCH
    window = pd.Timedelta(days=LISTING_DATE_TOLERANCE_DAYS)
    nearby = listed[(listed["listing_date"] - listing_date).abs() <= window]
    if nearby.empty:
        return NO_MATCH

    scores = nearby["norm_name"].map(lambda candidate: name_score(ipo_name, candidate))
    best = scores.idxmax()
    if scores[best] < NAME_MATCH_MIN_SCORE:
        return {**NO_MATCH, "match_score": float(scores[best])}
    row = nearby.loc[best]
    return {
        "symbol": row["symbol"],
        "nse_company_name": row["company_name"],
        "segment": row["segment"],
        "nse_listing_date": row["listing_date"],
        "match_score": float(scores[best]),
        "match_method": "name_and_date",
    }


def match_ipos(ipos, listed):
    """Return ipos with symbol, segment and match diagnostics added (inputs untouched)."""
    candidates = listed.assign(norm_name=listed["company_name"].map(normalize_name))
    results = [best_candidate(normalize_name(r.ipo_name), r.listing_date, candidates)
               for r in ipos.itertuples(index=False)]
    return pd.concat([ipos.reset_index(drop=True), pd.DataFrame(results)], axis=1)
