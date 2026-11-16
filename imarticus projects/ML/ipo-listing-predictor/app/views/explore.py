import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app import cache, charts, ui
from src.viz import BLUE, LOSS, NEUTRAL


def render():
    df = cache.history()
    ui.hero("Data", f"{len(df)} IPOs, one view",
            f"Every Indian mainboard IPO from 2010 to {df['listing_date'].max():%B %Y} with its subscription and "
            "listing-day gain. Filter by year and demand to see how the market has changed.")

    a, b = st.columns([2, 1])
    years = a.slider("Listing year", int(df.year.min()), int(df.year.max()), (2019, int(df.year.max())))
    min_sub = b.select_slider("Minimum total subscription", options=[0, 1, 3, 10, 30, 100], value=0,
                              format_func=lambda v: f"{v}x")
    view = df[df["year"].between(*years) & (df["sub_total"] >= min_sub)]
    if view.empty:
        st.warning("No IPOs match these filters.")
        return

    gain = view["target_gain_pct"]
    ui.cards([
        ("IPOs", f"{len(view)}", f"{years[0]}–{years[1]}", "blue"),
        ("Median gain", f"{gain.median():+.1f}%", "listing-day open", "good" if gain.median() >= 0 else "bad"),
        ("Listed below offer", f"{(gain < 0).mean():.0%}", "of IPOs in view", "bad"),
        ("Gain above 15%", f"{(gain > 15).mean():.0%}", "of IPOs in view", "good"),
    ])

    colors = np.where(gain >= 0, BLUE, LOSS)
    fig = go.Figure(go.Scatter(
        x=view["sub_total"], y=gain, mode="markers",
        marker=dict(size=8, color=colors, opacity=0.65, line=dict(color="white", width=1)),
        customdata=np.stack([view["ipo_name"], view["listing_date"].dt.strftime("%d %b %Y")], axis=1),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Subscribed %{x:.1f}x<br>"
                      "Listing gain %{y:+.1f}%<extra></extra>",
    ))
    ticks = [0.3, 1, 3, 10, 30, 100, 300]
    fig.update_xaxes(type="log", title="Total subscription (times, log scale)", tickvals=ticks,
                     ticktext=[f"{t:g}x" for t in ticks])
    fig.update_yaxes(title="Listing-day gain (%)", ticksuffix="%")
    st.plotly_chart(charts.style(fig, height=420, title="Subscription vs listing gain"), use_container_width=True)

    by_year = view.groupby("year")["target_gain_pct"].median()
    year_fig = go.Figure(go.Bar(x=by_year.index, y=by_year.values,
                                marker_color=[BLUE if v >= 0 else LOSS for v in by_year.values],
                                hovertemplate="%{x}: median %{y:+.1f}%<extra></extra>"))
    year_fig.update_yaxes(title="Median gain (%)", ticksuffix="%")
    year_fig.add_hline(y=0, line_color=NEUTRAL, line_width=1)
    st.plotly_chart(charts.style(year_fig, height=300, title="Median listing gain by year"), use_container_width=True)

    ui.section("All IPOs in view", "Sorted by listing date, newest first.")
    table = view.sort_values("listing_date", ascending=False)[
        ["ipo_name", "listing_date", "offer_price", "issue_size_cr", "sub_qib", "sub_hni", "sub_rii", "sub_total",
         "target_gain_pct", "target_source"]]
    st.dataframe(
        table.rename(columns={"ipo_name": "IPO", "listing_date": "Listed", "offer_price": "Offer ₹",
                              "issue_size_cr": "Size ₹ cr", "sub_qib": "QIB", "sub_hni": "HNI", "sub_rii": "Retail",
                              "sub_total": "Total", "target_gain_pct": "Listing gain %", "target_source": "Source"}),
        hide_index=True, use_container_width=True, height=420,
        column_config={"Listed": st.column_config.DateColumn(format="DD MMM YYYY"),
                       "Listing gain %": st.column_config.NumberColumn(format="%+.1f")},
    )
    st.caption("Source `nse_open_yahoo`: listing price verified against the NSE open. "
               "`kaggle_unverified`: company no longer on NSE's list, Kaggle's figure kept.")
