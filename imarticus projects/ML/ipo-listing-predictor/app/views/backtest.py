import plotly.graph_objects as go
import streamlit as st

from app import cache, charts, ui
from src.backtest import LOT_VALUE, allotment_chance, summarize

PERIODS = ["Jun – Nov 2026 (forward test)", "2024 – May 2026", "2019–2023"]
NOTES = {
    "Jun – Nov 2026 (forward test)": "78 IPOs collected after every setting was frozen. Edge over the 30x rule held in "
                                     "97% of bootstrap resamples; edge over applying to everything was not significant.",
    "2024 – May 2026": "Out of sample. Edge over applying to everything: bootstrap 95% interval ₹1,241 to ₹11,978; "
                       "edge over the 30x rule not significant.",
    "2019–2023": "In sample for the threshold: the −2% cut-off was picked on these years.",
}


def render():
    ui.page_header("Strategy performance", "Does following the desk pay?",
                   f"One minimum lot (₹{LOT_VALUE:,}) per application, sold at the listing-day open, with the retail "
                   "allotment lottery priced in. Every call was made before the IPO listed.")

    wf = cache.walk_forward_predictions().merge(cache.history()[["ipo_id", "sub_rii"]], on="ipo_id")
    _, rule, _ = cache.models()
    period = st.segmented_control("Period", PERIODS, default=PERIODS[0])
    frame = wf[wf["period"] == (period or PERIODS[0])].sort_values("listing_date").reset_index(drop=True)
    threshold = st.slider("Subscribe when expected listing return is at least (%)", -10.0, 30.0,
                          float(rule["model_threshold"]), 0.5,
                          help=f"The desk's rule, {rule['model_threshold']:+g}%, was picked on 2019–2023.")

    plans = {
        "Subscribe to every IPO": frame["random_forest"] > -1e9,
        "Only if 30x+ subscribed": frame["sub_total"] >= 30,
        "Follow the desk": frame["random_forest"] >= threshold,
    }
    stats = {name: summarize(frame, mask) for name, mask in plans.items()}
    ui.kpis([(name, f"₹{s['expected_profit']:,.0f}",
              f"{s['applied']} applications · {s['hit_rate']:.0f}% listed up") for name, s in stats.items()]
            + [("Losses avoided", f"{stats['Follow the desk']['losses_avoided']}", "below-issue listings skipped")])

    per_ipo = frame["target_gain_pct"] / 100 * LOT_VALUE * frame["sub_rii"].map(allotment_chance)
    fig = go.Figure()
    for (name, mask), color in zip(plans.items(), [charts.MUTED, charts.BLUE, charts.ACCENT], strict=True):
        path = per_ipo.where(mask, 0).cumsum()
        fig.add_trace(go.Scatter(x=frame["listing_date"], y=path, name=name, mode="lines",
                                 line=dict(color=color, width=2.6 if name == "Follow the desk" else 1.8),
                                 customdata=frame["ipo_name"],
                                 hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>₹%{y:,.0f}<extra>" + name + "</extra>"))
    fig.update_yaxes(title="Cumulative expected profit", tickprefix="₹", tickformat=",.0f")
    ui.section("Equity curve", "Cumulative expected profit, one lot per application")
    st.plotly_chart(charts.style(fig, height=400), use_container_width=True, config={"displayModeBar": False})

    ui.section("Strategy detail")
    st.dataframe([{"Strategy": k, "Expected profit ₹": s["expected_profit"], "Applications": s["applied"],
                   "Listed up": s["hit_rate"], "Avg return %": s["avg_gain"], "Worst %": s["worst_gain"],
                   "Expected allotments": s["expected_allotments"]} for k, s in stats.items()],
                 hide_index=True, use_container_width=True, column_config={
                     "Expected profit ₹": st.column_config.NumberColumn(format="₹%,.0f"),
                     "Listed up": st.column_config.NumberColumn(format="%.0f%%"),
                     "Avg return %": st.column_config.NumberColumn(format="%+.1f"),
                     "Worst %": st.column_config.NumberColumn(format="%+.1f"),
                     "Expected allotments": st.column_config.NumberColumn(format="%.1f")})
    st.caption(NOTES[period or PERIODS[0]] + " The 30x rule picks issues that list high but almost never allot to "
               "retail. Moving the slider is hindsight; the fair number is at the desk's rule.")
