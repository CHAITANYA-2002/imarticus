"""Look and feel: a dark, research-desk style and the HTML blocks every page is built from."""

from html import escape

import streamlit as st

BRAND = "Primary Desk"
TAGLINE = "IPO Research · India"
GOLD = "#d4a72c"
UP = "#22c55e"
DOWN = "#f05252"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&display=swap');

:root { --bg:#070b14; --panel:#0e1524; --panel2:#121b2e; --line:#1f2a40; --text:#e6e9ef; --muted:#8b95a8;
        --gold:#d4a72c; --gold2:#f0c75e; --up:#22c55e; --down:#f05252; --blue:#5b8def; }

html, body, [class*="css"], .stMarkdown, input, textarea, button, label { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: radial-gradient(1200px 600px at 100% -10%, rgba(212,167,44,.07), transparent 60%),
                     radial-gradient(900px 500px at -10% 10%, rgba(91,141,239,.06), transparent 60%), var(--bg); }
.block-container { padding-top: 3.2rem; max-width: 1180px; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; letter-spacing: -0.01em; color: var(--text); }
.mono, .num { font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }
.up { color: var(--up) !important; } .down { color: var(--down) !important; } .gold { color: var(--gold) !important; }

/* top bar */
.topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
          border:1px solid var(--line); background:linear-gradient(180deg,#0f1729,#0b1220); border-radius:14px;
          padding:12px 16px; margin-bottom:10px; }
.brand { display:flex; align-items:center; gap:12px; }
.mark { width:36px; height:36px; border-radius:9px; display:grid; place-items:center; font-family:'Fraunces',serif;
        font-weight:700; color:#0b1220; background:linear-gradient(135deg,var(--gold2),var(--gold)); font-size:17px; }
.brand .name { font-family:'Fraunces',serif; font-weight:700; font-size:1.15rem; color:var(--text); line-height:1; }
.brand .tag { font-size:11.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-top:3px; }
.quotes { display:flex; gap:18px; flex-wrap:wrap; }
.quote { font-family:'IBM Plex Mono',monospace; font-size:13px; color:var(--muted); }
.quote b { color:var(--text); font-weight:600; margin:0 4px; }

/* ticker */
.ticker { overflow:hidden; border:1px solid var(--line); border-radius:10px; background:#0a101d; margin-bottom:22px; }
.ticker .track { display:inline-flex; gap:34px; padding:8px 0; white-space:nowrap; animation: scroll 70s linear infinite; }
.ticker:hover .track { animation-play-state: paused; }
.ticker .item { font-family:'IBM Plex Mono',monospace; font-size:12.5px; color:var(--muted); }
.ticker .item b { color:var(--text); margin-right:6px; }
@keyframes scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }

/* page header */
.pagehead { margin: 4px 0 18px; }
.kicker { font-size:11.5px; letter-spacing:.18em; text-transform:uppercase; color:var(--gold); font-weight:600; }
.pagehead h1 { font-size:2.2rem; margin:6px 0 6px; padding:0; }
.pagehead p { color:var(--muted); margin:0; max-width:720px; font-size:15px; }

/* kpi strip */
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; margin:6px 0 20px; }
.kpi { background:linear-gradient(180deg,var(--panel2),var(--panel)); border:1px solid var(--line); border-radius:12px;
       padding:14px 16px; }
.kpi .label { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
.kpi .value { font-family:'IBM Plex Mono',monospace; font-size:1.45rem; font-weight:600; color:var(--text); margin-top:6px; }
.kpi .sub { font-size:12px; color:var(--muted); margin-top:3px; }

/* research note */
.note { border:1px solid var(--line); border-radius:18px; overflow:hidden; margin:8px 0 18px;
        background:linear-gradient(180deg,var(--panel2),var(--panel)); box-shadow:0 30px 60px -40px rgba(0,0,0,.8); }
.note .head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap;
              padding:20px 22px; border-bottom:1px solid var(--line); }
.note .eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.note .title { font-family:'Fraunces',serif; font-size:1.7rem; font-weight:700; color:var(--text); margin-top:4px; }
.note .meta { font-size:12.5px; color:var(--muted); margin-top:4px; font-family:'IBM Plex Mono',monospace; }
.rating { text-align:right; }
.badge { display:inline-block; padding:8px 16px; border-radius:8px; font-weight:700; letter-spacing:.12em; font-size:.95rem; }
.badge.sub { background:rgba(34,197,94,.12); color:var(--up); border:1px solid rgba(34,197,94,.35); }
.badge.avoid { background:rgba(240,82,82,.12); color:var(--down); border:1px solid rgba(240,82,82,.35); }
.conv { font-size:12px; color:var(--muted); margin-top:8px; letter-spacing:.06em; }
.conv b { color:var(--gold); }
.note .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); }
.note .cell { padding:16px 22px; border-right:1px solid var(--line); }
.note .cell:last-child { border-right:none; }
.note .cell .label { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
.note .cell .value { font-family:'IBM Plex Mono',monospace; font-size:1.6rem; font-weight:600; margin-top:6px; color:var(--text); }
.note .cell .value.big { font-size:2.4rem; }
.note .cell .sub { font-size:12px; color:var(--muted); margin-top:2px; }

/* thesis and risks */
.panel { border:1px solid var(--line); border-radius:14px; background:var(--panel); padding:16px 18px; height:100%; }
.panel h4 { font-family:'Fraunces',serif; font-size:1.05rem; margin:0 0 10px; color:var(--text); }
.point { display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-top:1px dashed var(--line); font-size:14px; color:#cdd3de; }
.point:first-of-type { border-top:none; }
.point .pp { font-family:'IBM Plex Mono',monospace; font-weight:600; white-space:nowrap; }
.risk { padding:8px 0 8px 18px; border-top:1px dashed var(--line); font-size:14px; color:#cdd3de; position:relative; }
.risk:first-of-type { border-top:none; }
.risk:before { content:''; position:absolute; left:2px; top:15px; width:7px; height:7px; border-radius:2px; background:var(--gold); }
.empty { color:var(--muted); font-size:13.5px; }

.section { margin:26px 0 8px; display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap;
           border-bottom:1px solid var(--line); padding-bottom:8px; }
.section h3 { margin:0; font-size:1.25rem; }
.section p { margin:0; color:var(--muted); font-size:13px; }
.disclaimer { margin-top:28px; padding-top:12px; border-top:1px solid var(--line); color:#6b7487; font-size:11.5px; line-height:1.6; }

/* streamlit widgets on the dark theme */
[data-testid="stForm"] { background:var(--panel); border:1px solid var(--line) !important; border-radius:16px; padding:18px 20px 8px; }
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] {
    background:linear-gradient(135deg,var(--gold2),var(--gold)); color:#0b1220; border:none; border-radius:10px;
    font-weight:700; letter-spacing:.04em; padding:.6rem 1.4rem; }
[data-testid="stFormSubmitButton"] button p { color:#0b1220; font-weight:700; }
[data-testid="stExpander"] details { border-radius:12px; border-color:var(--line); background:var(--panel); }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; border:1px solid var(--line); }
[data-testid="stAlert"] { border-radius:12px; }
[data-testid="stSidebar"] { background:#060a12; border-right:1px solid var(--line); }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:rgba(212,167,44,.12); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color:var(--gold2) !important; }
.side-foot { font-size:12px; color:var(--muted); line-height:1.6; padding:10px 6px; border-top:1px solid var(--line); margin-top:8px; }
.side-foot b { color:var(--text); }

@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .pagehead h1 { font-size:1.7rem; }
  .note .title { font-size:1.35rem; }
  .note .cell { border-right:none; border-top:1px solid var(--line); }
  .note .cell .value.big { font-size:2rem; }
  .rating { text-align:left; }
  .quotes { gap:12px; }
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
