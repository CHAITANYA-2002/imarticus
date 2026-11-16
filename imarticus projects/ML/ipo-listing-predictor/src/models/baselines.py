import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

SUB_BUCKETS = [0, 1, 3, 10, 30, 100, np.inf]


class MedianBaseline(BaseEstimator, RegressorMixin):
    """Predicts the training median for every IPO."""

    def fit(self, X, y):
        self.median_ = float(np.median(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.median_)


class BucketMedian(BaseEstimator, RegressorMixin):
    """Median gain of past IPOs in the same total-subscription bucket.

    This is roughly what an experienced IPO investor does by eye, so the
    ML models have to clearly beat it to be worth anything.
    """

    def __init__(self, column="sub_total", edges=None):
        self.column = column
        self.edges = edges

    def _bucket(self, X):
        edges = self.edges or SUB_BUCKETS
        return pd.cut(X[self.column], edges, right=False, labels=False)

    def fit(self, X, y):
        y = pd.Series(np.asarray(y, dtype=float), index=X.index)
        self.overall_ = float(y.median())
        self.medians_ = y.groupby(self._bucket(X)).median().to_dict()
        return self

    def predict(self, X):
        buckets = self._bucket(X)
        return np.array([self.medians_.get(b, self.overall_) for b in buckets], dtype=float)
