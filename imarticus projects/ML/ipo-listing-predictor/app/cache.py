"""Streamlit-cached wrappers so models and data load once per session."""

import pandas as pd
import streamlit as st

from app import core
from src import ledger
from src.config import PROCESSED_DIR
from src.models.train import MODELS_DIR


@st.cache_resource
def models():
    deploy, rule = core.load_models()
    return deploy, rule, core.make_explainer(deploy)


@st.cache_data
def history():
    return core.load_history()


@st.cache_data(ttl=3600, show_spinner="Fetching NIFTY and India VIX...")
def market():
    return core.load_market(live=True)


@st.cache_data
def walk_forward_predictions():
    return core.load_out_of_sample_predictions()


@st.cache_data
def csv(name):
    return pd.read_csv(PROCESSED_DIR / name)


@st.cache_resource
def model_id():
    """Name and SHA-256 prefix of the model file the app predicts with, stamped on every locked call."""
    return ledger.model_fingerprint(core.LIVE_MODEL if core.LIVE_MODEL.exists() else MODELS_DIR / "deploy.pkl")
