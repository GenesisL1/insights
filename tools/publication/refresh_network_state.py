#!/usr/bin/env python3
"""Refresh Article 02 with one newly captured GenesisL1 network-state snapshot.

The editorial argument and all non-network sections are preserved. This script
updates only the dated consensus/delegation/stake evidence, its references,
figure facts, evidence page and repository pointers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_DIR = ROOT / "content" / "article-02-next-verifiable-renaissance"
ARTICLE_MD = ARTICLE_DIR / "article.md"
ARTICLE_HTML = ROOT / "site" / "insights" / "genesisl1-decentralization-scientific-renaissance.html"
EVIDENCE_PAGE = ROOT / "site" / "decentralization" / "index.html"
REFERENCES = ARTICLE_DIR / "references.json"
STATE_FACTS = ARTICLE_DIR / "network-state.json"
REPO_README = ROOT / "README.md"
EVIDENCE_README = ROOT / "evidence" / "article-02" / "README.md"
WHITEPAPER = {
    "height": 13_313_640,
    "active": 20,
    "largest": Decimal("13.09"),
    "top3": Decimal("35.62"),
    "top5": Decimal("51.07"),
    "one_third": 3,
    "two_thirds": 8,
}
MOLNFT_HEIGHT = 13_412_747
MOLNFT_HASH = "19F42CD995E384E09D5CD4FB2751668E613D762DD1F22301D065EC84950F0F9A"


def require_sub(text: str, pattern: str, replacement: str, *, flags: int = 0, count: int = 1, label: str) -> str:
    updated, found = re.subn(pattern, replacement, text, count=count, flags=flags)
    if found != count:
        raise RuntimeError(f"Expected {count} replacement(s) for {label}, found {found}")
    return updated


def fmt_height(value: int) -> str:
    return f"{value:,}"


def q2(value: str | Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt2(value: str | Decimal) -> str:
    return f"{q2(value):.2f}"


def fmt_delta(current: Decimal, previous: Decimal) -> str:
    value = (current - previous).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}{abs(value):.2f}"


def fmt_count_delta(current: int, previous: int) -> str:
    value = current - previous
    return f"+{value}" if value > 0 else str(value)


def fmt_growth(current: int, previous: int) -> str:
    value = (Decimal(current - previous) / Decimal(previous) * Decimal(100)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    if value == value.to_integral():
        return f"{int(value)}"
    return f"{value:.1f}"


def number_word(value: int) -> str:
    words = {
        0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
        11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
        15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
        19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two",
        23: "twenty-three", 24: "twenty-four", 25: "twenty-five",
        26: "twenty-six", 27: "twenty-seven", 28: "twenty-eight",
        29: "twenty-nine", 30: "thirty", 31: "thirty-one", 32: "thirty-two",
        33: "thirty-three", 34: "thirty-four", 35: "thirty-five",
        36: "thirty-six", 37: "thirty-seven", 38: "thirty-eight",
        39: "thirty-nine", 40: "forty", 41: "forty-one", 42: "forty-two",
        43: "forty-three", 44: "forty-four", 45: "forty-five",
        46: "forty-six", 47: "forty-seven", 48: "forty-eight",
        49: "forty-nine", 50: "fifty",
    }
    return words.get(value, str(value))


def human_l1(value: str, places: int = 2) -> str:
    amount = Decimal(value)
    quant = Decimal(1).scaleb(-places)
    rounded = amount.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:,.{places}f}"


def load_snapshot(path: Path) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("metadata", {}).get("schema") != "org.genesisl1.network_state_snapshot.v3":
        raise RuntimeError("Unexpected network-state snapshot schema")
    base = path.parent
    import csv
    with (base / "validators.csv").open(encoding="utf-8", newline="") as handle:
        validators = list(csv.DictReader(handle))
    with (base / "delegators.csv").open(encoding="utf-8", newline="") as handle:
        delegators = list(csv.DictReader(handle))
    return snapshot, validators, delegators


def build_facts(snapshot: dict[str, Any], snapshot_dir: Path) -> dict[str, Any]:
    meta = snapshot["metadata"]
    consensus = snapshot["metrics"]["consensus"]
    staking = snapshot["metrics"]["staking"]
    delegation = snapshot["metrics"]["delegation"]
    height = int(meta["pinned_height"])
    block_time = dt.datetime.fromisoformat(str(meta["block_time_utc"]).replace("Z", "+00:00"))
    active = int(consensus["active_consensus_validators"])
    current_largest = q2(consensus["largest_validator_share_percent"])
    current_top3 = q2(consensus["top_3_share_percent"])
    current_top5 = q2(consensus["top_5_share_percent"])
    one = int(consensus["coefficient_at_or_above_one_third"])
    two = int(consensus["coefficient_strictly_above_two_thirds"])
    snapshot_rel = snapshot_dir.relative_to(ROOT).as_posix()
    snapshot_url = f"https://github.com/GenesisL1/insights/tree/main/{snapshot_rel}"
    return {
        "schema": "org.genesisl1.article02_network_state_facts.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pinned_height": height,
        "pinned_height_display": fmt_height(height),
        "block_time_utc": meta["block_time_utc"],
        "block_hash": meta["block_hash"],
        "block_date_iso": block_time.date().isoformat(),
        "block_date_display": f"{block_time.strftime('%B')} {block_time.day}, {block_time.year}",
        "block_date_label": f"{block_time.strftime('%B').upper()} {block_time.day} · BLOCK {fmt_height(height)}",
        "snapshot_relative_path": snapshot_rel,
        "snapshot_url": snapshot_url,
        "active_validators": active,
        "protocol_max_validators": int(consensus["protocol_max_validators"]),
        "active_set_utilization_percent": fmt2(consensus["active_set_utilization_percent"]),
        "active_delta": active - WHITEPAPER["active"],
        "active_delta_display": fmt_count_delta(active, WHITEPAPER["active"]),
        "active_growth_percent": fmt_growth(active, WHITEPAPER["active"]),
        "largest_share_percent": fmt2(current_largest),
        "largest_delta_points": fmt_delta(current_largest, WHITEPAPER["largest"]),
        "top3_share_percent": fmt2(current_top3),
        "top3_delta_points": fmt_delta(current_top3, WHITEPAPER["top3"]),
        "top5_share_percent": fmt2(current_top5),
        "top5_delta_points": fmt_delta(current_top5, WHITEPAPER["top5"]),
        "top10_share_percent": fmt2(consensus["top_10_share_percent"]),
        "one_third_coefficient": one,
        "one_third_delta": one - WHITEPAPER["one_third"],
        "two_thirds_coefficient": two,
        "two_thirds_delta": two - WHITEPAPER["two_thirds"],
        "effective_validator_count": f"{Decimal(consensus['effective_validator_count']):.2f}",
        "registered_validators": int(staking["registered_validator_records"]),
        "bonded_stake_l1": staking["pool_bonded_tokens_l1"],
        "bonded_stake_display": human_l1(staking["pool_bonded_tokens_l1"], 2),
        "bonded_ratio_total_supply_percent": fmt2(staking["bonded_ratio_total_supply_percent"]),
        "total_supply_l1": staking["total_supply_l1"],
        "total_supply_display": human_l1(staking["total_supply_l1"], 2),
        "unique_active_delegators": int(delegation["unique_delegators_to_active_validators"]),
        "active_delegation_relationships": int(delegation["active_delegation_relationships"]),
        "multi_validator_delegators": int(delegation["delegators_spread_across_multiple_active_validators"]),
        "largest_delegator_share_percent": fmt2(delegation["active_delegator_largest_share_percent"]),
        "top10_delegator_share_percent": fmt2(delegation["active_delegator_top_10_share_percent"]),
        "active_delegator_effective_count": f"{Decimal(delegation['active_delegator_effective_count']):.2f}",
        "whitepaper": {
            "height": WHITEPAPER["height"],
            "height_display": fmt_height(WHITEPAPER["height"]),
            "active_validators": WHITEPAPER["active"],
            "largest_share_percent": fmt2(WHITEPAPER["largest"]),
            "top3_share_percent": fmt2(WHITEPAPER["top3"]),
            "top5_share_percent": fmt2(WHITEPAPER["top5"]),
            "one_third_coefficient": WHITEPAPER["one_third"],
            "two_thirds_coefficient": WHITEPAPER["two_thirds"],
        },
        "molnft": {
            "pinned_height": MOLNFT_HEIGHT,
            "pinned_height_display": fmt_height(MOLNFT_HEIGHT),
            "block_hash": MOLNFT_HASH,
            "snapshot_url": "https://github.com/GenesisL1/insights/tree/main/evidence/article-02/molnft/block-13412747",
        },
    }


def update_markdown(facts: dict[str, Any]) -> None:
    text = ARTICLE_MD.read_text(encoding="utf-8")
    h = facts["pinned_height_display"]
    w = facts["whitepaper"]
    table = "\n".join(
        [
            f"| Measure | Whitepaper reference | Block {h} | Change |",
            "|---|---:|---:|---:|",
            f"| Active validators | {w['active_validators']} | {facts['active_validators']} | {facts['active_delta_display']} |",
            f"| Largest validator | {w['largest_share_percent']}% | {facts['largest_share_percent']}% | {facts['largest_delta_points']} points |",
            f"| Top three | {w['top3_share_percent']}% | {facts['top3_share_percent']}% | {facts['top3_delta_points']} points |",
            f"| Top five | {w['top5_share_percent']}% | {facts['top5_share_percent']}% | {facts['top5_delta_points']} points |",
            f"| One-third coefficient | {w['one_third_coefficient']} | {facts['one_third_coefficient']} | {fmt_count_delta(facts['one_third_coefficient'], w['one_third_coefficient'])} validators |",
            f"| Strict two-thirds coefficient | {w['two_thirds_coefficient']} | {facts['two_thirds_coefficient']} | {fmt_count_delta(facts['two_thirds_coefficient'], w['two_thirds_coefficient'])} validators |",
        ]
    )
    text = require_sub(
        text,
        r"The GenesisL1 comparison below uses the July 2026 whitepaper reference at block \*\*13,313,640\*\* and a preserved (?:CometBFT|current network-state) snapshot at block \*\*[\d,]+\*\*\.",
        f"The GenesisL1 comparison below uses the July 2026 whitepaper reference at block **13,313,640** and a preserved current network-state snapshot at block **{h}**.",
        label="Markdown evidence introduction",
    )
    text = require_sub(
        text,
        r"\| Measure \| Whitepaper reference \| Block [\d,]+ \| Change \|\n\|---\|---:\|---:\|---:\|\n(?:\|.*\n){6}",
        table + "\n",
        flags=re.MULTILINE,
        label="Markdown comparison table",
    )
    paragraph = (
        f"The active set expanded by {facts['active_growth_percent']}%. "
        f"{number_word(facts['one_third_coefficient']).capitalize()} leading validators were required to reach one-third of voting power, while "
        f"{number_word(facts['two_thirds_coefficient'])} were required to exceed the two-thirds commit threshold. "
        f"At the same height, **{facts['bonded_stake_display']} L1** was bonded across **{facts['unique_active_delegators']:,} unique delegator addresses** and **{facts['active_delegation_relationships']:,} active delegation relationships**. "
        "The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference."
    )
    text = require_sub(
        text,
        r"The active set expanded by [^\n]+The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference\.",
        paragraph,
        label="Markdown evidence summary",
    )
    faq = (
        f"The active set expanded from 20 to {facts['active_validators']} validators. Rounded consistently to two decimals, "
        f"the largest-validator share moved from 13.09% to {facts['largest_share_percent']}%, the top-three share from 35.62% to {facts['top3_share_percent']}%, "
        f"and the top-five share from 51.07% to {facts['top5_share_percent']}%. The one-third coefficient widened from three validators to "
        f"{number_word(facts['one_third_coefficient'])}, and the strict two-thirds coefficient from eight to {number_word(facts['two_thirds_coefficient'])}. "
        f"The same snapshot records {facts['bonded_stake_display']} L1 bonded across {facts['unique_active_delegators']:,} unique active delegator addresses."
    )
    text = require_sub(
        text,
        r"The active set expanded from 20 to \d+ validators\. Rounded consistently to two decimals, the largest-validator share moved from 13\.09% to [\d.]+%, the top-three share from 35\.62% to [\d.]+%, and the top-five share from 51\.07% to [\d.]+%\. The one-third coefficient widened from three validators to [a-z\-]+, and the strict two-thirds coefficient from eight to [a-z\-]+\.(?: The same snapshot records [^\n]+\.)?",
        faq,
        label="Markdown FAQ answer",
    )
    source = (
        f"2. **GenesisL1 reproducible network-state snapshot at block {h}.** Raw CometBFT and Cosmos JSON, complete validator and delegation CSVs, bonded-stake metrics, manifest and SHA-256 checksums. "
        f"[Immutable snapshot ↗]({facts['snapshot_url']})"
    )
    text = require_sub(
        text,
        r"2\. \*\*GenesisL1 reproducible (?:consensus|network-state) snapshot at block [\d,]+\.\*\*[^\n]+",
        source,
        label="Markdown source 2",
    )
    note = (
        f"Measurement note: Current validator, delegator and stake figures are pinned to block {h}. Publication comparisons are rounded consistently to two decimal places; exact integer state and higher-precision calculations remain in the machine-readable snapshot. MOLNFT reconstruction claims remain pinned separately to block 13,412,747 and refer only to the predeclared sample published in that evidence package."
    )
    text = require_sub(
        text,
        r"Measurement note: Current (?:consensus figures|validator, delegator and stake figures) are pinned to block [\d,]+\.[^\n]+",
        note,
        label="Markdown measurement note",
    )
    ARTICLE_MD.write_text(text, encoding="utf-8")


def html_table(facts: dict[str, Any]) -> str:
    w = facts["whitepaper"]
    rows = [
        ("Active validators", str(w["active_validators"]), str(facts["active_validators"]), facts["active_delta_display"]),
        ("Largest validator", f"{w['largest_share_percent']}%", f"{facts['largest_share_percent']}%", f"{facts['largest_delta_points']} points"),
        ("Top three", f"{w['top3_share_percent']}%", f"{facts['top3_share_percent']}%", f"{facts['top3_delta_points']} points"),
        ("Top five", f"{w['top5_share_percent']}%", f"{facts['top5_share_percent']}%", f"{facts['top5_delta_points']} points"),
        ("One-third coefficient", str(w["one_third_coefficient"]), str(facts["one_third_coefficient"]), f"{fmt_count_delta(facts['one_third_coefficient'], w['one_third_coefficient'])} validators"),
        ("Strict two-thirds coefficient", str(w["two_thirds_coefficient"]), str(facts["two_thirds_coefficient"]), f"{fmt_count_delta(facts['two_thirds_coefficient'], w['two_thirds_coefficient'])} validators"),
    ]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(label)}</td>"
        f"<td style=\"text-align:right\">{html.escape(previous)}</td>"
        f"<td style=\"text-align:right\">{html.escape(current)}</td>"
        f"<td style=\"text-align:right\">{html.escape(change)}</td>"
        "</tr>"
        for label, previous, current, change in rows
    )
    return (
        '<table aria-label="GenesisL1 decentralization metrics table 1" class="verification-table">'
        '<thead><tr><th>Measure</th><th style="text-align:right">Whitepaper reference</th>'
        f'<th style="text-align:right">Block {facts["pinned_height_display"]}</th><th style="text-align:right">Change</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def update_json_ld(text: str, facts: dict[str, Any], faq_answer: str) -> str:
    pattern = r'<script type="application/ld\+json">(.*?)</script>'
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        raise RuntimeError("JSON-LD script not found")
    data = json.loads(match.group(1))
    graph = data.get("@graph", [])
    article = next(item for item in graph if item.get("@type") == "TechArticle")
    article["dateModified"] = facts["block_date_iso"]
    citations = list(article.get("citation") or [])
    old_prefixes = (
        "https://github.com/GenesisL1/insights/tree/main/evidence/article-02/consensus/",
        "https://github.com/GenesisL1/insights/tree/main/evidence/article-02/network-state/",
    )
    citations = [facts["snapshot_url"] if value.startswith(old_prefixes) else value for value in citations]
    if facts["snapshot_url"] not in citations:
        citations.insert(1, facts["snapshot_url"])
    article["citation"] = citations
    faq_page = next(item for item in graph if item.get("@type") == "FAQPage")
    for entity in faq_page.get("mainEntity", []):
        if entity.get("name") == "How has GenesisL1 decentralization changed since the whitepaper?":
            entity["acceptedAnswer"]["text"] = faq_answer
    article_text = ARTICLE_MD.read_text(encoding="utf-8")
    word_count = len(re.findall(r"\b[\w’'-]+\b", re.sub(r"<[^>]+>", " ", article_text)))
    article["wordCount"] = word_count
    article["timeRequired"] = f"PT{max(1, math.ceil(word_count / 200))}M"
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start(1)] + encoded + text[match.end(1) :]


def update_article_html(facts: dict[str, Any]) -> None:
    text = ARTICLE_HTML.read_text(encoding="utf-8")
    h = facts["pinned_height_display"]
    figcaption = (
        f"The active set grew from 20 to {facts['active_validators']}, the top-five share moved from 51.07% to {facts['top5_share_percent']}%, "
        f"and the one-third and strict two-thirds cohorts widened to {facts['one_third_coefficient']} and {facts['two_thirds_coefficient']} validators."
    )
    figure = (
        f'<figure class="article-figure"><button aria-label="Enlarge image: GenesisL1 validator distribution comparison between the July 2026 whitepaper reference and block {h}." '
        f'class="figure-zoom" data-caption="{html.escape(figcaption, quote=True)}" data-fallback-src="assets/genesisl1-consensus-widening.png" '
        'data-full-src="assets/genesisl1-consensus-widening.svg" data-zoom-image="" type="button"><picture><source srcset="assets/genesisl1-consensus-widening.svg" '
        f'type="image/svg+xml"/><img alt="GenesisL1 validator distribution comparison between the July 2026 whitepaper reference and block {h}." decoding="async" height="900" '
        'loading="lazy" src="assets/genesisl1-consensus-widening.png" width="1600"/></picture><span aria-hidden="true" class="zoom-badge"><svg focusable="false" '
        'viewbox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m15.5 15.5 5 5M10.5 7.5v6M7.5 10.5h6"></path></svg><span>Enlarge</span></span>'
        f'</button><figcaption>{html.escape(figcaption)}</figcaption></figure>'
    )
    text = require_sub(
        text,
        r'<figure class="article-figure"><button aria-label="Enlarge image: GenesisL1 validator distribution comparison.*?</figure>(?=<h2 id="decentralization-measured">)',
        figure,
        flags=re.DOTALL,
        label="HTML consensus figure",
    )
    fact_strip = (
        '<section class="fact-strip" aria-label="GenesisL1 decentralization comparison">'
        f'<div class="fact"><span>Active set</span><strong>20 → {facts["active_validators"]}</strong><small>{facts["active_delta"]} additional consensus seats.</small></div>'
        f'<div class="fact"><span>Top five</span><strong>51.07 → {facts["top5_share_percent"]}%</strong><small>Publication values rounded to two decimals.</small></div>'
        f'<div class="fact"><span>One-third coefficient</span><strong>3 → {facts["one_third_coefficient"]}</strong><small>A broader liveness-relevant cohort.</small></div>'
        f'<div class="fact"><span>Strict two-thirds</span><strong>8 → {facts["two_thirds_coefficient"]}</strong><small>{facts["two_thirds_coefficient"]} validators to cross commit power.</small></div>'
        '</section>'
    )
    text = require_sub(
        text,
        r'<section class="fact-strip" aria-label="GenesisL1 decentralization comparison">.*?</section>',
        fact_strip,
        flags=re.DOTALL,
        label="HTML fact strip",
    )
    snapshot_note = (
        '<aside class="snapshot-note"><span>PINNED, REPRODUCIBLE EVIDENCE</span>'
        f'<p>Current validator, delegator and stake state is preserved at block <strong>{h}</strong>; MOLNFT reconstruction remains preserved separately at block <strong>13,412,747</strong>. '
        'Both packages include raw responses, tabular results and SHA-256 manifests. <a href="https://genesisl1.com/decentralization/">Open the evidence page.</a></p></aside>'
    )
    text = require_sub(
        text,
        r'<aside class="snapshot-note">.*?</aside>',
        snapshot_note,
        flags=re.DOTALL,
        label="HTML snapshot note",
    )
    text = require_sub(
        text,
        r'<p>The GenesisL1 comparison below uses the July 2026 whitepaper reference at block <strong>13,313,640</strong> and a preserved (?:CometBFT|current network-state) snapshot at block <strong>[\d,]+</strong>\.',
        f'<p>The GenesisL1 comparison below uses the July 2026 whitepaper reference at block <strong>13,313,640</strong> and a preserved current network-state snapshot at block <strong>{h}</strong>.',
        label="HTML evidence introduction",
    )
    text = require_sub(
        text,
        r'<table aria-label="GenesisL1 decentralization metrics table 1" class="verification-table">.*?</table>',
        html_table(facts),
        flags=re.DOTALL,
        label="HTML comparison table",
    )
    summary = (
        f'<p>The active set expanded by {facts["active_growth_percent"]}%. {number_word(facts["one_third_coefficient"]).capitalize()} leading validators were required to reach one-third of voting power, while '
        f'{number_word(facts["two_thirds_coefficient"])} were required to exceed the two-thirds commit threshold. At the same height, <strong>{facts["bonded_stake_display"]} L1</strong> was bonded across '
        f'<strong>{facts["unique_active_delegators"]:,} unique delegator addresses</strong> and <strong>{facts["active_delegation_relationships"]:,} active delegation relationships</strong>. '
        'The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference.</p>'
    )
    text = require_sub(
        text,
        r'<p>The active set expanded by .*?The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference\.</p>',
        summary,
        flags=re.DOTALL,
        label="HTML evidence summary",
    )
    faq_text = (
        f'The active set expanded from 20 to {facts["active_validators"]} validators. Rounded consistently to two decimals, the largest-validator share moved from 13.09% to {facts["largest_share_percent"]}%, '
        f'the top-three share from 35.62% to {facts["top3_share_percent"]}%, and the top-five share from 51.07% to {facts["top5_share_percent"]}%. The one-third coefficient widened from three validators to '
        f'{number_word(facts["one_third_coefficient"])}, and the strict two-thirds coefficient from eight to {number_word(facts["two_thirds_coefficient"])}. The same snapshot records '
        f'{facts["bonded_stake_display"]} L1 bonded across {facts["unique_active_delegators"]:,} unique active delegator addresses.'
    )
    text = require_sub(
        text,
        r'(<summary>How has GenesisL1 decentralization changed since the whitepaper\?</summary><p>).*?(</p>)',
        lambda match: match.group(1) + html.escape(faq_text) + match.group(2),
        flags=re.DOTALL,
        label="HTML FAQ answer",
    )
    source = (
        f'<li id="source-2"><strong>GenesisL1 reproducible network-state snapshot at block {h}.</strong> Raw CometBFT and Cosmos JSON, complete validator and delegation CSVs, bonded-stake metrics, manifest and SHA-256 checksums. '
        f'<a href="{facts["snapshot_url"]}">Immutable snapshot ↗</a></li>'
    )
    text = require_sub(
        text,
        r'<li id="source-2"><strong>GenesisL1 reproducible (?:consensus|network-state) snapshot at block [\d,]+\.</strong>.*?</li>',
        source,
        flags=re.DOTALL,
        label="HTML source 2",
    )
    note = (
        f'<p class="article-disclaimer">Measurement note: Current validator, delegator and stake figures are pinned to block {h}. Publication comparisons are rounded consistently to two decimal places; exact integer state and higher-precision calculations remain in the machine-readable snapshot. MOLNFT reconstruction claims remain pinned separately to block 13,412,747 and refer only to the predeclared sample published in that evidence package.</p>'
    )
    text = require_sub(
        text,
        r'<p class="article-disclaimer">Measurement note: Current (?:consensus figures|validator, delegator and stake figures) are pinned to block [\d,]+\..*?</p>',
        note,
        flags=re.DOTALL,
        label="HTML measurement note",
    )
    text = text.replace(
        'https://github.com/GenesisL1/insights/tree/main/evidence/article-02/consensus/block-13412747',
        facts["snapshot_url"],
    )
    text = require_sub(
        text,
        r'<meta property="article:modified_time" content="[^"]+">',
        f'<meta property="article:modified_time" content="{facts["block_date_iso"]}T00:00:00+03:00">',
        label="article modified time",
    )
    text = update_json_ld(text, facts, faq_text)
    ARTICLE_HTML.write_text(text, encoding="utf-8")


def validator_table_html(validators: list[dict[str, str]]) -> str:
    active = [row for row in validators if row["status"] == "BOND_STATUS_BONDED"]
    active.sort(key=lambda row: int(row["consensus_rank"]))
    body = "".join(
        "<tr>"
        f"<td>{row['consensus_rank']}</td>"
        f"<td>{html.escape(row['moniker'])}</td>"
        f"<td class=\"num\">{int(row['voting_power']):,}</td>"
        f"<td class=\"num\">{q2(row['voting_power_share_percent']):.2f}%</td>"
        f"<td class=\"num\">{q2(row['cumulative_voting_power_share_percent']):.2f}%</td>"
        f"<td class=\"num\">{Decimal(row['tokens_l1']):,.2f} L1</td>"
        f"<td class=\"num\">{int(row['delegation_relationships']):,}</td>"
        "</tr>"
        for row in active
    )
    return (
        f'<section id="validators"><div class="eyebrow">Ranked active set</div><h2>All {len(active)} consensus validators.</h2>'
        '<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Validator</th><th>Voting power</th><th>Share</th><th>Cumulative</th><th>Bonded stake</th><th>Delegators</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div></section>'
    )


def update_evidence_page(facts: dict[str, Any], validators: list[dict[str, str]]) -> None:
    text = EVIDENCE_PAGE.read_text(encoding="utf-8")
    h = facts["pinned_height_display"]
    text = require_sub(
        text,
        r'<meta name="description" content="[^"]+">',
        f'<meta name="description" content="Reproduce GenesisL1 validator, delegator and bonded-stake state at block {h}, alongside the pinned MOLNFT reconstruction package at block 13,412,747.">',
        label="evidence meta description",
    )
    text = require_sub(
        text,
        r'<meta property="og:type".*?<meta property="og:image" content="[^"]+">',
        f'<meta property="og:type" content="website"><meta property="og:site_name" content="GenesisL1"><meta property="og:title" content="GenesisL1 Evidence — Current Network State and MOLNFT Reconstruction"><meta property="og:description" content="Reproducible validator, delegator and stake evidence at block {h}, plus pinned MOLNFT reconstruction at block 13,412,747."><meta property="og:url" content="https://genesisl1.com/decentralization/"><meta property="og:image" content="https://genesisl1.com/insights/assets/genesisl1-scientific-renaissance-social-1200x630.png">',
        flags=re.DOTALL,
        label="evidence Open Graph",
    )
    dataset = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "GenesisL1 current network state and pinned MOLNFT evidence",
        "description": "Height-pinned GenesisL1 validator, delegator and bonded-stake state with raw responses and SHA-256 checksums, alongside pinned MOLNFT contract-state reconstruction evidence.",
        "url": "https://genesisl1.com/decentralization/",
        "dateModified": facts["block_date_iso"],
        "creator": {"@type": "Organization", "name": "GenesisL1", "url": "https://genesisl1.com/"},
        "isBasedOn": [facts["snapshot_url"], facts["molnft"]["snapshot_url"]],
    }
    text = require_sub(
        text,
        r'<script type="application/ld\+json">.*?</script>',
        '<script type="application/ld+json">' + json.dumps(dataset, ensure_ascii=False, separators=(",", ":")) + '</script>',
        flags=re.DOTALL,
        label="evidence JSON-LD",
    )
    text = require_sub(
        text,
        r'<main><div class="eyebrow">.*?<div class="provenance">.*?</div>',
        f'<main><div class="eyebrow">Pinned evidence / current network state</div><h1>Two claims. Two reproducible evidence packages.</h1><p class="deck">GenesisL1 publishes validator, delegator and bonded-stake state as a preserved dataset, while MOLNFT reconstruction remains separately pinned to its original scientific evidence block. Publication values are rounded for readability; the artifacts retain exact integer state and full machine precision.</p>'
        f'<div class="provenance"><span><b>Chain</b> genesis_29-2</span><span><b>Network-state block</b> {h}</span><span><b>MOLNFT block</b> 13,412,747</span><span><b>Network-state hash</b> {facts["block_hash"]}</span></div>',
        flags=re.DOTALL,
        label="evidence page introduction",
    )
    w = facts["whitepaper"]
    comparison_rows = "".join(
        [
            f'<tr><th scope="row">Active validators</th><td>{w["active_validators"]}</td><td><strong>{facts["active_validators"]}</strong></td><td>{facts["active_delta_display"]} · +{facts["active_growth_percent"]}%</td></tr>',
            f'<tr><th scope="row">Largest validator</th><td>13.09%</td><td><strong>{facts["largest_share_percent"]}%</strong></td><td>{facts["largest_delta_points"]} points</td></tr>',
            f'<tr><th scope="row">Top three</th><td>35.62%</td><td><strong>{facts["top3_share_percent"]}%</strong></td><td>{facts["top3_delta_points"]} points</td></tr>',
            f'<tr><th scope="row">Top five</th><td>51.07%</td><td><strong>{facts["top5_share_percent"]}%</strong></td><td>{facts["top5_delta_points"]} points</td></tr>',
            f'<tr><th scope="row">One-third coefficient</th><td>3</td><td><strong>{facts["one_third_coefficient"]}</strong></td><td>{fmt_count_delta(facts["one_third_coefficient"], 3)} validators</td></tr>',
            f'<tr><th scope="row">Strict two-thirds coefficient</th><td>8</td><td><strong>{facts["two_thirds_coefficient"]}</strong></td><td>{fmt_count_delta(facts["two_thirds_coefficient"], 8)} validators</td></tr>',
        ]
    )
    consensus_section = (
        '<section id="consensus"><div class="eyebrow">01 / Current network state</div><h2>Decentralization should be measured, not declared.</h2>'
        f'<p class="lead">The headline validator values are calculated from CometBFT voting power at the pinned height. The same package captures all registered validator records, every returned delegation relationship, the staking pool and native supply.</p>'
        '<div class="metrics">'
        f'<article class="metric"><span>Pinned block</span><strong>{h}</strong><small>{html.escape(facts["block_time_utc"])}</small></article>'
        f'<article class="metric"><span>Active validators</span><strong>{facts["active_validators"]}</strong><small>{facts["active_set_utilization_percent"]}% of {facts["protocol_max_validators"]} slots</small></article>'
        f'<article class="metric"><span>Largest validator</span><strong>{facts["largest_share_percent"]}%</strong><small>Rounded for publication; exact value in JSON</small></article>'
        f'<article class="metric"><span>Top five</span><strong>{facts["top5_share_percent"]}%</strong><small>Down from 51.07% in the whitepaper</small></article>'
        f'<article class="metric"><span>Unique active delegators</span><strong>{facts["unique_active_delegators"]:,}</strong><small>{facts["active_delegation_relationships"]:,} active delegation relationships</small></article>'
        f'<article class="metric"><span>Bonded stake</span><strong>{facts["bonded_stake_display"]} L1</strong><small>{facts["bonded_ratio_total_supply_percent"]}% of native supply</small></article>'
        '</div>'
        f'<div class="table-wrap"><table><thead><tr><th>Measure</th><th>Whitepaper</th><th>Pinned snapshot</th><th>Change</th></tr></thead><tbody>{comparison_rows}</tbody></table></div>'
        f'<div class="actions"><a class="button" href="{facts["snapshot_url"]}">Open immutable network-state artifact ↗</a><a class="button secondary" href="https://explorer.genesisl1.org/validators">Live validator explorer ↗</a></div></section>'
    )
    text = require_sub(
        text,
        r'<section id="consensus">.*?</section>',
        consensus_section,
        flags=re.DOTALL,
        label="evidence consensus section",
    )
    text = require_sub(
        text,
        r'<section id="validators">.*?</section>',
        validator_table_html(validators),
        flags=re.DOTALL,
        label="evidence validator section",
    )
    EVIDENCE_PAGE.write_text(text, encoding="utf-8")


def update_references(facts: dict[str, Any]) -> None:
    data = json.loads(REFERENCES.read_text(encoding="utf-8"))
    data["validator_snapshot_directory"] = Path(facts["snapshot_relative_path"]).name
    data["validator_immutable_url"] = facts["snapshot_url"]
    data["network_state_block"] = facts["pinned_height"]
    data["network_state_block_hash"] = facts["block_hash"]
    data["network_state_captured_at_utc"] = facts["generated_at_utc"]
    REFERENCES.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_readmes(facts: dict[str, Any]) -> None:
    readme = REPO_README.read_text(encoding="utf-8")
    readme = require_sub(
        readme,
        r'- \[(?:Consensus evidence|Current validator, delegator and stake evidence)\]\(evidence/article-02/(?:consensus|network-state)/block-[^/]+/\)',
        f'- [Current validator, delegator and stake evidence]({facts["snapshot_relative_path"]}/)',
        label="repository current evidence link",
    )
    readme = require_sub(
        readme,
        r'The (?:evidence workflow is pinned to GenesisL1 block `13,412,747` and rejects a mismatching block hash|current network-state evidence is pinned to GenesisL1 block `[\d,]+`\. The MOLNFT reconstruction package remains independently pinned to block `13,412,747`)\.',
        f'The current network-state evidence is pinned to GenesisL1 block `{facts["pinned_height_display"]}`. The MOLNFT reconstruction package remains independently pinned to block `13,412,747`.',
        label="repository evidence note",
    )
    REPO_README.write_text(readme, encoding="utf-8")

    evidence_readme = (
        "# Article 02 evidence\n\n"
        f"The current validator, delegator and bonded-stake package is pinned to GenesisL1 block `{facts['pinned_height_display']}` with block hash `{facts['block_hash']}`. "
        "The MOLNFT reconstruction package remains pinned to its original block because it supports a separate scientific claim.\n\n"
        f"- [`{facts['snapshot_relative_path'].split('evidence/article-02/',1)[1]}/`]({facts['snapshot_relative_path'].split('evidence/article-02/',1)[1]}/) — current CometBFT voting-power distribution, all registered validators, complete returned delegation relationships, staking-pool state, native supply, raw responses and SHA-256 checksums.\n"
        "- [`consensus/block-13412747/`](consensus/block-13412747/) — historical consensus-only snapshot used by the previous Article 02 edition.\n"
        "- [`molnft/block-13412747/`](molnft/block-13412747/) — contract counters, raw JSON-RPC, runtime-code hashes, eight predeclared reconstructed BinaryCIF objects and SHA-256 checksums.\n\n"
        "These directories are immutable observations. Publication prose rounds percentages to two decimal places; the snapshots retain exact state.\n"
    )
    EVIDENCE_README.write_text(evidence_readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    snapshot_path = args.snapshot.resolve()
    snapshot, validators, _delegators = load_snapshot(snapshot_path)
    facts = build_facts(snapshot, snapshot_path.parent)
    STATE_FACTS.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_markdown(facts)
    update_article_html(facts)
    update_evidence_page(facts, validators)
    update_references(facts)
    update_readmes(facts)
    print(json.dumps(facts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
