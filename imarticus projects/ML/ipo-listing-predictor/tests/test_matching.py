import pandas as pd
import pytest

from src.data.matching import listing_gain_pct, match_ipos, normalize_name


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Zomato Limited", "zomato"),
        ("ZOMATO LTD.", "zomato"),
        ("Zomato Ltd IPO", "zomato"),
        ("Life Insurance Corporation of India", "life insurance corporation of india"),
        ("Tata Technologies Ltd", "tata technologies"),
        ("Bajaj Housing Finance Limited", "bajaj housing finance"),
        ("PB Fintech (Policybazaar) Ltd", "pb fintech policybazaar"),
        ("Hindustan Aeronautics & Co. Pvt. Ltd.", "hindustan aeronautics and co"),
        ("  Nykaa   ", "nykaa"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_normalize_name_handles_missing():
    assert normalize_name(None) == ""
    assert normalize_name(float("nan")) == ""


def listed_frame():
    return pd.DataFrame(
        {
            "symbol": ["ZOMATO", "TATATECH", "NYKAA", "TATAMOTORS"],
            "company_name": ["Zomato Limited", "Tata Technologies Limited", "FSN E-Commerce Ventures Limited", "Tata Motors Limited"],
            "listing_date": pd.to_datetime(["2021-07-23", "2023-11-30", "2021-11-10", "1998-07-22"]),
            "segment": ["mainboard", "mainboard", "mainboard", "mainboard"],
        }
    )


def test_match_by_name_within_date_window():
    ipos = pd.DataFrame(
        {"ipo_name": ["Zomato Ltd", "Tata Technologies Ltd"], "listing_date": pd.to_datetime(["2021-07-23", "2023-11-30"])}
    )
    matched = match_ipos(ipos, listed_frame())
    assert matched["symbol"].tolist() == ["ZOMATO", "TATATECH"]
    assert (matched["match_method"] == "name_and_date").all()


def test_similar_name_outside_date_window_is_not_matched():
    # "Tata Motors" listed in 1998; an IPO dated 2023 must not borrow its symbol.
    ipos = pd.DataFrame({"ipo_name": ["Tata Motors Ltd"], "listing_date": pd.to_datetime(["2023-11-30"])})
    matched = match_ipos(ipos, listed_frame())
    assert pd.isna(matched.loc[0, "symbol"])
    assert matched.loc[0, "match_method"] == "unmatched"


def test_legal_name_with_brand_in_brackets_matches():
    # Nykaa lists under its legal name; the IPO name carries the brand in brackets.
    ipos = pd.DataFrame({"ipo_name": ["FSN E-Commerce Ventures Ltd (Nykaa)"], "listing_date": pd.to_datetime(["2021-11-10"])})
    matched = match_ipos(ipos, listed_frame())
    assert matched.loc[0, "symbol"] == "NYKAA"


@pytest.mark.parametrize(
    "ipo, listed, should_match",
    [
        ("vms industries", "pi industries", False),  # shared generic word only
        ("highway infrastruc", "highway infrastructure", True),  # name cut off in source
        ("xelpmoc design and technologies", "xelpmoc design and tech", True),
        ("one97 communications", "one 97 communications", True),
        ("gandhar oil refineries", "gandhar oil refinery india", True),
    ],
)
def test_name_score_threshold(ipo, listed, should_match):
    from src.config import NAME_MATCH_MIN_SCORE
    from src.data.matching import name_score

    assert (name_score(ipo, listed) >= NAME_MATCH_MIN_SCORE) is should_match


def test_match_does_not_mutate_inputs():
    ipos = pd.DataFrame({"ipo_name": ["Zomato Ltd"], "listing_date": pd.to_datetime(["2021-07-23"])})
    listed = listed_frame()
    ipos_before, listed_before = ipos.copy(), listed.copy()
    match_ipos(ipos, listed)
    pd.testing.assert_frame_equal(ipos, ipos_before)
    pd.testing.assert_frame_equal(listed, listed_before)


@pytest.mark.parametrize(
    "issue, price, expected",
    [(76.0, 115.0, 51.3158), (100.0, 100.0, 0.0), (949.0, 867.2, -8.6196)],
)
def test_listing_gain_pct(issue, price, expected):
    assert listing_gain_pct(issue, price) == pytest.approx(expected, abs=1e-3)


def test_listing_gain_pct_rejects_bad_issue_price():
    assert pd.isna(listing_gain_pct(0, 100))
    assert pd.isna(listing_gain_pct(float("nan"), 100))
