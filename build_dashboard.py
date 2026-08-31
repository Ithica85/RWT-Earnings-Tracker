"""
Assemble the RWT KPI dashboard page from the template and the chart PNGs.

`rwt_dashboard_template.html` is the page source. Wherever it contains a
placeholder of the form

    %%IMG:rwt_eps_chart.png%%

this script substitutes a base64 data URI built from that chart file, and
writes the finished single-file page to `rwt_dashboard.html`.

Why everything is inlined: the page is published as an Artifact, and a strict
CSP there blocks requests to any external host. Nothing can be loaded at view
time, so every image has to be embedded in the HTML itself.

Why WEBP rather than the source PNGs: matplotlib writes 2700px-wide files,
several times wider than any viewport needs. Downscaling to 1500px and
re-encoding as WEBP brings the finished page from roughly 1.9 MB to under
0.7 MB with no visible difference.

To publish or update the artifact, build the page and then hand
`rwt_dashboard.html` to Claude - the publishing step needs an interactive
session, so it is deliberately not automated here.
"""

import base64
import io
import os
import re

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "rwt_dashboard_template.html")
OUTPUT = os.path.join(HERE, "rwt_dashboard.html")

# Charts are rendered at 2700px; no viewport needs more than about 1500.
MAX_WIDTH = 1500
WEBP_QUALITY = 88

PLACEHOLDER = re.compile(r"%%IMG:([a-z0-9_]+\.png)%%")


def embed(chart_name):
    """Return a base64 WEBP data URI for one chart file."""
    path = os.path.join(HERE, chart_name)
    image = Image.open(path)

    if image.width > MAX_WIDTH:
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.LANCZOS)

    buffer = io.BytesIO()
    image.convert("RGB").save(
        buffer, format="WEBP", quality=WEBP_QUALITY, method=6
    )
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/webp;base64,{encoded}"


def main():
    html = open(TEMPLATE).read()

    charts = sorted(set(PLACEHOLDER.findall(html)))
    if not charts:
        raise SystemExit(f"No %%IMG:...%% placeholders found in {TEMPLATE}")

    missing = [c for c in charts if not os.path.exists(os.path.join(HERE, c))]
    if missing:
        raise SystemExit(
            "Missing chart files - run the plot_*.py scripts first:\n  "
            + "\n  ".join(missing)
        )

    for chart in charts:
        uri = embed(chart)
        html = html.replace(f"%%IMG:{chart}%%", uri)
        print(f"  embedded {chart:44} {len(uri) / 1024:7.0f} KB")

    with open(OUTPUT, "w") as handle:
        handle.write(html)

    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\nWrote {OUTPUT}  ({size:.2f} MB, {len(charts)} charts)")


if __name__ == "__main__":
    main()
