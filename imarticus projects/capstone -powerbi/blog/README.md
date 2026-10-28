# blog

The AML Sentinel write-up, ready for Medium.

| File | What it is |
|---|---|
| `aml-sentinel-blog.html` | The post as a designed page. Images load from `images/`, so it reads correctly offline. |
| `_medium-paste.html` | The same post for pasting into Medium: page styling stripped, every image pointed at its raw GitHub URL. |
| `images/` | 14 PNGs: 13 charts drawn from the project's outputs, plus a screenshot of report page 04. |
| `make_blog_figures.py` | Draws the 13 charts. Each one asserts the data reproduces the number the post quotes before drawing it. |
| `build_medium_paste.py` | Writes `_medium-paste.html` from `aml-sentinel-blog.html`. |

## Publishing to Medium

Medium imports a pasted image only if it can fetch it from a public URL, so the images must be online first.

1. Commit and push `blog/` to `main` of `CHAITANYA-2002/imarticus`. Until then the raw image URLs return 404.
2. Open `_medium-paste.html` in a browser, select all (Ctrl+A), copy, and paste into a new Medium story. The first heading becomes the title; headings, lists, quotes, images and captions come across.
3. Check that every image loaded. If one did not, drag it in from `images/` at that spot.

Without pushing: paste the text from `aml-sentinel-blog.html` instead and drag the 14 images in by hand, in file-name order.

The post has no tables on purpose: Medium has no table support and pastes them as flat text.

## Regenerating

From the project root:

```bash
python blog/make_blog_figures.py
python blog/build_medium_paste.py
```

`make_blog_figures.py` reads `data/powerbi/*.csv` and `data/processed/test_scores.parquet`. If the model is re-run, run both scripts again; any number in the prose that no longer matches will stop the figure script with the mismatch named. The leakage-control chart uses three scores from separate model runs recorded in `docs/QA_REPORT.md`; those are typed in and must be updated by hand.
