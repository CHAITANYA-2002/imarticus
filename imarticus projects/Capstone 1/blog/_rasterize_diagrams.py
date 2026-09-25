"""Render docs/diagrams/*.svg to blog/images/diagram-*.png, legibly and in colour.

    python blog/_rasterize_diagrams.py

The SVGs were drawn against Segoe UI. Rendered anywhere else they fall back to a
wider face and the text spills out of its boxes, which is what Medium showed.
This renders them with a metric-compatible narrow face, then checks every label
against the box it sits in: a label that still overflows is shrunk to fit, and a
box whose last line crosses its bottom edge grows to hold it.

It also breaks up the single-accent palette. Plain boxes take turns through a
set of soft tints, so sibling boxes read as distinct things at a glance, while
the accent box keeps its orange as the one the diagram is about.

Needs: playwright (and a Chromium; /opt/pw-browsers is used if present).
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BLOG = Path(__file__).resolve().parent
SOURCE = BLOG.parent / "docs" / "diagrams"
IMAGES = BLOG / "images"
SCALE = 2

# fill, stroke, heading ink for plain boxes, in turn
TINTS = [
    ("#E6F0FB", "#2F6DB5", "#1F4E86"),   # blue
    ("#E4F4EA", "#2E8B57", "#1E6440"),   # green
    ("#EFE8F9", "#7A4FB5", "#583589"),   # purple
    ("#FCE8EC", "#B8465F", "#8C2F45"),   # rose
    ("#E3F4F4", "#1F8A8A", "#166565"),   # teal
]

OVERRIDES = """
.t, .t-b { font-family: "Liberation Sans", Arial, sans-serif !important; }
.t-s     { font-family: "Liberation Sans", Arial, sans-serif !important; }
.t-m     { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace !important;
           font-size: 9.6px !important; }
"""

PAGE_JS = r"""
([tints]) => {
  const svg = document.querySelector('svg');
  const report = [];

  // 1. colour: plain boxes take turns through the tints
  const plain = [...svg.querySelectorAll('rect.n')];
  plain.forEach((r, i) => {
    const [fill, stroke] = tints[i % tints.length];
    r.style.fill = fill; r.style.stroke = stroke; r.style.strokeWidth = '1.6px';
    r.dataset.tint = i % tints.length;
  });

  const rects = [...svg.querySelectorAll('rect')].map(r => {
    const b = r.getBBox();
    return {el: r, x: b.x, y: b.y, w: b.width, h: b.height};
  }).filter(r => r.w > 30 && r.h > 16);

  const container = (t) => {
    const x = +t.getAttribute('x'), y = +t.getAttribute('y');
    const pick = (slack) => rects
      .filter(r => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h + slack)
      .sort((a, b) => a.w * a.h - b.w * b.h)[0];
    const strict = pick(4);
    if (strict) return strict;
    // A line drawn just below its box (a source slip) still belongs to that box,
    // but only when it continues a text block: same x and anchor as the line
    // right above it, which is itself inside the box. Axis labels do not qualify.
    const prev = t.previousElementSibling;
    if (prev && prev.tagName === 'text'
        && prev.getAttribute('x') === t.getAttribute('x')
        && prev.getAttribute('text-anchor') === t.getAttribute('text-anchor')
        && y - +prev.getAttribute('y') <= 18) {
      const box = pick(14);
      const py = +prev.getAttribute('y');
      if (box && py >= box.y && py <= box.y + box.h) return box;
    }
    return undefined;
  };

  // 2. headings inside a tinted box pick up its ink
  for (const t of svg.querySelectorAll('text.t-b')) {
    const c = container(t);
    if (c && c.el.dataset.tint !== undefined && !t.classList.contains('t-acc')) {
      t.style.fill = tints[+c.el.dataset.tint][2];
    }
  }

  // 3. fit: shrink labels wider than their box, grow boxes whose text runs past the bottom
  const PAD = 6;
  for (const t of svg.querySelectorAll('text')) {
    const c = container(t);
    if (!c) continue;
    let b = t.getBBox();
    const anchor = t.getAttribute('text-anchor') || 'start';
    const room = anchor === 'middle'
      ? 2 * Math.min(+t.getAttribute('x') - c.x, c.x + c.w - +t.getAttribute('x')) - 2 * PAD
      : anchor === 'end' ? +t.getAttribute('x') - c.x - PAD : c.x + c.w - +t.getAttribute('x') - PAD;
    if (b.width > room && anchor === 'start' && room <= 20) {
      // Too close to the right edge to shrink sensibly: slide it left to fit.
      const x = c.x + c.w - PAD - b.width;
      if (x >= c.x + PAD) {
        t.setAttribute('x', x.toFixed(1));
        report.push(`moved "${t.textContent.slice(0, 40)}" left to ${x.toFixed(1)}`);
        b = t.getBBox();
      }
    } else if (b.width > room && room > 20) {
      const size = parseFloat(getComputedStyle(t).fontSize);
      t.style.setProperty('font-size', (size * room / b.width).toFixed(2) + 'px', 'important');
      report.push(`shrunk "${t.textContent.slice(0, 40)}" ${size}px -> ${(size * room / b.width).toFixed(1)}px`);
      b = t.getBBox();
    }
    const bottom = b.y + b.height + 4;
    if (bottom > c.y + c.h) {
      const grow = bottom - (c.y + c.h);
      c.el.setAttribute('height', (c.h + grow).toFixed(1));
      c.h += grow;
      report.push(`grew box under "${t.textContent.slice(0, 40)}" by ${grow.toFixed(1)}`);
    }
  }

  // 4. make sure nothing now sits outside the canvas
  const bb = svg.getBBox();
  const vb = svg.viewBox.baseVal;
  const x0 = Math.min(vb.x, bb.x - 8), y0 = Math.min(vb.y, bb.y - 8);
  const x1 = Math.max(vb.x + vb.width, bb.x + bb.width + 8), y1 = Math.max(vb.y + vb.height, bb.y + bb.height + 8);
  svg.setAttribute('viewBox', `${x0} ${y0} ${x1 - x0} ${y1 - y0}`);
  svg.setAttribute('width', x1 - x0); svg.setAttribute('height', y1 - y0);
  return report;
}
"""


def main():
    exe = next(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"), None) if Path("/opt/pw-browsers").exists() else None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(exe) if exe else None)
        page = browser.new_page(device_scale_factor=SCALE, color_scheme="light")
        for svg_path in sorted(SOURCE.glob("*.svg")):
            svg = svg_path.read_text(encoding="utf-8").split("?>", 1)[-1]
            svg = svg.replace("</style>", OVERRIDES + "</style>", 1)
            page.set_content(f"<html><body style='margin:0;background:#fff'>{svg}</body></html>")
            report = page.evaluate(PAGE_JS, [TINTS])
            out = IMAGES / f"diagram-{svg_path.stem}.png"
            page.locator("svg").screenshot(path=str(out))
            print(f"{out.name}: {len(report)} fixes")
            for line in report:
                print("   ", line)
        browser.close()


if __name__ == "__main__":
    main()
