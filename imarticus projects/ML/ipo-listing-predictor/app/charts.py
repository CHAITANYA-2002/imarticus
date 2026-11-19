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
