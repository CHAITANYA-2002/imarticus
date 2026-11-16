"""NSE's lists of currently listed companies (mainboard + SME).

    python -m src.data.nse
"""

import pandas as pd
import requests

from src.config import HTTP_HEADERS, HTTP_TIMEOUT_SECONDS, NSE_SOURCES, RAW_NSE_DIR
from src.data.provenance import record


def download(url, destination):
    try:
        response = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"download failed for {url}: {e}") from e
    if not response.content.strip():
        raise RuntimeError(f"{url} returned an empty file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def load_equity_list(path, segment):
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.apply(lambda col: col.str.strip())
    return pd.DataFrame({
        "symbol": df["symbol"],
        "company_name": df["name_of_company"],
        "series": df["series"],
        "listing_date": pd.to_datetime(df["date_of_listing"], format="%d-%b-%Y", errors="coerce"),
        "isin": df["isin_number"],
        "segment": segment,
    })


def load_all(raw_dir=RAW_NSE_DIR):
    return pd.concat([
        load_equity_list(raw_dir / "EQUITY_L.csv", "mainboard"),
        load_equity_list(raw_dir / "SME_EQUITY_L.csv", "sme"),
    ], ignore_index=True)


def main():
    for filename, url in NSE_SOURCES.items():
        path = download(url, RAW_NSE_DIR / filename)
        record(path, url, note="NSE list of currently listed securities")
    listed = load_all()
    print("saved:", listed.groupby("segment").size().to_dict())
    print(f"listing dates {listed.listing_date.min():%Y-%m-%d} to {listed.listing_date.max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
