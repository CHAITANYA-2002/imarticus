from datetime import UTC, date, datetime, timedelta

import pandas as pd
import streamlit as st

from app import cache, charts, core, research, ui
from src import ledger

NEW_IPO = "New issue (enter details)"
FIELDS = ["listing_date", "offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total"]


def defaults():
    return {"name": "", "listing_date": date.today() + timedelta(days=3), "offer_price": 250.0,
            "issue_size_cr": 800.0, "sub_qib": 40.0, "sub_hni": 25.0, "sub_rii": 8.0, "sub_total": 25.0}


def pick_past_ipo(history):
    names = [NEW_IPO] + history.sort_values("listing_date", ascending=False)["ipo_name"].tolist()
    choice = st.selectbox("Issue", names, help="Pick a past IPO to see the call the model would have made.")
    if choice == NEW_IPO:
        return defaults(), None
    row = history[history["ipo_name"] == choice].iloc[0]
    return core.readable_inputs(row), row


def input_form(start):
    with st.form("ipo"):
        name = st.text_input("Issuer name", value=start["name"], placeholder="e.g. Acme Technologies Ltd")
        a, b, c = st.columns(3)
        listing_date = a.date_input("Expected listing date", value=start["listing_date"])
        offer_price = b.number_input("Issue price, upper band (₹)", min_value=1.0, value=start["offer_price"], step=1.0)
        issue_size = c.number_input("Issue size (₹ crore)", min_value=1.0, value=start["issue_size_cr"], step=10.0)
        st.markdown("**Final-day book (times subscribed)**")
        q, h, r, t = st.columns(4)
        sub_qib = q.number_input("QIB", min_value=0.0, value=start["sub_qib"], step=0.5)
        sub_hni = h.number_input("HNI / NII", min_value=0.0, value=start["sub_hni"], step=0.5)
        sub_rii = r.number_input("Retail", min_value=0.0, value=start["sub_rii"], step=0.5)
        sub_total = t.number_input("Overall", min_value=0.0, value=start["sub_total"], step=0.5)
        submitted = st.form_submit_button("Generate research note", type="primary", use_container_width=True)
    ipo = {"listing_date": listing_date, "offer_price": offer_price, "issue_size_cr": issue_size,
           "sub_qib": sub_qib, "sub_hni": sub_hni, "sub_rii": sub_rii, "sub_total": sub_total}
    return name, ipo, submitted


def recent_market_inputs(history, listing_date):
    count, mean_gain = core.recent_ipo_stats(history, pd.Timestamp(listing_date))
    data_end = history["listing_date"].max()
    stale = pd.Timestamp(listing_date) - pd.Timedelta(days=7) > data_end + pd.Timedelta(days=30)
    if stale:
        last_year = history[history["listing_date"] > data_end - pd.Timedelta(days=365)]
        count = int(last_year["recent_ipo_count"].median())
        mean_gain = float(last_year["recent_ipo_mean_gain"].median())
        st.warning(f"IPO history ends {data_end:%d %b %Y}; recent-listing figures below use last year's typical "
                   "values. Replace them with the actual figures for a live call.", icon=":material/warning:")
    a, b = st.columns(2)
    count = a.number_input("Mainboard listings, last 90 days", min_value=0, value=int(count), step=1)
    mean_gain = b.number_input("Their average day-one return (%)",
                               value=float(0 if pd.isna(mean_gain) else round(mean_gain, 1)), step=0.5)
    return count, mean_gain


def show_market(features, note):
    f = features.iloc[0]
    st.caption(f"Market data: {note}. Measured 7 days before listing, as in training.")
    ui.kpis([
        ("NIFTY · 1M", ui.signed(f["nifty_ret_1m"]), "return"),
        ("NIFTY · 3M", ui.signed(f["nifty_ret_3m"]), "return"),
        ("NIFTY vs 200-DMA", ui.signed(f["nifty_vs_200dma"]), "trend"),
        ("India VIX", f"{f['vix']:.1f}", "volatility"),
    ])


def odds_text(odds):
    return f"{odds:.0%}" if odds >= 0.1 else f"1 in {1 / odds:,.0f}"


def show_note(name, ipo, pred, past_row, explained, base_value, history):
    verdict, conviction = research.rating(pred.expected, pred.low, pred.threshold)
    meta = (f"Listing {pd.Timestamp(ipo['listing_date']):%d %b %Y} · Issue price ₹{ipo['offer_price']:,.0f} · "
            f"Size ₹{ipo['issue_size_cr']:,.0f} cr · Book {ipo['sub_total']:,.1f}x")
    ui.research_note(name or "Unnamed issue", meta, verdict, conviction, pred.expected, pred.low, pred.high,
                     odds_text(pred.allotment_odds), pred.expected_value)

    actual = past_row["target_gain_pct"] if past_row is not None else None
    st.plotly_chart(charts.range_bar(pred, actual), use_container_width=True, config={"displayModeBar": False})
    if past_row is not None:
        show_past_check(past_row)
    else:
        lock_panel(name, ipo, pred)

    ui.section("Investment thesis", "What drives the call, in percentage points of expected return")
    supports, weighs = research.thesis(explained["column"], explained["value"], explained["impact"])
    left, right = st.columns(2)
    with left:
        ui.thesis_panel("Supports the listing", supports, "No strong positive drivers.")
    with right:
        ui.thesis_panel("Weighs on the listing", weighs, "No strong negative drivers.")

    f = pred.features.iloc[0]
    left, right = st.columns([1, 1.1])
    with left:
        ui.section("Key risks", "What could go wrong with this call")
        impacts = dict(zip(explained["column"], explained["impact"], strict=True))
        ui.risk_panel(research.risks(pred.expected, pred.low, pred.high, pred.allotment_odds, ipo["sub_total"],
                                     f["nifty_vs_200dma"], f["recent_ipo_count"], impacts=impacts))
    with right:
        ui.section("Driver attribution", f"From the average IPO ({base_value:+.1f}%)")
        st.plotly_chart(charts.contributions(explained), use_container_width=True, config={"displayModeBar": False})

    ui.section("Comparable listings", "Closest past IPOs by QIB, HNI, retail and overall demand")
    similar = core.similar_ipos(history, pred.features)
    st.dataframe(
        similar.rename(columns={"ipo_name": "Issuer", "listing_date": "Listed", "sub_qib": "QIB", "sub_hni": "HNI",
                                "sub_rii": "Retail", "sub_total": "Overall", "target_gain_pct": "Day-one return"}),
        hide_index=True, use_container_width=True,
        column_config={"Listed": st.column_config.DateColumn(format="MMM YYYY"),
                       **{c: st.column_config.NumberColumn(format="%.1fx") for c in ["QIB", "HNI", "Retail", "Overall"]},
                       "Day-one return": st.column_config.NumberColumn(format="%+.1f%%")},
    )


def lock_call(entry):
    """Button callback: append the call to the ledger. Runs before the rerun, so the message survives it."""
    try:
        book = ledger.lock(ledger.load(), entry)
        ledger.save(book)
        row = book.iloc[-1]
        st.session_state["lock_message"] = ("ok", (f"Locked as call #{row['seq']} · fingerprint {row['hash'][:12]}. "
                                                  "Commit ledger/calls.csv to git for an outside timestamp."))
    except ValueError as error:
        st.session_state["lock_message"] = ("error", str(error))


def lock_panel(name, ipo, pred):
    """Offer to lock a new issue's call in the public track record (only before it lists)."""
    message = st.session_state.pop("lock_message", None)
    if message:
        (st.success if message[0] == "ok" else st.error)(message[1], icon=":material/lock:")
    today = datetime.now(UTC).astimezone(ledger.IST).date()
    book = ledger.load()
    same = book[book["ipo_name"].str.casefold().str.split().str.join(" ") == " ".join(name.split()).casefold()]
    if not name.strip():
        ui.lockbox("Lock this call", "Add the issuer name above to lock this call in the public track record.")
    elif len(same):
        r = same.iloc[0]
        ui.lockbox(f"Already on the record as call #{r['seq']}",
                   f"{r['call'].title()} at {r['expected']:+.1f}%, locked {r['locked_at'][:10]}. "
                   "Calls cannot be replaced, so the record cannot be cherry-picked.")
    elif ipo["listing_date"] <= today:
        ui.lockbox("Too late to lock", "Calls can only be locked before the listing date (India time).")
    else:
        entry = {"ipo_name": name, **{k: ipo[k] for k in FIELDS}, "expected": pred.expected, "low": pred.low,
                 "high": pred.high, "threshold": pred.threshold, "model": cache.model_id()}
        ui.lockbox("Put this call on the record",
                   "Locking writes the call, its range and the model version to the track record with a timestamp "
                   "and fingerprint. It cannot be edited or removed later, and it is scored after listing.")
        st.button("Lock this call", icon=":material/lock:", type="primary", on_click=lock_call, args=(entry,))


def show_past_check(row):
    wf = cache.walk_forward_predictions()
    at_the_time = wf[wf["ipo_id"] == row["ipo_id"]]
    actual = row["target_gain_pct"]
    if at_the_time.empty:
        st.info(f"Actual day-one return: **{actual:+.1f}%**. This listing predates 2019, so there is no "
                "out-of-sample call on record; the note above comes from a model that was trained on it.")
        return
    wf_row = at_the_time.iloc[0]
    inside = wf_row["low"] <= actual <= wf_row["high"]
    st.info(
        f"**Track record.** Actual day-one return **{actual:+.1f}%**. The call on record, made before listing, was "
        f"**{wf_row['random_forest']:+.1f}%** with a range of {wf_row['low']:+.0f}% to {wf_row['high']:+.0f}%: "
        f"the outcome landed {'inside' if inside else 'outside'} the range. (The note above uses today's model, "
        "which has since seen this IPO.)",
        icon=":material/verified:" if inside else ":material/info:",
    )


def render():
    deploy, rule, explainer = cache.models()
    history = cache.history()
    nifty, vix, note = cache.market()
    ui.page_header("Research note", "Listing-day call",
                   "Enter the final-day book for any mainboard issue. The desk returns a Subscribe or Avoid call with "
                   "an expected listing return, a calibrated bull and bear case, and the drivers behind it.")

    start, past_row = pick_past_ipo(history)
    name, ipo, submitted = input_form(start)
    if past_row is not None and any(ipo[k] != start[k] for k in FIELDS):
        past_row = None  # inputs were edited, so it's no longer that IPO

    if not core.is_valid_subscription([ipo[k] for k in ["sub_qib", "sub_hni", "sub_rii", "sub_total"]]):
        st.error("Subscription figures must be zero or more.")
        return

    with st.expander("Market context", expanded=False, icon=":material/monitoring:"):
        count, mean_gain = recent_market_inputs(history, ipo["listing_date"])
        features = core.build_features(ipo, nifty, vix, count, mean_gain)
        show_market(features, note)

    current = (name, tuple(ipo.values()))
    if submitted:
        st.session_state["note_for"] = current
    submitted = submitted or st.session_state.get("note_for") == current  # keep the note up after a button press
    if not submitted and past_row is None:
        st.caption("Enter the issue details and press **Generate research note**, or pick a past issue above.")
        return

    pred = core.predict(deploy, rule, features, ipo["sub_rii"])
    explained, base_value = core.explain(deploy, explainer, features)
    show_note(name or (past_row["ipo_name"] if past_row is not None else ""), ipo, pred, past_row, explained,
              base_value, history)
