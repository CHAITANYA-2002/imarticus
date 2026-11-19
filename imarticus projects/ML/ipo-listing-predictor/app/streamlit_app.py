"""Primary Desk: listing-day research for Indian mainboard IPOs.

    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from app import cache, ui  # noqa: E402
from app.views import backtest, explore, model_card, predict, track_record  # noqa: E402

st.set_page_config(page_title="Primary Desk · IPO Research", page_icon="📈", layout="wide")
ui.setup()


def market_header():
    nifty, vix, _ = cache.market()
    n_last, n_prev = nifty["close"].iloc[-1], nifty["close"].iloc[-2]
    v_last, v_prev = vix["close"].iloc[-1], vix["close"].iloc[-2]
    ui.topbar([
        ("NIFTY 50", f"{n_last:,.0f}", (n_last / n_prev - 1) * 100),
        ("INDIA VIX", f"{v_last:.2f}", (v_last / v_prev - 1) * 100),
        ("AS OF", f"{nifty.index[-1]:%d %b %Y}", None),
    ])
    recent = cache.history().dropna(subset=["symbol"]).sort_values("listing_date").tail(30).iloc[::-1]
    ui.ticker(list(zip(recent["symbol"], recent["target_gain_pct"], strict=True)))


market_header()
nav = st.navigation([
    st.Page(predict.render, title="Research Note", icon=":material/description:", default=True),
    st.Page(explore.render, title="Market Monitor", icon=":material/monitoring:", url_path="monitor"),
    st.Page(track_record.render, title="Track Record", icon=":material/verified:", url_path="track-record"),
    st.Page(backtest.render, title="Strategy Performance", icon=":material/account_balance_wallet:", url_path="performance"),
    st.Page(model_card.render, title="Methodology", icon=":material/science:", url_path="methodology"),
])
nav.run()
ui.disclaimer()
