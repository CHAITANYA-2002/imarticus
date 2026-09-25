# blog

The Slopewatch write-up, in the two forms it needs to exist in.

| File | What it is |
|---|---|
| `slopewatch-medium.md` | The post. Medium-ready Markdown, ~3,900 words, 12 images referenced by absolute raw-GitHub URL so they resolve once pushed. |
| `slopewatch-blog.html` | The same post as a designed standalone page — for sharing a link, or reading it the way it was meant to look. |
| `images/` | 31 PNGs: 18 diagrams lifted from the walkthrough, 13 generated charts. |
| `_rasterize.html` | The tool that made the diagram PNGs. See below. |

---

## Publishing to Medium

Medium does not import Markdown files directly. Two routes, in order of preference:

**1. Import from GitHub (keeps images automatically).**
Medium's *Import a story* accepts a URL and pulls the images itself. Point it at the rendered Markdown:

```
https://github.com/CHAITANYA-2002/imarticus/blob/main/imarticus%20projects/Capstone%201/blog/slopewatch-medium.md
```

**2. Paste, then re-add images.**
Paste the Markdown body into a new Medium story. Medium converts headings, bold, lists and tables on paste but drops image links. Then drag each PNG in from `images/` at the marked positions.

Either way the post must be pushed to `main` first — the image URLs are absolute and point at the public raw endpoint. They 404 until the commit lands.

### A note on tables

Medium has no native table support. The ten tables in this post paste as plain text and look flat. Two options: screenshot them from the HTML version and insert as images, or rewrite the two or three that carry real weight — the coverage comparison and the model comparison — as short bullet lists. The rest are reference and read fine as text.

---

## Why the images are PNG and not SVG

The walkthrough draws its diagrams as inline SVG styled by the page's stylesheet. Pull one out and it renders black-on-black: every stroke is `currentColor` and every fill is a CSS variable defined three hundred lines away. `scripts/15_extract_diagrams.py` solves that for GitHub by writing the palette into each standalone file.

Medium needs a further step — it will not take SVG uploads at all. So `_rasterize.html` converts them: it loads each extracted SVG same-origin, pins the light palette (the files carry a dark-mode media query, and otherwise the machine's theme would decide how the blog looks), draws it to a canvas at 2× scale, and POSTs the PNG to a small local helper that writes it here.

Regenerating them:

```bash
.venv/Scripts/python.exe scripts/15_extract_diagrams.py
```

then serve the project root and open `blog/_rasterize.html` from that server — it needs same-origin access to `docs/diagrams/` and a `POST /save` endpoint that writes into `blog/images/`. The helper script lives outside the repo; the page tells you what it expects.

The charts in `images/chart-*.png` come straight from `scripts/14_report_figures.py` and need no conversion.

---

## Keeping it honest

Every figure is generated from a committed artefact — `models/metrics_v1.json`, `feature_importance_v1.csv`, `calibration_v1.csv`, `learning_curve_logistic.csv` — and `14_report_figures.py` asserts each one reproduces the metric it illustrates before drawing it.

That check has already earned itself once: an early version skipped the calibration step and drew recall@5% as 0.117 against 0.130 in the JSON. A figure that cannot reproduce the number it illustrates is worse than no figure.

If the model is retrained, rerun both scripts before republishing. The numbers quoted in the post prose are not generated and will need a manual pass — they are listed in the post's tables and in §10 and §17 of the README.
