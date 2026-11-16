import plotly.graph_objects as go
import streamlit as st

from app import cache, charts, ui
from src.backtest import LOT_VALUE, allotment_chance, summarize
from src.viz import BLUE, NEUTRAL, ORANGE


def render():
    ui.hero("Backtest", "Would following the model have paid?",
            f"One minimum lot (₹{LOT_VALUE:,}) per application, sold at the listing-day open, with the retail "
            "allotment lottery built in. Every prediction was made before the IPO listed.")

    wf = cache.walk_forward_predictions().merge(cache.history()[["ipo_id", "sub_rii"]], on="ipo_id")
    _, rule, _ = cache.models()
    period = st.radio("Period", ["2024–2026 (out of sample)", "2019–2023 (used to pick the threshold)"],
                      horizontal=True)
    frame = wf[wf["year"] >= 2024] if period.startswith("2024") else wf[wf["year"] < 2024]
    frame = frame.sort_values("listing_date").reset_index(drop=True)

    threshold = st.slider("Apply when the model's expected gain is at least (%)", -10.0, 30.0,
                          float(rule["model_threshold"]), 0.5,
                          help=f"The backtest picked {rule['model_threshold']:+g}% on 2019–2023.")

    plans = {
        "Apply to every IPO": frame["random_forest"] > -1e9,
        "Only if 30x+ subscribed": frame["sub_total"] >= 30,
        "Follow the model": frame["random_forest"] >= threshold,
    }
    rows = []
    for name, mask in plans.items():
        s = summarize(frame, mask)
        rows.append({"Strategy": name, "Expected profit ₹": s["expected_profit"], "Applied": s["applied"],
                     "Listed with gain": s["hit_rate"], "Avg gain %": s["avg_gain"],
                     "Expected allotments": s["expected_allotments"], "Losses avoided": s["losses_avoided"]})
    tones = {"Apply to every IPO": "", "Only if 30x+ subscribed": "", "Follow the model": "good"}
    ui.cards([(r["Strategy"], f"₹{r['Expected profit ₹']:,.0f}",
               f"{r['Applied']} applications · {r['Listed with gain']:.0f}% listed up", tones[r["Strategy"]])
              for r in rows])
    st.dataframe(rows, hide_index=True, use_container_width=True, column_config={
        "Listed with gain": st.column_config.NumberColumn(format="%.0f%%"),
        "Avg gain %": st.column_config.NumberColumn(format="%+.1f"),
        "Expected allotments": st.column_config.NumberColumn(format="%.1f"),
        "Expected profit ₹": st.column_config.NumberColumn(format="₹%,.0f"),
    })

    per_ipo = frame["target_gain_pct"] / 100 * LOT_VALUE * frame["sub_rii"].map(allotment_chance)
    fig = go.Figure()
    for (name, mask), color in zip(plans.items(), [NEUTRAL, ORANGE, BLUE], strict=True):
        path = per_ipo.where(mask, 0).cumsum()
        fig.add_trace(go.Scatter(x=frame["listing_date"], y=path, name=name, mode="lines",
                                 line=dict(color=color, width=2.5),
                                 customdata=frame["ipo_name"],
                                 hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>₹%{y:,.0f}<extra>" + name + "</extra>"))
    fig.update_yaxes(title="Cumulative expected profit", tickprefix="₹", tickformat=",.0f")
    ui.section("Expected profit over time", "Cumulative, one lot per application.")
    st.plotly_chart(charts.style(fig, height=400), use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        "**Reading this.** The 30x rule picks IPOs that list high, but they are so oversubscribed that a retail "
        "applicant rarely gets shares. Against applying to every IPO, the model's 2024–2026 edge is statistically "
        "clear (bootstrap 95% interval ₹1,241 to ₹11,978 at the −2% threshold). Against the 30x rule, it earns more "
        "on average but the difference is not significant. Moving the slider on 2024–2026 is hindsight: the fair "
        "number is the one at the threshold picked on 2019–2023."
    )
