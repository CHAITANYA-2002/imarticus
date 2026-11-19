"""Planner: compare several open issues side by side, then plan how to apply (retail vs small HNI)."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import cache, charts, core, insights, ui

MANUAL = "Enter my own figures"


def example_rows():
    listing = date.today() + timedelta(days=4)
    return pd.DataFrame([
        {"Issuer": "Issue A", "Listing date": listing, "Offer ₹": 320.0, "Size ₹ cr": 1200.0,
         "QIB x": 95.0, "HNI x": 60.0, "Retail x": 14.0, "Overall x": 55.0},
        {"Issuer": "Issue B", "Listing date": listing, "Offer ₹": 145.0, "Size ₹ cr": 450.0,
         "QIB x": 6.0, "HNI x": 9.0, "Retail x": 7.0, "Overall x": 7.0},
        {"Issuer": "Issue C", "Listing date": listing + timedelta(days=1), "Offer ₹": 610.0, "Size ₹ cr": 3200.0,
         "QIB x": 1.4, "HNI x": 0.6, "Retail x": 1.1, "Overall x": 1.1},
    ])


def feature_builder(history, nifty, vix):
    def build(ipo):
        count, mean_gain = core.recent_ipo_stats(history, pd.Timestamp(ipo["listing_date"]))
        return core.build_features(ipo, nifty, vix, count, mean_gain)
    return build


def compare_section(deploy, rule, history, nifty, vix):
    ui.section("Compare issues", "Edit the table: one row per issue, final-day book in times subscribed")
    table = st.data_editor(
        example_rows(), num_rows="dynamic", hide_index=True, use_container_width=True, key="compare_table",
        column_config={"Listing date": st.column_config.DateColumn(format="DD MMM YYYY", required=True),
                       "Offer ₹": st.column_config.NumberColumn(min_value=1.0, format="₹%.0f"),
                       "Size ₹ cr": st.column_config.NumberColumn(min_value=1.0, format="%.0f"),
                       **{c: st.column_config.NumberColumn(min_value=0.0, format="%.1fx")
                          for c in ["QIB x", "HNI x", "Retail x", "Overall x"]}})
    results, skipped = insights.compare_ipos(table, feature_builder(history, nifty, vix), deploy, rule)
    for message in skipped:
        st.caption(f"Skipped {message}.")
    if results.empty:
        st.info("Add at least one complete row to compare.")
        return results

    best = results.iloc[0]
    ui.kpis([
        ("Best expected value", best["Issuer"], f"₹{best['ev']:,.0f} per lot after allotment odds"),
        ("Subscribe calls", f"{(results['call'] == 'SUBSCRIBE').sum()} of {len(results)}",
         f"threshold {rule['model_threshold']:+g}%"),
        ("Lowest loss chance", results.loc[results["loss_chance"].idxmin(), "Issuer"],
         f"{results['loss_chance'].min():.0%} chance of listing below issue"),
    ])
    st.plotly_chart(charts.compare_chart(results), use_container_width=True, config={"displayModeBar": False})
    st.dataframe(pd.DataFrame({
        "Rank": results["rank"], "Issuer": results["Issuer"], "Call": results["call"].str.title(),
        "Expected %": results["expected"],
        "Range": [f"{a:+.0f}% to {b:+.0f}%" for a, b in zip(results["low"], results["high"], strict=True)],
        "Loss chance": results["loss_chance"] * 100, "Retail odds": results["odds"] * 100,
        "Expected ₹ / lot": results["ev"],
    }), hide_index=True, use_container_width=True, column_config={
        "Expected %": st.column_config.NumberColumn(format="%+.1f"),
        "Loss chance": st.column_config.NumberColumn(format="%.0f%%"),
        "Retail odds": st.column_config.NumberColumn(format="%.1f%%"),
        "Expected ₹ / lot": st.column_config.NumberColumn(format="₹%.0f")})
    st.caption("Ranked by expected value of one retail lot: expected gain × lot value × retail allotment odds. "
               "A hot issue with tiny odds can rank below a calmer one you are likely to get.")
    return results


def allotment_section(results, rule):
    ui.section("Allotment planner", "Retail lot or small-HNI application, across family accounts")
    names = [MANUAL, *results["Issuer"].tolist()] if not results.empty else [MANUAL]
    pick = st.selectbox("Use figures from", names, index=1 if len(names) > 1 else 0)
    row = results[results["Issuer"] == pick].iloc[0] if pick != MANUAL else None

    a, b, c = st.columns(3)
    gain = a.number_input("Expected listing gain (%)", value=round(float(row["expected"]), 1) if row is not None
                          else 15.0, step=0.5, key=f"gain_{pick}")
    sub_rii = b.number_input("Retail subscription (x)", min_value=0.0, step=0.5, key=f"rii_{pick}",
                             value=float(row["sub_rii"]) if row is not None else 10.0)
    sub_hni = c.number_input("HNI / NII subscription (x)", min_value=0.0, step=0.5, key=f"hni_{pick}",
                             value=float(row["sub_hni"]) if row is not None else 30.0)
    d, e = st.columns(2)
    lot = d.number_input("One lot costs (₹)", min_value=1_000, value=int(rule["lot_value"]), step=500)
    accounts = e.slider("Accounts (separate PANs) applying", 1, 10, 1)

    plan = insights.allotment_plan(lot, gain, sub_rii, sub_hni, accounts)
    retail, shni = plan.iloc[0], plan.iloc[1]
    better = retail if retail["Return on blocked money %"] >= shni["Return on blocked money %"] else shni
    ui.kpis([
        ("Retail: chance of at least one", f"{retail['Chance of at least one']:.1f}%",
         f"₹{retail['Money blocked ₹']:,.0f} blocked · expected ₹{retail['Expected profit ₹']:,.0f}"),
        ("Small HNI: chance of at least one", f"{shni['Chance of at least one']:.1f}%",
         f"₹{shni['Money blocked ₹']:,.0f} blocked · expected ₹{shni['Expected profit ₹']:,.0f}"),
        ("Better use of blocked money", better["Route"].split(" (")[0],
         f"{better['Return on blocked money %']:+.2f}% expected return on money blocked"),
    ])
    st.dataframe(plan, hide_index=True, use_container_width=True, column_config={
        **{c: st.column_config.NumberColumn(format="₹%.0f") for c in
           ["Per account ₹", "Money blocked ₹", "Profit if allotted ₹", "Expected profit ₹"]},
        "Chance per account": st.column_config.NumberColumn(format="%.1f%%"),
        "Chance of at least one": st.column_config.NumberColumn(format="%.1f%%"),
        "Expected allotments": st.column_config.NumberColumn(format="%.2f"),
        "Return on blocked money %": st.column_config.NumberColumn(format="%+.2f%%")})
    st.caption("Both routes are lotteries: retail odds ≈ 1 ÷ retail subscription, small-HNI odds ≈ 1 ÷ HNI "
               "subscription (the minimum application above ₹2 lakh is what gets allotted). One PAN can apply in "
               "only one category per issue. Money is blocked via UPI/ASBA, not spent, until allotment.")


def render():
    deploy, rule, _ = cache.models()
    history = cache.history()
    nifty, vix, _ = cache.market()
    ui.page_header("Planner", "Compare issues and plan your application",
                   "Line up the issues open this week, see which one the model rates best once allotment odds are "
                   "counted, then work out whether a retail lot or a small-HNI application gives you more.")
    results = compare_section(deploy, rule, history, nifty, vix)
    allotment_section(results, rule)
