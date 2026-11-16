"""Turn a prediction into the language of an IPO research note: rating, thesis, risks."""

import math
from dataclasses import dataclass

TYPICAL_MISS_PP = 11  # median absolute error on the 78-IPO forward test


@dataclass
class Point:
    text: str
    impact: float


def describe(feature, value):
    """Plain-English reading of one model input (features are stored on log scales)."""
    times = lambda v: f"{math.expm1(v):,.1f}x"  # noqa: E731
    readers = {
        "log_sub_total": lambda v: f"Overall book covered {times(v)}",
        "log_sub_qib": lambda v: f"QIB book covered {times(v)}",
        "log_sub_hni": lambda v: f"HNI / NII book covered {times(v)}",
        "log_sub_rii": lambda v: f"Retail book covered {times(v)}",
        "qib_to_rii": lambda v: f"Institutional demand {math.exp(v):,.1f}x retail demand",
        "log_issue_size": lambda v: f"Issue size ₹{math.exp(v):,.0f} cr",
        "log_offer_price": lambda v: f"Offer price ₹{math.exp(v):,.0f}",
        "nifty_ret_1m": lambda v: f"NIFTY {v:+.1f}% over the past month",
        "nifty_ret_3m": lambda v: f"NIFTY {v:+.1f}% over three months",
        "nifty_vs_200dma": lambda v: f"NIFTY {v:+.1f}% versus its 200-day average",
        "vix": lambda v: f"India VIX at {v:.1f}",
        "recent_ipo_mean_gain": lambda v: f"Recent listings averaged {v:+.1f}% on day one",
        "recent_ipo_count": lambda v: f"{v:.0f} mainboard listings in the past 90 days",
    }
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return readers.get(feature, lambda v: f"{feature} = {v}")(value)


def thesis(columns, values, impacts, top=3, min_impact=0.5):
    """Strongest drivers for and against, as (supports, weighs) lists of Points."""
    rows = [(describe(c, v), i) for c, v, i in zip(columns, values, impacts, strict=True)]
    rows = [(t, i) for t, i in rows if t is not None and abs(i) >= min_impact]
    supports = sorted((r for r in rows if r[1] > 0), key=lambda r: -r[1])[:top]
    weighs = sorted((r for r in rows if r[1] < 0), key=lambda r: r[1])[:top]
    return [Point(t, i) for t, i in supports], [Point(t, i) for t, i in weighs]


def rating(expected, low, threshold):
    """SUBSCRIBE / AVOID plus conviction, from the expected gain and the downside case."""
    if expected < threshold:
        return "AVOID", "High" if expected < threshold - 5 else "Low"
    if low > 0:
        return "SUBSCRIBE", "High"
    return "SUBSCRIBE", "Medium" if expected >= 10 else "Low"


def risks(expected, low, high, odds, sub_total, nifty_vs_200dma, recent_count, busy_calendar=12, impacts=None):
    """Plain risk flags. Market flags are dropped when the model reads that factor as a positive
    for this issue (impacts: feature -> SHAP pp), so the note never contradicts its own drivers."""
    impacts = impacts or {}
    hurts = lambda feature: impacts.get(feature, -1) < 0  # noqa: E731
    items = []
    if low < 0:
        items.append(f"Downside case lists below issue price ({low:+.0f}%).")
    if high - low > 50:
        items.append(f"Wide outcome range ({low:+.0f}% to {high:+.0f}%): conviction on the exact gain is limited.")
    if odds < 0.05:
        items.append(f"Retail book heavily oversubscribed: about 1 in {1 / odds:,.0f} chance of an allotment.")
    if sub_total < 3:
        items.append("Thin overall demand (under 3x): such issues often list close to the offer price.")
    if nifty_vs_200dma < 0 and hurts("nifty_vs_200dma"):
        items.append("NIFTY is trading below its 200-day average, historically a weaker backdrop for listings.")
    if recent_count >= busy_calendar and hurts("recent_ipo_count"):
        items.append(f"Crowded primary calendar ({recent_count:.0f} listings in 90 days) splits investor attention.")
    items.append(f"Model error: a typical miss is about ±{TYPICAL_MISS_PP} percentage points.")
    return items
