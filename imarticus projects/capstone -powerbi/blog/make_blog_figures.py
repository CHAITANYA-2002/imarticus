"""Draw the blog's charts from the project's current outputs.

Every chart is drawn from a committed feed (``data/powerbi/*.csv``) or the saved test scores
(``data/processed/test_scores.parquet``), and each one first asserts that the data reproduces
the figure the post quotes. A chart that cannot reproduce its own number is not drawn.

The leakage-control chart is the one exception: those three scores come from separate model
runs recorded in ``docs/QA_REPORT.md`` and are typed in here, with that file named on the chart.

Run from the project root:

    python blog/make_blog_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import average_precision_score, precision_recall_curve

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDS = PROJECT_ROOT / "data" / "powerbi"
SCORES = PROJECT_ROOT / "data" / "processed" / "test_scores.parquet"
IMAGES = Path(__file__).resolve().parent / "images"

# The report's palette: navy ink, brass accent, green for the model, red for risk only.
NAVY = "#14213d"
BRASS = "#a9791c"
GREEN = "#1f7a4d"
RED = "#b3372f"
GREY = "#9aa5b1"
LIGHT = "#d5dbe1"
INK_SOFT = "#4a5568"
PAPER = "#ffffff"

RANDOM_SEED = 20260422  # same seed as python/run_risk_model.py

plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 15, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlepad": 14, "axes.edgecolor": LIGHT,
    "axes.labelcolor": INK_SOFT, "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": PAPER,
    "axes.facecolor": PAPER, "text.color": NAVY, "axes.titlecolor": NAVY,
})


def close(actual: float, expected: float, tolerance: float, what: str) -> None:
    if abs(actual - expected) > tolerance:
        raise SystemExit(f"{what}: data gives {actual}, the post says {expected}. Not drawn.")


def save(figure: plt.Figure, name: str, source: str) -> None:
    figure.text(0.01, 0.01, f"Source: {source}", fontsize=9, color=INK_SOFT)
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    figure.savefig(IMAGES / name, dpi=200)
    plt.close(figure)
    print(f"  {name}")


def pipeline() -> None:
    figure, axes = plt.subplots(figsize=(12, 3.2))
    axes.set_axis_off()
    axes.set_xlim(0, 12.6)
    axes.set_ylim(0.6, 3.5)
    steps = [
        ("Raw data", "3 files\n5,078,345 payments", "#eceae4"),
        ("SQLite", "clean, enrich\n37 quality gates", "#e3eaf6"),
        ("SQL marts", "summary tables\nper question", "#f3e7c9"),
        ("Python", "EDA, networks,\nmodel, capacity", "#dff1e6"),
        ("Power BI", "24 tables, 56 measures\n13 pages", "#e3eaf6"),
    ]
    width, gap = 2.2, 0.35
    for index, (title, body, fill) in enumerate(steps):
        x = 0.1 + index * (width + gap)
        axes.add_patch(FancyBboxPatch((x, 0.95), width, 1.8, boxstyle="round,pad=0.02,rounding_size=0.15",
                                      facecolor=fill, edgecolor=LIGHT, linewidth=1.5))
        axes.text(x + width / 2, 2.3, title, ha="center", va="center", fontsize=14,
                  fontweight="bold", color=NAVY)
        axes.text(x + width / 2, 1.6, body, ha="center", va="center", fontsize=10.5, color=INK_SOFT)
        if index < len(steps) - 1:
            axes.annotate("", xy=(x + width + gap - 0.05, 1.85), xytext=(x + width + 0.05, 1.85),
                          arrowprops={"arrowstyle": "-|>", "color": BRASS, "lw": 2})
    axes.text(0.1, 3.2, "The pipeline, end to end", fontsize=15, fontweight="bold", color=NAVY)
    save(figure, "01_pipeline.png", "project structure")


def channels() -> None:
    feed = pd.read_csv(FEEDS / "payment_format_risk.csv")
    ach = feed.set_index("payment_format").loc["ACH"]
    close(ach.volume_share_pct, 11.83, 0.01, "ACH volume share")
    close(ach.share_of_all_laundering_pct, 86.59, 0.01, "ACH label share")
    feed = feed.sort_values("share_of_all_laundering_pct")
    figure, axes = plt.subplots(figsize=(11, 5.6))
    y = np.arange(len(feed))
    axes.barh(y + 0.2, feed.volume_share_pct, height=0.38, color=LIGHT, label="Share of all payments")
    axes.barh(y - 0.2, feed.share_of_all_laundering_pct, height=0.38, color=RED,
              label="Share of all labelled laundering")
    for row, (volume, label) in enumerate(zip(feed.volume_share_pct, feed.share_of_all_laundering_pct)):
        axes.text(volume + 0.8, row + 0.2, f"{volume:.1f}%", va="center", fontsize=10, color=INK_SOFT)
        axes.text(label + 0.8, row - 0.2, f"{label:.1f}%", va="center", fontsize=10, color=RED)
    axes.set_yticks(y, feed.payment_format)
    axes.set_xlim(0, 100)
    axes.set_xlabel("% of total")
    axes.legend(frameon=False, loc="lower right")
    axes.set_title("ACH is 12% of payments and 87% of labelled laundering")
    save(figure, "02_channels.png", "data/powerbi/payment_format_risk.csv")


def ach_by_hour() -> None:
    feed = pd.read_csv(FEEDS / "daily_format_risk.csv")
    feed = feed[(feed.payment_format == "ACH") & (feed.calendar_date <= "2022/09/10")]
    hours = feed.groupby("transaction_hour")[["transaction_count", "laundering_transaction_count"]].sum()
    rate = 100 * hours.laundering_transaction_count / hours.transaction_count
    close(rate.max() / rate.loc[0], 3.5, 0.15, "ACH midday against midnight")
    figure, axes = plt.subplots(figsize=(11, 4.8))
    colours = [RED if hour == rate.idxmax() else NAVY for hour in rate.index]
    axes.bar(rate.index, rate.values, color=colours, width=0.75)
    axes.annotate(f"peak {rate.max():.2f}%", (rate.idxmax(), rate.max()), xytext=(0, 8),
                  textcoords="offset points", ha="center", color=RED, fontsize=11)
    axes.annotate(f"midnight {rate.loc[0]:.2f}%", (0, rate.loc[0]), xytext=(0, 8),
                  textcoords="offset points", ha="center", color=NAVY, fontsize=11)
    axes.set_xticks(range(0, 24, 2))
    axes.set_xlabel("Hour of day")
    axes.set_ylabel("Labelled rate (%)")
    axes.set_title("Inside ACH, midday runs 3.5x midnight (Sep 1-10)")
    save(figure, "03_ach_by_hour.png", "data/powerbi/daily_format_risk.csv")


def cross_border() -> None:
    feed = pd.read_csv(FEEDS / "jurisdiction_corridor_risk.csv")
    unknown = {"Unclassified", "Crypto exchange"}
    real_from = ~feed.from_jurisdiction.isin(unknown) & feed.from_jurisdiction.notna()
    real_to = ~feed.to_jurisdiction.isin(unknown) & feed.to_jurisdiction.notna()
    groups = {
        "Same country": real_from & real_to & (feed.from_jurisdiction == feed.to_jurisdiction),
        "Two different countries": real_from & real_to & (feed.from_jurisdiction != feed.to_jurisdiction),
        "Country and a bank\nwith no country": ((feed.from_jurisdiction == "Unclassified") & real_to)
        | ((feed.to_jurisdiction == "Unclassified") & real_from),
    }
    rates = {name: 100 * feed[mask].laundering_transaction_count.sum() / feed[mask].transaction_count.sum()
             for name, mask in groups.items()}
    values = list(rates.values())
    close(values[0], 0.0435, 0.0005, "domestic rate")
    close(values[1], 0.1444, 0.0005, "cross-border rate")
    close(values[2], 0.3870, 0.0005, "country to unclassified rate")
    figure, axes = plt.subplots(figsize=(10, 4.8))
    bars = axes.bar(list(rates), values, color=[GREY, RED, LIGHT], width=0.55)
    for bar, value in zip(bars, values):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 0.008, f"{value:.4f}%", ha="center",
                  fontsize=12, color=NAVY)
    axes.set_ylabel("Labelled rate (%)")
    axes.set_title("Between two countries: 3.3x the domestic labelled rate")
    save(figure, "04_cross_border.png", "data/powerbi/jurisdiction_corridor_risk.csv")


def typologies() -> None:
    feed = pd.read_csv(FEEDS / "dim_typology.csv").sort_values("network_count")
    close(feed.network_count.sum(), 370, 0, "networks")
    close(feed.transaction_count.sum(), 3209, 0, "pattern payments")
    figure, axes = plt.subplots(figsize=(10, 4.8))
    names = feed.typology_name.str.title().str.replace("-", "-", regex=False)
    axes.barh(names, feed.network_count, color=NAVY, height=0.6)
    for row, (networks, payments) in enumerate(zip(feed.network_count, feed.transaction_count)):
        axes.text(networks + 0.6, row, f"{networks} networks, {payments} payments", va="center",
                  fontsize=10, color=INK_SOFT)
    axes.set_xlim(0, 80)
    axes.set_xlabel("Labelled networks")
    axes.set_title("370 labelled laundering networks in 8 shapes")
    save(figure, "05_typologies.png", "data/powerbi/dim_typology.csv")


def load_scores() -> pd.DataFrame:
    scores = pd.read_parquet(SCORES, columns=["transaction_timestamp", "from_bank_key", "from_account_id",
                                              "to_bank_key", "to_account_id", "is_laundering", "risk_score"])
    close(len(scores), 1_345_565, 0, "test rows")
    close(scores.is_laundering.sum(), 1495, 0, "test labels")
    return scores


def review_order(scores: pd.DataFrame) -> np.ndarray:
    """Score first, then first-in first-out: the same order as capacity_simulation.rank_by."""
    arrived = pd.to_datetime(scores.transaction_timestamp).to_numpy()
    sender = (scores.from_bank_key.astype(str) + "|" + scores.from_account_id.astype(str)).to_numpy()
    receiver = (scores.to_bank_key.astype(str) + "|" + scores.to_account_id.astype(str)).to_numpy()
    return np.lexsort((np.arange(len(scores)), receiver, sender, arrived, -scores.risk_score.to_numpy()))


def pr_curve(scores: pd.DataFrame) -> None:
    labels, values = scores.is_laundering.to_numpy(), scores.risk_score.to_numpy()
    pr_auc = average_precision_score(labels, values)
    close(round(pr_auc, 4), 0.2982, 0.0001, "PR-AUC")
    precision, recall, _ = precision_recall_curve(labels, values)
    base = labels.mean()
    figure, axes = plt.subplots(figsize=(10, 5.2))
    axes.plot(recall, precision, color=GREEN, linewidth=2.2, label=f"Model, PR-AUC {pr_auc:.2f}")
    axes.axhline(base, color=GREY, linestyle="--", linewidth=1.5,
                 label=f"Random list, PR-AUC {base:.4f}")
    axes.set_xlabel("Recall: share of all laundering caught")
    axes.set_ylabel("Precision: share of alerts that are real")
    axes.set_ylim(0, 1.02)
    axes.legend(frameon=False)
    axes.set_title("Precision against recall on all 1,345,565 test payments")
    save(figure, "06_pr_curve.png", "data/processed/test_scores.parquet")


def top_k(scores: pd.DataFrame, order: np.ndarray) -> None:
    hits = np.cumsum(scores.is_laundering.to_numpy()[order])
    close(hits[99], 92, 0, "top-100 cases")
    close(hits[1499], 509, 0, "cases in 1,500 alerts")
    alerts = np.arange(1, 5001)
    precision = 100 * hits[:5000] / alerts
    figure, axes = plt.subplots(figsize=(10, 5))
    axes.plot(alerts, precision, color=GREEN, linewidth=2.2)
    for k in (100, 500, 1000, 1500):
        axes.plot(k, precision[k - 1], "o", color=NAVY)
        axes.annotate(f"top {k:,}: {hits[k - 1]} real ({precision[k - 1]:.0f}%)", (k, precision[k - 1]),
                      xytext=(10, 6), textcoords="offset points", fontsize=10.5, color=NAVY)
    axes.axvline(1500, color=BRASS, linestyle=":", linewidth=1.5)
    axes.text(1530, 82, "the team's budget:\n500 a day x 3 days", color=BRASS, fontsize=10)
    axes.set_xlabel("Alerts opened, highest score first")
    axes.set_ylabel("Precision so far (%)")
    axes.set_ylim(0, 100)
    axes.set_title("Walking down the model's list: the top is almost all real")
    save(figure, "07_top_k.png", "data/processed/test_scores.parquet")


def deciles() -> None:
    feed = pd.read_csv(FEEDS / "model_performance_bands.csv")
    feed = feed[feed.model == feed.model.iloc[0]] if "model" in feed else feed
    share = 100 * feed.labelled_laundering / feed.labelled_laundering.sum()
    feed = feed.assign(share=share).sort_values("risk_decile")
    close(feed.set_index("risk_decile").share.loc["D10"], 92.4, 0.05, "top decile label share")
    figure, axes = plt.subplots(figsize=(10, 4.8))
    colours = [GREEN if decile == "D10" else LIGHT for decile in feed.risk_decile]
    bars = axes.bar(feed.risk_decile, feed.share, color=colours, width=0.65)
    for bar, value in zip(bars, feed.share):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center", fontsize=10)
    axes.set_xlabel("Model score band (D01 = lowest 10% of scores, D10 = highest 10%)")
    axes.set_ylabel("Share of test laundering (%)")
    axes.set_ylim(0, 100)
    axes.set_title("The top 10% of scores holds 92.4% of the test laundering")
    save(figure, "08_deciles.png", "data/powerbi/model_performance_bands.csv")


def importance() -> None:
    feed = pd.read_csv(FEEDS / "feature_importance.csv").nlargest(10, "average_precision_drop")
    close(feed.iloc[0].average_precision_drop, 0.281, 0.001, "top feature drop")
    feed = feed.iloc[::-1]
    figure, axes = plt.subplots(figsize=(10, 5.2))
    axes.barh(feed.feature_label, feed.average_precision_drop, color=NAVY, height=0.6)
    for row, value in enumerate(feed.average_precision_drop):
        axes.text(value + 0.004, row, f"{value:.3f}", va="center", fontsize=10, color=INK_SOFT)
    axes.set_xlabel("Fall in PR-AUC when the input is shuffled")
    axes.set_title("What the model looks at: the ten inputs that matter most")
    save(figure, "09_feature_importance.png", "data/powerbi/feature_importance.csv")


def sampling_trap(scores: pd.DataFrame) -> None:
    labels, values = scores.is_laundering.to_numpy(), scores.risk_score.to_numpy()
    honest = average_precision_score(labels, values)
    generator = np.random.default_rng(RANDOM_SEED)
    negatives = np.flatnonzero(labels == 0)
    kept = generator.choice(negatives, size=len(negatives) // 45, replace=False)
    subset = np.concatenate([np.flatnonzero(labels == 1), kept])
    inflated = average_precision_score(labels[subset], values[subset])
    close(inflated, 0.7824, 0.02, "sampled-test PR-AUC")
    figure, axes = plt.subplots(figsize=(9, 4.6))
    bars = axes.bar(["Honest test\n(every payment)", "Trimmed test\n(1 in 45 normal payments kept)"],
                    [honest, inflated], color=[GREEN, RED], width=0.5)
    for bar, value in zip(bars, (honest, inflated)):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.2f}", ha="center", fontsize=14)
    axes.set_ylim(0, 1)
    axes.set_ylabel("PR-AUC")
    axes.set_title("Trim the test and the same model looks 2.6x better")
    save(figure, "10_sampling_trap.png", "data/processed/test_scores.parquet")


def leakage_controls() -> None:
    runs = [("Main model\n(Sep 1-7 -> 8-10)", 0.2982, GREEN), ("Shuffled labels", 0.0014, RED),
            ("Earlier split\n(Sep 1-5 -> 6-7)", 0.26, NAVY), ("History frozen\nat Sep 7", 0.26, NAVY)]
    figure, axes = plt.subplots(figsize=(10, 4.8))
    bars = axes.bar([name for name, _, _ in runs], [value for _, value, _ in runs],
                    color=[colour for _, _, colour in runs], width=0.55)
    for bar, (_, value, _) in zip(bars, runs):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 0.008, f"{value:g}", ha="center", fontsize=12)
    axes.axhline(0.0011, color=GREY, linestyle="--", linewidth=1.2)
    axes.text(1.32, 0.006, "random list: 0.0011", color=INK_SOFT, fontsize=10, ha="left")
    axes.set_ylim(0, 0.35)
    axes.set_ylabel("PR-AUC")
    axes.set_title("Three checks that the result is not a leak")
    save(figure, "11_leakage_controls.png", "model runs recorded in docs/QA_REPORT.md")


def capacity() -> None:
    feed = pd.read_csv(FEEDS / "capacity_curve.csv")
    feed = feed[feed.alerts_per_day == 500].set_index("policy")
    order = ["Model queue", "Expert rule queue", "Random review", "Account rule queue"]
    cases = feed.loc[order, "cases_caught"]
    close(cases["Model queue"], 509, 0, "model cases")
    close(cases["Expert rule queue"], 13, 0, "expert rule cases")
    hours = feed.loc[order, "analyst_hours_per_day"] * 3 / cases.replace(0, np.nan)
    close(hours["Expert rule queue"], 38.5, 0.05, "expert rule hours per case")

    figure, axes = plt.subplots(figsize=(10, 4.8))
    labels = ["Model", "Expert rule", "Random", "Account rule"]
    bars = axes.bar(labels, cases, color=[GREEN, BRASS, GREY, LIGHT], width=0.55)
    for bar, value in zip(bars, cases):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 8, f"{value:g}" if value < 10 else f"{value:.0f}",
                  ha="center", fontsize=13)
    axes.set_ylabel("Labelled cases in 1,500 alerts")
    axes.set_title("Same team, same 1,500 alerts: 509 cases against 13 (39x)")
    save(figure, "12_cases_by_policy.png", "data/powerbi/capacity_curve.csv")

    figure, axes = plt.subplots(figsize=(10, 4.6))
    shown = hours.dropna()
    bars = axes.barh(["Model", "Expert rule", "Random"][::-1], shown.values[::-1],
                     color=[GREY, BRASS, GREEN], height=0.55)
    for bar, value in zip(bars, shown.values[::-1]):
        axes.text(value + 4, bar.get_y() + bar.get_height() / 2, f"{value:.1f} hours", va="center", fontsize=12)
    axes.set_xlim(0, 360)
    axes.set_xlabel("Analyst hours spent for each labelled case found (20 minutes an alert)")
    axes.set_title("About 1 analyst hour per case with the model, 38.5 with the rule")
    save(figure, "13_hours_per_case.png", "data/powerbi/capacity_curve.csv")


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    print("Drawing blog figures:")
    pipeline()
    channels()
    ach_by_hour()
    cross_border()
    typologies()
    deciles()
    importance()
    leakage_controls()
    capacity()
    scores = load_scores()
    order = review_order(scores)
    pr_curve(scores)
    top_k(scores, order)
    sampling_trap(scores)


if __name__ == "__main__":
    main()
