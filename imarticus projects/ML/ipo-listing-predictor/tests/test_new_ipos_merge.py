import numpy as np
import pandas as pd

from src.data.new_ipos_merge import include_reason, price_check


def test_price_check():
    assert price_check(634.0, 634.0) == "ok"
    assert price_check(640.0, 634.0) == "ok"          # within 3%
    assert price_check(700.0, 485.0) == "mismatch"
    assert price_check(np.nan, 500.0) == "not_reported"
    assert price_check(500.0, np.nan) == "no_nse_price"


def reason(**fields):
    base = {"is_mainboard_ipo": "yes", "agreement": "two_sources", "price_check": "ok"}
    return include_reason(pd.Series({**base, **fields}))


def test_include_reason():
    assert reason() == ""
    assert reason(price_check="not_reported") == ""
    assert reason(agreement="single_source") == ""
    assert reason(is_mainboard_ipo="no") == "not a mainboard IPO"
    assert reason(agreement="conflict") == "sources: conflict"
    assert reason(price_check="mismatch") == "reported listing price does not match NSE open"
