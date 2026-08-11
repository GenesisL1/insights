#!/usr/bin/env python3
"""Publish Article 02 from one current network/protocol snapshot.

The script updates only marked current-state sections in the Markdown sources,
writes a compact machine-readable fact file, and regenerates the article,
press-release, Insights-index and evidence HTML pages.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import quote

import mistune

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content" / "article-02-next-verifiable-renaissance"
SITE = ROOT / "site"
ARTICLE_MD = CONTENT / "article.md"
PRESS_MD = CONTENT / "press-release.md"
FACTS_JSON = CONTENT / "network-state.json"
AUDIT_DIR = ROOT / "evidence" / "article-02" / "molnft" / "block-13436937"
AUDIT_SUMMARY = AUDIT_DIR / "summary.json"
WHITEPAPER = {
    "height": 13_313_640,
    "active_validators": 20,
    "largest_share_percent": Decimal("13.09"),
    "top3_share_percent": Decimal("35.62"),
    "top5_share_percent": Decimal("51.07"),
    "one_third_coefficient": 3,
    "two_thirds_coefficient": 8,
}


def q2(value: str | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt2(value: str | int | Decimal) -> str:
    return f"{q2(value):,.2f}"


def fmt_int(value: int) -> str:
    return f"{int(value):,}"


def fmt_signed(value: Decimal) -> str:
    rounded = q2(value)
    if rounded > 0:
        return f"+{rounded:.2f}"
    if rounded < 0:
        return f"−{abs(rounded):.2f}"
    return "0.00"


def replace_marker(text: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf"<!-- {re.escape(name)}_BEGIN -->.*?<!-- {re.escape(name)}_END -->",
        flags=re.S,
    )
    replacement = f"<!-- {name}_BEGIN -->\n{content.rstrip()}\n<!-- {name}_END -->"
    updated, count = pattern.subn(lambda _match: replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one marker block for {name}; found {count}")
    return updated


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def relative(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()



def build_facts(snapshot_path: pathlib.Path, molnft_path: pathlib.Path) -> dict[str, Any]:
    snapshot = load_json(snapshot_path)
    molnft = load_json(molnft_path)
    audit = load_json(AUDIT_SUMMARY)
    meta = snapshot["metadata"]
    metrics = snapshot["metrics"]
    consensus = metrics["consensus"]
    staking = metrics["staking"]
    delegation = metrics["delegation"]
    height = int(meta["pinned_height"])
    block_time = dt.datetime.fromisoformat(str(meta["block_time_utc"]).replace("Z", "+00:00"))

    active = int(consensus["active_consensus_validators"])
    current_largest = q2(consensus["largest_validator_share_percent"])
    current_top3 = q2(consensus["top_3_share_percent"])
    current_top5 = q2(consensus["top_5_share_percent"])
    current_top10 = q2(consensus["top_10_share_percent"])
    active_delta = active - WHITEPAPER["active_validators"]
    active_growth = Decimal(active_delta) / Decimal(WHITEPAPER["active_validators"]) * 100

    facts = {
        "schema": "org.genesisl1.article02_current_state.v2",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pinned_height": height,
        "pinned_height_display": fmt_int(height),
        "block_hash": str(meta["block_hash"]),
        "app_hash": str(meta["app_hash"]),
        "block_time_utc": str(meta["block_time_utc"]),
        "block_date_iso": block_time.date().isoformat(),
        "block_date_display": block_time.strftime("%B %-d, %Y"),
        "block_date_label": f"{block_time.strftime('%B %d').upper()} · BLOCK {fmt_int(height)}",
        "provider_name": str(meta["provider_name"]),
        "snapshot_relative_path": relative(snapshot_path.parent),
        "snapshot_url": f"https://github.com/GenesisL1/insights/tree/main/{relative(snapshot_path.parent)}",
        "active_validators": active,
        "protocol_max_validators": int(consensus["protocol_max_validators"]),
        "active_set_utilization_percent": fmt2(consensus["active_set_utilization_percent"]),
        "active_delta": active_delta,
        "active_delta_display": f"+{active_delta}" if active_delta >= 0 else str(active_delta),
        "active_growth_percent": fmt2(active_growth),
        "largest_share_percent": fmt2(current_largest),
        "top3_share_percent": fmt2(current_top3),
        "top5_share_percent": fmt2(current_top5),
        "top10_share_percent": fmt2(current_top10),
        "largest_delta_points": fmt_signed(current_largest - WHITEPAPER["largest_share_percent"]),
        "top3_delta_points": fmt_signed(current_top3 - WHITEPAPER["top3_share_percent"]),
        "top5_delta_points": fmt_signed(current_top5 - WHITEPAPER["top5_share_percent"]),
        "one_third_coefficient": int(consensus["coefficient_at_or_above_one_third"]),
        "two_thirds_coefficient": int(consensus["coefficient_at_or_above_two_thirds"]),
        "validator_hhi_10000": fmt2(consensus["hhi_10000"]),
        "effective_validator_count": fmt2(consensus["effective_validator_count"]),
        "validator_gini": str(consensus["gini_coefficient"]),
        "validator_normalized_entropy": str(consensus["normalized_entropy"]),
        "registered_validators": int(staking["registered_validator_records"]),
        "bonded_validators": int(staking["bonded_validator_records"]),
        "unbonding_validators": int(staking["unbonding_validator_records"]),
        "unbonded_validators": int(staking["unbonded_validator_records"]),
        "bonded_stake_l1": str(staking["pool_bonded_tokens_l1"]),
        "bonded_stake_display": fmt2(staking["pool_bonded_tokens_l1"]),
        "not_bonded_stake_l1": str(staking["pool_not_bonded_tokens_l1"]),
        "not_bonded_stake_display": fmt2(staking["pool_not_bonded_tokens_l1"]),
        "total_supply_l1": str(staking["total_supply_l1"]),
        "total_supply_display": fmt2(staking["total_supply_l1"]),
        "bonded_ratio_total_supply_percent": fmt2(staking["bonded_ratio_total_supply_percent"]),
        "unique_active_delegators": int(delegation["active_delegator_count"]),
        "active_delegation_relationships": int(delegation["active_delegation_relationships"]),
        "multi_validator_delegators": int(delegation["delegators_spread_across_multiple_active_validators"]),
        "largest_delegator_share_percent": fmt2(delegation["active_delegator_largest_share_percent"]),
        "top3_delegator_share_percent": fmt2(delegation["active_delegator_top_3_share_percent"]),
        "top5_delegator_share_percent": fmt2(delegation["active_delegator_top_5_share_percent"]),
        "top10_delegator_share_percent": fmt2(delegation["active_delegator_top_10_share_percent"]),
        "delegator_hhi_10000": fmt2(delegation["active_delegator_hhi_10000"]),
        "active_delegator_effective_count": fmt2(delegation["active_delegator_effective_count"]),
        "delegator_gini": str(delegation["active_delegator_gini_coefficient"]),
        "delegator_one_third_coefficient": int(delegation["active_delegator_coefficient_at_or_above_one_third"]),
        "delegator_two_thirds_coefficient": int(delegation["active_delegator_coefficient_at_or_above_two_thirds"]),
        "crosschecks": metrics["crosschecks"],
        "whitepaper": {
            "height": WHITEPAPER["height"],
            "height_display": fmt_int(WHITEPAPER["height"]),
            "active_validators": WHITEPAPER["active_validators"],
            "largest_share_percent": fmt2(WHITEPAPER["largest_share_percent"]),
            "top3_share_percent": fmt2(WHITEPAPER["top3_share_percent"]),
            "top5_share_percent": fmt2(WHITEPAPER["top5_share_percent"]),
            "one_third_coefficient": WHITEPAPER["one_third_coefficient"],
            "two_thirds_coefficient": WHITEPAPER["two_thirds_coefficient"],
        },
        "molnft": {
            "pinned_height": int(molnft["pinned_height"]),
            "pinned_height_display": fmt_int(int(molnft["pinned_height"])),
            "evm_block_hash": str(molnft["evm_block_hash"]),
            "counts": molnft["counts"],
            "state_relative_path": relative(molnft_path),
        },
        "molnft_randomized": {
            "B_pin": int(audit["B_pin"]),
            "B_seed": int(audit["B_seed"]),
            "N": int(audit["N"]),
            "successes": int(audit["successes"]),
            "fidelity_passes": int(audit["fidelity_passes"]),
            "failures": int(audit["failures"]),
            "failures_by_reason": audit["failures_by_reason"],
            "replacement_draws": int(audit["targeted_requery"]["replacement_draws"]),
            "revision_aware_records": audit["revision_aware_records"],
            "evidence_relative_path": relative(AUDIT_DIR),
        },
    }
    return facts


def network_block(f: dict[str, Any]) -> str:
    w = f["whitepaper"]
    return f'''At GenesisL1 block **{f['pinned_height_display']}**, dated **{f['block_date_display']}**, the active consensus set contained **{f['active_validators']} validators** out of a protocol maximum of {f['protocol_max_validators']}. The largest validator held **{f['largest_share_percent']}%** of voting power; the top three held **{f['top3_share_percent']}%**, the top five **{f['top5_share_percent']}%**, and the top ten **{f['top10_share_percent']}%**. {f['one_third_coefficient']} validators were required to reach one third of voting power and {f['two_thirds_coefficient']} to reach two thirds. The validator HHI was **{f['validator_hhi_10000']}**, corresponding to an effective validator count of **{f['effective_validator_count']}**. <sup><a href="#source-2">2</a></sup>

| Current observable state | Result |
|---|---:|
| Active consensus validators | **{f['active_validators']} / {f['protocol_max_validators']}** |
| Largest validator share | **{f['largest_share_percent']}%** |
| Top-three / top-five / top-ten share | **{f['top3_share_percent']}% / {f['top5_share_percent']}% / {f['top10_share_percent']}%** |
| Validators required for one third / two thirds | **{f['one_third_coefficient']} / {f['two_thirds_coefficient']}** |
| Validator HHI / effective validator count | **{f['validator_hhi_10000']} / {f['effective_validator_count']}** |
| Bonded stake | **{f['bonded_stake_display']} L1** |
| Bonded share of native supply | **{f['bonded_ratio_total_supply_percent']}%** |
| Unique delegator addresses to active validators | **{fmt_int(f['unique_active_delegators'])}** |
| Largest / top-ten active-delegator share | **{f['largest_delegator_share_percent']}% / {f['top10_delegator_share_percent']}%** |

Compared on the same two-decimal basis with the whitepaper reference state, the active set expanded from **{w['active_validators']} to {f['active_validators']} validators**. The largest-validator share moved from **{w['largest_share_percent']}% to {f['largest_share_percent']}%** ({f['largest_delta_points']} percentage points), the top-three share from **{w['top3_share_percent']}% to {f['top3_share_percent']}%** ({f['top3_delta_points']} points), and the top-five share from **{w['top5_share_percent']}% to {f['top5_share_percent']}%** ({f['top5_delta_points']} points). The one-third coefficient widened from **{w['one_third_coefficient']} to {f['one_third_coefficient']} validators**, and the two-thirds coefficient from **{w['two_thirds_coefficient']} to {f['two_thirds_coefficient']}**.

Delegation was also distributed across **{fmt_int(f['unique_active_delegators'])} active delegator addresses** and **{fmt_int(f['active_delegation_relationships'])} active validator–delegator relationships**; **{fmt_int(f['multi_validator_delegators'])} addresses** delegated across more than one active validator. The largest active delegator address represented **{f['largest_delegator_share_percent']}%** of bonded delegation and the top ten represented **{f['top10_delegator_share_percent']}%**. An address is not necessarily one beneficial owner: custodians can aggregate many users, while one party can control multiple addresses. These figures therefore measure observable ledger distribution, not complete social independence.'''


def molnft_block(f: dict[str, Any]) -> str:
    c = f["molnft"]["counts"]
    a = f["molnft_randomized"]
    rev = a["revision_aware_records"][0]
    return f'''At the current evidence block, the MOLNFT PDB v2 contract reported **{fmt_int(c['pdb_v2_parent_records'])} parent molecular records** and **{fmt_int(c['pdb_v2_total_tokens'])} total ERC-721 tokens**, including **{fmt_int(c['pdb_v2_child_chunks'])} child chunks** used to extend larger payloads. Legacy PDB v1 and AlphaFold/Swiss-Prot v1 collections are reported separately because they represent a different storage generation and may overlap scientifically; they are not added to the PDB v2 parent count as one corpus total. <sup><a href="#source-2">2</a></sup>

A separate randomized audit tested reconstruction fidelity rather than merely reading counters. The sample specification records an announcement time of 19:15:22Z, before block 13,436,979 existed; that time is self-recorded and not independently timestamped. What any third party can verify from the published record is that the draw is fully determined by the hash of block 13,436,979 and the specification's contents. The resulting {a['N']} IDs were drawn without replacement from the pinned PDB v2 parent range, with no off-chain token index and no replacement draws. The finalized result was **{a['successes']} successful reconstructions, {a['fidelity_passes']} of {a['N']} canonical structural-fidelity passes and zero final failures**. <sup><a href="#source-3">3</a></sup>

One sampled record, {rev['pdb_id']}, had {rev['atom_name_change_count']} atom-name labels changed by a documented later RCSB nomenclature revision. Stable atom IDs, every non-name identity field and all **148,945 Cartesian coordinates** remained aligned, with maximum deviation of **{rev['max_coordinate_deviation_angstrom']:g} Å**. It is therefore recorded as a structural-fidelity pass, with the nomenclature revision retained transparently as provenance—not as a second score.'''


def sources_block(f: dict[str, Any]) -> str:
    return f'''1. <span id="source-1"></span>**GenesisL1 Technical Whitepaper, Version 1.0, July 2026.** Public distribution, protocol architecture, L1 coin utility, governance and institutional operation. [Whitepaper ↗](https://genesisl1.com/whitepaper.pdf)
2. <span id="source-2"></span>**GenesisL1 current network and protocol-state snapshot at block {f['pinned_height_display']}.** Raw CometBFT, Cosmos and EVM responses; complete validator and delegation tables; current MOLNFT counters; calculations and SHA-256 manifest. [Current evidence ↗]({f['snapshot_url']})
3. <span id="source-3"></span>**GenesisL1 randomized MOLNFT reconstruction evidence at block {fmt_int(f['molnft_randomized']['B_pin'])}.** Published sample specification, future-block seed, direct NFT-ID calls, reconstructed and canonical BinaryCIF objects, per-record outcomes and checksums. [Audit evidence ↗](https://github.com/GenesisL1/insights/tree/main/{f['molnft_randomized']['evidence_relative_path']})
4. <span id="source-4"></span>**GenesisL1 Forest / GL1F.** Deterministic model representation and inference tooling. [Source ↗](https://github.com/GenesisL1/Forest) · [Technical paper ↗](https://gl1f.com/GL1F.pdf)
5. <span id="source-5"></span>**GenesisL1 CIPNFT.** Client-side encryption, on-chain ciphertext provenance and recipient-bound disclosure. [Source ↗](https://github.com/GenesisL1/cipnft)
6. **CometBFT consensus specification, v0.38.** Voting-power and commit-threshold model. [Specification ↗](https://docs.cometbft.com/v0.38/spec/consensus/consensus)'''


def measurement_block(f: dict[str, Any]) -> str:
    return f'''**Measurement note.** Current validator, delegator, stake and MOLNFT counter figures are pinned to GenesisL1 block {f['pinned_height_display']}. Publication comparisons use two-decimal displayed values consistently; exact integers and higher-precision calculations remain in the machine-readable snapshot. The randomized MOLNFT reconstruction audit is a separate immutable experiment pinned to block {fmt_int(f['molnft_randomized']['B_pin'])}.'''


def press_block(f: dict[str, Any]) -> str:
    w = f["whitepaper"]
    c = f["molnft"]["counts"]
    return f'''At GenesisL1 block **{f['pinned_height_display']}**, the network had **{f['active_validators']} active consensus validators**. The largest validator represented **{f['largest_share_percent']}%** of voting power, the top three **{f['top3_share_percent']}%**, and the top five **{f['top5_share_percent']}%**. {f['one_third_coefficient']} validators were required to reach one third of voting power and {f['two_thirds_coefficient']} to reach two thirds. The snapshot records a validator HHI of **{f['validator_hhi_10000']}** and an effective validator count of **{f['effective_validator_count']}**.

The same state records **{f['bonded_stake_display']} L1** bonded, equal to **{f['bonded_ratio_total_supply_percent']}%** of native supply, across **{fmt_int(f['unique_active_delegators'])} unique delegator addresses** to active validators. The largest active delegator address represented **{f['largest_delegator_share_percent']}%** of bonded delegation and the top ten represented **{f['top10_delegator_share_percent']}%**. Address-level figures are published with an explicit caveat that an address is not necessarily one beneficial owner.

Compared consistently at two-decimal precision with the whitepaper reference state, the active validator set expanded from {w['active_validators']} to {f['active_validators']}. The largest-validator share moved from {w['largest_share_percent']}% to {f['largest_share_percent']}%, the top-three share from {w['top3_share_percent']}% to {f['top3_share_percent']}%, and the top-five share from {w['top5_share_percent']}% to {f['top5_share_percent']}%.

Current MOLNFT contract counters are captured at the same publication block. The PDB v2 contract reported **{fmt_int(c['pdb_v2_parent_records'])} parent molecular records** and **{fmt_int(c['pdb_v2_total_tokens'])} total ERC-721 tokens**, including **{fmt_int(c['pdb_v2_child_chunks'])} child chunks** for larger payloads. Legacy v1 collections are reported separately and are not combined into an ambiguous corpus total.'''


def update_markdown(facts: dict[str, Any]) -> None:
    article = ARTICLE_MD.read_text(encoding="utf-8")
    article = replace_marker(article, "CURRENT_NETWORK", network_block(facts))
    article = replace_marker(article, "CURRENT_MOLNFT", molnft_block(facts))
    article = replace_marker(article, "CURRENT_SOURCES", sources_block(facts))
    article = replace_marker(article, "CURRENT_MEASUREMENT", measurement_block(facts))
    # Keep the FAQ statement current without making the entire article a template.
    article = re.sub(
        r"At the latest pinned publication block, GenesisL1 had \d+ active consensus validators\..*?Exact data and raw responses are preserved in the current evidence snapshot\.",
        f"At the latest pinned publication block, GenesisL1 had {facts['active_validators']} active consensus validators. The largest held {facts['largest_share_percent']}% of voting power; {facts['one_third_coefficient']} validators were required to reach one third and {facts['two_thirds_coefficient']} to reach two thirds. Exact data and raw responses are preserved in the current evidence snapshot.",
        article,
        count=1,
        flags=re.S,
    )
    ARTICLE_MD.write_text(article.rstrip() + "\n", encoding="utf-8")

    press = PRESS_MD.read_text(encoding="utf-8")
    press = replace_marker(press, "PRESS_CURRENT_STATE", press_block(facts))
    press = re.sub(r"\*\*ONLINE — [^*]+\*\*", f"**ONLINE — {facts['block_date_display']}**", press, count=1)
    PRESS_MD.write_text(press.rstrip() + "\n", encoding="utf-8")


def split_title(markdown_text: str) -> tuple[str, str, str]:
    lines = markdown_text.strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("Markdown document must begin with an H1")
    title = lines[0][2:].strip()
    subtitle = ""
    index = 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].strip().startswith("*") and lines[index].strip().endswith("*"):
        subtitle = lines[index].strip().strip("*").strip()
        index += 1
    body = "\n".join(lines[index:]).lstrip()
    return title, subtitle, body


def slugify(value: str) -> str:
    plain = re.sub(r"<[^>]+>", "", value)
    plain = html.unescape(plain).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")
    return slug or "section"


class HeadingRenderer(mistune.HTMLRenderer):
    def heading(self, text: str, level: int, **attrs: Any) -> str:
        return f'<h{level} id="{slugify(text)}">{text}</h{level}>\n'


def markdown_html(markdown_text: str) -> str:
    renderer = HeadingRenderer(escape=False)
    markdown = mistune.create_markdown(renderer=renderer, plugins=["table", "strikethrough"])
    return markdown(markdown_text)


def json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def article_shell(title: str, subtitle: str, body_html: str, facts: dict[str, Any], canonical: str, description: str, page_type: str = "TechArticle") -> str:
    word_count = len(re.findall(r"\b[\w’'-]+\b", re.sub(r"<[^>]+>", " ", body_html)))
    minutes = max(1, (word_count + 199) // 200)
    date_modified = facts["block_date_iso"]
    social = "https://genesisl1.com/insights/assets/genesisl1-scientific-renaissance-social-1200x630.png"
    schema = {
        "@context": "https://schema.org",
        "@type": page_type,
        "headline": title,
        "description": description,
        "datePublished": "2026-08-01" if page_type == "TechArticle" else facts["block_date_iso"],
        "dateModified": date_modified,
        "inLanguage": "en",
        "wordCount": word_count,
        "timeRequired": f"PT{minutes}M",
        "mainEntityOfPage": canonical,
        "image": social,
        "author": {"@type": "Person", "name": "Mikhail Fedorov", "url": "https://genesisl1.com/"},
        "publisher": {"@type": "Organization", "name": "GenesisL1", "url": "https://genesisl1.com/"},
        "citation": [
            "https://genesisl1.com/whitepaper.pdf",
            facts["snapshot_url"],
            f"https://github.com/GenesisL1/insights/tree/main/{facts['molnft_randomized']['evidence_relative_path']}",
        ],
    }
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)} | GenesisL1</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{canonical}"><meta name="author" content="Mikhail Fedorov"><meta name="theme-color" content="#ffffff">
<meta property="og:type" content="article"><meta property="og:site_name" content="GenesisL1"><meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{html.escape(description, quote=True)}"><meta property="og:image" content="{social}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(title, quote=True)}"><meta name="twitter:description" content="{html.escape(description, quote=True)}"><meta name="twitter:image" content="{social}">
<meta property="article:published_time" content="2026-08-01T00:00:00+03:00"><meta property="article:modified_time" content="{facts['block_time_utc']}">
<script type="application/ld+json">{json_script(schema)}</script>
<link rel="icon" type="image/svg+xml" href="assets/genesisl1-official-logo.svg"><link rel="apple-touch-icon" href="assets/genesisl1-official-logo.png">
<link rel="stylesheet" href="article-02.css">
</head>
<body>
<a class="skip-link" href="#article">Skip to article</a><div class="reading-progress" data-reading-progress aria-hidden="true"></div>
<header class="site-header"><a class="brand" href="https://genesisl1.com/" aria-label="GenesisL1 home"><img src="assets/genesisl1-official-logo.svg" width="40" height="40" alt=""><span>GenesisL1</span></a><button class="menu-toggle" data-menu-toggle type="button" aria-label="Open navigation" aria-expanded="false"><span></span><span></span></button><nav class="primary-nav" data-primary-nav aria-label="Primary"><a href="https://genesisl1.com/">Home</a><a href="https://genesisl1.com/overview.html">Overview</a><a href="https://genesisl1.com/ecosystem.html">Ecosystem</a><a href="https://genesisl1.com/insights/">Insights</a><a class="nav-cta" href="https://genesisl1.com/whitepaper.pdf">Whitepaper ↗</a></nav></header>
<main><section class="article-hero"><div class="article-hero__copy"><div class="article-kicker">GenesisL1 Insights · evidence-backed publication</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p><div class="article-meta"><span>By Mikhail Fedorov</span><span>Updated {html.escape(facts['block_date_display'])}</span><span>{minutes} min read</span></div></div><figure class="article-hero__figure"><picture><source srcset="assets/genesisl1-scientific-renaissance-hero.svg" type="image/svg+xml"><img src="assets/genesisl1-scientific-renaissance-hero.png" width="1600" height="1000" alt="GenesisL1 public scientific infrastructure for data, models, rights and verification"></picture></figure></section>
<div class="article-layout"><aside class="article-rail"><div class="rail-label">Current evidence</div><strong>Block {facts['pinned_height_display']}</strong><span>{facts['active_validators']} validators</span><span>{fmt_int(facts['unique_active_delegators'])} active delegators</span><a href="{facts['snapshot_url']}">Verify state ↗</a></aside><article class="article-body" id="article">{body_html}<div class="share-row"><span>SHARE / VERIFY / OPERATE</span><div class="share-actions"><button type="button" data-copy-link>Copy link</button><a target="_blank" rel="noopener noreferrer" href="https://twitter.com/intent/tweet?text={quote(title)}&url={quote(canonical)}">X ↗</a><a target="_blank" rel="noopener noreferrer" href="https://www.linkedin.com/sharing/share-offsite/?url={quote(canonical)}">LinkedIn ↗</a></div></div></article></div></main>
<footer class="site-footer"><div><strong>GenesisL1 · Chain 29</strong><br>Public Layer 1 for verifiable scientific data, models, rights and applications.</div><div class="footer-links"><a href="https://genesisl1.com/">Home</a><a href="https://genesisl1.com/insights/">Insights</a><a href="https://genesisl1.com/decentralization/">Evidence</a><a href="https://github.com/GenesisL1/insights">GitHub ↗</a></div></footer>
<script defer src="article-02.js"></script></body></html>'''


def render_pages(facts: dict[str, Any]) -> None:
    article_text = ARTICLE_MD.read_text(encoding="utf-8")
    title, subtitle, body = split_title(article_text)
    article_description = "GenesisL1 combines public ownership, current validator evidence, MOLNFT molecular-data integrity, deterministic models and encrypted scientific rights."
    article_html = article_shell(
        title,
        subtitle,
        markdown_html(body),
        facts,
        "https://genesisl1.com/insights/genesisl1-decentralization-scientific-renaissance.html",
        article_description,
        "TechArticle",
    )
    (SITE / "insights" / "genesisl1-decentralization-scientific-renaissance.html").write_text(article_html, encoding="utf-8")

    press_text = PRESS_MD.read_text(encoding="utf-8")
    press_title, press_subtitle, press_body = split_title(press_text)
    press_description = "GenesisL1 publishes current validator and delegation evidence alongside a 100-record MOLNFT audit with 100 of 100 structural-fidelity passes."
    press_html = article_shell(
        press_title,
        press_subtitle,
        markdown_html(press_body),
        facts,
        "https://genesisl1.com/insights/genesisl1-verifiable-ai-sovereign-science-press-release.html",
        press_description,
        "NewsArticle",
    )
    (SITE / "insights" / "genesisl1-verifiable-ai-sovereign-science-press-release.html").write_text(press_html, encoding="utf-8")

    render_insights_index(facts, title, article_description, press_title, press_description)
    render_evidence_page(facts)


def render_insights_index(facts: dict[str, Any], title: str, description: str, press_title: str, press_description: str) -> None:
    path = SITE / "insights" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'<article class="article-card" id="article-scientific-renaissance">.*?</article>',
        f'''<article class="article-card" id="article-scientific-renaissance"><a aria-label="Read {html.escape(title, quote=True)}" class="article-card-media" href="genesisl1-decentralization-scientific-renaissance.html"><picture><source srcset="assets/genesisl1-scientific-renaissance-card.svg" type="image/svg+xml"><img alt="GenesisL1 public infrastructure for verifiable AI and sovereign science" decoding="async" height="920" loading="lazy" src="assets/genesisl1-scientific-renaissance-card.png" width="1100"></picture></a><div class="article-card-copy"><div class="card-meta"><span>Current evidence · verifiable AI · DeSci</span><span>Updated {html.escape(facts['block_date_display'])}</span></div><h2>{html.escape(title)}</h2><p>{html.escape(description)}</p><div class="card-tags"><span>MOLNFT</span><span>CIPNFT</span><span>Validators</span><span>Sovereign science</span></div><a class="card-link" href="genesisl1-decentralization-scientific-renaissance.html"><span>Read the article</span><span aria-hidden="true">↗</span></a></div></article>
<article class="article-card" id="press-release-current"><a aria-label="Read the current GenesisL1 press release" class="article-card-media" href="genesisl1-verifiable-ai-sovereign-science-press-release.html"><picture><source srcset="assets/genesisl1-press-patron-public-record.svg" type="image/svg+xml"><img alt="GenesisL1 evidence-backed publication and public scientific record" decoding="async" height="920" loading="lazy" src="assets/genesisl1-press-patron-public-record.png" width="1100"></picture></a><div class="article-card-copy"><div class="card-meta"><span>Press release</span><span>{html.escape(facts['block_date_display'])}</span></div><h2>{html.escape(press_title)}</h2><p>{html.escape(press_description)}</p><div class="card-tags"><span>Current network state</span><span>100/100 audit</span><span>Public infrastructure</span></div><a class="card-link" href="genesisl1-verifiable-ai-sovereign-science-press-release.html"><span>Read the release</span><span aria-hidden="true">↗</span></a></div></article>''',
        text,
        count=1,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")


def render_evidence_page(f: dict[str, Any]) -> None:
    c = f["molnft"]["counts"]
    canonical = "https://genesisl1.com/decentralization/"
    description = f"Current GenesisL1 validator, delegation, stake and MOLNFT counter evidence pinned to block {f['pinned_height_display']}, plus the immutable 100-record MOLNFT fidelity audit."
    data_schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "GenesisL1 current network and protocol state",
        "description": description,
        "url": canonical,
        "dateModified": f["block_date_iso"],
        "creator": {"@type": "Organization", "name": "GenesisL1", "url": "https://genesisl1.com/"},
        "isBasedOn": [f["snapshot_url"], f"https://github.com/GenesisL1/insights/tree/main/{f['molnft_randomized']['evidence_relative_path']}"],
    }
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>GenesisL1 Current Evidence | Block {f['pinned_height_display']}</title><meta name="description" content="{html.escape(description, quote=True)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:title" content="GenesisL1 Current Network and Scientific Protocol Evidence"><meta property="og:description" content="{html.escape(description, quote=True)}"><meta property="og:image" content="https://genesisl1.com/insights/assets/genesisl1-scientific-renaissance-social-1200x630.png"><script type="application/ld+json">{json_script(data_schema)}</script><link rel="stylesheet" href="../insights/article-02.css"></head><body><header class="site-header"><a class="brand" href="https://genesisl1.com/"><img src="../insights/assets/genesisl1-official-logo.svg" width="40" height="40" alt=""><span>GenesisL1</span></a><nav class="primary-nav"><a href="https://genesisl1.com/">Home</a><a href="../insights/">Insights</a><a class="nav-cta" href="https://genesisl1.com/whitepaper.pdf">Whitepaper ↗</a></nav></header><main><section class="article-hero"><div class="article-hero__copy"><div class="article-kicker">Current reproducible evidence</div><h1>GenesisL1 state at block {f['pinned_height_display']}.</h1><p>One current snapshot for validators, delegators, bonded stake and MOLNFT counters; one separate immutable randomized fidelity audit.</p><div class="article-meta"><span>{html.escape(f['block_date_display'])}</span><span>{html.escape(f['provider_name'])}</span><span>SHA-256 manifest included</span></div></div><figure class="article-hero__figure"><img src="../insights/assets/genesisl1-consensus-widening.svg" alt="GenesisL1 validator distribution evidence"></figure></section><div class="article-layout"><aside class="article-rail"><div class="rail-label">Pinned state</div><strong>{f['pinned_height_display']}</strong><span>{f['active_validators']} validators</span><span>{fmt_int(f['unique_active_delegators'])} active delegators</span><a href="{f['snapshot_url']}">Open raw evidence ↗</a></aside><article class="article-body"><h2>Current network</h2><table><thead><tr><th>Metric</th><th>Result</th></tr></thead><tbody><tr><td>Active validators</td><td><strong>{f['active_validators']} / {f['protocol_max_validators']}</strong></td></tr><tr><td>Largest / top-three / top-five voting-power share</td><td><strong>{f['largest_share_percent']}% / {f['top3_share_percent']}% / {f['top5_share_percent']}%</strong></td></tr><tr><td>One-third / two-thirds coefficient</td><td><strong>{f['one_third_coefficient']} / {f['two_thirds_coefficient']}</strong></td></tr><tr><td>Validator HHI / effective validator count</td><td><strong>{f['validator_hhi_10000']} / {f['effective_validator_count']}</strong></td></tr><tr><td>Bonded stake / native supply bonded</td><td><strong>{f['bonded_stake_display']} L1 / {f['bonded_ratio_total_supply_percent']}%</strong></td></tr><tr><td>Active delegator addresses / relationships</td><td><strong>{fmt_int(f['unique_active_delegators'])} / {fmt_int(f['active_delegation_relationships'])}</strong></td></tr></tbody></table><p>Address-level distribution is not beneficial-owner distribution. The snapshot publishes exact raw state and complete tables so alternative analyses can be performed without relying on this summary.</p><h2>Current MOLNFT counters</h2><table><thead><tr><th>Metric</th><th>Result</th></tr></thead><tbody><tr><td>PDB v2 parent records</td><td><strong>{fmt_int(c['pdb_v2_parent_records'])}</strong></td></tr><tr><td>PDB v2 total ERC-721 tokens</td><td><strong>{fmt_int(c['pdb_v2_total_tokens'])}</strong></td></tr><tr><td>PDB v2 child chunks</td><td><strong>{fmt_int(c['pdb_v2_child_chunks'])}</strong></td></tr><tr><td>Legacy PDB v1 tokens</td><td><strong>{fmt_int(c['pdb_v1_tokens'])}</strong></td></tr><tr><td>Legacy AlphaFold/Swiss-Prot v1 tokens</td><td><strong>{fmt_int(c['af_v1_tokens'])}</strong></td></tr></tbody></table><p>Storage generations are reported separately and are not combined into one corpus total.</p><h2>Immutable randomized audit</h2><p>The precommitted audit at block {fmt_int(f['molnft_randomized']['B_pin'])} records <strong>{f['molnft_randomized']['successes']} successful reconstructions, {f['molnft_randomized']['fidelity_passes']} of {f['molnft_randomized']['N']} structural-fidelity passes, zero failures and no replacement draws</strong>.</p><div class="share-row"><a href="{f['snapshot_url']}">Current state package ↗</a><a href="https://github.com/GenesisL1/insights/tree/main/{f['molnft_randomized']['evidence_relative_path']}">Randomized audit ↗</a><a href="../insights/genesisl1-decentralization-scientific-renaissance.html">Read the article ↗</a></div><h2>Verify</h2><pre><code>cd evidence/article-02/network-state/block-{f['pinned_height']}
sha256sum -c SHA256SUMS.txt</code></pre></article></div></main><footer class="site-footer"><div><strong>GenesisL1 · Chain 29</strong><br>Observable protocol state, preserved with raw responses and checksums.</div><div class="footer-links"><a href="../insights/">Insights</a><a href="https://github.com/GenesisL1/insights">GitHub ↗</a></div></footer></body></html>'''
    (SITE / "decentralization" / "index.html").write_text(page, encoding="utf-8")


def write_readmes(f: dict[str, Any], snapshot_path: pathlib.Path) -> None:
    c = f["molnft"]["counts"]
    root_readme = f'''# GenesisL1 Insights

Current evidence-backed publications and reproducible source data for GenesisL1 scientific infrastructure.

## Current publication

- [Article: GenesisL1 — Public Infrastructure for Verifiable AI and Sovereign Science](content/article-02-next-verifiable-renaissance/article.md)
- [Press release](content/article-02-next-verifiable-renaissance/press-release.md)
- [Production HTML](site/insights/genesisl1-decentralization-scientific-renaissance.html)
- [Current evidence page](site/decentralization/index.html)

## Current verified state

Pinned GenesisL1 block: **{f['pinned_height_display']}** ({f['block_date_display']})

- **{f['active_validators']}** active validators; largest share **{f['largest_share_percent']}%**; top five **{f['top5_share_percent']}%**.
- **{f['bonded_stake_display']} L1** bonded across **{fmt_int(f['unique_active_delegators'])}** active delegator addresses.
- MOLNFT PDB v2: **{fmt_int(c['pdb_v2_parent_records'])}** parent records and **{fmt_int(c['pdb_v2_total_tokens'])}** total tokens.
- Randomized MOLNFT audit: **100/100 structural-fidelity passes, zero failures**.

[Open the current raw snapshot and checksums]({f['snapshot_relative_path']})

## Verify

```bash
cd {f['snapshot_relative_path']}
sha256sum -c SHA256SUMS.txt
```

The repository intentionally retains one current network/protocol snapshot and one immutable randomized MOLNFT audit. Historical workflow notes, temporary migration files and superseded network snapshots are not part of the current publication tree.
'''
    (ROOT / "README.md").write_text(root_readme, encoding="utf-8")

    evidence_readme = f'''# Article 02 evidence

## Current network and protocol state

- Block: **{f['pinned_height_display']}**
- Time: **{f['block_time_utc']}**
- Active validators: **{f['active_validators']}**
- Bonded stake: **{f['bonded_stake_display']} L1**
- Active delegator addresses: **{fmt_int(f['unique_active_delegators'])}**
- MOLNFT PDB v2 parent records: **{fmt_int(c['pdb_v2_parent_records'])}**

[Open the current state package](network-state/block-{f['pinned_height']})

## Immutable randomized MOLNFT audit

- Pinned reconstruction block: **{fmt_int(f['molnft_randomized']['B_pin'])}**
- Selected records: **100**
- Successful reconstructions: **100**
- Structural-fidelity passes: **100/100**
- Final failures: **0**

[Open the randomized audit](molnft/block-{f['molnft_randomized']['B_pin']})
'''
    (ROOT / "evidence" / "article-02" / "README.md").write_text(evidence_readme, encoding="utf-8")

    molnft_root = ROOT / "evidence" / "article-02" / "molnft"
    molnft_readme = f'''# MOLNFT randomized fidelity evidence

- Reconstruction block: **{fmt_int(f['molnft_randomized']['B_pin'])}**
- Future seed block: **{fmt_int(f['molnft_randomized']['B_seed'])}**
- Selected records: **100**
- Successful reconstructions: **100**
- Canonical structural-fidelity passes: **100/100**
- Final failures: **0**
- Replacement draws: **0**

[`sample-spec.json`](sample-spec.json) fixes the sample before the future seed block. [`block-{f['molnft_randomized']['B_pin']}/`](block-{f['molnft_randomized']['B_pin']}/) contains the draw, raw calls, reconstructed and canonical BinaryCIF objects, per-record outcomes and checksums.

The documented 5KCS RCSB atom-name revision is retained as provenance; all 148,945 coordinates align at `0 Å`, so the record is a structural-fidelity pass.
'''
    (molnft_root / "README.md").write_text(molnft_readme, encoding="utf-8")
    molnft_latest = {
        "schema": "org.genesisl1.molnft_audit_pointer.v2",
        "path": f"block-{f['molnft_randomized']['B_pin']}",
        "sample_size": 100,
        "successful_reconstructions": 100,
        "structural_fidelity_passes": 100,
        "final_failures": 0,
        "replacement_draws": 0,
        "precommit": "sample-spec.json",
    }
    (molnft_root / "LATEST.json").write_text(json.dumps(molnft_latest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    snapshot_readme = f'''# GenesisL1 current state snapshot

**Pinned block:** `{f['pinned_height']}`  
**Block time:** `{f['block_time_utc']}`  
**Block hash:** `{f['block_hash']}`  
**Provider:** `{f['provider_name']}`

| Metric | Result |
|---|---:|
| Active validators | **{f['active_validators']}** |
| Largest / top-three / top-five share | **{f['largest_share_percent']}% / {f['top3_share_percent']}% / {f['top5_share_percent']}%** |
| One-third / two-thirds coefficient | **{f['one_third_coefficient']} / {f['two_thirds_coefficient']}** |
| Validator HHI / effective count | **{f['validator_hhi_10000']} / {f['effective_validator_count']}** |
| Bonded stake | **{f['bonded_stake_display']} L1** |
| Native supply bonded | **{f['bonded_ratio_total_supply_percent']}%** |
| Active delegator addresses | **{fmt_int(f['unique_active_delegators'])}** |
| MOLNFT PDB v2 parents / total tokens | **{fmt_int(c['pdb_v2_parent_records'])} / {fmt_int(c['pdb_v2_total_tokens'])}** |

`validators.csv`, `delegations.csv` and `delegators.csv` contain the complete current tables. `raw/` contains the unmodified provider responses. `snapshot.json` and `molnft-state.json` contain exact machine-readable metrics and contract counters.

Address-level distribution is not beneficial-owner distribution. Current contract counters are separate from the immutable randomized reconstruction audit.

## Verify

```bash
sha256sum -c SHA256SUMS.txt
```
'''
    (snapshot_path.parent / "README.md").write_text(snapshot_readme, encoding="utf-8")


def write_latest(f: dict[str, Any], snapshot_path: pathlib.Path) -> None:
    pointer = {
        "schema": "org.genesisl1.current_state_pointer.v2",
        "pinned_height": f["pinned_height"],
        "block_time_utc": f["block_time_utc"],
        "block_hash": f["block_hash"],
        "snapshot_relative_path": f["snapshot_relative_path"],
        "captured_at_utc": load_json(snapshot_path)["metadata"]["captured_at_utc"],
    }
    latest = snapshot_path.parent.parent / "LATEST.json"
    latest.write_text(json.dumps(pointer, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_deployment(f: dict[str, Any]) -> None:
    deployment = ROOT / "deployment"
    deployment.mkdir(parents=True, exist_ok=True)
    readme = f'''# Deployment

1. Upload `site/insights/` to `/insights/`.
2. Upload `site/decentralization/` to `/decentralization/`.
3. Apply the permanent redirects in `_redirects`, `htaccess-snippet.txt` or `redirects.nginx.conf`.
4. Merge `sitemap-entry.xml` into the production sitemap.
5. Purge cached HTML and social-preview assets.
6. Confirm that the article and evidence page identify block **{f['pinned_height_display']}**.
'''
    (deployment / "README.md").write_text(readme, encoding="utf-8")
    sitemap = f'''<url>
  <loc>https://genesisl1.com/insights/genesisl1-decentralization-scientific-renaissance.html</loc>
  <lastmod>{f['block_date_iso']}</lastmod>
  <changefreq>weekly</changefreq>
  <priority>0.90</priority>
</url>
<url>
  <loc>https://genesisl1.com/insights/genesisl1-verifiable-ai-sovereign-science-press-release.html</loc>
  <lastmod>{f['block_date_iso']}</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.82</priority>
</url>
<url>
  <loc>https://genesisl1.com/decentralization/</loc>
  <lastmod>{f['block_date_iso']}</lastmod>
  <changefreq>weekly</changefreq>
  <priority>0.86</priority>
</url>
'''
    (deployment / "sitemap-entry.xml").write_text(sitemap, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--molnft", required=True, type=pathlib.Path)
    args = parser.parse_args()
    facts = build_facts(args.snapshot, args.molnft)
    FACTS_JSON.write_text(json.dumps(facts, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    update_markdown(facts)
    write_readmes(facts, args.snapshot)
    write_latest(facts, args.snapshot)
    render_pages(facts)
    write_deployment(facts)
    print(json.dumps({"pinned_height": facts["pinned_height"], "active_validators": facts["active_validators"], "unique_active_delegators": facts["unique_active_delegators"], "molnft_parent_records": facts["molnft"]["counts"]["pdb_v2_parent_records"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
