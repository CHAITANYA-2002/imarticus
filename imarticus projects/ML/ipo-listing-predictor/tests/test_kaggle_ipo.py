import pandas as pd

from src.data.kaggle_ipo import standardize

RAW_COLUMNS = [
    "Date", "IPO_Name", "Issue_Size(crores)", "QIB", "HNI", "RII", "Total",
    "Offer Price", "List Price", "Listing Gain", "CMP(BSE)", "CMP(NSE)", "Current Gains",
]


def raw_frame(rows):
    return pd.DataFrame(rows, columns=RAW_COLUMNS)


def sample_rows():
    return [
        ["2021-07-23", "Zomato Limited", 9375.0, 54.7, 32.96, 7.45, 38.25, 76, 115.0, 51.32, 140.0, 140.1, 84.2],
        ["2026-05-14", "Bagmane Prime Offi...", 3405.0, 17.09, 15.79, 0.0, 16.5, 100, 103.4, 3.4, 103.9, 103.9, 3.9],
        ["2019-02-25", "Embassy Office Parks REIT", 4750.0, 2.6, 2.4, 0.0, 2.6, 300, 308.0, 2.67, 380.0, 380.0, 26.0],
    ]


def test_standardize_renames_and_types():
    clean = standardize(raw_frame(sample_rows()))
    expected = {
        "listing_date", "ipo_name", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total",
        "offer_price", "list_price", "listing_gain_pct", "name_truncated", "is_trust",
    }
    assert expected.issubset(clean.columns)
    assert pd.api.types.is_datetime64_any_dtype(clean["listing_date"])
    assert clean["offer_price"].dtype.kind == "f"


def test_drops_current_price_columns():
    # Today's price is not known at listing time and differs by download date: keep it out.
    clean = standardize(raw_frame(sample_rows()))
    assert not {"cmp_bse", "cmp_nse", "current_gains"} & set(clean.columns)


def test_flags_truncated_names_and_strips_ellipsis():
    clean = standardize(raw_frame(sample_rows()))
    bagmane = clean[clean["ipo_name"].str.startswith("Bagmane")].iloc[0]
    assert bool(bagmane["name_truncated"])
    assert bagmane["ipo_name"] == "Bagmane Prime Offi"


def test_flags_reits_and_invits():
    clean = standardize(raw_frame(sample_rows()))
    flags = dict(zip(clean["ipo_name"], clean["is_trust"], strict=True))
    assert flags["Embassy Office Parks REIT"]
    assert flags["Bagmane Prime Offi"]  # no retail category: trust structure
    assert not flags["Zomato Limited"]


def test_sorted_by_date_with_stable_id():
    clean = standardize(raw_frame(sample_rows()))
    assert clean["listing_date"].is_monotonic_increasing
    assert clean["ipo_id"].tolist() == ["IPO0001", "IPO0002", "IPO0003"]


def test_standardize_does_not_mutate_input():
    raw = raw_frame(sample_rows())
    before = raw.copy()
    standardize(raw)
    pd.testing.assert_frame_equal(raw, before)
