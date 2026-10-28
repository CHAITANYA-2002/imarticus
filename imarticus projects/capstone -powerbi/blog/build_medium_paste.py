"""Write the Medium paste page from the designed blog page.

``aml-sentinel-blog.html`` loads its images from ``images/`` next to it, which is right for
reading it locally and wrong for Medium: a pasted image is only imported if Medium can
fetch it from a public URL. This writes ``_medium-paste.html``, the same post with every
image pointed at the raw GitHub URL it will have once ``blog/`` is pushed to ``main``, and
with the page styling stripped so Medium keeps only headings, text, lists and images.

Run from the project root:

    python blog/build_medium_paste.py
"""

from __future__ import annotations

import re
from pathlib import Path

BLOG = Path(__file__).resolve().parent
SOURCE = BLOG / "aml-sentinel-blog.html"
TARGET = BLOG / "_medium-paste.html"
RAW_IMAGES = ("https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/"
              "imarticus%20projects/capstone%20-powerbi/blog/images/")

MEDIUM_STYLE = """<style>
 body{font:18px/1.6 Georgia,serif;max-width:42rem;margin:2rem auto;padding:0 1rem;}
 img{max-width:100%;height:auto;}
 figcaption{font-size:.85rem;color:#555;font-style:italic;}
</style>"""


def main() -> None:
    page = SOURCE.read_text(encoding="utf-8")
    images = re.findall(r'src="images/([^"]+)"', page)
    missing = [name for name in images if not (BLOG / "images" / name).exists()]
    if missing:
        raise SystemExit(f"Images referenced but not on disk: {missing}")

    page = re.sub(r"<style>.*?</style>", MEDIUM_STYLE, page, count=1, flags=re.S)
    page = page.replace('src="images/', f'src="{RAW_IMAGES}')
    TARGET.write_text(page, encoding="utf-8")
    print(f"Wrote {TARGET.name}: {len(images)} images pointed at {RAW_IMAGES}")


if __name__ == "__main__":
    main()
