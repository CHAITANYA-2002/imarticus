"""The rainfall baseline must be chosen on validation and scored fairly."""

import numpy as np
import pandas as pd

from src.model import baseline


def _frame(n: int, signal_column: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    label = (rng.random(n) < 0.15).astype(int)
    frame = pd.DataFrame({column: rng.gamma(1.0, 10.0, n) for column in baseline.CANDIDATE_RULES})
    frame[signal_column] += label * 40.0
    frame["label"] = label
    return frame


def test_rule_is_chosen_on_validation_not_test():
    # Validation rewards rain_7d; test would reward rain_1d. The choice must follow validation.
    val = _frame(2000, "rain_7d", seed=1)
    test = _frame(2000, "rain_1d", seed=2)

    assert baseline.choose_rule(val) == "rain_7d"
    assert baseline.choose_rule(test) == "rain_1d"


def test_ties_do_not_inflate_recall_at_budget():
    # Every score ties at zero, so the rule knows nothing. Recall in the top
    # 10% should sit near 10%, not wherever row order happens to put positives.
    n = 5000
    frame = pd.DataFrame({"rain_1d": np.zeros(n), "label": np.zeros(n, dtype=int)})
    frame.loc[: n // 10 - 1, "label"] = 1  # every positive first in row order

    result = baseline.evaluate_rule(frame, "rain_1d")
    assert 0.05 < result["recall_at_10pct"] < 0.15


def test_missing_columns_are_skipped():
    val = _frame(500, "api", seed=3)[["api", "label"]]
    assert baseline.choose_rule(val) == "api"


def test_rule_scores_accept_rainfall_in_millimetres():
    # Rainfall totals run far above 1; the rule must be scored on ranking alone.
    frame = _frame(3000, "rain_3d", seed=4)
    result = baseline.evaluate_rule(frame, "rain_3d")
    assert result["pr_auc"] > result["base_rate"]
    assert result["recall_at_10pct"] > 0.10
