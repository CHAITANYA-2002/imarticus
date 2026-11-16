import pandas as pd
import streamlit as st

from app import cache, ui

NAMES = {"median": "Median of all past IPOs", "bucket_median": "Same-subscription-bucket median",
         "ridge": "Ridge regression", "random_forest": "Random forest", "lightgbm": "LightGBM"}


def render():
    ui.hero("Model card", "How it works, and where it doesn't",
            "Data sources, how the model was tested, the numbers it scored, and its limits.")
    deploy, rule, _ = cache.models()
    trained = deploy["trained_on"]
    ui.cards([
        ("Ranking 2024–26", "0.71", "Spearman, walk-forward", "blue"),
        ("Ranking, unseen IPOs", "0.72", "78 IPOs, Jun–Nov 2026", "blue"),
        ("80% range hit rate", "79% / 87%", "2024–26 / unseen IPOs", "good"),
        ("IPOs used", f"{trained['ipos']}", f"{trained['first'][:4]}–{trained['last'][:4]}", ""),
    ])

    st.markdown(f"""
**What it predicts.** The listing-day gain of an Indian mainboard IPO (listing-day open vs offer price),
using only what is known once subscription closes.

**Data.** {trained['ipos']} mainboard IPOs listed between {trained['first']} and {trained['last']}.
Up to May 2026: the Kaggle dataset *IPO Data India 2010–2026*, with listing prices checked against
the NSE open (Yahoo Finance, corrected for later splits and bonuses; 95% of checkable IPOs agree).
June–November 2026: 78 IPOs researched from news and broker pages, each with two agreeing sources and
a reported listing price that matches the NSE open within 3%. Market data: NIFTY 50 and India VIX.
REITs, InvITs and FPOs are excluded.

**Models.**
- Expected gain: a random forest.
- 80% range: LightGBM quantile models with rolling conformal calibration (current margin
  {deploy['conformal_margin']:.1f} pp).
- Verdict: Apply when the expected gain is at least {rule['model_threshold']:+g}%, a threshold picked
  on {rule['picked_on']}.

**How it was tested.** Models were tuned on 2010–2023 using yearly folds and evaluated walk-forward:
refit every quarter on IPOs known at the time. 2024 – May 2026 was never used to choose anything.
Then, with every setting frozen, it was scored once on 78 IPOs from June–November 2026 that had not
been collected when the model was built.
""")

    st.subheader("Forward test: 78 IPOs it had never seen (Jun–Nov 2026)")
    st.dataframe(pd.DataFrame({
        "Model": ["Random forest", "Same-subscription-bucket median", "Median of all past IPOs"],
        "MAE (pp)": [15.44, 14.54, 17.65], "Spearman": [0.72, 0.73, -0.05],
    }), hide_index=True, use_container_width=True)
    st.markdown("80% range coverage: **87%**. Expected profit, one lot per IPO: model ₹13,781, apply to "
                "every IPO ₹12,064, only 30x+ ₹8,122. The edge over the 30x rule held in 97% of bootstrap "
                "resamples; the edge over applying to everything was not significant (80%).")

    wf = cache.csv("wf_results.csv")
    table = wf.pivot(index="model", columns="period", values=["mae", "spearman"]).round(2)
    table.index = [NAMES[m] for m in table.index]
    table.columns = [f"{metric.upper() if metric == 'mae' else 'Spearman'} {period}" for metric, period in table.columns]
    st.subheader("Walk-forward accuracy")
    st.dataframe(table.sort_values(table.columns[0]), use_container_width=True)

    ranges = cache.csv("range_results.csv")
    st.subheader("80% range coverage")
    st.dataframe(pd.DataFrame({
        "Period": ranges["period"],
        "Before calibration": (ranges["raw_coverage"] * 100).round(0).astype(int).astype(str) + "%",
        "After calibration": (ranges["coverage"] * 100).round(0).astype(int).astype(str) + "%",
        "Average width (pp)": ranges["width"].round(0),
    }), hide_index=True, use_container_width=True)

    st.subheader("Limitations")
    st.markdown("""
- **Regime shifts.** Subscription has inflated (median 5x before 2020, 28x after 2023) and the gain
  for the same demand has roughly halved. The model adapts only as new IPOs are added and it is refit.
- **Exact gain vs ranking.** Out of sample the model ranks IPOs well (Spearman 0.71–0.72), but a simple
  subscription-bucket lookup was as good or slightly better on absolute error in both test periods.
- **History ends 4 Nov 2026.** Later IPOs need to be added (data/manual) for the recent-IPO features to
  stay current; until then, check the values under Predict → Market context.
- **Allotment odds** use 1 / retail subscription, an approximation.
- Not investment advice. Grey market premium (GMP) is deliberately not used.
""")
