"""Track record: the hash-chained ledger of calls, scored against what actually happened."""

import math
from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import charts, ui
from src import ledger

VIEWS = {"live": "Locked before listing", "forward_test": "Forward test · 78 IPOs"}


def pct(value, digits=0):
    return "–" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.{digits}f}%"


def scorecard_strip(card):
    if not card["scored"]:
        ui.kpis([("Calls locked", f"{card['calls']}", f"{card['pending']} awaiting listing"),
                 ("Scored", "0", "results appear after listing day")])
        return
    avg = (f"avg {card['subscribe_avg_gain']:+.1f}% on listing day" if card["subscribe"] else "no subscribe calls")
    ui.kpis([
        ("Calls right", pct(card["accuracy"]), f"{card['correct']} of {card['scored']} scored · {card['pending']} pending"),
        ("Subscribe calls listed up", pct(card["subscribe_hit_rate"]), f"{card['subscribe']} calls · {avg}"),
        ("Losses avoided", f"{card['losses_avoided']} of {card['losses_avoided'] + card['losses_taken']}",
         "below-issue listings flagged Avoid"),
        ("Inside 80% range", pct(card["in_range"] / card["scored"] * 100), f"miss {card['mae']:.1f} pts on average"),
    ])


def outcome_chart(scored):
    fig = go.Figure()
    dates = pd.to_datetime(scored["listing_date"])
    fig.add_trace(go.Scatter(
        x=[d for d in dates for _ in range(3)],
        y=[v for lo, hi in zip(scored["low"], scored["high"], strict=True) for v in (lo, hi, None)],
        mode="lines", line={"color": "#d5dbe3", "width": 3}, name="80% range", hoverinfo="skip"))
    for call, color, symbol in [("SUBSCRIBE", charts.UP, "circle"), ("AVOID", charts.DOWN, "x")]:
        part = scored[scored["call"] == call]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(part["listing_date"]), y=part["actual_gain_pct"], mode="markers",
            name=f"{call.title()} call · actual",
            marker={"size": 9, "color": color, "symbol": symbol, "line": {"color": charts.BG, "width": 1.5}},
            customdata=part[["ipo_name", "expected", "low", "high"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>%{x|%d %b %Y}<br>" + call.title() +
                          " · expected %{customdata[1]:+.1f}%<br>range %{customdata[2]:+.0f}% to %{customdata[3]:+.0f}%"
                          "<br>actual %{y:+.1f}%<extra></extra>"))
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1, line_dash="dot")
    fig.update_yaxes(title="Listing-day return (%)", ticksuffix="%")
    return charts.style(fig, height=400)


def ledger_table(book):
    status = book.apply(lambda r: "Pending" if pd.isna(r["actual_gain_pct"]) else
                        ("✓ Right" if (r["call"] == "SUBSCRIBE") == (r["actual_gain_pct"] > 0) else "✗ Wrong"), axis=1)
    locked = pd.to_datetime(book["locked_at"]).dt.tz_convert(ledger.IST).dt.strftime("%d %b %Y %H:%M")
    table = pd.DataFrame({
        "#": book["seq"], "Locked (IST)": locked, "Issuer": book["ipo_name"],
        "Listing": pd.to_datetime(book["listing_date"]), "Call": book["call"].str.title(),
        "Expected %": book["expected"], "Range": book.apply(lambda r: f"{r['low']:+.0f}% to {r['high']:+.0f}%", axis=1),
        "Actual %": book["actual_gain_pct"], "Result": status, "Fingerprint": book["hash"].str[:12],
    }).sort_values("#", ascending=False)
    st.dataframe(table, hide_index=True, use_container_width=True, height=min(460, 38 + 35 * len(table)),
                 column_config={"Listing": st.column_config.DateColumn(format="DD MMM YYYY"),
                                "Expected %": st.column_config.NumberColumn(format="%+.1f"),
                                "Actual %": st.column_config.NumberColumn(format="%+.1f")})


def record_results(book):
    today = datetime.now(UTC).astimezone(ledger.IST).date()
    due = book[book["actual_gain_pct"].isna() & (pd.to_datetime(book["listing_date"]).dt.date <= today)]
    if due.empty:
        st.caption("No calls are waiting for a result. Results can be added from the listing date onwards.")
        return
    with st.form("result"):
        labels = {f"#{r.seq} · {r.ipo_name} · listed {r.listing_date}": int(r.seq) for r in due.itertuples()}
        pick = st.selectbox("Call", list(labels))
        opening = st.number_input("Listing-day open on NSE (₹)", min_value=0.01, value=100.0, step=0.5)
        if st.form_submit_button("Record result", type="primary"):
            try:
                ledger.save(ledger.record_result(ledger.load(), labels[pick], float(opening)))
                st.success("Result recorded.")
                st.rerun()
            except (ValueError, KeyError) as error:
                st.error(str(error))
    st.caption("Or run `python -m src.ledger score` after refreshing the IPO data to fill results automatically.")


def render():
    book = ledger.load()
    ui.page_header("Track record", "Every call, on the record",
                   "Calls are locked before the IPO lists, chained by fingerprint so no past call can be edited or "
                   "quietly dropped, and scored against the listing-day open. Wins and misses both stay.")

    problems = ledger.verify(book)
    first = (pd.to_datetime(book["locked_at"]).min().tz_convert(ledger.IST).strftime("%d %b %Y")
             if len(book) else "–")
    ui.ledger_seal(problems, len(book), book.sort_values("seq")["hash"].iloc[-1] if len(book) else "", first)
    ui.steps([
        ("Lock", ("Before listing, the call, its range and the exact model version are written to the ledger "
                 "with a timestamp.")),
        ("Chain", "Each row's SHA-256 fingerprint covers the row before it, so edits or deletions break the chain."),
        ("Score", "After listing, the NSE open is added. Right or wrong, the call stays on the record."),
    ])

    counts = book["source"].value_counts()
    default = "live" if counts.get("live", 0) or not counts.get("forward_test", 0) else "forward_test"
    pick = st.segmented_control("Record", list(VIEWS), default=default,
                                format_func=lambda k: f"{VIEWS[k]} ({counts.get(k, 0)})") or default
    view = book[book["source"] == pick].reset_index(drop=True)
    if pick == "forward_test":
        st.caption("The model was frozen before these IPOs listed, but the calls were written to the ledger after "
                   "listing. Treat them as a backtest; only 'Locked before listing' calls are true live calls.")

    if view.empty:
        ui.lockbox("No live calls locked yet",
                   "Open the Research Note page, enter an issue that has not listed yet, and press "
                   "'Lock this call'. It will appear here with its fingerprint, then get scored after listing.")
        return

    scorecard_strip(ledger.scorecard(view))
    scored = view[view["actual_gain_pct"].notna()]
    if len(scored):
        ui.section("Call vs outcome", "Grey bar: the 80% range given before listing · dot: what actually happened")
        st.plotly_chart(outcome_chart(scored), use_container_width=True, config={"displayModeBar": False})

    pending = view[view["actual_gain_pct"].isna()]
    if len(pending):
        ui.section("Awaiting listing", f"{len(pending)} locked call(s)")
        ledger_table(pending)

    ui.section("Ledger", "Newest first · right = Subscribe that listed up, or Avoid that listed flat or down")
    ledger_table(view)

    left, right = st.columns(2)
    with left, st.expander("Record a listing result", icon=":material/edit_note:"):
        record_results(book)
    with right, st.expander("Check it yourself", icon=":material/verified_user:"):
        st.markdown("Download the ledger and run `python -m src.ledger verify`. It recomputes every fingerprint "
                    "from the row's contents and the previous fingerprint. The file is committed to git after each "
                    "lock, so the commit history is a second, outside timestamp.")
        st.download_button("Download ledger (CSV)", book[ledger.COLUMNS].to_csv(index=False).encode("utf-8"),
                           "primary_desk_calls.csv", "text/csv", use_container_width=True)
