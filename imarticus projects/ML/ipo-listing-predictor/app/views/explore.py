import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app import cache, charts, ui


def render():
    df = cache.history()
    ui.page_header("Market monitor", "Primary market, 2010 to today",
                   f"Every Indian mainboard IPO from 2010 to {df['listing_date'].max():%B %Y}: final-day book and "
                   "day-one return. Filter by year and demand to see how the cycle has moved.")

    a, b = st.columns([2, 1])
    years = a.slider("Listing year", int(df.year.min()), int(df.year.max()), (2019, int(df.year.max())))
    min_sub = b.select_slider("Minimum total subscription", options=[0, 1, 3, 10, 30, 100], value=0,
                              format_func=lambda v: f"{v}x")
    view = df[df["year"].between(*years) & (df["sub_total"] >= min_sub)]
    if view.empty:
        st.warning("No IPOs match these filters.")
        return

    gain = view["target_gain_pct"]
    ui.kpis([
        ("Listings", f"{len(view)}", f"{years[0]}–{years[1]}"),
        ("Median day-one return", ui.signed(gain.median()), "at the listing open"),
        ("Listed below issue", f"{(gain < 0).mean():.0%}", "share of listings"),
        ("Returned over 15%", f"{(gain > 15).mean():.0%}", "share of listings"),
        ("Median book", f"{view['sub_total'].median():,.1f}x", "overall subscription"),
    ])

    colors = np.where(gain >= 0, charts.UP, charts.DOWN)
    ui.section("Demand vs day-one return", "Each dot is one IPO; hover for details")
    fig = go.Figure(go.Scatter(
        x=view["sub_total"], y=gain, mode="markers",
        marker=dict(size=8, color=colors, opacity=0.7, line=dict(color=charts.BG, width=1)),
        customdata=np.stack([view["ipo_name"], view["listing_date"].dt.strftime("%d %b %Y")], axis=1),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Subscribed %{x:.1f}x<br>"
                      "Listing gain %{y:+.1f}%<extra></extra>",
    ))
    ticks = [0.3, 1, 3, 10, 30, 100, 300]
    fig.update_xaxes(type="log", title="Total subscription (times, log scale)", tickvals=ticks,
                     ticktext=[f"{t:g}x" for t in ticks])
    fig.update_yaxes(title="Listing-day gain (%)", ticksuffix="%")
    st.plotly_chart(charts.style(fig, height=420), use_container_width=True, config={"displayModeBar": False})

    by_year = view.groupby("year")["target_gain_pct"].median()
    year_fig = go.Figure(go.Bar(x=by_year.index, y=by_year.values, marker_line_width=0,
                                marker_color=[charts.UP if v >= 0 else charts.DOWN for v in by_year.values],
                                hovertemplate="%{x}: median %{y:+.1f}%<extra></extra>"))
    year_fig.update_yaxes(title="Median return (%)", ticksuffix="%")
    ui.section("The cycle", "Median day-one return by listing year")
    st.plotly_chart(charts.style(year_fig, height=300), use_container_width=True, config={"displayModeBar": False})

    ui.section("Listings", "Newest first")
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
