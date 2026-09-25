"""Does the model beat a plain rainfall rule?

    .venv/Scripts/python.exe scripts/16_rainfall_baseline.py

Random guessing is the easy baseline. The one a landslide scientist will ask
about is older and harder: rank cells by how much it has rained and inspect the
wettest. This scores that rule on the same test split, with the same metrics,
as the shipped model, and writes both side by side.

The rule's rainfall column is chosen on validation only (see src/model/baseline).
Either answer is worth having: a clear win justifies the model's complexity, and
a near-tie says the rainfall data is doing most of the work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings                      # noqa: E402
from src.logging_setup import configure          # noqa: E402
from src.model import baseline                   # noqa: E402

log = configure("rainfall_baseline")

OUT_PATH = settings.MODELS_DIR / "baseline_rainfall_v1.json"
METRICS_PATH = settings.MODELS_DIR / "metrics_v1.json"
COMPARED = ("pr_auc", "recall_at_5pct", "recall_at_10pct", "recall_at_20pct")


def main() -> int:
    path = settings.PROCESSED_DIR / "features.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run scripts/06_build_features.py first")
    if not METRICS_PATH.exists():
        raise FileNotFoundError(f"{METRICS_PATH} missing — run scripts/07_train_model.py first")

    matrix = pd.read_parquet(path)
    val = matrix[matrix["split"] == "val"]
    test = matrix[matrix["split"] == "test"]

    rule = baseline.choose_rule(val)
    rule_test = baseline.evaluate_rule(test, rule)

    shipped = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    model_name = shipped["selected"]
    model_test = shipped["scores"][model_name]["test"]

    if rule_test["n"] != model_test["n"] or rule_test["positives"] != model_test["positives"]:
        log.warning(
            "test split differs from the one metrics_v1.json was scored on "
            "(%d rows / %d positives here, %d / %d there) — retrain before comparing",
            rule_test["n"], rule_test["positives"], model_test["n"], model_test["positives"],
        )

    table = pd.DataFrame({
        f"rule: {rule}": {k: rule_test[k] for k in COMPARED},
        f"model: {model_name}": {k: model_test[k] for k in COMPARED},
    })
    table["model / rule"] = table.iloc[:, 1] / table.iloc[:, 0]
    log.info("--- test split, %d rows, %d positives ---\n%s",
             rule_test["n"], rule_test["positives"], table.round(3).to_string())
    log.info(
        "rule PR-AUC 95%% CI %.3f – %.3f; model %.3f – %.3f",
        rule_test["pr_auc_lo"], rule_test["pr_auc_hi"],
        model_test["pr_auc_lo"], model_test["pr_auc_hi"],
    )

    OUT_PATH.write_text(json.dumps({
        "rule": rule,
        "model": model_name,
        "rule_test": rule_test,
        "model_test": {k: model_test[k] for k in (*COMPARED, "pr_auc_lo", "pr_auc_hi", "n", "positives")},
    }, indent=2), encoding="utf-8")
    log.info("wrote %s", OUT_PATH.relative_to(settings.PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
