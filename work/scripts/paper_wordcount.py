"""Word count for docs/index.html and a few structural checks.

Strips tags, scripts, and styles. Counts words in the article at about 230 wpm.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "docs" / "index.html"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.imgs: list[tuple[str, str | None]] = []
        self._tag: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag in {"script", "style"}:
            self.skip += 1
        self._tag.append(tag)
        if attr.get("id"):
            self.ids.append(attr["id"])
        href = attr.get("href")
        if href and href.startswith("#"):
            self.hrefs.append(href[1:])
        if tag == "img":
            self.imgs.append((attr.get("src") or "", attr.get("alt")))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if self._tag:
            self._tag.pop()

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self._tag and self._tag[-1] in {"script", "style"}:
            return
        self.parts.append(data)


def main() -> None:
    raw = HTML.read_text(encoding="utf-8")
    parser = TextExtractor()
    parser.feed(raw)
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    # Drop the metadata line's placeholder so the count is the paper, then
    # the caller writes the count back. Count everything visible except nav.
    words = re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?", text)
    # Remove TOC words by a second pass is unnecessary if we accept them.
    # Recount article only.
    article = raw.split("<article>", 1)[1].split("</article>", 1)[0]
    article = re.sub(r"<script[\s\S]*?</script>", " ", article)
    article = re.sub(r"<style[\s\S]*?</style>", " ", article)
    article = re.sub(r"<[^>]+>", " ", article)
    article = re.sub(r"&\w+;", " ", article)
    article = re.sub(r"\s+", " ", article).strip()
    article_words = re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?", article)
    n = len(article_words)
    minutes = max(1, round(n / 230))
    print(f"article_words={n}")
    print(f"minutes={minutes}")
    dupes = [i for i in parser.ids if parser.ids.count(i) > 1]
    print("duplicate_ids", sorted(set(dupes)))
    missing = sorted({h for h in parser.hrefs if h not in parser.ids})
    print("missing_anchors", missing)
    missing_alt = [src for src, alt in parser.imgs if not alt]
    print("missing_alt", missing_alt)
    body = raw.split("<body>", 1)[1]
    repro = body.split('id="reproducibility"', 1)[1] if 'id="reproducibility"' in body else ""
    before = body.split('id="reproducibility"', 1)[0]
    w_before = re.findall(r"w0\d", before)
    print("w0_before_reproducibility", w_before)
    print("honest_count", len(re.findall(r"honest", body, flags=re.I)))
    print("em_dash_count", body.count("—"))
    assets = re.findall(r'(?:src|href)="(assets/[^"]+)"', raw)
    missing_files = [a for a in assets if not (ROOT / "docs" / a).exists()]
    print("missing_assets", missing_files)
    print("fonts_ok", all((ROOT / "docs" / p).exists() for p in [
        "assets/fonts/source-serif-4-latin-400-normal.woff2",
        "assets/fonts/source-serif-4-latin-400-italic.woff2",
        "assets/fonts/source-serif-4-latin-600-normal.woff2",
        "assets/fonts/inter-latin-400-normal.woff2",
        "assets/fonts/inter-latin-500-normal.woff2",
        "assets/fonts/inter-latin-600-normal.woff2",
    ]))


if __name__ == "__main__":
    main()
