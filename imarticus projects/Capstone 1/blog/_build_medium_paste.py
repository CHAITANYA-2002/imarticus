"""Build medium-paste.html: the post as rich HTML that pastes into Medium intact.

Medium keeps headings, bold, italics, links, code, separators and <img> tags from
the clipboard, but has no tables. So every Markdown table is rendered to a PNG
(images/table-NN.png) and swapped in as a figure. Image URLs are absolute raw
GitHub URLs, so Medium can fetch and rehost them during the paste.

    python blog/_build_medium_paste.py [--ref main]

Needs: markdown, playwright (and a Chromium; /opt/pw-browsers is used if present).
"""
import argparse
import html
import re
from pathlib import Path

import markdown

BLOG = Path(__file__).resolve().parent
SRC = BLOG / "slopewatch-medium.md"
OUT = BLOG / "medium-paste.html"
IMAGES = BLOG / "images"
REPO_PATH = "imarticus%20projects/Capstone%201/blog/images"

TABLE_CAPTIONS = [
    "Same model, more data: PR-AUC falls with the base rate while every rate-independent metric improves",
    "Three models at 74% coverage: PR-AUC intervals overlap; recall at budget does not",
    "The honest headline, on the held-out test split",
]

TABLE_CSS = """
body { margin: 0; background: #fff; }
.wrap { padding: 28px 32px; display: inline-block; background: #fff; }
table { border-collapse: collapse; font: 17px/1.4 Georgia, 'Times New Roman', serif; color: #242424; }
th { font: 600 13px/1.3 -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; text-transform: uppercase;
     letter-spacing: .06em; color: #6b6b6b; text-align: left; padding: 10px 22px 10px 0; border-bottom: 2px solid #242424; }
td { padding: 11px 22px 11px 0; border-bottom: 1px solid #e6e6e6; white-space: nowrap; }
td:first-child { color: #242424; }
tr:last-child td { border-bottom: none; }
td strong { font-weight: 700; }
tr:has(td:first-child strong) td { background: #f7f5ef; }
"""


def raw_url(ref, name):
    return f"https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/{ref}/{REPO_PATH}/{name}"


def render_tables(tables):
    from playwright.sync_api import sync_playwright

    exe = next(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"), None) if Path("/opt/pw-browsers").exists() else None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(exe) if exe else None)
        page = browser.new_page(device_scale_factor=2)
        for i, table in enumerate(tables, 1):
            page.set_content(f"<style>{TABLE_CSS}</style><div class='wrap'>{table}</div>")
            page.locator(".wrap").screenshot(path=str(IMAGES / f"table-{i:02d}.png"))
        browser.close()


def figure(src, caption):
    cap = html.escape(caption)
    return f'<figure><img src="{src}" alt="{cap}"><figcaption>{cap}</figcaption></figure>'


def embed_images(page):
    import base64

    def swap(m):
        url = m.group(1)
        data = base64.b64encode((IMAGES / url.rsplit("/", 1)[1]).read_bytes()).decode()
        return f'<img src="data:image/png;base64,{data}" data-src="{url}"'

    return re.sub(r'<img src="(https://raw[^"]+)"', swap, page)


def build(ref, skip_render, embed_to=None):
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = lines[0].removeprefix("# ").strip()
    subtitle = lines[2].removeprefix("### ").strip()
    body_md = "\n".join(lines[3:]).lstrip("\n")
    body_md = re.sub(r"^---\s*\n", "", body_md)  # leading separator under the subtitle

    body = markdown.markdown(body_md, extensions=["tables", "fenced_code"])

    # The post may reference the table PNGs directly; only render when Markdown tables are present.
    tables = re.findall(r"<table>.*?</table>", body, flags=re.S)
    assert len(tables) in (0, len(TABLE_CAPTIONS)), f"expected 0 or {len(TABLE_CAPTIONS)} tables, found {len(tables)}"
    if tables and not skip_render:
        render_tables(tables)
    for i, (table, cap) in enumerate(zip(tables, TABLE_CAPTIONS), 1):
        body = body.replace(table, figure(raw_url(ref, f"table-{i:02d}.png"), cap), 1)

    def img_to_figure(m):
        alt, src = html.unescape(m.group(1)), m.group(2).replace("/main/", f"/{ref}/", 1)
        return figure(src, alt)

    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]*)" ?/?></p>', img_to_figure, body)

    n_img = body.count("<img ")
    page = TEMPLATE.format(
        title=html.escape(title), subtitle=html.escape(subtitle), body=body, n_img=n_img,
        n_h=len(re.findall(r"<h[23]>", body)),
    )
    OUT.write_text(page, encoding="utf-8")
    if embed_to:
        Path(embed_to).write_text(embed_images(page), encoding="utf-8")
        print(f"wrote self-contained preview {embed_to}")
    print(f"wrote {OUT.name}: {n_img} images, {len(tables)} tables rendered, ref={ref}")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Medium Paste Kit</title>
<style>
:root {{ --bg:#fbfaf7; --panel:#fff; --ink:#242424; --muted:#6b6b6b; --line:#e6e3dc; --accent:#1a8917; --accent-ink:#fff; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141414; --panel:#1d1d1d; --ink:#ececec; --muted:#a0a0a0; --line:#333; --accent:#3fb950; --accent-ink:#0b0b0b; }} }}
:root[data-theme="dark"] {{ --bg:#141414; --panel:#1d1d1d; --ink:#ececec; --muted:#a0a0a0; --line:#333; --accent:#3fb950; --accent-ink:#0b0b0b; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; }}
.kit {{ max-width:760px; margin:0 auto; padding:24px 16px 8px; }}
.kit h1 {{ font-size:22px; margin:0 0 4px; }}
.kit p.lead {{ color:var(--muted); margin:0 0 18px; }}
ol.steps {{ padding-left:20px; margin:0 0 18px; }}
ol.steps li {{ margin:6px 0; }}
.row {{ display:flex; gap:10px; align-items:flex-start; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; margin:8px 0; }}
.row .txt {{ flex:1; min-width:0; }}
.row .lbl {{ font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
button {{ font:600 14px/1 inherit; font-family:inherit; border:0; border-radius:999px; padding:10px 16px; cursor:pointer; background:var(--accent); color:var(--accent-ink); white-space:nowrap; }}
button.big {{ width:100%; padding:14px; font-size:16px; margin:10px 0 4px; }}
.status {{ min-height:1.4em; font-size:14px; color:var(--accent); text-align:center; }}
.checks {{ font-size:14px; color:var(--muted); }}
hr.kitline {{ border:0; border-top:1px solid var(--line); margin:22px 0 0; }}
#article {{ max-width:720px; margin:0 auto; padding:8px 16px 64px; font:20px/1.6 Georgia,'Times New Roman',serif; }}
#article h2 {{ font:700 28px/1.25 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; margin:40px 0 8px; }}
#article h3 {{ font:700 21px/1.3 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; margin:30px 0 6px; }}
#article img {{ max-width:100%; height:auto; display:block; margin:0 auto; background:#fff; }}
#article figure {{ margin:32px 0; }}
#article figcaption {{ font:14px/1.4 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; color:var(--muted); text-align:center; margin-top:8px; }}
#article pre {{ background:var(--panel); border:1px solid var(--line); padding:14px; overflow-x:auto; font-size:14px; line-height:1.45; }}
#article code {{ font-family:Menlo,Consolas,monospace; font-size:.85em; }}
#article hr {{ border:0; text-align:center; margin:36px 0; }}
#article hr::after {{ content:'. . .'; letter-spacing:.6em; color:var(--muted); }}
</style>
</head>
<body>
<div class="kit">
  <h1>Medium Paste Kit</h1>
  <p class="lead">Everything below the line pastes into Medium with headings, bold, code and all {n_img} images intact.</p>
  <ol class="steps">
    <li>On Medium, click <b>Write</b> to open a new, empty story.</li>
    <li>Click <b>Copy title</b>, click the Title line in Medium, paste. Press Enter.</li>
    <li>Click <b>Copy subtitle</b>, paste on the second line, press Enter.</li>
    <li>Click <b>Copy article</b>, paste on the empty line below. Wait for every image to finish uploading.</li>
    <li>Check it, then use <b>Publish</b>: add up to 5 topics and set the preview image to the first diagram.</li>
  </ol>
  <div class="row"><div class="txt"><div class="lbl">Title</div><div id="t">{title}</div></div><button data-copy="t">Copy title</button></div>
  <div class="row"><div class="txt"><div class="lbl">Subtitle</div><div id="s">{subtitle}</div></div><button data-copy="s">Copy subtitle</button></div>
  <button class="big" id="copyArticle">Copy article</button>
  <div class="status" id="status" role="status"></div>
  <p class="checks">After pasting, check for <b>{n_img} images</b> and <b>{n_h} section headings</b>.
  Suggested topics: Machine Learning, Data Science, Artificial Intelligence, Climate, Python.</p>
  <hr class="kitline">
</div>
<article id="article">
{body}
</article>
<script>
const status = document.getElementById('status');
function say(msg) {{ status.textContent = msg; }}
function selectNode(node) {{
  const r = document.createRange(); r.selectNodeContents(node);
  const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
}}
function pasteHtml(node) {{
  // Always hand Medium the public image URLs, even when the preview shows embedded copies.
  const c = node.cloneNode(true);
  c.querySelectorAll('img[data-src]').forEach(i => {{ i.src = i.dataset.src; i.removeAttribute('data-src'); }});
  return c.innerHTML;
}}
async function copyRich(node, label) {{
  const html = pasteHtml(node), text = node.innerText;
  const done = () => say(label + ' copied. Paste it into Medium.');
  let ok = false;
  const onCopy = e => {{ e.clipboardData.setData('text/html', html); e.clipboardData.setData('text/plain', text); e.preventDefault(); ok = true; }};
  document.addEventListener('copy', onCopy, {{once: true}});
  try {{ document.execCommand('copy'); }} catch (e) {{}}
  document.removeEventListener('copy', onCopy);
  if (ok) return done();
  try {{
    await navigator.clipboard.write([new ClipboardItem({{
      'text/html': new Blob([html], {{type: 'text/html'}}),
      'text/plain': new Blob([text], {{type: 'text/plain'}}),
    }})]);
    return done();
  }} catch (e) {{}}
  selectNode(node);
  say(label + ' is selected. Press Ctrl+C (Cmd+C on Mac) to copy it.');
}}
document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => {{
  const el = document.getElementById(b.dataset.copy);
  copyRich(el, b.textContent.replace('Copy ', '').replace(/^./, c => c.toUpperCase()));
}}));
document.getElementById('copyArticle').addEventListener('click', () => copyRich(document.getElementById('article'), 'Article'));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="main", help="git ref the raw image URLs point at")
    ap.add_argument("--skip-render", action="store_true", help="reuse existing table PNGs")
    ap.add_argument("--embed-to", help="also write a copy with images inlined, for viewers that block remote images")
    a = ap.parse_args()
    build(a.ref, a.skip_render, a.embed_to)
