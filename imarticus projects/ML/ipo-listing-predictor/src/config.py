from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_NSE_DIR = RAW_DIR / "nse"
RAW_KAGGLE_DIR = RAW_DIR / "kaggle"
RAW_MARKET_DIR = RAW_DIR / "market"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = RAW_DIR / "manifest.json"

NSE_SOURCES = {
    "EQUITY_L.csv": "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
    "SME_EQUITY_L.csv": "https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv",
}

KAGGLE_DATASET = "karanammithul/ipo-data-india-2010-2025"
KAGGLE_URL = f"https://www.kaggle.com/datasets/{KAGGLE_DATASET}"

MARKET_TICKERS = {"nifty50": "^NSEI", "india_vix": "^INDIAVIX"}
MARKET_START_DATE = "2009-01-01"

# NSE's archive returns 403 without a browser-like user agent
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,application/octet-stream,*/*",
}
HTTP_TIMEOUT_SECONDS = 30

# IPO -> NSE symbol matching
LISTING_DATE_TOLERANCE_DAYS = 7
NAME_MATCH_MIN_SCORE = 85
