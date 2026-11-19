"""Render the three editorial images the blog uses: cover, the 1-in-48,000 dot field, and the lessons card.

    python blog/_make_cards.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

IMAGES = Path(__file__).resolve().parent / "images"

BASE = """
<style>
* { margin:0; box-sizing:border-box; }
body { background:#fff; }
.card { width:1400px; font-family: Georgia, 'Times New Roman', serif; color:#1f2a2e; }
.sans { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }
</style>
"""

# Faint contour lines, drawn as nested wobbly ellipses, for the cover's terrain texture.
CONTOURS = "".join(
    f'<ellipse cx="{1120 + i*6}" cy="{560 - i*4}" rx="{90 + i*46}" ry="{50 + i*27}" '
    f'transform="rotate({-18 + i*2} 1120 560)" fill="none" stroke="#e8b04b" stroke-opacity="{0.34 - i*0.022}" stroke-width="1.6"/>'
    for i in range(14)
)

# Built to survive Medium's preview crop (roughly 2.2:1, shown ~480px wide):
# one big number, one short line, everything inside the vertical middle.
COVER = BASE + f"""
<div class="card" style="height:788px;background:#16242a;position:relative;overflow:hidden;">
  <svg width="1400" height="788" style="position:absolute;inset:0">{CONTOURS}</svg>
  <div class="sans" style="position:absolute;left:96px;top:196px;color:#e8b04b;font-size:26px;letter-spacing:.2em;text-transform:uppercase;font-weight:700;">Slopewatch</div>
  <div style="position:absolute;left:84px;top:236px;display:flex;align-items:center;gap:44px;">
    <div style="color:#e8b04b;font-size:250px;line-height:1;font-weight:700;letter-spacing:-6px;">2.9×</div>
    <div>
      <div style="color:#fff;font-size:76px;line-height:1.05;font-weight:700;">the landslides<br>caught</div>
      <div class="sans" style="color:#c9d6d9;font-size:32px;line-height:1.35;margin-top:22px;width:640px;">
        vs. random inspection, checking just 10% of Himalayan slopes with public data</div>
    </div>
  </div>
</div>
"""

DOTS = BASE + """
<div class="card sans" style="padding:56px 64px 48px;">
  <div style="font-size:40px;font-weight:700;font-family:Georgia,serif;">This is what 1 in 48,000 looks like.</div>
  <div style="font-size:22px;color:#5b6b70;margin-top:10px;">Each dot is one grid cell on one day. Exactly one of them had a landslide. It's circled in orange.</div>
  <canvas id="c" width="1272" height="560" style="margin-top:28px;display:block;"></canvas>
  <div style="font-size:20px;color:#5b6b70;margin-top:22px;line-height:1.5;">
    A model that says <b style="color:#1f2a2e">"no landslide"</b> for every dot is right 47,999 times out of 48,000:
    <b style="color:#1f2a2e">99.998% accuracy</b>, and it never warns anyone about anything.</div>
</div>
<script>
const c = document.getElementById('c'), x = c.getContext('2d');
const cols = 320, rows = 150, sx = c.width / cols, sy = c.height / rows;
x.fillStyle = '#c3ccce';
for (let r = 0; r < rows; r++) for (let q = 0; q < cols; q++) {
  x.beginPath(); x.arc(q*sx + sx/2, r*sy + sy/2, 1.25, 0, 7); x.fill();
}
const tq = 231, tr = 97, cx = tq*sx + sx/2, cy = tr*sy + sy/2;
x.fillStyle = '#d9480f'; x.beginPath(); x.arc(cx, cy, 3.2, 0, 7); x.fill();
x.strokeStyle = '#d9480f'; x.lineWidth = 2.5; x.beginPath(); x.arc(cx, cy, 16, 0, 7); x.stroke();
</script>
"""

LESSONS = BASE + """
<div class="card" style="background:#f7f4ec;padding:72px 88px 76px;">
  <div class="sans" style="color:#b36b00;font-size:20px;letter-spacing:.16em;text-transform:uppercase;font-weight:700;">Four things I'd tell anyone building a model</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:44px 64px;margin-top:44px;">
    <div><div style="font-size:54px;color:#d9480f;font-weight:700;">1</div>
      <div style="font-size:31px;font-weight:700;line-height:1.2;margin-top:6px;">A number can be true and still mislead you.</div>
      <div class="sans" style="font-size:20px;color:#55656a;line-height:1.5;margin-top:12px;">Always ask what it's measured against.</div></div>
    <div><div style="font-size:54px;color:#d9480f;font-weight:700;">2</div>
      <div style="font-size:31px;font-weight:700;line-height:1.2;margin-top:6px;">The bug usually sits upstream of the symptom.</div>
      <div class="sans" style="font-size:20px;color:#55656a;line-height:1.5;margin-top:12px;">When a result looks odd, retrace how the data was made.</div></div>
    <div><div style="font-size:54px;color:#d9480f;font-weight:700;">3</div>
      <div style="font-size:31px;font-weight:700;line-height:1.2;margin-top:6px;">A fix without a test isn't finished.</div>
      <div class="sans" style="font-size:20px;color:#55656a;line-height:1.5;margin-top:12px;">And the test must be unable to pass by accident.</div></div>
    <div><div style="font-size:54px;color:#d9480f;font-weight:700;">4</div>
      <div style="font-size:31px;font-weight:700;line-height:1.2;margin-top:6px;">Measure your excuses.</div>
      <div class="sans" style="font-size:20px;color:#55656a;line-height:1.5;margin-top:12px;">"Not enough data" is a guess until you draw the learning curve.</div></div>
  </div>
</div>
"""


def main():
    exe = next(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"), None) if Path("/opt/pw-browsers").exists() else None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(exe) if exe else None)
        page = browser.new_page(device_scale_factor=1.5, viewport={"width": 1400, "height": 900})
        for name, html in [("card-cover.png", COVER), ("card-one-in-48000.png", DOTS), ("card-lessons.png", LESSONS)]:
            page.set_content(html)
            page.locator(".card").screenshot(path=str(IMAGES / name))
            print("wrote", name)
        browser.close()


if __name__ == "__main__":
    main()
