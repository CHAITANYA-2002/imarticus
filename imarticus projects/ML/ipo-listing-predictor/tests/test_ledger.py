"""The track-record ledger: calls are locked before listing, chained by hash, and scored once."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from src import ledger

NOW = datetime(2026, 11, 19, 6, 0, tzinfo=UTC)  # 11:30 IST


def call(name="Acme Technologies", listing=date(2026, 11, 24), expected=12.0, **extra):
    return {"ipo_name": name, "listing_date": listing, "offer_price": 250.0, "issue_size_cr": 800.0,
            "sub_qib": 40.0, "sub_hni": 25.0, "sub_rii": 8.0, "sub_total": 25.0,
            "expected": expected, "low": -5.0, "high": 30.0, "threshold": -2.0, "model": "deploy_live:abc123",
            **extra}


@pytest.fixture
def book():
    first = ledger.lock(ledger.empty(), call(), now=NOW)
    return ledger.lock(first, call("Beta Foods", date(2026, 11, 25), expected=-8.0), now=NOW)


def test_lock_appends_a_chained_entry(book):
    assert book["seq"].tolist() == [1, 2]
    assert book.loc[0, "prev_hash"] == ledger.GENESIS
    assert book.loc[1, "prev_hash"] == book.loc[0, "hash"]
    assert book["call"].tolist() == ["SUBSCRIBE", "AVOID"]
    assert book["source"].eq("live").all()
    assert ledger.verify(book) == []


def test_lock_does_not_change_the_ledger_it_was_given():
    start = ledger.empty()
    ledger.lock(start, call(), now=NOW)
    assert start.empty


def test_cannot_lock_on_or_after_listing_day():
    with pytest.raises(ValueError, match="before the listing date"):
        ledger.lock(ledger.empty(), call(listing=date(2026, 11, 19)), now=NOW)


def test_listing_day_is_judged_in_india_time():
    late_evening_utc = datetime(2026, 11, 23, 19, 0, tzinfo=UTC)  # 00:30 IST on 24 Nov
    with pytest.raises(ValueError, match="before the listing date"):
        ledger.lock(ledger.empty(), call(listing=date(2026, 11, 24)), now=late_evening_utc)


def test_one_call_per_issue(book):
    with pytest.raises(ValueError, match="already locked"):
        ledger.lock(book, call("  acme technologies "), now=NOW)


@pytest.mark.parametrize("bad", [{"ipo_name": " "}, {"expected": float("nan")}, {"sub_rii": -1.0},
                                 {"low": 40.0}])
def test_lock_rejects_bad_inputs(bad):
    with pytest.raises(ValueError):
        ledger.lock(ledger.empty(), call(**bad), now=NOW)


def test_editing_a_locked_number_breaks_verification(book):
    tampered = book.assign(expected=book["expected"].where(book["seq"] != 1, 50.0))
    problems = ledger.verify(tampered)
    assert any("seq 1" in p and "hash" in p for p in problems)


def test_deleting_an_entry_breaks_the_chain(book):
    third = ledger.lock(book, call("Gamma Steel", date(2026, 11, 26)), now=NOW)
    gap = third[third["seq"] != 2].reset_index(drop=True)
    assert any("chain" in p for p in ledger.verify(gap))


def test_record_result_scores_once_after_listing(book):
    after = datetime(2026, 11, 24, 6, 0, tzinfo=UTC)
    scored = ledger.record_result(book, 1, listing_open=287.5, now=after)
    row = scored.set_index("seq").loc[1]
    assert row["actual_gain_pct"] == pytest.approx(15.0)
    assert row["listing_open"] == 287.5
    assert ledger.verify(scored) == []  # results sit outside the hash
    with pytest.raises(ValueError, match="already scored"):
        ledger.record_result(scored, 1, listing_open=300.0, now=after)


def test_record_result_refuses_before_listing(book):
    with pytest.raises(ValueError, match="has not listed"):
        ledger.record_result(book, 1, listing_open=287.5, now=NOW)


def test_record_result_unknown_seq(book):
    with pytest.raises(KeyError):
        ledger.record_result(book, 99, listing_open=287.5, now=NOW)


def test_save_and_load_round_trip_keeps_hashes_valid(book, tmp_path):
    path = tmp_path / "calls.csv"
    ledger.save(book, path)
    loaded = ledger.load(path)
    assert ledger.verify(loaded) == []
    assert loaded["hash"].tolist() == book["hash"].tolist()


def test_load_missing_file_gives_empty_ledger(tmp_path):
    assert ledger.load(tmp_path / "nope.csv").empty


def test_scorecard_counts_hits_and_avoided_losses(book):
    after = datetime(2026, 11, 26, 6, 0, tzinfo=UTC)
    scored = ledger.record_result(book, 1, listing_open=287.5, now=after)   # SUBSCRIBE, +15%
    scored = ledger.record_result(scored, 2, listing_open=225.0, now=after)  # AVOID, -10%
    card = ledger.scorecard(scored)
    assert card["calls"] == 2 and card["scored"] == 2 and card["pending"] == 0
    assert card["correct"] == 2
    assert card["subscribe_hit_rate"] == pytest.approx(100.0)
    assert card["losses_avoided"] == 1
    assert card["in_range"] == 1  # -10% sits below the -5% low end
    assert card["mae"] == pytest.approx((3 + 2) / 2)


def test_scorecard_of_empty_ledger():
    card = ledger.scorecard(ledger.empty())
    assert card["calls"] == 0 and card["scored"] == 0
    assert pd.isna(card["mae"])


def test_seed_forward_test_marks_entries_as_not_pre_locked():
    fwd = pd.DataFrame({
        "ipo_id": ["NEW0001", "NEW0002"], "ipo_name": ["CMR Green", "Turtlemint"],
        "listing_date": pd.to_datetime(["2026-06-10", "2026-06-29"]), "sub_total": [127.0, 1.24],
        "sub_rii": [27.0, 1.11], "target_gain_pct": [39.6, -11.2], "random_forest": [48.0, 0.38],
        "low": [16.9, -12.4], "high": [79.7, 15.0]})
    details = pd.DataFrame({"ipo_id": ["NEW0001", "NEW0002"], "offer_price": [100.0, 200.0],
                            "issue_size_cr": [500.0, 900.0], "sub_qib": [200.0, 1.5], "sub_hni": [150.0, 0.8]})
    seeded = ledger.seed_forward_test(ledger.empty(), fwd, details, threshold=-2.0, model="deploy:x", now=NOW)
    assert seeded["source"].eq("forward_test").all()
    assert seeded["actual_gain_pct"].tolist() == pytest.approx([39.6, -11.2])
    assert seeded["listing_open"].tolist() == pytest.approx([139.6, 177.6])
    assert seeded["call"].tolist() == ["SUBSCRIBE", "SUBSCRIBE"]
    assert ledger.verify(seeded) == []
    with pytest.raises(ValueError, match="already"):
        ledger.seed_forward_test(seeded, fwd, details, threshold=-2.0, model="deploy:x", now=NOW)
