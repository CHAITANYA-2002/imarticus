"""Look and feel: a clean, light fintech style and the HTML blocks every page is built from."""

from html import escape

import streamlit as st

BRAND = "Primary Desk"
TAGLINE = "IPO Research · India"
ACCENT = "#08875d"
UP = "#08875d"
DOWN = "#d23b3b"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root { --bg:#f5f6f8; --card:#ffffff; --soft:#f8f9fb; --line:#e6e8ec; --line2:#eef0f3;
        --text:#0f172a; --text2:#334155; --muted:#64748b; --faint:#94a3b8;
        --accent:#08875d; --accent-d:#06704d; --accent-soft:#e8f5ef;
        --up:#08875d; --down:#d23b3b; --down-soft:#fdeeee; --amber:#b7791f;
        --shadow:0 1px 2px rgba(16,24,40,.04), 0 6px 20px -10px rgba(16,24,40,.10); }

html, body, [class*="css"], .stMarkdown, .stMarkdown p, input, textarea, button, label {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; }
.stApp { background: var(--bg); }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }
h1, h2, h3, h4 { font-family: 'Inter', sans-serif !important; letter-spacing: -0.02em; color: var(--text); }
.mono, .num { font-variant-numeric: tabular-nums; }
.up { color: var(--up) !important; } .down { color: var(--down) !important; } .gold { color: var(--accent) !important; }

/* top bar */
.topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
          background:var(--card); border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow);
          padding:14px 18px; margin-bottom:12px; }
.brand { display:flex; align-items:center; gap:12px; }
.mark { width:38px; height:38px; border-radius:11px; display:grid; place-items:center; font-weight:800; font-size:15px;
        color:#fff; background:var(--accent); letter-spacing:-.02em; }
.brand .name { font-weight:700; font-size:1.08rem; color:var(--text); line-height:1.1; letter-spacing:-.01em; }
.brand .tag { font-size:12px; color:var(--muted); margin-top:2px; }
.quotes { display:flex; gap:8px; flex-wrap:wrap; }
.quote { display:inline-flex; align-items:center; gap:6px; font-size:12.5px; color:var(--muted); font-weight:500;
         background:var(--soft); border:1px solid var(--line2); border-radius:999px; padding:6px 12px;
         font-variant-numeric: tabular-nums; }
.quote b { color:var(--text); font-weight:650; margin:0; }

/* ticker */
.ticker { overflow:hidden; background:var(--card); border:1px solid var(--line); border-radius:12px; margin-bottom:28px;
          -webkit-mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);
                  mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent); }
.ticker .track { display:inline-flex; gap:30px; padding:9px 0; white-space:nowrap; animation: scroll 80s linear infinite; }
.ticker:hover .track { animation-play-state: paused; }
.ticker .item { font-size:12.5px; color:var(--muted); font-weight:500; font-variant-numeric: tabular-nums; }
.ticker .item b { color:var(--text2); font-weight:650; margin-right:6px; }
@keyframes scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }

/* page header */
.pagehead { margin: 0 0 20px; }
.kicker { display:inline-block; font-size:12px; font-weight:600; color:var(--accent); background:var(--accent-soft);
          border-radius:999px; padding:4px 10px; }
.pagehead h1 { font-size:2.15rem; font-weight:800; margin:10px 0 6px; padding:0; letter-spacing:-.03em; }
.pagehead p { color:var(--muted); margin:0; max-width:720px; font-size:15.5px; line-height:1.6; }

/* kpi strip */
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:8px 0 22px; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; box-shadow:var(--shadow); }
.kpi .label { font-size:12.5px; font-weight:500; color:var(--muted); }
.kpi .value { font-size:1.6rem; font-weight:700; color:var(--text); margin-top:6px; letter-spacing:-.02em;
              font-variant-numeric: tabular-nums; }
.kpi .sub { font-size:12px; color:var(--faint); margin-top:2px; }

/* research note */
.note { background:var(--card); border:1px solid var(--line); border-radius:20px; overflow:hidden; margin:10px 0 16px;
        box-shadow:0 1px 2px rgba(16,24,40,.04), 0 18px 40px -20px rgba(16,24,40,.18); }
.note .head { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;
              padding:22px 26px; border-bottom:1px solid var(--line2); }
.note .eyebrow { font-size:12px; font-weight:600; color:var(--muted); }
.note .title { font-size:1.55rem; font-weight:750; color:var(--text); margin-top:4px; letter-spacing:-.02em; }
.note .meta { font-size:13px; color:var(--muted); margin-top:6px; font-variant-numeric: tabular-nums; }
.rating { text-align:right; }
.badge { display:inline-flex; align-items:center; gap:8px; padding:9px 16px; border-radius:999px; font-weight:700;
         letter-spacing:.06em; font-size:.92rem; }
.badge:before { content:''; width:8px; height:8px; border-radius:50%; background:currentColor; }
.badge.sub { background:var(--accent-soft); color:var(--accent-d); }
.badge.avoid { background:var(--down-soft); color:#b42323; }
.conv { font-size:12.5px; color:var(--muted); margin-top:8px; }
.conv b { color:var(--text); font-weight:650; }
.note .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); background:var(--soft); }
.note .cell { padding:18px 26px; border-right:1px solid var(--line2); }
.note .cell:last-child { border-right:none; }
.note .cell .label { font-size:12.5px; font-weight:500; color:var(--muted); }
.note .cell .value { font-size:1.55rem; font-weight:700; margin-top:6px; color:var(--text); letter-spacing:-.02em;
                     font-variant-numeric: tabular-nums; white-space:nowrap; }
.note .cell .value.big { font-size:clamp(1.9rem, 3vw, 2.5rem); font-weight:800; letter-spacing:-.03em; }
.kpi .value, .point .pp, .quote, .ticker .item { white-space:nowrap; }
.note .cell .sub { font-size:12px; color:var(--faint); margin-top:2px; }

/* thesis and risks */
.panel { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px 20px; height:100%;
         box-shadow:var(--shadow); }
.panel h4 { font-size:1rem; font-weight:650; margin:0 0 8px; color:var(--text); letter-spacing:-.01em; }
.point { display:flex; justify-content:space-between; gap:12px; padding:10px 0; border-top:1px solid var(--line2);
         font-size:14px; color:var(--text2); }
.point:first-of-type { border-top:none; }
.point .pp { font-weight:650; white-space:nowrap; font-variant-numeric: tabular-nums; }
.risk { padding:10px 0 10px 22px; border-top:1px solid var(--line2); font-size:14px; color:var(--text2); position:relative; }
.risk:first-of-type { border-top:none; }
.risk:before { content:'!'; position:absolute; left:0; top:11px; width:15px; height:15px; border-radius:50%;
               background:#fdf3e2; color:var(--amber); font-size:10.5px; font-weight:800; display:grid; place-items:center; }
.empty { color:var(--muted); font-size:13.5px; }

.section { margin:30px 0 12px; display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.section h3 { margin:0; font-size:1.15rem; font-weight:700; letter-spacing:-.015em; }
.section p { margin:0; color:var(--muted); font-size:13px; }
.disclaimer { margin-top:36px; padding-top:14px; border-top:1px solid var(--line); color:var(--faint); font-size:11.5px; line-height:1.6; }

/* streamlit widgets on the light theme */
[data-testid="stForm"] { background:var(--card); border:1px solid var(--line) !important; border-radius:18px;
                         padding:20px 22px 10px; box-shadow:var(--shadow); }
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] {
    background:var(--accent); color:#fff; border:none; border-radius:12px; font-weight:650; padding:.65rem 1.4rem;
    box-shadow:0 1px 2px rgba(16,24,40,.08); transition: background .15s ease, transform .05s ease; }
[data-testid="stFormSubmitButton"] button:hover, .stButton button[kind="primary"]:hover { background:var(--accent-d); color:#fff; }
[data-testid="stFormSubmitButton"] button:active { transform: translateY(1px); }
[data-testid="stFormSubmitButton"] button p { color:#fff; font-weight:650; }
[data-testid="stExpander"] details { border-radius:14px; border-color:var(--line); background:var(--card); box-shadow:var(--shadow); }
[data-testid="stDataFrame"] { border-radius:14px; overflow:hidden; border:1px solid var(--line); box-shadow:var(--shadow); }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stPlotlyChart"] { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:8px 10px;
                                box-shadow:var(--shadow); }
[data-testid="stWidgetLabel"] p { font-weight:500; color:var(--text2); }
[data-testid="stSidebar"] { background:var(--card); border-right:1px solid var(--line); }
[data-testid="stSidebarNav"] a { border-radius:10px; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:var(--accent-soft); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color:var(--accent-d) !important; font-weight:650; }
.side-foot { font-size:12.5px; color:var(--muted); line-height:1.6; padding:14px; margin-top:10px;
             background:var(--soft); border:1px solid var(--line2); border-radius:14px; }
.side-foot b { color:var(--text); font-weight:650; }

@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .pagehead h1 { font-size:1.7rem; }
  .note .head, .note .cell { padding-left:18px; padding-right:18px; }
  .note .title { font-size:1.3rem; }
  .note .cell { border-right:none; border-top:1px solid var(--line2); }
  .note .cell .value.big { font-size:2.1rem; }
  .rating { text-align:left; }
}
</style>
"""


def setup():
    st.markdown(CSS, unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="side-foot"><b>Coverage</b><br>712 mainboard IPOs, 2010 – Nov 2026<br><br>'
        '<b>Engine</b><br>Random forest + calibrated 80% range<br><br>'
        '<b>Track record</b><br>Walk-forward 2019–2026, then a frozen forward test on 78 unseen IPOs</div>',
        unsafe_allow_html=True,
    )


def signed(value, digits=1, suffix="%"):
    tone = "up" if value >= 0 else "down"
    return f'<span class="{tone}">{value:+.{digits}f}{suffix}</span>'


def topbar(quotes):
    """quotes: list of (label, value_text, change or None)."""
    parts = []
    for label, value, change in quotes:
        chg = f" {signed(change, 2)}" if change is not None else ""
        parts.append(f'<span class="quote">{escape(label)}<b>{escape(value)}</b>{chg}</span>')
    st.markdown(
        f'<div class="topbar"><div class="brand"><div class="mark">PD</div><div><div class="name">{BRAND}</div>'
        f'<div class="tag">{TAGLINE}</div></div></div><div class="quotes">{"".join(parts)}</div></div>',
        unsafe_allow_html=True,
    )


def ticker(items):
    """items: list of (symbol, gain). Rendered twice so the scroll loops seamlessly."""
    cells = "".join(f'<span class="item"><b>{escape(str(s))}</b>{signed(g)}</span>' for s, g in items)
    st.markdown(f'<div class="ticker"><div class="track">{cells}{cells}</div></div>', unsafe_allow_html=True)


def page_header(kicker, title, text):
    st.markdown(f'<div class="pagehead"><div class="kicker">{escape(kicker)}</div><h1>{escape(title)}</h1>'
                f'<p>{escape(text)}</p></div>', unsafe_allow_html=True)


def kpis(items):
    """items: (label, value_html, sub) — value_html may contain signed() spans."""
    cells = "".join(f'<div class="kpi"><div class="label">{escape(label)}</div><div class="value">{value}</div>'
                    f'<div class="sub">{escape(sub)}</div></div>' for label, value, sub in items)
    st.markdown(f'<div class="kpis">{cells}</div>', unsafe_allow_html=True)


def section(title, text=""):
    st.markdown(f'<div class="section"><h3>{escape(title)}</h3><p>{escape(text)}</p></div>', unsafe_allow_html=True)


def research_note(name, meta, verdict, conviction, expected, low, high, odds_text, ev):
    badge = "sub" if verdict == "SUBSCRIBE" else "avoid"
    st.markdown(
        f'<div class="note"><div class="head"><div><div class="eyebrow">IPO Research Note · Listing-day call</div>'
        f'<div class="title">{escape(name)}</div><div class="meta">{escape(meta)}</div></div>'
        f'<div class="rating"><span class="badge {badge}">{verdict}</span>'
        f'<div class="conv">Conviction <b>{conviction}</b></div></div></div>'
        f'<div class="grid">'
        f'<div class="cell"><div class="label">Expected listing return</div><div class="value big">{signed(expected)}</div>'
        f'<div class="sub">model estimate at the open</div></div>'
        f'<div class="cell"><div class="label">Bear case (P10)</div><div class="value">{signed(low, 0)}</div>'
        f'<div class="sub">80% range, lower end</div></div>'
        f'<div class="cell"><div class="label">Bull case (P90)</div><div class="value">{signed(high, 0)}</div>'
        f'<div class="sub">80% range, upper end</div></div>'
        f'<div class="cell"><div class="label">Retail allotment odds</div><div class="value">{escape(odds_text)}</div>'
        f'<div class="sub">one-lot application</div></div>'
        f'<div class="cell"><div class="label">Expected value / lot</div>'
        f'<div class="value"><span class="{"up" if ev >= 0 else "down"}">{"−" if ev < 0 else ""}₹{abs(ev):,.0f}</span></div>'
        f'<div class="sub">gain × ₹15,000 × odds</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def thesis_panel(title, points, empty):
    rows = "".join(f'<div class="point"><span>{escape(p.text)}</span><span class="pp">{signed(p.impact, 1, " pp")}</span></div>'
                   for p in points) or f'<div class="empty">{escape(empty)}</div>'
    st.markdown(f'<div class="panel"><h4>{escape(title)}</h4>{rows}</div>', unsafe_allow_html=True)


def risk_panel(items):
    rows = "".join(f'<div class="risk">{escape(r)}</div>' for r in items)
    st.markdown(f'<div class="panel">{rows}</div>', unsafe_allow_html=True)


def disclaimer():
    st.markdown(
        '<div class="disclaimer">Model-generated research for educational purposes. Not investment advice and not a '
        'recommendation to buy or sell any security. Calls use only information available when subscription closes. '
        'Past listing performance does not predict future results.</div>',
        unsafe_allow_html=True,
    )
