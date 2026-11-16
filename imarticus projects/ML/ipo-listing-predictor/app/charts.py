"""Plotly helpers with the same colours as the report figures."""

import plotly.graph_objects as go

from src.viz import BLUE, GRID, LOSS, NEUTRAL, ORANGE, TEXT_SECONDARY

FONT = dict(family="Inter, Segoe UI, sans-serif", size=13, color=TEXT_SECONDARY)


def style(fig, height=360, title=None):
    fig.update_layout(
        height=height, title=dict(text=title, x=0, font=dict(size=15)) if title else None,
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=FONT,
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0), hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=TEXT_SECONDARY)
    return fig


def contributions(explained, top=8):
    shown = explained.head(top).iloc[::-1]
    colors = [BLUE if v >= 0 else LOSS for v in shown["impact"]]
    fig = go.Figure(go.Bar(
        x=shown["impact"], y=shown["feature"], orientation="h", marker_color=colors,
        hovertemplate="%{y}: %{x:+.1f} pp<extra></extra>",
        text=[f"{v:+.1f}" for v in shown["impact"]], textposition="outside", cliponaxis=False,
    ))
    reach = max(abs(shown["impact"].min()), abs(shown["impact"].max()), 1) * 1.35
    lo = -reach if shown["impact"].min() < 0 else -reach * 0.1
    hi = reach if shown["impact"].max() > 0 else reach * 0.1
    fig.update_xaxes(title="Push on predicted gain (pp)", range=[lo, hi])
    return style(fig, height=320)


def range_bar(pred, actual=None):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=pred.low, x1=pred.high, y0=-0.3, y1=0.3,
                  fillcolor=BLUE, opacity=0.18, line_width=0)
    fig.add_trace(go.Scatter(x=[pred.expected], y=[0], mode="markers", name="Expected",
                             marker=dict(size=16, color=BLUE, line=dict(color="white", width=2)),
                             hovertemplate="Expected %{x:.1f}%<extra></extra>"))
    if actual is not None:
        fig.add_trace(go.Scatter(x=[actual], y=[0], mode="markers", name="Actual",
                                 marker=dict(size=14, color=ORANGE, symbol="diamond", line=dict(color="white", width=2)),
                                 hovertemplate="Actual %{x:.1f}%<extra></extra>"))
    fig.add_vline(x=0, line_color=NEUTRAL, line_width=1)
    points = [pred.low, pred.high, 0] + ([actual] if actual is not None else [])
    pad = (max(points) - min(points)) * 0.08
    fig.update_yaxes(visible=False, range=[-0.6, 0.6])
    fig.update_xaxes(title="Listing-day gain (%)", ticksuffix="%", range=[min(points) - pad, max(points) + pad])
    fig = style(fig, height=190)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
                      margin=dict(t=30))
    return fig
