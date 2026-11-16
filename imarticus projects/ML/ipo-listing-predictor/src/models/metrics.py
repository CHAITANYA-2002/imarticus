import numpy as np
from scipy.stats import spearmanr


def regression_scores(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    errors = y_pred - y_true
    rank_corr = spearmanr(y_true, y_pred).statistic if np.std(y_pred) > 0 else 0.0
    return {
        "mae": float(np.mean(np.abs(errors))),
        "median_ae": float(np.median(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "spearman": float(rank_corr),
    }


def interval_scores(y_true, lower, upper):
    y_true = np.asarray(y_true, float)
    inside = (y_true >= lower) & (y_true <= upper)
    return {"coverage": float(inside.mean()), "avg_width": float(np.mean(np.asarray(upper) - np.asarray(lower)))}


def pinball_loss(y_true, y_pred, q):
    diff = np.asarray(y_true, float) - np.asarray(y_pred, float)
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))
