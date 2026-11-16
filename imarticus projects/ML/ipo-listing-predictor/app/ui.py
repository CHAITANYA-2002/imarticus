"""Look and feel: one stylesheet plus a few HTML building blocks used across pages."""

from html import escape

import streamlit as st

INK = "#0f172a"
BLUE = "#2a78d6"
GREEN = "#12a150"
RED = "#e34948"
MUTED = "#64748b"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, input, textarea, button { font-family: 'Inter', sans-serif; }
h1, h2, h3, .hero h1, .big-number { font-family: 'Space Grotesk', 'Inter', sans-serif !important; letter-spacing: -0.02em; }
.block-container { padding-top: 3.6rem; max-width: 1150px; }

/* hero */
.hero { background: radial-gradient(1200px 400px at 85% -20%, rgba(42,120,214,.55), transparent 60%),
                    linear-gradient(135deg, #0b1224 0%, #13254d 55%, #1b3d7a 100%);
        border-radius: 22px; padding: 30px 30px 26px; color: #fff; margin-bottom: 22px;
        box-shadow: 0 18px 40px -18px rgba(15,23,42,.55); }
.hero .eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: 12px; font-weight: 600; color: #9cc3ff; }
.hero h1 { color: #fff !important; font-size: 2.3rem; margin: 6px 0 6px; padding: 0; line-height: 1.1; }
.hero p { color: #cbd5e1; font-size: 1rem; margin: 0 0 16px; max-width: 640px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); color: #e2e8f0;
        padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 500; backdrop-filter: blur(4px); }
.chip b { color: #fff; }

/* cards */
.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 6px 0 18px; }
.card { background: #fff; border: 1px solid #e6e9f0; border-radius: 16px; padding: 16px 18px;
        box-shadow: 0 6px 18px -12px rgba(15,23,42,.25); }
.card .label { font-size: 12.5px; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: .06em; }
.card .value { font-family: 'Space Grotesk', sans-serif; font-size: 1.75rem; font-weight: 700; color: #0f172a; margin-top: 4px; }
.card .sub { font-size: 13px; color: #64748b; margin-top: 2px; }
.card.good .value { color: #12a150; } .card.bad .value { color: #e34948; } .card.blue .value { color: #2a78d6; }

/* result */
.result { background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%); border: 1px solid #dfe7f5; border-radius: 20px;
          padding: 22px 24px; box-shadow: 0 14px 32px -20px rgba(42,120,214,.45); margin: 8px 0 14px; }
.result .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.result .label { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
.big-number { font-size: 3.4rem; font-weight: 700; line-height: 1; margin: 6px 0 8px; }
.big-number.up { color: #12a150; } .big-number.down { color: #e34948; }
.range-text { color: #334155; font-size: 15px; }
.range-text b { color: #0f172a; }
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 999px;
         font-weight: 700; font-size: 1.05rem; letter-spacing: .02em; }
.badge.apply { background: #e7f7ee; color: #0d7a3c; border: 1px solid #b8e6cb; }
.badge.skip { background: #fdeceb; color: #b42323; border: 1px solid #f6c4c2; }
.badge .dot { width: 9px; height: 9px; border-radius: 50%; background: currentColor; }
.note { font-size: 13px; color: #64748b; margin-top: 10px; }

/* section titles */
.section { margin: 22px 0 6px; }
.section h3 { margin: 0; font-size: 1.25rem; }
.section p { margin: 2px 0 0; color: #64748b; font-size: 14px; }

/* streamlit widgets */
[data-testid="stForm"] { background: #fff; border: 1px solid #e6e9f0 !important; border-radius: 18px; padding: 18px 20px 8px;
                         box-shadow: 0 10px 28px -20px rgba(15,23,42,.35); }
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] {
    background: linear-gradient(135deg, #2a78d6, #1d5fb8); border: none; border-radius: 12px; font-weight: 600;
    padding: .6rem 1.4rem; box-shadow: 0 8px 18px -10px rgba(42,120,214,.9); }
[data-testid="stExpander"] details { border-radius: 14px; border-color: #e6e9f0; background: #fff; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid #e6e9f0; }
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #cbd5e1; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(42,120,214,.22); }
[data-testid="stSidebarNav"] a span { color: #e2e8f0 !important; }
.side-brand { padding: 4px 6px 12px; }
.side-brand .name { font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 700; color: #fff; }
.side-brand .tag { font-size: 12.5px; color: #94a3b8; margin-top: 2px; }
.side-foot { font-size: 12px; color: #94a3b8; line-height: 1.5; padding: 8px 6px; border-top: 1px solid rgba(148,163,184,.2); }

@media (max-width: 640px) {
  .hero { padding: 22px 18px; border-radius: 18px; }
  .hero h1 { font-size: 1.7rem; }
  .big-number { font-size: 2.7rem; }
  .card .value { font-size: 1.45rem; }
  .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
"""


def setup():
    st.markdown(CSS, unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="side-brand"><div class="name">📈 IPO Predictor</div>'
        '<div class="tag">Listing-day gains for Indian mainboard IPOs</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="side-foot">712 IPOs, 2010 to Nov 2026<br>Random forest + calibrated 80% range<br>'
        'Walk-forward tested, then forward-tested<br>on 78 IPOs it had never seen<br><br>Not investment advice.</div>',
        unsafe_allow_html=True,
    )


def hero(eyebrow, title, text, chips=()):
    chip_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1>'
        f'<p>{escape(text)}</p><div class="chips">{chip_html}</div></div>',
        unsafe_allow_html=True,
    )


def cards(items):
    """items: (label, value, sub, tone) tuples; tone in '', 'good', 'bad', 'blue'."""
    html = "".join(
        f'<div class="card {tone}"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div>'
        f'<div class="sub">{escape(sub)}</div></div>'
        for label, value, sub, tone in items
    )
    st.markdown(f'<div class="card-grid">{html}</div>', unsafe_allow_html=True)


def section(title, text=""):
    st.markdown(f'<div class="section"><h3>{escape(title)}</h3><p>{escape(text)}</p></div>', unsafe_allow_html=True)


def result_card(name, expected, low, high, apply, threshold):
    direction = "up" if expected >= 0 else "down"
    badge = ('<span class="badge apply"><span class="dot"></span>APPLY</span>' if apply
             else '<span class="badge skip"><span class="dot"></span>SKIP</span>')
    title = escape(name) if name else "Expected listing-day gain"
    st.markdown(
        f'<div class="result"><div class="top"><div><div class="label">{title}</div>'
        f'<div class="big-number {direction}">{expected:+.1f}%</div>'
        f'<div class="range-text">80% range <b>{low:+.0f}%</b> to <b>{high:+.0f}%</b></div></div>'
        f'<div>{badge}</div></div>'
        f'<div class="note">Verdict rule: apply when the expected gain is at least {threshold:+g}% '
        f'(picked on 2019–2023 in the backtest). The range held 79% of actual outcomes in 2024–2026.</div></div>',
        unsafe_allow_html=True,
    )
