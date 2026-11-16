"""Cross-check Kaggle's listing gains against the NSE open from Yahoo.

Writes data/interim/ipos_verified.csv and reports/data_audit.md.
    python -m src.data.audit
"""

import pandas as pd

from src.config import INTERIM_DIR, REPORTS_DIR
from src.data.listing_prices import BARS_PATH, MATCHED_PATH
from src.data.matching import listing_gain_pct

# Kaggle's list price is sometimes the BSE open, Yahoo's .NS bar is the NSE open.
# <=2 pp: same price. <=10 pp: probably the other exchange. More: one side is wrong.
AGREE_TOLERANCE_PP = 2.0
CLOSE_TOLERANCE_PP = 10.0
VERIFIED_PATH = INTERIM_DIR / "ipos_verified.csv"
REPORT_PATH = REPORTS_DIR / "data_audit.md"

MANUAL_EXCLUSIONS = {
    "Vodafone Idea Ltd": "Follow-on public offer (FPO) of a listed company, not an IPO",
}


def verdict(kaggle_gain, yf_gain, status, on_listing_day=True):
    if not isinstance(status, str):
        return "not_on_nse"
    if pd.isna(kaggle_gain):
        return "no_kaggle_gain"
    if status != "ok" or pd.isna(yf_gain):
        return "no_price"
    if not on_listing_day:
        return "bar_not_listing_day"
    gap = abs(kaggle_gain - yf_gain)
    if gap <= AGREE_TOLERANCE_PP:
        return "agree"
    return "close" if gap <= CLOSE_TOLERANCE_PP else "disagree"


def choose_target(kaggle_gain, yf_gain, check):
    """Use the NSE open when Kaggle backs it up (within 10 pp), else Kaggle's number, flagged.

    Spot checks of the big disagreements (CDSL, Paras, Nazara) showed Yahoo's split
    history was wrong there, not Kaggle.
    """
    if check in {"agree", "close"}:
        return yf_gain, "nse_open_yahoo"
    return kaggle_gain, "kaggle_unverified"


def cross_check(matched, bars):
    price_cols = ["symbol", "bar_date", "open", "close", "status"]
    joined = matched.merge(bars[price_cols].drop_duplicates("symbol"), on="symbol", how="left")
    open_gain = [listing_gain_pct(i, p) for i, p in zip(joined["offer_price"], joined["open"], strict=True)]
    close_gain = [listing_gain_pct(i, p) for i, p in zip(joined["offer_price"], joined["close"], strict=True)]
    checked = joined.assign(
        yf_open_gain_pct=open_gain,
        yf_close_gain_pct=close_gain,
        bar_on_listing_date=pd.to_datetime(joined["bar_date"]) == pd.to_datetime(joined["nse_listing_date"]),
    )
    verdicts = [
        verdict(k, y, s, bool(on_day))
        for k, y, s, on_day in zip(
            checked["listing_gain_pct"], checked["yf_open_gain_pct"], checked["status"], checked["bar_on_listing_date"],
            strict=True,
        )
    ]
    targets = [choose_target(k, y, c)
               for k, y, c in zip(checked["listing_gain_pct"], checked["yf_open_gain_pct"], verdicts, strict=True)]
    return checked.assign(
        check=verdicts,
        target_gain_pct=[gain for gain, _ in targets],
        target_source=[source for _, source in targets],
    )


def exclusion_reason(row):
    if row["ipo_name"] in MANUAL_EXCLUSIONS:
        return MANUAL_EXCLUSIONS[row["ipo_name"]]
    if row["is_trust"]:
        return "REIT/InvIT: trust units, no retail quota, different investor base"
    if pd.isna(row["listing_gain_pct"]) or pd.isna(row["sub_total"]):
        return "Missing subscription or listing gain"
    return ""


def markdown_table(frame):
    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    divider = "|" + "---|" * len(frame.columns)
    rows = ["| " + " | ".join(map(str, values)) + " |" for values in frame.itertuples(index=False)]
    return "\n".join([header, divider, *rows])


def build_report(verified):
    kept = verified[verified["exclude_reason"] == ""]
    checkable = kept[kept["check"].isin(["agree", "close", "disagree"])]
    corroborated = checkable["check"].isin(["agree", "close"])
    agree_rate = corroborated.mean() * 100 if len(checkable) else float("nan")

    funnel = pd.DataFrame(
        [
            ("IPOs in Kaggle file", len(verified)),
            ("Excluded (trusts, FPOs, missing values)", int((verified["exclude_reason"] != "").sum())),
            ("Kept for modelling", len(kept)),
            ("  matched to a current NSE symbol", int(kept["symbol"].notna().sum())),
            ("  with a Yahoo price on the listing day", len(checkable)),
            ("  agree within 2 pp", int((checkable["check"] == "agree").sum())),
            ("  within 10 pp (likely BSE vs NSE open)", int((checkable["check"] == "close").sum())),
            ("  disagree by more than 10 pp", int((checkable["check"] == "disagree").sum())),
            ("Target from NSE open (verified)", int((kept["target_source"] == "nse_open_yahoo").sum())),
            ("Target from Kaggle (unverified)", int((kept["target_source"] == "kaggle_unverified").sum())),
        ],
        columns=["Step", "Count"],
    )
    excluded = verified[verified["exclude_reason"] != ""][["ipo_id", "ipo_name", "exclude_reason"]]
    disagree = checkable[checkable["check"] == "disagree"].assign(
        diff_pp=lambda d: (d["listing_gain_pct"] - d["yf_open_gain_pct"]).round(2)
    )
    disagree_cols = ["ipo_id", "ipo_name", "symbol", "offer_price", "list_price", "open",
                     "listing_gain_pct", "yf_open_gain_pct", "diff_pp", "bar_on_listing_date"]
    disagree_table = disagree.reindex(disagree["diff_pp"].abs().sort_values(ascending=False).index)[disagree_cols].round(2)
    by_year = kept.groupby(kept["listing_date"].dt.year)["check"].value_counts().unstack(fill_value=0)

    return "\n\n".join(
        [
            "# Data audit: Kaggle listing gains vs Yahoo Finance",
            f"Kaggle's listing gain is corroborated by the NSE open (within {CLOSE_TOLERANCE_PP:.0f} pp) for "
            f"**{agree_rate:.1f}%** of checkable IPOs ({int(corroborated.sum())} of {len(checkable)}).",
            "Listing gain = listing-day open / offer price - 1. Yahoo back-adjusts history for splits and "
            "bonuses, so each bar is multiplied back by the split factor after the listing day. IPOs not on "
            "NSE's current list (delisted, merged, BSE-only) keep Kaggle's figure, marked unverified.",
            "Where the two disagree by more than 10 pp, spot checks against the known NSE listing prices "
            "(CDSL 250, Paras Defence 475, Nazara 1,971, Bansal Wire 352) show Kaggle is right and Yahoo's "
            "split history is wrong or double-counted. Those rows therefore keep Kaggle's gain, marked unverified.",
            "## Funnel", markdown_table(funnel),
            "## Verdict by listing year (kept IPOs)", markdown_table(by_year.reset_index()),
            "## Disagreements (largest first)", markdown_table(disagree_table) if len(disagree_table) else "None.",
            "## Excluded rows", markdown_table(excluded),
        ]
    ) + "\n"


def main():
    matched = pd.read_csv(MATCHED_PATH, parse_dates=["listing_date", "nse_listing_date"])
    bars = pd.read_csv(BARS_PATH, parse_dates=["bar_date"])
    checked = cross_check(matched, bars)
    verified = checked.assign(exclude_reason=checked.apply(exclusion_reason, axis=1))
    verified.to_csv(VERIFIED_PATH, index=False)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(verified), encoding="utf-8")
    print(verified["check"].value_counts().to_dict())
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
