"""Render docs/index.html to a PDF through headless Chromium."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "docs" / "index.html"
DEFAULT_OUTPUT = ROOT / "submission" / "paper.pdf"
# Chromium writes the current time into CreationDate and ModDate. The string
# length matches Chromium's stamp, so replacing it does not move the xref table.
FIXED_STAMP = b"D:20261005000000+00'00'"
STAMP_RE = re.compile(rb"D:20\d{12}\+00'00'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the research paper to PDF.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright is not installed. Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        chromium = playwright.chromium
        if not Path(chromium.executable_path).is_file():
            print(
                "Chromium is missing. Run: playwright install chromium",
                file=sys.stderr,
            )
            return 1
        try:
            browser = chromium.launch()
        except PlaywrightError as exc:
            if "doesn't exist" in str(exc):
                print(
                    "Chromium is missing. Run: playwright install chromium",
                    file=sys.stderr,
                )
                return 1
            raise
        try:
            # Viewport width is the screen layout width. Paper size is A4 below.
            # US Letter is the fallback if a submission requires it: format="Letter".
            page = browser.new_page(
                viewport={"width": 1280, "height": 1810},
                device_scale_factor=2,
            )
            page.emulate_media(media="print", color_scheme="light")
            page.goto(HTML_PATH.resolve().as_uri(), wait_until="load")
            page.evaluate("() => document.fonts.ready")
            page.pdf(
                path=str(output),
                format="A4",
                print_background=True,
                margin={
                    "top": "20mm",
                    "bottom": "20mm",
                    "left": "22mm",
                    "right": "22mm",
                },
                prefer_css_page_size=True,
                display_header_footer=False,
            )
        finally:
            browser.close()

    frozen = STAMP_RE.sub(FIXED_STAMP, output.read_bytes(), count=2)
    output.write_bytes(frozen)

    try:
        shown = output.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        shown = output.as_posix()
    print(f"Wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
