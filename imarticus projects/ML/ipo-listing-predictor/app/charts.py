"""Plotly helpers styled for the light fintech theme."""

import plotly.graph_objects as go

UP = "#08875d"
DOWN = "#d23b3b"
ACCENT = "#08875d"
BLUE = "#4f46e5"
MUTED = "#94a3b8"
GRID = "#eef0f3"
TEXT = "#334155"
BG = "#ffffff"

FONT = dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=12.5, color=TEXT)


def style(fig, height=360, title=None):
    fig.update_layout(
        height=height, title=dict(text=title, x=0, font=dict(size=15, color=TEXT)) if title else None,
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=FONT,
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0, font=dict(color=TEXT)),
        hoverlabel=dict(bgcolor=BG, bordercolor="#e3e6eb", font=dict(color="#0f172a", family=FONT["family"])),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor="#d5d9e0", linecolor="#e3e6eb", tickfont=dict(color="#64748b"))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor="#d5d9e0", linecolor="#e3e6eb", tickfont=dict(color="#64748b"))
    return fig


def contributions(explained, top=8):
    shown = explained.head(top).iloc[::-1]
    colors = [UP if v >= 0 else DOWN for v in shown["impact"]]
    fig = go.Figure(go.Bar(
        x=shown["impact"], y=shown["feature"], orientation="h", marker_color=colors, marker_line_width=0,
        hovertemplate="%{y}: %{x:+.1f} pp<extra></extra>",
        text=[f"{v:+.1f}" for v in shown["impact"]], textposition="outside", cliponaxis=False,
        textfont=dict(family=FONT["family"], color=TEXT),
    ))
    reach = max(abs(shown["impact"].min()), abs(shown["impact"].max()), 1) * 1.35
    lo = -reach if shown["impact"].min() < 0 else -reach * 0.1
    hi = reach if shown["impact"].max() > 0 else reach * 0.1
    fig.update_xaxes(title="Push on expected return (pp)", range=[lo, hi])
    fig = style(fig, height=320)
    fig.update_layout(margin=dict(l=10, r=48, t=10, b=10))
    return fig


def range_bar(pred, actual=None):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=pred.low, x1=pred.high, y0=-0.28, y1=0.28,
                  fillcolor=ACCENT, opacity=0.12, line=dict(color=ACCENT, width=1))
    fig.add_trace(go.Scatter(x=[pred.expected], y=[0], mode="markers", name="Expected",
                             marker=dict(size=16, color=ACCENT, line=dict(color=BG, width=2)),
                             hovertemplate="Expected %{x:+.1f}%<extra></extra>"))
    if actual is not None:
        fig.add_trace(go.Scatter(x=[actual], y=[0], mode="markers", name="Actual",
                                 marker=dict(size=14, color=BLUE, symbol="diamond", line=dict(color=BG, width=2)),
                                 hovertemplate="Actual %{x:+.1f}%<extra></extra>"))
    fig.add_vline(x=0, line_color="#94a3b8", line_width=1, line_dash="dot")
    points = [pred.low, pred.high, 0] + ([actual] if actual is not None else [])
    pad = (max(points) - min(points)) * 0.08
    fig.update_yaxes(visible=False, range=[-0.6, 0.6])
    fig.update_xaxes(title="Listing-day return (%)", ticksuffix="%", range=[min(points) - pad, max(points) + pad])
    fig = style(fig, height=180)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1), margin=dict(t=30))
    return fig


def what_if_chart(curve, current, threshold, label):
    """Expected gain (line) and 80% range (band) as one group's subscription changes."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["value"], y=curve["high"], mode="lines", line=dict(width=0), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=curve["value"], y=curve["low"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(8,135,93,0.12)", name="80% range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=curve["value"], y=curve["expected"], mode="lines", name="Expected return", line=dict(color=ACCENT, width=2.4),
        customdata=curve[["low", "high", "loss_chance"]].to_numpy(),
        hovertemplate=label + " %{x:,.1f}x<br>expected %{y:+.1f}%<br>range %{customdata[0]:+.0f}% to "
                              "%{customdata[1]:+.0f}%<br>loss chance %{customdata[2]:.0%}<extra></extra>"))
    now = curve.iloc[(curve["value"] - current).abs().argmin()]
    fig.add_trace(go.Scatter(x=[now["value"]], y=[now["expected"]], mode="markers", name="Today's book",
                             marker=dict(size=12, color=BLUE, line=dict(color=BG, width=2)),
                             hovertemplate="Today: %{x:,.1f}x · %{y:+.1f}%<extra></extra>"))
    fig.add_hline(y=threshold, line_color=DOWN, line_width=1, line_dash="dash",
                  annotation_text=f"Subscribe above {threshold:+g}%", annotation_position="bottom right",
                  annotation_font=dict(color=DOWN, size=11))
    lo, hi = curve["value"].min(), curve["value"].max()
    ticks = [t for t in [0.3, 1, 3, 10, 30, 100, 300, 1000, 3000] if lo <= t <= hi]
    fig.update_xaxes(type="log", title=f"{label} subscription (times)", tickvals=ticks,
                     ticktext=[f"{t:g}x" for t in ticks])
    fig.update_yaxes(title="Listing-day return (%)", ticksuffix="%")
    return style(fig, height=340)


def compare_chart(results):
    """One row per issue: the 80% range as a bar, the expected return as a dot coloured by the call."""
    shown = results.iloc[::-1]
    fig = go.Figure()
    for _, r in shown.iterrows():
        fig.add_trace(go.Scatter(x=[r["low"], r["high"]], y=[r["Issuer"]] * 2, mode="lines",
                                 line=dict(color="#d5dbe3", width=10), hoverinfo="skip", showlegend=False))
    for call, color in [("SUBSCRIBE", UP), ("AVOID", DOWN)]:
        part = shown[shown["call"] == call]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["expected"], y=part["Issuer"], mode="markers", name=call.title(),
            marker=dict(size=13, color=color, line=dict(color=BG, width=2)),
            customdata=part[["low", "high", "loss_chance"]].to_numpy(),
            hovertemplate="<b>%{y}</b><br>expected %{x:+.1f}%<br>range %{customdata[0]:+.0f}% to "
                          "%{customdata[1]:+.0f}%<br>loss chance %{customdata[2]:.0%}<extra></extra>"))
    fig.add_vline(x=0, line_color="#94a3b8", line_width=1, line_dash="dot")
    fig.update_xaxes(title="Listing-day return (%)", ticksuffix="%")
    return style(fig, height=max(200, 70 + 48 * len(results)))


def heat_gauge(percentile, label):
    title = (f"<b>{label}</b><br><span style='font-size:12px;color:#64748b'>percentile vs every month "
             "since 2010</span>")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=percentile, number=dict(valueformat=".0f", font=dict(size=34, color="#0f172a")),
        title=dict(text=title, font=dict(size=16, color="#0f172a")),
        gauge=dict(axis=dict(range=[0, 100], tickvals=[0, 20, 60, 80, 100], tickfont=dict(color="#64748b")),
                   bar=dict(color=ACCENT, thickness=0.28), bgcolor=BG, borderwidth=0,
                   steps=[dict(range=[0, 20], color="#eef2f6"), dict(range=[20, 60], color="#e5eaf0"),
                          dict(range=[60, 80], color="#d9e0e8"), dict(range=[80, 100], color="#cbd4de")])))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=60, b=0), paper_bgcolor="rgba(0,0,0,0)", font=FONT)
    return fig


def heat_history(series, current):
    fig = go.Figure(go.Scatter(x=series["date"], y=series["mean_gain"], mode="lines", line=dict(color=MUTED, width=1.8),
                               name="90-day average", customdata=series["count"],
                               hovertemplate="%{x|%b %Y}: %{y:+.1f}% across %{customdata} listings<extra></extra>"))
    fig.add_trace(go.Scatter(x=[current["as_of"]], y=[current["mean_gain"]], mode="markers", name="Now",
                             marker=dict(size=12, color=ACCENT, line=dict(color=BG, width=2)),
                             hovertemplate="Now: %{y:+.1f}%<extra></extra>"))
    fig.update_yaxes(title="90-day avg gain", ticksuffix="%")
    return style(fig, height=250)
