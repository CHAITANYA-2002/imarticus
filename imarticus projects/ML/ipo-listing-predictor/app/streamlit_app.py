"""IPO Listing Day Predictor.

    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from app import ui  # noqa: E402
from app.views import backtest, explore, model_card, predict  # noqa: E402

st.set_page_config(page_title="IPO Listing Day Predictor", page_icon="📈", layout="wide")
ui.setup()

nav = st.navigation([
    st.Page(predict.render, title="Predict", icon=":material/insights:", default=True),
    st.Page(explore.render, title="Explore past IPOs", icon=":material/table_chart:", url_path="explore"),
    st.Page(backtest.render, title="Backtest", icon=":material/account_balance_wallet:", url_path="backtest"),
    st.Page(model_card.render, title="Model card", icon=":material/description:", url_path="model-card"),
])
nav.run()
