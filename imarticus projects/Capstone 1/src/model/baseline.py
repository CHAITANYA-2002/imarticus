"""The rainfall-threshold baseline the model has to beat.

Landslide early warning has a long tradition of rules that need no model at all:
rank locations by how much it has rained, and inspect the wettest first. Any
claim that the model is worth its complexity has to be made against that rule,
not only against random guessing.

A rule here is a single rainfall column used as the score. Which column is
chosen on the validation split, never the test split. Picking the best of ten
columns by their test score would hand the baseline a tuned advantage the model
was never given, and the comparison would flatter nobody honestly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.model import metrics

# Candidate single-column rules, from the trigger day out to the monthly build-up.
CANDIDATE_RULES = (
    "rain_1d", "rain_3d", "rain_7d", "rain_15d", "rain_30d",
    "rain_max_1d_in_7", "rain_max_1d_in_30", "api",
    "rain_7d_anomaly", "rain_30d_anomaly",
)

TIE_BREAK_SEED = 42


def rule_score(frame: pd.DataFrame, column: str) -> np.ndarray:
    """A rainfall column as a ranking score, with ties broken at random.

    Dry days tie at exactly zero in their thousands. recall_at_budget takes the
    top slice by argsort, and without a tie-break the order inside a tie is an
    artefact of row order. A seeded jitter far below any real rainfall
    difference makes the ordering fair and repeatable.
    """
    values = frame[column].astype(float).fillna(0.0).to_numpy()
    rng = np.random.default_rng(TIE_BREAK_SEED)
    return values + rng.random(len(values)) * 1e-9


def choose_rule(val: pd.DataFrame, candidates: tuple[str, ...] = CANDIDATE_RULES) -> str:
    """The candidate with the best validation PR-AUC."""
    available = [c for c in candidates if c in val.columns and val[c].notna().any()]
    if not available:
        raise ValueError("no rainfall columns available to build a baseline rule")

    labels = val["label"].to_numpy()
    scored = {
        column: average_precision_score(labels, rule_score(val, column))
        for column in available
    }
    return max(scored, key=scored.get)


def evaluate_rule(frame: pd.DataFrame, column: str) -> dict[str, float]:
    """Ranking metrics for one rule.

    Only ranking measures apply. A rainfall total is not a probability, so
    Brier score and an operating threshold mean nothing for it, and
    metrics.evaluate would reject millimetres outright.
    """
    labels = frame["label"].to_numpy().astype(int)
    scores = rule_score(frame, column)
    lower, upper = metrics.pr_auc_interval(labels, scores)

    results = {
        "n": int(len(labels)),
        "positives": int(labels.sum()),
        "base_rate": float(labels.mean()),
        "pr_auc": float(average_precision_score(labels, scores)),
        "pr_auc_lo": lower,
        "pr_auc_hi": upper,
        "roc_auc": float(roc_auc_score(labels, scores)),
    }
    for budget in metrics.ALERT_BUDGETS:
        results[f"recall_at_{int(budget * 100)}pct"] = metrics.recall_at_budget(labels, scores, budget)
    return results
