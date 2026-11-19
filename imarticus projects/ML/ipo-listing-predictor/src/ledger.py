"""Public track record: every call is locked before the IPO lists, then scored once.

Each locked call is one row of ledger/calls.csv. The row's hash covers the call and the
previous row's hash, so editing a number, deleting a row or reordering rows after the fact
breaks verify(). The listing result is added later and sits outside the hash. Committing the
file to git after each lock gives an outside timestamp as well.

    python -m src.ledger verify                # check the chain
    python -m src.ledger score                 # fill results for listed IPOs from the IPO history
    python -m src.ledger result SEQ OPEN       # record one listing-day open by hand
    python -m src.ledger seed-forward          # one-off: add the 78-IPO forward test
"""

import argparse
import hashlib
import math
import sys
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT

LEDGER_PATH = PROJECT_ROOT / "ledger" / "calls.csv"
GENESIS = "0" * 64
IST = timezone(timedelta(hours=5, minutes=30))

NUMBERS = ["offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total",
           "expected", "low", "high", "threshold"]
LOCKED = ["seq", "locked_at", "source", "ipo_name", "listing_date", *NUMBERS, "call", "model", "prev_hash"]
RESULTS = ["listing_open", "actual_gain_pct", "scored_at"]
COLUMNS = [*LOCKED, "hash", *RESULTS]
TEXT = ["locked_at", "source", "ipo_name", "listing_date", "call", "model", "prev_hash", "hash", "scored_at"]
SOURCES = {"live": "Locked before listing", "forward_test": "Forward test (scored after listing)"}


def empty():
    return pd.DataFrame(columns=COLUMNS)


def load(path=LEDGER_PATH):
    if not Path(path).exists():
        return empty()
    book = pd.read_csv(path, dtype={c: str for c in TEXT}, keep_default_na=False, na_values={c: [""] for c in
                                                                                             [*NUMBERS, *RESULTS[:2]]})
    return book.assign(seq=book["seq"].astype(int))[COLUMNS]


def save(book, path=LEDGER_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    book[COLUMNS].to_csv(path, index=False, lineterminator="\n")


def _text(value):
    if isinstance(value, float):
        return "" if math.isnan(value) else f"{value:.4f}"
    return "" if value is None else str(value)


def row_hash(row):
    """SHA-256 of the locked fields, which include the previous row's hash."""
    parts = [_text(int(row["seq"]) if k == "seq" else (float(row[k]) if k in NUMBERS else row[k])) for k in LOCKED]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _iso(now):
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _india_date(timestamp):
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return timestamp.astimezone(IST).date()


def _as_date(value):
    return value if isinstance(value, date) and not isinstance(value, datetime) else pd.Timestamp(value).date()


def _normal_name(name):
    return " ".join(str(name).split()).casefold()


def _append(book, entry, source, now):
    seq = int(book["seq"].max()) + 1 if len(book) else 1
    prev = book.sort_values("seq")["hash"].iloc[-1] if len(book) else GENESIS
    expected, threshold = float(entry["expected"]), float(entry["threshold"])
    row = {
        "seq": seq, "locked_at": _iso(now), "source": source, "ipo_name": " ".join(str(entry["ipo_name"]).split()),
        "listing_date": _as_date(entry["listing_date"]).isoformat(),
        **{k: round(float(entry[k]), 4) for k in NUMBERS},
        "call": "SUBSCRIBE" if expected >= threshold else "AVOID",
        "model": str(entry["model"]), "prev_hash": prev,
    }
    row = {**row, "hash": row_hash(row), "listing_open": math.nan, "actual_gain_pct": math.nan, "scored_at": ""}
    new = pd.DataFrame([row], columns=COLUMNS)
    return new if book.empty else pd.concat([book, new], ignore_index=True)


def _check_entry(book, entry, now):
    if not str(entry.get("ipo_name") or "").strip():
        raise ValueError("Issuer name is required.")
    values = {k: float(entry[k]) for k in NUMBERS}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("All numbers must be filled in.")
    if any(values[k] < 0 for k in ["sub_qib", "sub_hni", "sub_rii", "sub_total"]):
        raise ValueError("Subscription figures cannot be negative.")
    if values["offer_price"] <= 0 or values["issue_size_cr"] <= 0:
        raise ValueError("Offer price and issue size must be positive.")
    if values["low"] > values["high"]:
        raise ValueError("Range low end is above the high end.")
    if _india_date(now) >= _as_date(entry["listing_date"]):
        raise ValueError("A call can only be locked before the listing date (India time).")
    name = _normal_name(entry["ipo_name"])
    if len(book) and book["ipo_name"].map(_normal_name).eq(name).any():
        raise ValueError(f"A call for {entry['ipo_name'].strip()} is already locked; calls cannot be replaced.")


def lock(book, entry, now=None):
    """Return a new ledger with this call appended. entry needs ipo_name, listing_date, NUMBERS and model."""
    now = now or datetime.now(UTC)
    _check_entry(book, entry, now)
    return _append(book, entry, "live", now)


def record_result(book, seq, listing_open, now=None):
    """Return a new ledger with the listing-day open of call `seq` filled in."""
    now = now or datetime.now(UTC)
    matches = book.index[book["seq"] == seq]
    if matches.empty:
        raise KeyError(f"No call with seq {seq}.")
    i = matches[0]
    row = book.loc[i]
    if pd.notna(row["actual_gain_pct"]):
        raise ValueError(f"Call {seq} is already scored.")
    if _india_date(now) < _as_date(row["listing_date"]):
        raise ValueError(f"{row['ipo_name']} has not listed yet ({row['listing_date']}).")
    if not (math.isfinite(listing_open) and listing_open > 0):
        raise ValueError("Listing open must be a positive price.")
    gain = (listing_open / float(row["offer_price"]) - 1) * 100
    updated = book.copy()
    updated.loc[i, RESULTS] = [round(float(listing_open), 4), round(gain, 4), _iso(now)]
    return updated


def verify(book):
    """List of problems; empty means every row is intact, chained, and live calls were locked in time."""
    problems = []
    prev = GENESIS
    for position, (_, row) in enumerate(book.sort_values("seq").iterrows(), start=1):
        seq = int(row["seq"])
        if seq != position:
            problems.append(f"chain broken: expected seq {position}, found seq {seq}")
        if row["prev_hash"] != prev:
            problems.append(f"chain broken at seq {seq}: previous-hash link does not match")
        if row_hash(row) != row["hash"]:
            problems.append(f"seq {seq}: hash does not match its contents (edited after locking)")
        if row["source"] == "live" and _india_date(row["locked_at"]) >= _as_date(row["listing_date"]):
            problems.append(f"seq {seq}: locked on or after its listing date")
        prev = row["hash"]
    return problems


def scorecard(book):
    scored = book[book["actual_gain_pct"].notna()]
    actual = scored["actual_gain_pct"].astype(float)
    sub = scored["call"].eq("SUBSCRIBE")
    up = actual > 0
    correct = (sub & up) | (~sub & ~up)
    in_range = (scored["low"].astype(float) <= actual) & (actual <= scored["high"].astype(float))
    return {
        "calls": len(book), "scored": len(scored), "pending": len(book) - len(scored),
        "subscribe": int(sub.sum()), "avoid": int((~sub).sum()),
        "correct": int(correct.sum()),
        "accuracy": correct.mean() * 100 if len(scored) else math.nan,
        "subscribe_hit_rate": up[sub].mean() * 100 if sub.any() else math.nan,
        "subscribe_avg_gain": actual[sub].mean() if sub.any() else math.nan,
        "avoid_avg_gain": actual[~sub].mean() if (~sub).any() else math.nan,
        "losses_avoided": int((~sub & (actual < 0)).sum()),
        "losses_taken": int((sub & (actual < 0)).sum()),
        "in_range": int(in_range.sum()),
        "mae": (scored["expected"].astype(float) - actual).abs().mean() if len(scored) else math.nan,
    }


def seed_forward_test(book, forward, details, threshold, model, now=None):
    """Add the forward-test calls, already scored. They are marked forward_test, not live:
    the model was frozen before these IPOs, but the calls were written down after they listed."""
    now = now or datetime.now(UTC)
    if len(book) and book["source"].eq("forward_test").any():
        raise ValueError("The forward test is already in the ledger.")
    rows = forward.merge(details, on="ipo_id", how="left").sort_values(["listing_date", "ipo_id"])
    for _, r in rows.iterrows():
        entry = {**{k: r[k] for k in ["ipo_name", "listing_date", "offer_price", "issue_size_cr", "sub_qib",
                                      "sub_hni", "sub_rii", "sub_total", "low", "high"]},
                 "expected": r["random_forest"], "threshold": threshold, "model": model}
        book = _append(book, entry, "forward_test", now)
        gain = float(r["target_gain_pct"])
        opening = float(r["offer_price"]) * (1 + gain / 100)
        book.loc[book.index[-1], RESULTS] = [round(opening, 4), round(gain, 4), _iso(now)]
    return book


def model_fingerprint(path):
    """Model file name plus the first 12 hex digits of its SHA-256, so each call names the exact model."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    return f"{Path(path).stem}:{digest}"


def score_from_history(book, history, now=None):
    """Fill results for pending live calls whose IPO is now in the history table (same name, same date)."""
    known = history.assign(key=history["ipo_name"].map(_normal_name),
                           day=pd.to_datetime(history["listing_date"]).dt.date)
    filled = []
    for _, row in book[book["actual_gain_pct"].isna()].iterrows():
        hit = known[(known["key"] == _normal_name(row["ipo_name"])) & (known["day"] == _as_date(row["listing_date"]))]
        if hit.empty or pd.isna(hit.iloc[0]["target_gain_pct"]):
            continue
        h = hit.iloc[0]
        opening = float(h["offer_price"]) * (1 + float(h["target_gain_pct"]) / 100)
        book = record_result(book, int(row["seq"]), opening, now)
        filled.append(row["ipo_name"])
    return book, filled


def _cli(argv=None):
    parser = argparse.ArgumentParser(prog="python -m src.ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("score")
    sub.add_parser("seed-forward")
    one = sub.add_parser("result")
    one.add_argument("seq", type=int)
    one.add_argument("listing_open", type=float)
    args = parser.parse_args(argv)
    book = load()

    if args.command == "verify":
        problems = verify(book)
        print("\n".join(problems) if problems else f"OK: {len(book)} calls, head {book['hash'].iloc[-1][:12] if len(book) else '-'}")
        return 1 if problems else 0

    from src.models.dataset import load_features  # heavy import, only needed below

    if args.command == "result":
        book = record_result(book, args.seq, args.listing_open)
        print(f"Recorded call {args.seq}.")
    elif args.command == "score":
        from app.core import LIVE_FEATURES
        history = load_features(LIVE_FEATURES) if LIVE_FEATURES.exists() else load_features()
        book, filled = score_from_history(book, history)
        print(f"Scored {len(filled)}: {', '.join(filled) or 'none'}")
    elif args.command == "seed-forward":
        import json

        from app.core import FORWARD_PREDICTIONS, LIVE_FEATURES
        from src.backtest import DECISION_RULE
        from src.models.train import BEST_CONFIGS
        forward = pd.read_csv(FORWARD_PREDICTIONS, parse_dates=["listing_date"])
        details = load_features(LIVE_FEATURES)[["ipo_id", "offer_price", "issue_size_cr", "sub_qib", "sub_hni"]]
        threshold = json.loads(DECISION_RULE.read_text())["model_threshold"]
        book = seed_forward_test(book, forward, details, threshold, model_fingerprint(BEST_CONFIGS).replace("best_configs", "walk_forward"))
        print(f"Added {int(book['source'].eq('forward_test').sum())} forward-test calls.")
    save(book)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
