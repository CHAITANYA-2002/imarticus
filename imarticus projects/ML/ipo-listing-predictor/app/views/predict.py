from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import cache, charts, core, ui

NEW_IPO = "New IPO (enter details)"
FIELDS = ["listing_date", "offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total"]


def defaults():
    return {"name": "", "listing_date": date.today() + timedelta(days=3), "offer_price": 250.0,
            "issue_size_cr": 800.0, "sub_qib": 40.0, "sub_hni": 25.0, "sub_rii": 8.0, "sub_total": 25.0}


def pick_past_ipo(history):
    names = [NEW_IPO] + history.sort_values("listing_date", ascending=False)["ipo_name"].tolist()
    choice = st.selectbox("Start from", names, help="Pick a past IPO to see how the model would have called it.")
    if choice == NEW_IPO:
        return defaults(), None
    row = history[history["ipo_name"] == choice].iloc[0]
    return core.readable_inputs(row), row


def input_form(start):
    with st.form("ipo"):
        name = st.text_input("IPO name (optional)", value=start["name"])
        a, b, c = st.columns(3)
        listing_date = a.date_input("Expected listing date", value=start["listing_date"])
        offer_price = b.number_input("Offer price, upper band (₹)", min_value=1.0, value=start["offer_price"], step=1.0)
        issue_size = c.number_input("Issue size (₹ crore)", min_value=1.0, value=start["issue_size_cr"], step=10.0)
        st.markdown("**Final-day subscription (times)**")
        q, h, r, t = st.columns(4)
        sub_qib = q.number_input("QIB", min_value=0.0, value=start["sub_qib"], step=0.5)
        sub_hni = h.number_input("HNI / NII", min_value=0.0, value=start["sub_hni"], step=0.5)
        sub_rii = r.number_input("Retail", min_value=0.0, value=start["sub_rii"], step=0.5)
        sub_total = t.number_input("Total", min_value=0.0, value=start["sub_total"], step=0.5)
        submitted = st.form_submit_button("Predict listing gain", type="primary", use_container_width=True)
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
        st.warning(
            f"The IPO history in this app ends on {data_end:%d %b %Y}, so the recent-IPO numbers below are "
            "filled with last year's typical values. For a live call, replace them with the actual count "
            "and average listing gain of mainboard IPOs in the last 90 days (from NSE or Chittorgarh).",
            icon=":material/warning:",
        )
    a, b = st.columns(2)
    count = a.number_input("Mainboard IPOs listed in the last 90 days", min_value=0, value=int(count), step=1)
    mean_gain = b.number_input("Their average listing gain (%)",
                               value=float(0 if pd.isna(mean_gain) else round(mean_gain, 1)), step=0.5)
    return count, mean_gain


def show_market(features, note):
    f = features.iloc[0]
    st.caption(f"Market data: {note}. Measured 7 days before listing, as in training.")
    tone = lambda v: "good" if v >= 0 else "bad"  # noqa: E731
    ui.cards([
        ("NIFTY · 1 month", f"{f['nifty_ret_1m']:+.1f}%", "return", tone(f["nifty_ret_1m"])),
        ("NIFTY · 3 months", f"{f['nifty_ret_3m']:+.1f}%", "return", tone(f["nifty_ret_3m"])),
        ("NIFTY vs 200-DMA", f"{f['nifty_vs_200dma']:+.1f}%", "trend", tone(f["nifty_vs_200dma"])),
        ("India VIX", f"{f['vix']:.1f}", "volatility", ""),
    ])


def odds_text(odds):
    return f"{odds:.0%}" if odds >= 0.1 else f"1 in {1 / odds:,.0f}"


def show_result(name, pred, past_row, explained, base_value, history):
    ui.result_card(name, pred.expected, pred.low, pred.high, pred.apply, pred.threshold)
    ui.cards([
        ("Allotment odds", odds_text(pred.allotment_odds), "one-lot retail application", "blue"),
        ("Expected value", f"₹{pred.expected_value:,.0f}", "gain × ₹15,000 × odds",
         "good" if pred.expected_value >= 0 else "bad"),
        ("Best case (P90)", f"{pred.high:+.0f}%", "upper end of the range", ""),
        ("Worst case (P10)", f"{pred.low:+.0f}%", "lower end of the range", ""),
    ])

    actual = past_row["target_gain_pct"] if past_row is not None else None
    st.plotly_chart(charts.range_bar(pred, actual), use_container_width=True, config={"displayModeBar": False})
    if past_row is not None:
        show_past_check(past_row)

    left, right = st.columns([1.1, 1])
    with left:
        ui.section("Why this number", f"Starts from the average IPO ({base_value:+.1f}%); each bar pushes it up or down.")
        st.plotly_chart(charts.contributions(explained), use_container_width=True, config={"displayModeBar": False})
    with right:
        ui.section("IPOs with similar demand", "Matched on QIB, HNI, retail and total subscription.")
        similar = core.similar_ipos(history, pred.features)
        st.dataframe(
            similar[["ipo_name", "sub_total", "target_gain_pct", "listing_date"]].rename(
                columns={"ipo_name": "IPO", "sub_total": "Subscribed", "target_gain_pct": "Listing gain",
                         "listing_date": "Listed"}),
            hide_index=True, use_container_width=True,
            column_config={"IPO": st.column_config.TextColumn(width="medium"),
                           "Subscribed": st.column_config.NumberColumn(format="%.1fx"),
                           "Listing gain": st.column_config.NumberColumn(format="%+.1f%%"),
                           "Listed": st.column_config.DateColumn(format="MMM YYYY")},
        )


def show_past_check(row):
    wf = cache.walk_forward_predictions()
    at_the_time = wf[wf["ipo_id"] == row["ipo_id"]]
    actual = row["target_gain_pct"]
    if at_the_time.empty:
        st.info(f"Actual listing gain: **{actual:+.1f}%**. This IPO is from before 2019, so there's no "
                "out-of-sample prediction for it; the numbers above come from a model that was trained on it.")
        return
    wf_row = at_the_time.iloc[0]
    inside = wf_row["low"] <= actual <= wf_row["high"]
    st.info(
        f"Actual listing gain: **{actual:+.1f}%**. The model above was trained on all IPOs, including this one. "
        f"At the time (walk-forward, before it listed) the model said **{wf_row['random_forest']:+.1f}%** with a "
        f"range of {wf_row['low']:+.0f}% to {wf_row['high']:+.0f}%, so the actual gain was "
        f"{'inside' if inside else 'outside'} that range.",
        icon=":material/check_circle:" if inside else ":material/info:",
    )


def render():
    deploy, rule, explainer = cache.models()
    history = cache.history()
    ui.hero(
        "Machine learning · Indian IPOs",
        "Will this IPO list with a gain?",
        "Enter the final-day subscription and get the expected listing-day gain, an honest 80% range, "
        "and an Apply or Skip call, with the reasons behind it.",
        chips=[f"<b>{len(history)}</b> IPOs since 2010", "<b>0.72</b> ranking on 78 unseen IPOs",
               "<b>79–87%</b> range hit rate out of sample"],
    )

    nifty, vix, note = cache.market()

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

    if not submitted and past_row is None:
        st.caption("Fill in the details and press **Predict listing gain**, or pick a past IPO above.")
        return

    pred = core.predict(deploy, rule, features, ipo["sub_rii"])
    explained, base_value = core.explain(deploy, explainer, features)
    show_result(name, pred, past_row, explained, base_value, history)
