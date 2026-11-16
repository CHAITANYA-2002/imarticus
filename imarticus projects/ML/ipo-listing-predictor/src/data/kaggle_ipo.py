"""Kaggle 'IPO Data India 2010-2026': download and clean.

The dataset is public, no Kaggle login needed.
    python -m src.data.kaggle_ipo
"""

import zipfile

import pandas as pd
import requests

from src.config import HTTP_TIMEOUT_SECONDS, INTERIM_DIR, KAGGLE_DATASET, KAGGLE_URL, RAW_KAGGLE_DIR
from src.data.provenance import record

DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{KAGGLE_DATASET}"
ZIP_PATH = RAW_KAGGLE_DIR / "ipo-data-india.zip"
PRIMARY_FILE = RAW_KAGGLE_DIR / "Initial Public Offering (Updated).xlsx"
# Kaggle answers 404 to browser and python-requests user agents on this endpoint
KAGGLE_HEADERS = {"User-Agent": "ipo-listing-predictor/0.1"}

RENAME = {
    "Date": "listing_date",
    "IPO_Name": "ipo_name",
    "Issue_Size(crores)": "issue_size_cr",
    "QIB": "sub_qib",
    "HNI": "sub_hni",
    "RII": "sub_rii",
    "Total": "sub_total",
    "Offer Price": "offer_price",
    "List Price": "list_price",
    "Listing Gain": "listing_gain_pct",
}
NUMERIC = ["issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total", "offer_price", "list_price",
           "listing_gain_pct"]


def standardize(raw):
    """Rename, fix types, flag cut-off names and REITs/InvITs, add an id.

    CMP / Current Gains are dropped: they depend on when the file was made and
    aren't known at listing time.
    """
    df = raw[list(RENAME)].rename(columns=RENAME)
    names = df["ipo_name"].astype(str).str.strip()
    df = df.assign(
        listing_date=pd.to_datetime(df["listing_date"], errors="coerce"),
        ipo_name=names.str.replace(r"\.\.\.$", "", regex=True).str.strip(),
        name_truncated=names.str.endswith("..."),
        **{c: pd.to_numeric(df[c], errors="coerce").astype(float) for c in NUMERIC},
    )
    # trusts have no retail quota, so RII = 0 also gives them away
    is_trust = df["ipo_name"].str.lower().str.contains(r"\b(?:reit|invit|trust)\b", regex=True) | (df["sub_rii"] == 0)
    df = df.assign(is_trust=is_trust).sort_values(["listing_date", "ipo_name"], kind="mergesort").reset_index(drop=True)
    df.insert(0, "ipo_id", [f"IPO{i:04d}" for i in range(1, len(df) + 1)])
    return df


def download(destination=ZIP_PATH):
    try:
        response = requests.get(DOWNLOAD_URL, headers=KAGGLE_HEADERS, timeout=HTTP_TIMEOUT_SECONDS * 2)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Kaggle download failed ({e}). Get the zip from {KAGGLE_URL} "
                           f"and save it as {destination}") from e
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def extract(zip_path=ZIP_PATH, out_dir=RAW_KAGGLE_DIR):
    """Unzip only spreadsheets, and never outside out_dir."""
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            target = (out_dir / member).resolve()
            if out_dir.resolve() not in target.parents or target.suffix.lower() not in {".xlsx", ".csv"}:
                continue
            target.write_bytes(archive.read(member))
            extracted.append(target)
    return extracted


def load(path=PRIMARY_FILE):
    return standardize(pd.read_excel(path))


def main():
    zip_path = download()
    record(zip_path, DOWNLOAD_URL, note=f"Kaggle dataset {KAGGLE_URL}")
    for path in extract(zip_path):
        record(path, DOWNLOAD_URL, note="extracted from ipo-data-india.zip")
    ipos = load()
    out = INTERIM_DIR / "ipos_kaggle.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    ipos.to_csv(out, index=False)
    print(f"{len(ipos)} IPOs, {ipos.listing_date.min():%Y-%m-%d} to {ipos.listing_date.max():%Y-%m-%d}")
    print(f"trusts: {ipos.is_trust.sum()}, cut-off names: {ipos.name_truncated.sum()}")


if __name__ == "__main__":
    main()
