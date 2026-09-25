"""Blog versions of the two charts that can be drawn from committed artefacts.

    python blog/_make_charts.py

The report figures (scripts/14_report_figures.py) use two colours, which suits a
technical README. The blog is read by people who have never seen a SHAP value,
so these versions label features in plain English, colour them by what kind of
signal they are, and give each region its own colour.

Reads models/feature_importance_v1.csv and models/metrics_v1.json only.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BLOG = Path(__file__).resolve().parent
MODELS = BLOG.parent / "models"
IMAGES = BLOG / "images"

INK, MUTED, RULE = "#1F2A2E", "#6B7A80", "#D5DCDF"
FAMILIES = {
    "Rainfall": "#2F6DB5",
    "Soil moisture & evaporation": "#2E8B57",
    "Terrain": "#C0661B",
    "History & calendar": "#7A4FB5",
}
LABELS = {
    "rain_1d": "Rain today",
    "rain_3d": "Rain, last 3 days",
    "wet_days_30": "Wet days in the last 30",
    "slope_std": "Slope roughness",
    "et0_7d": "Evaporation, last 7 days",
    "rain_max_1d_in_30": "Wettest day in the last 30",
    "aspect_cos": "Slope direction (north–south)",
    "hist_events_before": "Past landslides in this cell",
    "rain_15d": "Rain, last 15 days",
    "sm_0_7_delta_7d": "Topsoil moisture change, 7 days",
    "elev_range": "Elevation range in the cell",
    "rain_30d": "Rain, last 30 days",
    "rain_30d_anomaly": "30-day rain vs normal",
    "slope_max": "Steepest slope in the cell",
    "rain_max_1d_in_7": "Wettest day in the last 7",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": RULE, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": INK, "axes.titleweight": "bold", "axes.titlesize": 13,
})


def family(name: str) -> str:
    if name.startswith(("rain", "wet_days", "api")):
        return "Rainfall"
    if name.startswith(("sm_", "et0", "wetness")):
        return "Soil moisture & evaporation"
    if name.startswith(("elev", "slope", "aspect", "tri")):
        return "Terrain"
    return "History & calendar"


def shap_chart():
    top = pd.read_csv(MODELS / "feature_importance_v1.csv").head(15).iloc[::-1]
    colours = [FAMILIES[family(f)] for f in top["feature"]]
    labels = [LABELS.get(f, f) for f in top["feature"]]

    fig, ax = plt.subplots(figsize=(8.4, 6.2), dpi=180)
    ax.barh(labels, top["mean_abs_shap"], color=colours, height=0.72)
    for y, value in enumerate(top["mean_abs_shap"]):
        ax.text(value + 0.003, y, f"{value:.3f}", va="center", fontsize=8.5, color=MUTED)
    ax.set_title("What the model pays attention to (top 15 inputs)", loc="left", pad=14)
    ax.set_xlabel("average influence on a prediction (mean |SHAP|)", color=MUTED)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color=RULE, alpha=0.6)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in FAMILIES.values()]
    ax.legend(handles, FAMILIES.keys(), loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMAGES / "chart-shap.png", facecolor="white")
    plt.close(fig)


REGION_COLOURS = {
    "central_himalaya": ("Central Himalaya", "#2F6DB5"),
    "west_himalaya": ("West Himalaya", "#2E8B57"),
    "eastern_himalaya": ("Eastern Himalaya", "#7A4FB5"),
    "north_east": ("North East", "#B8465F"),
}


def region_chart():
    scores = json.loads((MODELS / "metrics_v1.json").read_text(encoding="utf-8"))
    blocks = pd.DataFrame(scores["spatial_cv"]).sort_values("pr_auc")
    temporal = scores["scores"][scores["selected"]]["test"]["pr_auc"]
    names = [REGION_COLOURS[b][0] for b in blocks["block"]]
    colours = [REGION_COLOURS[b][1] for b in blocks["block"]]

    fig, ax = plt.subplots(figsize=(8.4, 4.2), dpi=180)
    ax.barh(names, blocks["pr_auc"], color=colours, height=0.62)
    for y, value in enumerate(blocks["pr_auc"]):
        # inside the bar's end, so no value can collide with the reference line
        ax.text(value - 0.005, y, f"{value:.3f}", va="center", ha="right",
                fontsize=10, color="white", fontweight="bold")
    ax.axvline(temporal, color="#C0661B", linewidth=2.2)
    ax.text(temporal + 0.003, len(blocks) - 0.45, f"test on future years  {temporal:.3f}",
            color="#C0661B", fontsize=9, fontweight="bold", va="bottom")
    ax.set_xlim(0, max(blocks["pr_auc"].max(), temporal) * 1.3)
    ax.set_title("Does it work in a region it never trained on?", loc="left", pad=22)
    ax.set_xlabel("PR-AUC with that whole region held out of training", color=MUTED)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color=RULE, alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(IMAGES / "chart-region_generalisation.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    shap_chart()
    region_chart()
    print("wrote chart-shap.png, chart-region_generalisation.png")
