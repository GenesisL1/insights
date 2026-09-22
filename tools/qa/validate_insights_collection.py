#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
INSIGHTS = SITE / "insights"


def fail(message: str) -> None:
    raise AssertionError(message)


def image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise AssertionError("Pillow is required for publication image QA") from exc
    with Image.open(path) as image:
        return image.size


def relative_refs(html: str) -> list[str]:
    refs = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html, flags=re.I)
    return [r for r in refs if not urlsplit(r).scheme and not r.startswith(("#", "//", "mailto:", "tel:", "data:"))]


pages = {
    "index": INSIGHTS / "index.html",
    "initial": INSIGHTS / "genesisl1-desci-blockchain-verifiable-ai-model-nfts.html",
    "renaissance": INSIGHTS / "genesisl1-decentralization-scientific-renaissance.html",
    "stake": INSIGHTS / "genesisl1-stake-distribution-decentralization-evidence.html",
    "evidence": SITE / "evidence/stake-distribution/index.html",
}
for label, path in pages.items():
    if not path.is_file():
        fail(f"missing {label} page: {path}")

index = pages["index"].read_text(encoding="utf-8")
for forbidden in (
    "Verifiable knowledge.",
    "Sovereign science.",
    "Three" + " distinct publications",
    "Editorial" + " architecture:",
):
    if forbidden in index:
        fail(f"obsolete landing-page copy remains: {forbidden}")
if index.count('class="publication-card"') != 3:
    fail("Insights landing page must contain exactly the three publication cards")

for label in ("initial", "renaissance", "stake"):
    path = pages[label]
    html = path.read_text(encoding="utf-8")
    if len(re.findall(r"<h1(?:\s|>)", html, flags=re.I)) != 1:
        fail(f"{label} must contain exactly one H1")
    if "datePublished" in html or "dateModified" in html:
        fail(f"{label} still exposes publication dates in structured data")
    if re.search(r">\s*(?:Updated|Published)\s+[A-Z][a-z]+\s+\d", html):
        fail(f"{label} still exposes a visible publication date")
    for required in ('rel="canonical"', 'property="og:image"', 'name="twitter:image"', 'max-image-preview:large'):
        if required not in html:
            fail(f"{label} missing SEO field: {required}")

renaissance = pages["renaissance"].read_text(encoding="utf-8")
stake = pages["stake"].read_text(encoding="utf-8")


def source_list_count(html: str, heading_id: str) -> int:
    match = re.search(
        rf'<h2\s+id=["\']{re.escape(heading_id)}["\'][^>]*>.*?</h2>\s*<ol>(.*?)</ol>',
        html,
        flags=re.I | re.S,
    )
    if not match:
        fail(f"missing source list: {heading_id}")
    return len(re.findall(r"<li(?:\s|>)", match.group(1), flags=re.I))


if source_list_count(renaissance, "sources-and-further-reading") != 7:
    fail("Renaissance source list must contain seven references")
if source_list_count(stake, "sources") != 7:
    fail("Stake source list must contain seven references")

for html_path in SITE.rglob("*.html"):
    html = html_path.read_text(encoding="utf-8", errors="replace")
    for ref in relative_refs(html):
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        target = (html_path.parent / clean).resolve()
        try:
            target.relative_to(SITE.resolve())
        except ValueError:
            continue
        if not target.exists():
            fail(f"broken local reference in {html_path.relative_to(SITE)}: {ref}")

expected_images = {
    "genesisl1-next-verifiable-renaissance-cover.webp": (1672, 941),
    "genesisl1-next-verifiable-renaissance-card-1100x620.webp": (1100, 620),
    "genesisl1-next-verifiable-renaissance-social-1200x630.jpg": (1200, 630),
    "genesisl1-stake-distribution-cover.webp": (1672, 941),
    "genesisl1-stake-distribution-card-1100x620.webp": (1100, 620),
    "genesisl1-stake-distribution-social-1200x630.jpg": (1200, 630),
    "genesisl1-initial-article-social-1200x630.jpg": (1200, 630),
    "genesisl1-insights-social-1200x630.jpg": (1200, 630),
}
for filename, expected in expected_images.items():
    path = INSIGHTS / "assets" / filename
    if not path.is_file():
        fail(f"missing publication image: {filename}")
    actual = image_size(path)
    if actual != expected:
        fail(f"wrong image dimensions for {filename}: {actual} != {expected}")

for label in ("initial", "renaissance", "stake"):
    html = pages[label].read_text(encoding="utf-8")
    if "brand-lockup" not in html or "CHAIN 29" not in html:
        fail(f"{label} missing the canonical GenesisL1 header lockup")
    if "toc-action-label" in html:
        fail(f"{label} retains obsolete split TOC action labels")
    if "Browse Insights" not in html or "Evidence repository" not in html:
        fail(f"{label} missing simplified article-rail actions")

if (ROOT / "press").exists():
    fail("press-release source files must remain outside the Insights repository publication")
for html_path in SITE.rglob("*.html"):
    if "press-release" in html_path.name.lower():
        fail(f"press-release page must remain outside Insights: {html_path.relative_to(SITE)}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for required in ("13,690,968", "33", "9.27%", "27.38%", "1,402"):
    if required not in readme:
        fail(f"README missing current evidence value: {required}")

manifest = ROOT / "SHA256SUMS.txt"
if manifest.is_file():
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = ROOT / rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            fail(f"project checksum mismatch: {rel}")

print("GenesisL1 Insights static validation passed")
