"""Evaluate the way the model would actually be used: retrained every quarter.

A model frozen at the end of 2023 and scored on 2024-2026 is not how anyone would
run this. In practice you refit as new IPOs list. walk_forward() does exactly that,
and bias_correct() adds the recent average error back, which helps when the market
shifts faster than a quarterly refit can follow.
"""

import numpy as np
import pandas as pd

from src.features.build import PREDICTION_LAG_DAYS

LAG = pd.Timedelta(days=PREDICTION_LAG_DAYS)


def walk_forward(df, eval_mask, fit_fn, columns):
    """Predict rows in eval_mask quarter by quarter.

    The model for a quarter is trained on IPOs that listed before (quarter start - lag),
    so nothing that lists after an IPO's information cutoff is ever used for it.
    """
    df = df.sort_values("listing_date")
    eval_rows = df[eval_mask.reindex(df.index)]
    preds = []
    for quarter, rows in eval_rows.groupby(eval_rows["listing_date"].dt.to_period("Q")):
        train = df[df["listing_date"] < quarter.start_time - LAG]
        model = fit_fn(train)
        preds.append(pd.Series(model.predict(rows[columns]), index=rows.index))
    return pd.concat(preds).reindex(df.index[eval_mask.reindex(df.index)])


def known_before(dates, i, window):
    """Positions of the latest `window` IPOs that listed before IPO i's information cutoff."""
    known = np.where(dates < dates[i] - np.timedelta64(PREDICTION_LAG_DAYS, "D"))[0]
    return known[np.argsort(dates[known], kind="stable")][-window:]


def conformal_widen(frame, lower, upper, coverage=0.8, window=60, min_history=20):
    """Rolling conformalized quantile regression (CQR).

    For recent IPOs, measure how far the actual gain fell outside its predicted range
    (negative when inside). Widen (or narrow) every new range by the `coverage` quantile
    of those distances, so the range covers about `coverage` of outcomes going forward.
    """
    dates = frame["listing_date"].to_numpy()
    y = frame["target_gain_pct"].to_numpy(dtype=float)
    lo, hi = lower.to_numpy(dtype=float), upper.to_numpy(dtype=float)
    scores = np.maximum(lo - y, y - hi)
    new_lo, new_hi = lo.copy(), hi.copy()
    for i in range(len(frame)):
        recent = known_before(dates, i, window)
        if len(recent) < min_history:
            continue
        n = len(recent)
        level = min(1.0, np.ceil((n + 1) * coverage) / n)
        margin = np.quantile(scores[recent], level)
        new_lo[i], new_hi[i] = lo[i] - margin, hi[i] + margin
    return pd.Series(new_lo, index=lower.index), pd.Series(new_hi, index=upper.index)


def bias_correct(frame, raw_preds, window=20, min_history=5):
    """Add the median error of the last `window` IPOs known at each IPO's cutoff.

    frame needs listing_date and target_gain_pct, aligned with raw_preds.
    """
    dates = frame["listing_date"].to_numpy()
    errors = (frame["target_gain_pct"] - raw_preds).to_numpy()
    corrected = raw_preds.to_numpy(dtype=float).copy()
    for i in range(len(frame)):
        latest = known_before(dates, i, window)
        if len(latest) >= min_history:
            corrected[i] += np.median(errors[latest])
    return pd.Series(corrected, index=raw_preds.index)
