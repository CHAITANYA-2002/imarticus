import numpy as np

from src.models.dataset import FEATURE_SETS, TARGET
from src.models.train import fit, lgbm, recency_weights

QUANTILES = (0.1, 0.5, 0.9)


class QuantileSet:
    """Three LightGBM quantile models used as one: predict() returns sorted p10, p50, p90."""

    def __init__(self, params, data):
        self.params = {k: v for k, v in params.items() if k != "objective"}
        self.data = data
        self.columns = FEATURE_SETS[data["features"]]

    def fit(self, frame):
        weights = recency_weights(frame["year"], self.data.get("half_life"))
        self.models_ = {q: fit(lgbm(objective="quantile", alpha=q, **self.params), frame[self.columns],
                               frame[TARGET], weights) for q in QUANTILES}
        return self

    def predict(self, X):
        raw = np.column_stack([self.models_[q].predict(X[self.columns]) for q in QUANTILES])
        return np.sort(raw, axis=1)  # separately trained quantiles can cross
