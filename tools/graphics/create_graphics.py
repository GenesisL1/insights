#!/usr/bin/env python3
"""Generate SVG and PNG publication graphics for GenesisL1 Article 02."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Iterable

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_SLUG = "article-02-next-verifiable-renaissance"
FIGURES = ROOT / "content" / ARTICLE_SLUG / "figures"
ASSETS = ROOT / "site" / "insights" / "assets"
FIGURES.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

STATE_PATH = ROOT / "content" / ARTICLE_SLUG / "network-state.json"
DEFAULT_STATE = {
    "pinned_height": 13412747,
    "pinned_height_display": "13,412,747",
    "block_date_label": "AUGUST 6 · BLOCK 13,412,747",
    "active_validators": 26,
    "active_delta": 6,
    "active_growth_percent": "30",
    "largest_share_percent": "9.36",
    "top3_share_percent": "25.27",
    "top5_share_percent": "38.74",
    "top5_delta_points": "−12.33",
    "one_third_coefficient": 5,
    "two_thirds_coefficient": 10,
    "bonded_stake_display": "—",
    "unique_active_delegators": 0,
    "active_delegation_relationships": 0,
}
NETWORK_STATE = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else DEFAULT_STATE
CURRENT_HEIGHT = NETWORK_STATE["pinned_height_display"]
CURRENT_BLOCK_LABEL = NETWORK_STATE["block_date_label"]
CURRENT_ACTIVE = int(NETWORK_STATE["active_validators"])
CURRENT_ACTIVE_DELTA = int(NETWORK_STATE["active_delta"])
CURRENT_ACTIVE_GROWTH = str(NETWORK_STATE["active_growth_percent"])
CURRENT_LARGEST = str(NETWORK_STATE["largest_share_percent"])
CURRENT_TOP3 = str(NETWORK_STATE["top3_share_percent"])
CURRENT_TOP5 = str(NETWORK_STATE["top5_share_percent"])
CURRENT_TOP5_FLOAT = float(CURRENT_TOP5)
CURRENT_TOP5_DELTA = str(NETWORK_STATE["top5_delta_points"])
CURRENT_ONE_THIRD = int(NETWORK_STATE["one_third_coefficient"])
CURRENT_TWO_THIRDS = int(NETWORK_STATE["two_thirds_coefficient"])
CURRENT_BONDED_STAKE = str(NETWORK_STATE.get("bonded_stake_display", "—"))
CURRENT_DELEGATORS = int(NETWORK_STATE.get("unique_active_delegators", 0))
CURRENT_RELATIONSHIPS = int(NETWORK_STATE.get("active_delegation_relationships", 0))

INK = "#071522"
TEXT = "#0B1420"
MUTED = "#617086"
BLUE = "#2164DF"
BLUE2 = "#6EA6FF"
PALE = "#F4F8FD"
LIGHT = "#EAF2FF"
LINE = "#D8E0E9"
WHITE = "#FFFFFF"
SOFT = "#FAFCFF"
GOLD = "#B48A3C"
GOLD_LIGHT = "#F6EFD9"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def txt(x: float, y: float, content: str, size: int = 30, weight: int = 500, fill: str = TEXT,
        anchor: str = "start", family: str = "Arial, Helvetica, sans-serif", spacing: float | None = None,
        opacity: float | None = None, element_id: str | None = None) -> str:
    attrs = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"', f'font-weight="{weight}"',
             f'fill="{fill}"', f'text-anchor="{anchor}"', f'font-family="{family}"']
    if element_id:
        attrs.append(f'id="{element_id}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity}"')
    return f"<text {' '.join(attrs)}>{esc(content)}</text>"


def multiline(x: float, y: float, lines: Iterable[str], size: int, line_height: int, weight: int = 500,
              fill: str = TEXT, anchor: str = "start", spacing: float | None = None) -> str:
    rows = list(lines)
    attrs = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"', f'font-weight="{weight}"',
             f'fill="{fill}"', f'text-anchor="{anchor}"', 'font-family="Arial, Helvetica, sans-serif"']
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else line_height}">{esc(line)}</tspan>' for i, line in enumerate(rows))
    return f"<text {' '.join(attrs)}>{spans}</text>"


def rect(x: float, y: float, w: float, h: float, fill: str = WHITE, stroke: str = LINE,
         radius: float = 0, sw: float = 1, opacity: float | None = None, element_id: str | None = None) -> str:
    op = f' opacity="{opacity}"' if opacity is not None else ""
    ident = f' id="{element_id}"' if element_id else ""
    return f'<rect{ident} x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{op}/>'


def line(x1: float, y1: float, x2: float, y2: float, stroke: str = LINE, sw: float = 2,
         dash: str | None = None, marker: bool = False) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#arrow)"' if marker else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}{m}/>'


def circle(cx: float, cy: float, r: float, fill: str = WHITE, stroke: str = LINE, sw: float = 1) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def logo_group(x: float, y: float, scale: float = 0.1, dark: bool = True) -> str:
    """GenesisL1 brand mark without the coin circle, for wordmarks and diagrams."""
    c1 = WHITE if not dark else "#000000"
    c2 = "#C9D8EE" if not dark else "#1A1A1A"
    return (
        f'<g transform="translate({x} {y}) scale({scale})">'
        f'<path d="M230 77 77 230 153 306 191 268 153 229 267 115Z" fill="{c1}"/>'
        f'<path d="M345 192H269L307 230 192 345 229 382 382 230Z" fill="{c2}"/>'
        '</g>'
    )


def canonical_l1_logo(x: float, y: float, size: float, stroke: str = LINE, shadow: bool = False) -> str:
    """Exact canonical L1 coin mark: black GenesisL1 symbol on a white circle.

    Geometry is copied from the official master SVG at
    https://genesisl1.com/press/assets/brand/genesisl1-official-logo.svg.
    """
    scale = size / 460.0
    filt = ' filter="url(#shadow)"' if shadow else ''
    return (
        f'<g data-l1-canonical-logo="true" transform="translate({x} {y}) scale({scale})"{filt}>'
        f'<circle cx="230" cy="230" r="229" fill="#FFFFFF" stroke="{stroke}" stroke-width="1"/>'
        '<path d="M230 77 77 230 153 306 191 268 153 229 267 115Z" fill="#000000"/>'
        '<path d="M345 192H269L307 230 192 345 229 382 382 230Z" fill="#1A1A1A"/>'
        '</g>'
    )


def defs(grid: bool = True) -> str:
    grid_def = ""
    if grid:
        grid_def = (
            '<pattern id="grid" width="42" height="42" patternUnits="userSpaceOnUse">'
            '<path d="M42 0H0V42" fill="none" stroke="#DDE7F3" stroke-width="1" opacity=".48"/>'
            '</pattern>'
        )
    return (
        '<defs>'
        f'{grid_def}'
        '<linearGradient id="fade" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#F9FBFE"/><stop offset="1" stop-color="#EEF4FB"/>'
        '</linearGradient>'
        '<linearGradient id="warmFade" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#FBFCFE"/><stop offset="1" stop-color="#F7F0E2"/>'
        '</linearGradient>'
        '<linearGradient id="darkFade" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#071522"/><stop offset="1" stop-color="#0D2845"/>'
        '</linearGradient>'
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#071522" flood-opacity=".10"/>'
        '</filter>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0 0 10 5 0 10Z" fill="{BLUE}"/>'
        '</marker>'
        '</defs>'
    )


def svg_header(w: int, h: int, title: str, desc: str, grid: bool = True) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(desc)}</desc>{defs(grid)}'
    )


def icon_building(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="M6 42V15L26 5l20 10v27"/><path d="M2 42h48"/>'
        '<path d="M14 20h5M31 20h5M14 29h5M31 29h5M24 42V32h5v10"/>'
        '</g>'
    )


def icon_database(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<ellipse cx="25" cy="9" rx="20" ry="7"/><path d="M5 9v26c0 4 9 7 20 7s20-3 20-7V9"/>'
        '<path d="M5 22c0 4 9 7 20 7s20-3 20-7"/>'
        '</g>'
    )


def icon_validator(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<circle cx="25" cy="25" r="17"/><path d="m17 25 6 6 11-14"/>'
        '<path d="M25 2v6M25 42v6M2 25h6M42 25h6"/>'
        '</g>'
    )


def icon_document(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="M9 4h24l10 10v32H9Z"/><path d="M33 4v11h10M16 24h20M16 32h20M16 40h12"/>'
        '</g>'
    )


def icon_shield(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="M25 4 44 11v13c0 12-8 20-19 25C14 44 6 36 6 24V11Z"/><path d="m16 26 6 6 12-15"/>'
        '</g>'
    )


def icon_microscope(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="m19 5 12 12-6 6-12-12zM23 22l-9 9"/><path d="M17 29c0 9 7 16 16 16M8 45h36M31 17l5 5"/>'
        '</g>'
    )


def icon_book(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="M4 8c11-3 18 0 21 5v32c-5-5-12-7-21-4Z"/><path d="M46 8c-11-3-18 0-21 5v32c5-5 12-7 21-4Z"/>'
        '<path d="M25 13v32"/>'
        '</g>'
    )


def icon_press(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<path d="M8 6h34M13 6v37M37 6v37M8 43h34"/><path d="M19 15h12v10H19zM16 30h18"/>'
        '<path d="M25 6v9M20 2h10"/>'
        '</g>'
    )


def icon_network(x: float, y: float, s: float = 1, color: str = BLUE) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="3">'
        '<circle cx="25" cy="9" r="5"/><circle cx="8" cy="38" r="5"/><circle cx="42" cy="38" r="5"/>'
        '<path d="M22 14 11 33M28 14l11 19M13 38h24"/>'
        '</g>'
    )


def write_svg(name: str, content: str) -> Path:
    path = FIGURES / f"{name}.svg"
    path.write_text(content, encoding="utf-8")
    return path


def render(svg_path: Path, width: int, height: int) -> Path:
    site_svg = ASSETS / svg_path.name
    site_svg.write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8")
    png = ASSETS / f"{svg_path.stem}.png"
    cairosvg.svg2png(url=str(svg_path), write_to=str(png), output_width=width, output_height=height)
    return png


def hero() -> None:
    """Balanced 16:9 editorial hero with generous safe margins and no clipped text."""
    w, h = 1600, 900
    s = [svg_header(
        w, h,
        "GenesisL1 and the Next Verifiable Renaissance",
        "GenesisL1 Article 02 hero: MOLNFT, Model NFTs, CIPNFT and the native L1 protocol resource in one verifiable scientific state.",
    )]
    s += [rect(0, 0, w, h, "url(#warmFade)", "none"), '<rect width="1600" height="900" fill="url(#grid)" opacity=".52"/>']
    s += [rect(0, 0, w, 86, WHITE, "none"), line(0, 86, w, 86, LINE, 1)]
    s += [logo_group(46, 18, .108), txt(104, 55, "GENESISL1", 22, 700, INK, spacing=1.2), txt(1522, 53, "INSIGHTS / 02", 13, 700, MUTED, "end", spacing=2.1)]

    # Left editorial field. Four short title lines stay comfortably inside a 620 px column.
    s += [line(70, 136, 70, 624, BLUE, 3)]
    s += [txt(92, 150, "PUBLIC SCIENTIFIC INFRASTRUCTURE", 13, 700, BLUE, spacing=2.2)]
    s += [txt(92, 212, "GENESISL1", 42, 700, INK, spacing=-.7)]
    s += [txt(92, 284, "THE NEXT", 55, 520, INK, spacing=-1.7)]
    s += [txt(92, 365, "VERIFIABLE", 69, 700, BLUE, spacing=-2.1)]
    s += [txt(92, 438, "RENAISSANCE", 57, 520, INK, spacing=-1.8)]
    s += [multiline(94, 502, [
        "Molecular data, deterministic models, encrypted rights",
        "and autonomous agents—one durable public history.",
    ], 20, 31, 500, MUTED)]
    s += [rect(92, 584, 568, 62, WHITE, LINE, 13, 1)]
    s += [txt(116, 610, "THE LEDGER IS THE PRESS.", 12, 700, BLUE, spacing=1.05)]
    s += [txt(116, 633, "THE INSTITUTION IS THE CUSTODIAN.", 12, 700, INK, spacing=1.0)]

    # Right protocol panel. Every card is entirely inside x=760…1530.
    px, py, pw, ph = 744, 126, 786, 532
    s += [rect(px, py, pw, ph, WHITE, LINE, 24, 1, .985), txt(px+36, py+46, "ONE PUBLIC STATE FOR SCIENTIFIC WORK", 13, 700, BLUE, spacing=1.65)]
    s += [txt(px+36, py+72, "DATA · MODELS · RIGHTS · UTILITY", 11, 700, MUTED, spacing=1.35)]

    cx, cy = 1137, 385
    # Connectors first, so they remain behind cards, the state label and typography.
    for x1, y1, x2, y2 in [
        (1052, 264, cx-78, cy-45), (1230, 264, cx+78, cy-45),
        (1052, 579, cx-78, cy+45), (1230, 579, cx+78, cy+45),
    ]:
        s += [line(x1, y1, x2, y2, BLUE, 2, "6 8")]

    s += [circle(cx, cy, 96, PALE, BLUE, 3), circle(cx, cy, 70, WHITE, LINE, 1), logo_group(cx-31, cy-31, .137)]
    # The caption has its own measured container; it is intentionally outside the circle.
    s += [rect(cx-112, 484, 224, 32, INK, INK, 16, 1, element_id="hero-state-label-box")]
    s += [txt(cx, 505, "COMMON VERIFIABLE STATE", 10, 700, WHITE, "middle", spacing=.92, element_id="hero-state-label")]

    # Fixed-width cards with conservative typography.
    card_specs = [
        (782, 210, "MOLNFT", ("MOLECULAR DATA",), icon_database, False),
        (1230, 210, "MODEL NFT", ("VERIFIABLE AI",), icon_network, False),
        (782, 525, "CIPNFT", ("ENCRYPTED RIGHTS",), icon_shield, False),
        (1230, 525, "L1 COIN", ("GAS · STAKING", "GOVERNANCE"), None, True),
    ]
    for x, y, title, sub_lines, icon, is_l1 in card_specs:
        s += [rect(x, y, 270, 108, WHITE, LINE, 16, 1)]
        if is_l1:
            s += [circle(x+46, y+51, 31, PALE, LINE, 1), canonical_l1_logo(x+20, y+25, 52)]
        else:
            s += [icon(x+20, y+27, .68)]
        s += [txt(x+82, y+43, title, 14, 700, INK, spacing=.72)]
        if len(sub_lines) == 1:
            s += [txt(x+82, y+74, sub_lines[0], 11, 700, BLUE, spacing=.78)]
        else:
            s += [txt(x+82, y+69, sub_lines[0], 10, 700, BLUE, spacing=.62), txt(x+82, y+88, sub_lines[1], 10, 700, BLUE, spacing=.75)]

    # Exact evidence strip, with each value contained in an equal cell.
    bx, by, bw, bh = 70, 704, 1460, 132
    s += [rect(bx, by, bw, bh, WHITE, LINE, 18, 1)]
    cell = bw / 4
    metrics = [
        ("ACTIVE SET", f"20 → {CURRENT_ACTIVE}", "Pinned consensus"),
        ("TOP FIVE", f"51.07 → {CURRENT_TOP5}%", "Lower leading share"),
        ("THRESHOLD BREADTH", f"⅓ 3→{CURRENT_ONE_THIRD} · ⅔ 8→{CURRENT_TWO_THIRDS}", "Broader critical cohorts"),
        ("REPRODUCIBLE EVIDENCE", f"BLOCK {CURRENT_HEIGHT}", "Raw JSON + SHA-256"),
    ]
    for i, (label, big, small) in enumerate(metrics):
        x = bx + i * cell
        if i:
            s += [line(x, by+22, x, by+bh-22, LINE, 1)]
        tx = x + 26
        big_size = 21 if i != 2 else 18
        s += [txt(tx, by+36, label, 10, 700, BLUE, spacing=1.15), txt(tx, by+78, big, big_size, 650, INK), txt(tx, by+106, small, 12, 500, MUTED)]

    s += ["</svg>"]
    out = write_svg("genesisl1-scientific-renaissance-hero", "".join(s))
    render(out, w, h)


def l1_utility() -> None:
    w, h = 1600, 900
    s = [svg_header(w, h, "L1 coin — the native protocol resource of GenesisL1", "Canonical L1 coin coordinates execution, consensus security and public governance across GenesisL1.")]
    s += [rect(0, 0, w, h, "url(#fade)", "none"), '<rect width="1600" height="900" fill="url(#grid)" opacity=".6"/>']
    s += [canonical_l1_logo(70, 58, 72, shadow=True)]
    s += [txt(166, 86, "GENESISL1 NATIVE PROTOCOL RESOURCE", 14, 700, BLUE, spacing=2.1)]
    s += [txt(166, 138, "L1 COIN", 46, 700, INK, spacing=-1.25)]
    # Two separately measurable lines preserve the editorial rhythm while keeping a generous gap to the diagram.
    s += [txt(70, 218, "EXECUTION · SECURITY", 35, 550, INK, spacing=-1.0, element_id="l1-title-line-1")]
    s += [txt(70, 263, "GOVERNANCE · SETTLEMENT", 35, 550, INK, spacing=-1.0, element_id="l1-title-line-2")]
    s += [multiline(72, 339, ["Network fees, deterministic execution, staking security", "and public governance—one protocol-native resource."], 19, 29, 500, MUTED)]

    cx, cy = 840, 505
    # Connectors are drawn first so they never cut through card typography.
    s += [line(cx, 316, cx, 378, BLUE, 2, "7 8"), line(600, 493, 705, 493, BLUE, 2, "7 8"), line(600, 675, 722, 566, BLUE, 2, "7 8"), line(975, 493, 1120, 493, BLUE, 2, "7 8"), line(960, 566, 1120, 675, BLUE, 2, "7 8"), line(cx, 642, cx, 725, BLUE, 2, "7 8")]
    s += [circle(cx, cy, 133, LIGHT, BLUE, 2), canonical_l1_logo(cx-91, cy-91, 182, shadow=True)]
    s += [rect(cx-88, cy+112, 176, 30, INK, INK, 15, 1), txt(cx, cy+133, "PROTOCOL RESOURCE", 11, 700, WHITE, "middle", spacing=1.25)]

    cards = [
        (190, 430, 410, 126, "STATE + GAS", "Register data, contracts and provenance", icon_database, None),
        (190, 625, 410, 126, "STAKE + SECURE", "Coordinate validators and delegators", icon_validator, None),
        (1120, 430, 400, 126, "GOVERNANCE", "Vote, delegate and direct the pool", icon_building, None),
        (1120, 625, 400, 126, "RIGHTS + SETTLEMENT", "MOLNFT, Model NFT and CIPNFT flows", icon_document, None),
        (640, 190, 400, 126, "VERIFIABLE COMPUTATION", "Deploy models and meter deterministic inference", icon_network, "l1-top-card"),
        (625, 725, 430, 112, "AUTONOMOUS SERVICES", "Settle authorized machine-to-machine actions", icon_microscope, None),
    ]
    for x, y, ww, hh, title, sub, icon, card_id in cards:
        s += [rect(x, y, ww, hh, WHITE, LINE, 15, 1, element_id=card_id), icon(x+21, y+30, .75), txt(x+82, y+47, title, 14, 700, INK, spacing=.82), txt(x+82, y+80, sub, 14, 500, MUTED)]

    s += [rect(70, 850, 1460, 31, INK, INK, 16, 1), txt(800, 871, "ONE NATIVE RESOURCE FOR EXECUTION, CONSENSUS SECURITY AND PUBLIC GOVERNANCE", 11, 700, WHITE, "middle", spacing=.9)]
    s += ["</svg>"]
    out = write_svg("genesisl1-l1-utility-layer", "".join(s)); render(out, w, h)


def consensus() -> None:
    w, h = 1600, 900
    s = [svg_header(w, h, "GenesisL1 consensus distribution widened", "Exact comparison of the July 2026 whitepaper reference and the pinned August 2026 validator snapshot.")]
    s += [rect(0, 0, w, h, WHITE, "none"), '<rect width="1600" height="900" fill="url(#grid)" opacity=".6"/>']
    s += [txt(72, 72, "HEIGHT-PINNED CONSENSUS EVIDENCE", 15, 700, BLUE, spacing=2.3)]
    s += [multiline(72, 139, ["The active set grew.", "Critical cohorts widened."], 50, 57, 500, INK, spacing=-1.7)]
    s += [txt(72, 270, f"Every current figure below is reproducible from the raw CometBFT response at block {CURRENT_HEIGHT}.", 20, 500, MUTED)]

    cards = [
        (72, 328, "JULY 19 · WHITEPAPER", "20 ACTIVE VALIDATORS", 51.07, "13.09%", "35.62%", "3", "8", INK),
        (852, 328, CURRENT_BLOCK_LABEL, f"{CURRENT_ACTIVE} ACTIVE VALIDATORS", CURRENT_TOP5_FLOAT, f"{CURRENT_LARGEST}%", f"{CURRENT_TOP3}%", str(CURRENT_ONE_THIRD), str(CURRENT_TWO_THIRDS), BLUE),
    ]
    for x, y, label, count, pct, largest, top3, one, two, fill in cards:
        s += [rect(x, y, 676, 440, WHITE, LINE, 18, 1), txt(x+34, y+45, label, 13, 700, BLUE, spacing=1.25), txt(x+34, y+88, count, 28, 600, INK)]
        s += [txt(x+34, y+132, "TOP-FIVE CUMULATIVE POWER", 12, 700, MUTED, spacing=1.1)]
        barx, bary, barw, barh = x+34, y+158, 608, 52
        s += [rect(barx, bary, barw, barh, PALE, LINE, 8, 1)]
        fillw = barw * pct / 100
        s += [rect(barx, bary, fillw, barh, fill, "none", 8, 0)]
        one_x = barx + barw/3; two_x = barx + 2*barw/3
        s += [line(one_x, bary-11, one_x, bary+barh+13, GOLD, 2, "4 4"), txt(one_x, bary-19, "⅓", 14, 700, GOLD, "middle")]
        s += [line(two_x, bary-11, two_x, bary+barh+13, MUTED, 1.5, "4 4"), txt(two_x, bary-19, "⅔", 14, 700, MUTED, "middle")]
        label_text = f"{pct:.2f}%"
        s += [txt(barx+fillw-10, bary+34, label_text, 19, 700, WHITE, "end")]
        s += [rect(x+34, y+244, 286, 67, LIGHT, LINE, 9, 1), txt(x+50, y+268, "LARGEST", 11, 700, BLUE, spacing=1.0), txt(x+50, y+298, largest, 24, 650, INK)]
        s += [rect(x+356, y+244, 286, 67, LIGHT, LINE, 9, 1), txt(x+372, y+268, "TOP THREE", 11, 700, BLUE, spacing=1.0), txt(x+372, y+298, top3, 24, 650, INK)]
        s += [rect(x+34, y+334, 286, 72, WHITE, LINE, 9, 1), txt(x+50, y+358, "ONE-THIRD COEFFICIENT", 11, 700, MUTED, spacing=.75), txt(x+50, y+394, one, 31, 650, INK)]
        s += [rect(x+356, y+334, 286, 72, WHITE, LINE, 9, 1), txt(x+372, y+358, "STRICT TWO-THIRDS", 11, 700, MUTED, spacing=.75), txt(x+372, y+394, two, 31, 650, INK)]

    s += [circle(800, 548, 45, INK, INK, 0), txt(800, 558, "→", 34, 400, WHITE, "middle")]
    s += [rect(230, 798, 1140, 59, LIGHT, LINE, 10, 1), txt(800, 835, f"TOP FIVE: {CURRENT_TOP5_DELTA} points · ACTIVE SET: +{CURRENT_ACTIVE_GROWTH}% · ⅓: 3 → {CURRENT_ONE_THIRD} · ⅔: 8 → {CURRENT_TWO_THIRDS}", 17, 700, INK, "middle")]
    s += [txt(800, 884, "Raw JSON, ranked CSV, full metrics and SHA-256 checksums are published with the snapshot.", 13, 500, MUTED, "middle")]
    s += ["</svg>"]
    p = write_svg("genesisl1-consensus-widening", "".join(s)); render(p, w, h)

def press_patron() -> None:
    w, h = 1600, 900
    s = [svg_header(w, h, "The press, the patron and the public record", "Renaissance institutions mapped to a modern public scientific ledger.")]
    s += [rect(0, 0, w, h, "url(#warmFade)", "none"), '<rect width="1600" height="900" fill="url(#grid)"/>']
    s += [txt(72, 74, "THE ARCHITECTURE OF A RENAISSANCE", 15, 700, BLUE, spacing=2.3)]
    s += [multiline(72, 142, ["Knowledge endures when support,", "memory and verification become institutions."], 47, 55, 500, INK, spacing=-1.4)]
    s += [txt(72, 275, "GenesisL1 translates an old civilizational pattern into public digital infrastructure.", 21, 500, MUTED)]

    stages = [
        (120, "PATRON", "Creates capacity", icon_building, GOLD),
        (395, "PRESS", "Multiplies the record", icon_press, BLUE),
        (670, "LIBRARY", "Preserves memory", icon_book, BLUE),
        (945, "ACADEMY", "Tests claims", icon_microscope, BLUE),
        (1220, "PUBLIC LEDGER", "Makes history replayable", icon_network, BLUE),
    ]
    for i, (x, title, sub, icon, color) in enumerate(stages):
        s += [circle(x+80, 510, 82, WHITE, color, 2), icon(x+55, 478, 1.05, color), txt(x+80, 625, title, 15, 700, INK, "middle", spacing=1.1), txt(x+80, 653, sub, 14, 500, MUTED, "middle")]
        if i < len(stages)-1:
            s += [line(x+165, 510, stages[i+1][0]-8, 510, BLUE, 3, "8 8", True)]

    s += [rect(110, 720, 1380, 104, WHITE, LINE, 0, 1)]
    s += [txt(800, 761, "THE LEDGER IS THE PRESS · THE COMMUNITY POOL IS THE PATRON", 18, 700, INK, "middle", spacing=1.0)]
    s += [txt(800, 797, "THE NODES ARE THE LIBRARIES · VERIFICATION IS THE INHERITANCE", 15, 700, BLUE, "middle", spacing=1.0)]
    s += ["</svg>"]
    p = write_svg("genesisl1-press-patron-public-record", "".join(s)); render(p, w, h)


def institutional_sovereignty() -> None:
    w, h = 1600, 900
    s = [svg_header(w, h, "GenesisL1 sovereignty without isolation", "Three-layer boundary for sovereign custody, CIPNFT protected disclosure and common verification with MOLNFT and model provenance.")]
    s += [rect(0, 0, w, h, "url(#warmFade)", "none"), '<rect width="1600" height="900" fill="url(#grid)" opacity=".62"/>']
    s += [txt(70, 72, "INSTITUTIONAL SCIENTIFIC ARCHITECTURE", 15, 700, BLUE, spacing=2.35)]
    s += [multiline(70, 142, ["SOVEREIGNTY", "WITHOUT ISOLATION"], 54, 61, 530, INK, spacing=-1.8)]
    s += [txt(72, 290, "Local authority over sensitive data. Shared verification of permitted scientific claims.", 20, 500, MUTED)]

    columns = [
        (70, "01", "SOVEREIGN CUSTODY", "INSTITUTIONAL BOUNDARY", [
            "RAW GENOMIC / CLINICAL DATA",
            "IDENTITY + CONSENT",
            "PRIVATE KEYS + POLICY",
            "LOCAL COMPUTATION + LOGS",
        ], icon_building, GOLD_LIGHT, GOLD),
        (560, "02", "PROTECTED DISCLOSURE", "CIPNFT ENCRYPTED RIGHTS", [
            "CIPHERTEXT, NOT PLAINTEXT",
            "RECIPIENT-BOUND ENVELOPES",
            "ATTRIBUTION + PROVENANCE",
            "PROGRAMMABLE ACCESS RULES",
        ], icon_shield, LIGHT, BLUE),
        (1050, "03", "COMMON VERIFICATION", "PUBLIC GENESISL1 STATE", [
            "MOLNFT PUBLIC OBJECTS",
            "MODEL + METHOD IDENTITY",
            "COMMITMENTS + LINEAGE",
            "AUTHORIZED DERIVED OUTPUTS",
        ], icon_network, PALE, BLUE),
    ]
    for x, num, title, subtitle, items, icon, fill, accent in columns:
        s += [rect(x, 350, 430, 390, WHITE, LINE, 18, 1), rect(x, 350, 430, 82, fill, "none", 18, 0)]
        s += [txt(x+28, 388, num, 13, 700, accent, spacing=1.5), icon(x+342, 368, .72, accent), txt(x+28, 421, title, 18, 700, INK, spacing=.65), txt(x+28, 468, subtitle, 12, 700, BLUE, spacing=1.15)]
        for i, item in enumerate(items):
            y = 525 + i*47
            s += [circle(x+34, y-5, 5, accent, accent, 0), txt(x+54, y, item, 13, 650, INK, spacing=.45)]
        if x < 1050:
            s += [line(x+430, 548, x+480, 548, BLUE, 3, "7 7", True)]

    s += [rect(70, 776, 1410, 76, INK, INK, 12, 1)]
    s += [txt(235, 811, "LOCAL ARCHIVE + INDEXER", 13, 700, BLUE2, "middle", spacing=1.1), txt(800, 811, "SELECTIVE INTEROPERABILITY", 13, 700, BLUE2, "middle", spacing=1.1), txt(1360, 811, "INDEPENDENT VERIFICATION", 13, 700, BLUE2, "middle", spacing=1.1)]
    s += [txt(800, 837, "THE PROTOCOL IS SHARED · CUSTODY AND ACCOUNTABILITY REMAIN INSTITUTIONAL", 12, 700, WHITE, "middle", spacing=.95)]
    s += ["</svg>"]
    out = write_svg("genesisl1-institutional-sovereignty", "".join(s)); render(out, w, h)


def stewardship() -> None:
    w, h = 1600, 900
    s = [svg_header(w, h, "Four institutional roles in GenesisL1", "Validator, archive node, bounded scientific pilot and operational memorandum.")]
    s += [rect(0, 0, w, h, WHITE, "none"), '<rect width="1600" height="900" fill="url(#grid)" opacity=".55"/>']
    s += [txt(72, 72, "TAKE A SEAT IN THE NEW ACADEMY", 15, 700, BLUE, spacing=2.4)]
    s += [multiline(72, 142, ["Participation is an operating role,", "not a vague endorsement."], 54, 61, 500, INK, spacing=-2)]
    s += [txt(72, 287, "Each role creates measurable consensus, memory, access or scientific evidence.", 21, 500, MUTED)]

    cards = [
        (72, 356, "01", "RUN A VALIDATOR", ["Institution-controlled keys", "Independent upgrade decisions", "Broader consensus cohort"], icon_validator),
        (816, 356, "02", "HOST AN ARCHIVE + INDEXER", ["Local public-state replica", "Independent query path", "Continuity beyond hosted interfaces"], icon_database),
        (72, 608, "03", "COMPLETE A BOUNDED PILOT", ["Exact public method", "Identified model + inputs", "Independently inspectable output"], icon_microscope),
        (816, 608, "04", "SIGN AN OPERATING MEMORANDUM", ["Custody and security", "Research and publication duties", "Continuity and accountability"], icon_document),
    ]
    for x, y, num, title, bullets, icon in cards:
        s += [rect(x, y, 712, 210, WHITE, LINE, 16, 1), rect(x, y, 88, 210, PALE, "none", 16, 0)]
        s += [txt(x+44, y+48, num, 14, 700, BLUE, "middle", spacing=1.5), icon(x+19, y+75, 1.02)]
        s += [txt(x+116, y+50, title, 18, 700, INK, spacing=.7)]
        for i, bullet in enumerate(bullets):
            yy = y+92+i*36
            s += [circle(x+122, yy-5, 4, BLUE, BLUE, 0), txt(x+140, yy, bullet, 16, 500, MUTED)]
    s += [rect(435, 846, 730, 38, INK, INK, 19, 1), txt(800, 871, "OPERATION CREATES MEASURABLE PUBLIC VALUE", 13, 700, WHITE, "middle", spacing=1.2)]
    s += ["</svg>"]
    p = write_svg("genesisl1-institutional-stewardship", "".join(s)); render(p, w, h)


def card() -> None:
    w, h = 1100, 920
    s = [svg_header(w, h, "GenesisL1 and the Next Verifiable Renaissance", "GenesisL1 Insights Article 02 card featuring MOLNFT, CIPNFT, verifiable AI and reproducible evidence.")]
    s += [rect(0, 0, w, h, "url(#warmFade)", "none"), '<rect width="1100" height="920" fill="url(#grid)" opacity=".68"/>']
    s += [logo_group(52, 34, .105), txt(110, 70, "GENESISL1 / INSIGHTS 02", 15, 700, INK, spacing=1.45)]
    s += [txt(52, 144, "VERIFIABLE AI · DESCI · MOLNFT", 12, 700, BLUE, spacing=1.75)]
    s += [txt(52, 216, "GENESISL1", 49, 700, BLUE, spacing=-1.2)]
    s += [multiline(52, 282, ["THE NEXT", "VERIFIABLE", "RENAISSANCE"], 51, 57, 520, INK, spacing=-1.75)]
    s += [multiline(54, 486, ["The ledger is the press.", "Verification is the inheritance."], 19, 30, 500, MUTED)]

    cards = [
        (670, 160, "MOLNFT", "MOLECULAR DATA", icon_database, False),
        (875, 300, "MODEL NFT", "VERIFIABLE AI", icon_network, False),
        (670, 440, "CIPNFT", "ENCRYPTED RIGHTS", icon_shield, False),
        (875, 580, "L1 COIN", "GAS · STAKING", None, True),
    ]
    for x, y, title, sub, icon, is_l1 in cards:
        s += [rect(x, y, 175, 105, WHITE, LINE, 13, 1)]
        if is_l1:
            s += [circle(x+36, y+50, 27, PALE, LINE, 1), canonical_l1_logo(x+13, y+27, 46)]
        else:
            s += [icon(x+14, y+28, .56)]
        s += [txt(x+62, y+42, title, 12, 700, INK, spacing=.62), txt(x+62, y+69, sub, 9, 700, BLUE, spacing=.65)]

    s += [rect(52, 744, 996, 122, WHITE, LINE, 0, 1)]
    metrics = [(78, f"20 → {CURRENT_ACTIVE}", "ACTIVE SET"), (354, f"51.07 → {CURRENT_TOP5}%", "TOP FIVE"), (734, f"⅓ 3→{CURRENT_ONE_THIRD} · ⅔ 8→{CURRENT_TWO_THIRDS}", "COHORTS")]
    for i, (x, big, label) in enumerate(metrics):
        if i: s += [line(x-24, 765, x-24, 844, LINE, 1)]
        s += [txt(x, 796, big, 22 if i<2 else 18, 650, INK), txt(x, 830, label, 11, 700, BLUE, spacing=1.25)]
    s += ["</svg>"]
    out = write_svg("genesisl1-scientific-renaissance-card", "".join(s)); render(out, w, h)


def social() -> None:
    w, h = 1200, 630
    s = [svg_header(w, h, "GenesisL1 and the Next Verifiable Renaissance", "Social preview for GenesisL1 Article 02: MOLNFT, CIPNFT, verifiable AI and exact consensus evidence.")]
    s += [rect(0, 0, w, h, "url(#warmFade)", "none"), '<rect width="1200" height="630" fill="url(#grid)" opacity=".62"/>']
    s += [rect(0, 0, w, 74, WHITE, "none"), line(0, 74, w, 74, LINE, 1), logo_group(32, 12, .102), txt(88, 49, "GENESISL1", 19, 700, INK, spacing=1.15), txt(1158, 47, "INSIGHTS / 02", 12, 700, MUTED, "end", spacing=1.9)]
    s += [txt(46, 126, "VERIFIABLE AI · DESCI · SOVEREIGN SCIENCE", 12, 700, BLUE, spacing=1.55)]
    s += [txt(46, 190, "GENESISL1", 43, 700, BLUE, spacing=-1.1)]
    s += [multiline(46, 244, ["THE NEXT VERIFIABLE", "RENAISSANCE"], 41, 47, 520, INK, spacing=-1.45)]
    s += [multiline(48, 370, ["Molecular data, encrypted rights and AI agents", "coordinated through one public Layer 1."], 17, 26, 500, MUTED)]

    stack = [
        (810, 142, "MOLNFT", "DATA", icon_database, False),
        (1000, 142, "MODEL NFT", "AI", icon_network, False),
        (810, 290, "CIPNFT", "RIGHTS", icon_shield, False),
        (1000, 290, "L1 COIN", "NATIVE GAS", None, True),
    ]
    for x, y, title, sub, icon, is_l1 in stack:
        s += [rect(x, y, 160, 112, WHITE, LINE, 13, 1)]
        if is_l1:
            s += [circle(x+37, y+54, 27, PALE, LINE, 1), canonical_l1_logo(x+14, y+31, 46)]
        else:
            s += [icon(x+16, y+30, .58)]
        s += [txt(x+68, y+45, title, 11, 700, INK, spacing=.55), txt(x+68, y+72, sub, 10, 700, BLUE, spacing=.75)]

    s += [rect(46, 496, 1114, 86, WHITE, LINE, 0, 1)]
    metrics = [(68, f"20 → {CURRENT_ACTIVE}", "ACTIVE SET"), (324, f"51.07 → {CURRENT_TOP5}%", "TOP FIVE"), (660, f"⅓ 3→{CURRENT_ONE_THIRD} · ⅔ 8→{CURRENT_TWO_THIRDS}", "COHORTS"), (966, CURRENT_HEIGHT, "PINNED BLOCK")]
    for i, (x, big, label) in enumerate(metrics):
        if i: s += [line(x-20, 512, x-20, 566, LINE, 1)]
        s += [txt(x, 535, big, 17 if i!=2 else 15, 650, INK), txt(x, 562, label, 9, 700, BLUE, spacing=1.05)]
    s += [txt(600, 614, "RAW JSON · RANKED CSV · SHA-256 · GENESISL1.COM", 10, 700, MUTED, "middle", spacing=1.3)]
    s += ["</svg>"]
    out = write_svg("genesisl1-scientific-renaissance-social-1200x630", "".join(s)); render(out, w, h)


def derivatives() -> None:
    card_png = ASSETS / "genesisl1-scientific-renaissance-card.png"
    with Image.open(card_png).convert("RGB") as img:
        side = min(img.width, img.height)
        left = (img.width - side) // 2
        square = img.crop((left, 0, left + side, side)).resize((1200, 1200), Image.Resampling.LANCZOS)
        square.save(ASSETS / "genesisl1-scientific-renaissance-1x1.png", optimize=True)
        target_ratio = 4/3
        crop_h = min(img.height, int(img.width / target_ratio))
        top = (img.height - crop_h) // 2
        crop = img.crop((0, top, img.width, top + crop_h)).resize((1200, 900), Image.Resampling.LANCZOS)
        crop.save(ASSETS / "genesisl1-scientific-renaissance-4x3.png", optimize=True)


def main() -> None:
    # Re-export the canonical master logo at high resolution for favicons, schema and publication use.
    official_source = ROOT / "content" / "brand" / "genesisl1-official-logo.svg"
    official = ASSETS / "genesisl1-official-logo.svg"
    official.write_text(official_source.read_text(encoding="utf-8"), encoding="utf-8")
    cairosvg.svg2png(url=str(official_source), write_to=str(ASSETS / "genesisl1-official-logo.png"), output_width=2048, output_height=2048)
    fallback_source = ROOT / "content" / "shared" / "figures" / "genesisl1-first-article-card-fallback.svg"
    fallback_site = ASSETS / fallback_source.name
    fallback_site.write_text(fallback_source.read_text(encoding="utf-8"), encoding="utf-8")
    cairosvg.svg2png(url=str(fallback_source), write_to=str(ASSETS / "genesisl1-first-article-card-fallback.png"), output_width=1100, output_height=920)
    hero(); l1_utility(); consensus(); press_patron(); institutional_sovereignty(); stewardship(); card(); social(); derivatives()
    for name in [
        "genesisl1-scientific-renaissance-hero",
        "genesisl1-l1-utility-layer",
        "genesisl1-consensus-widening",
        "genesisl1-press-patron-public-record",
        "genesisl1-institutional-sovereignty",
        "genesisl1-institutional-stewardship",
        "genesisl1-scientific-renaissance-card",
        "genesisl1-scientific-renaissance-social-1200x630",
    ]:
        print(name + ".svg/png")


if __name__ == "__main__":
    main()
