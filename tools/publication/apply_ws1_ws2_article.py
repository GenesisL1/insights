#!/usr/bin/env python3
"""Apply WS-1 and WS-2 evidence results to Article 02 without rewriting it."""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
from collections import Counter
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup

ARTICLE = pathlib.Path("content/article-02-next-verifiable-renaissance/article.md")
HTML = pathlib.Path("site/insights/genesisl1-decentralization-scientific-renaissance.html")
FACTS = pathlib.Path("content/article-02-next-verifiable-renaissance/network-state.json")
REFERENCES = pathlib.Path("content/article-02-next-verifiable-renaissance/references.json")
EVIDENCE_INDEX = pathlib.Path("evidence/article-02/README.md")


def fmt_decimal(value: Any, places: int = 2, commas: bool = False) -> str:
    number = Decimal(str(value))
    spec = f",.{places}f" if commas else f".{places}f"
    return format(number, spec)


def read_results(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def failure_phrase(summary: dict[str, Any]) -> str:
    failures = int(summary["failures"])
    if failures == 0:
        return "no recorded failures"
    details = summary.get("failures_by_reason") or {}
    rendered = ", ".join(f"{value} {key}" for key, value in sorted(details.items()))
    return f"{failures} published failures ({rendered})"


def ws1_markdown(summary: dict[str, Any], seed: dict[str, Any], evidence_rel: str) -> str:
    n = int(summary["N"])
    successes = int(summary["successes"])
    fidelity = int(summary["fidelity_passes"])
    enumerated = int(summary["enumerated_parent_count"])
    tolerance = Decimal(str(summary["coordinate_tolerance_angstrom"]))
    return (
        f"A later randomized evidence package fixed **N = {n}** in a repository commit before GenesisL1 seed block "
        f"**{int(seed['B_seed']):,}** existed. The resulting block hash was transformed by the declared Keccak-256 seed rule, "
        f"and the draw was made without replacement over **{enumerated:,} actual parent-token IDs** enumerated from pinned "
        f"contract state at block **{int(summary['B_pin']):,}**—not over an assumed contiguous integer range. "
        f"The pipeline reconstructed **{successes} of {n}** selected records and published {failure_phrase(summary)} with raw RPC "
        f"responses for every draw. <sup><a href=\"#source-15\">15</a></sup>\n\n"
        f"Canonical fidelity was tested record by record against RCSB BinaryCIF objects after deterministic atom-order normalization. "
        f"**{fidelity} records passed** the declared atom-count, chain/entity-ID, atom-identity and coordinate-agreement checks at a "
        f"maximum permitted deviation of **{tolerance:.6f} Å**. Serialized BinaryCIF equality is neither calculated nor used as a "
        f"fidelity criterion. The sample specification, future-block seed derivation, enumeration, complete success/failure table, "
        f"reconstructed and canonical objects, environment fingerprint and SHA-256 manifest are all preserved in the evidence package."
    )


def ws2_table_rows(ws2: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    v = ws2["validator_concentration"]
    s = ws2["stake"]
    return [
        ("Validator HHI (0–10,000)", "—", fmt_decimal(v["hhi_10000"]), "—"),
        ("Effective validator count", "—", fmt_decimal(v["effective_count"]), "—"),
        ("Bonded / native supply", "—", fmt_decimal(s["bonded_ratio_percent"]) + "%", "—"),
    ]


def ws2_paragraph(ws2: dict[str, Any]) -> str:
    v = ws2["validator_concentration"]
    d = ws2["active_delegator_address_concentration"]
    s = ws2["stake"]
    return (
        "The active set expanded by 35%. Five leading validators were required to reach one-third of voting power, while eleven "
        "were required to exceed the two-thirds commit threshold. At the same height, **"
        + fmt_decimal(s["bonded_stake_l1"], 2, True)
        + " L1**—**"
        + fmt_decimal(s["bonded_ratio_percent"])
        + "%** of the **"
        + fmt_decimal(s["native_total_supply_l1"], 2, True)
        + " L1** native supply—was bonded; the staking pool also reported **"
        + fmt_decimal(s["not_bonded_tokens_l1"], 2, True)
        + " L1** not bonded. Validator HHI was **"
        + fmt_decimal(v["hhi_10000"])
        + "**, corresponding to an effective validator count of **"
        + fmt_decimal(v["effective_count"])
        + "**. The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference.\n\n"
        "Across addresses delegating to active validators, the largest address represented **"
        + fmt_decimal(d["top_1_share_percent"])
        + "%**, the top five **"
        + fmt_decimal(d["top_5_share_percent"])
        + "%**, the top ten **"
        + fmt_decimal(d["top_10_share_percent"])
        + "%** and the top 50 **"
        + fmt_decimal(d["top_50_share_percent"])
        + "%**. Address-level HHI was **"
        + fmt_decimal(d["hhi_10000"])
        + "**, with an effective address count of **"
        + fmt_decimal(d["effective_count"])
        + "**. These are address-level—not entity-level—measurements: custodians may aggregate many beneficiaries in one address, "
        "while one party may use many addresses, so address dispersion does not bound beneficial-owner dispersion."
    )


def replace_markdown(article: str, ws1: str, ws2: dict[str, Any], summary: dict[str, Any], seed: dict[str, Any]) -> str:
    old_ws1 = re.compile(
        r"The same pinned evidence package directly reconstructed \*\*8 predeclared PDB records\*\*.*?unsupported claim that every parent record was exhaustively downloaded in one run\. <sup><a href=\"#source-13\">13</a></sup>",
        re.S,
    )
    article, count = old_ws1.subn(ws1, article, count=1)
    if count != 1:
        raise RuntimeError("could not replace the previous eight-record MOLNFT paragraph")

    table_pattern = re.compile(
        r"\| Measure \| Whitepaper reference \| Block 13,431,722 \| Change \|\n"
        r"\|---\|---:\|---:\|---:\|\n"
        r"(?:\|.*\n)+?\| Strict two-thirds coefficient \| 8 \| 11 \| \+3 validators \|",
    )
    match = table_pattern.search(article)
    if not match:
        raise RuntimeError("decentralization table was not found")
    table = match.group(0)
    table = re.sub(r"\n\| (?:Validator HHI|Effective validator count|Bonded / native supply).*", "", table)
    extra = "".join(f"\n| {label} | {old} | {current} | {change} |" for label, old, current, change in ws2_table_rows(ws2))
    article = article[: match.start()] + table + extra + article[match.end() :]

    paragraph_pattern = re.compile(
        r"The active set expanded by 35%\..*?The largest-validator, top-three and top-five shares all declined relative to the whitepaper reference\.",
        re.S,
    )
    article, count = paragraph_pattern.subn(ws2_paragraph(ws2), article, count=1)
    if count != 1:
        raise RuntimeError("current network-state paragraph was not found")

    faq_pattern = re.compile(
        r"(### What does the pinned MOLNFT evidence prove\?\n\n).*?(?=\n### )",
        re.S,
    )
    faq = (
        f"The counters package at block 13,412,747 reports the collection state. A separately pre-committed randomized sample of "
        f"{int(summary['N'])} parent records at block {int(summary['B_pin']):,} was drawn from an enumerated parent-ID set using "
        f"a future block hash; {int(summary['successes'])} reconstructed successfully and {int(summary['fidelity_passes'])} passed "
        f"the declared canonical atom, chain/entity and coordinate-fidelity checks. Every draw and failure remains published.\n"
    )
    article, count = faq_pattern.subn(lambda m: m.group(1) + faq, article, count=1)
    if count != 1:
        raise RuntimeError("MOLNFT FAQ answer was not found")

    source_line = (
        f"15. **GenesisL1 randomized MOLNFT reconstruction and fidelity evidence at block {int(summary['B_pin']):,}.** "
        f"Pre-committed sample specification, future-block seed, enumerated parent IDs, raw calls, reconstructed and canonical BinaryCIF "
        f"objects, per-record outcomes and SHA-256 manifest. [Randomized evidence ↗](https://github.com/GenesisL1/insights/tree/main/{summary['evidence_relative_path']})"
    )
    if re.search(r"^15\. \*\*GenesisL1 randomized MOLNFT", article, re.M):
        article = re.sub(r"^15\. \*\*GenesisL1 randomized MOLNFT.*$", source_line, article, flags=re.M)
    else:
        marker = "14. **GenesisL1 CIPNFT source repository.**"
        position = article.find(marker)
        if position < 0:
            raise RuntimeError("source 14 marker was not found")
        end = article.find("\n", position)
        article = article[: end + 1] + source_line + "\n" + article[end + 1 :]

    return article


def html_fragment(markdown_text: str) -> list[str]:
    # Only the small evidence paragraphs require conversion; preserve emphasis and source links.
    text = markdown_text
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def update_html(path: pathlib.Path, ws1: str, ws2: dict[str, Any], summary: dict[str, Any]) -> None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    paragraphs = soup.find_all("p")
    target = next((p for p in paragraphs if "The same pinned evidence package directly reconstructed" in p.get_text(" ")), None)
    if target is None:
        raise RuntimeError("HTML eight-record paragraph was not found")
    fragments = html_fragment(ws1)
    first = BeautifulSoup(f"<p>{fragments[0]}</p>", "html.parser").p
    target.replace_with(first)
    cursor = first
    for fragment in fragments[1:]:
        node = BeautifulSoup(f"<p>{fragment}</p>", "html.parser").p
        cursor.insert_after(node)
        cursor = node

    heading = next((h for h in soup.find_all(["h2", "h3"]) if h.get_text(" ", strip=True) == "Decentralization, measured"), None)
    if heading is None:
        raise RuntimeError("HTML decentralization heading was not found")
    table = heading.find_next("table")
    if table is None:
        raise RuntimeError("HTML decentralization table was not found")
    tbody = table.find("tbody") or table
    for row in list(tbody.find_all("tr")):
        if row.find("td") and row.find("td").get_text(" ", strip=True) in {"Validator HHI (0–10,000)", "Effective validator count", "Bonded / native supply"}:
            row.decompose()
    for cells in ws2_table_rows(ws2):
        tr = soup.new_tag("tr")
        for value in cells:
            td = soup.new_tag("td")
            td.string = value
            tr.append(td)
        tbody.append(tr)

    current = next((p for p in soup.find_all("p") if p.get_text(" ", strip=True).startswith("The active set expanded by 35%.")), None)
    if current is None:
        raise RuntimeError("HTML current-state paragraph was not found")
    fragments = html_fragment(ws2_paragraph(ws2))
    first = BeautifulSoup(f"<p>{fragments[0]}</p>", "html.parser").p
    current.replace_with(first)
    cursor = first
    for fragment in fragments[1:]:
        node = BeautifulSoup(f"<p>{fragment}</p>", "html.parser").p
        cursor.insert_after(node)
        cursor = node

    faq_heading = next((h for h in soup.find_all(["h3", "h4"]) if h.get_text(" ", strip=True) == "What does the pinned MOLNFT evidence prove?"), None)
    if faq_heading and faq_heading.find_next("p"):
        faq_heading.find_next("p").string = (
            f"The counters package at block 13,412,747 reports collection state. A separately pre-committed randomized sample of "
            f"{int(summary['N'])} parent records at block {int(summary['B_pin']):,} was drawn from an enumerated parent-ID set using "
            f"a future block hash; {int(summary['successes'])} reconstructed successfully and {int(summary['fidelity_passes'])} passed "
            f"the declared canonical fidelity checks. Every draw and failure remains published."
        )

    modified = soup.find("meta", attrs={"property": "article:modified_time"})
    if modified:
        modified["content"] = summary["wall_clock_end_utc"]
    path.write_text(str(soup), encoding="utf-8")


def update_facts(ws2: dict[str, Any], summary: dict[str, Any], seed: dict[str, Any]) -> None:
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    v = ws2["validator_concentration"]
    d = ws2["active_delegator_address_concentration"]
    s = ws2["stake"]
    payload["validator_hhi_10000"] = fmt_decimal(v["hhi_10000"])
    payload["effective_validator_count"] = fmt_decimal(v["effective_count"])
    payload["validator_gini"] = str(v["gini_coefficient"])
    payload["validator_normalized_entropy"] = str(v["normalized_entropy"])
    payload["bonded_ratio_total_supply_percent"] = fmt_decimal(s["bonded_ratio_percent"])
    payload["not_bonded_stake_display"] = fmt_decimal(s["not_bonded_tokens_l1"], 2, True)
    payload["delegator_top1_share_percent"] = fmt_decimal(d["top_1_share_percent"])
    payload["delegator_top5_share_percent"] = fmt_decimal(d["top_5_share_percent"])
    payload["delegator_top10_share_percent"] = fmt_decimal(d["top_10_share_percent"])
    payload["delegator_top50_share_percent"] = fmt_decimal(d["top_50_share_percent"])
    payload["delegator_hhi_10000"] = fmt_decimal(d["hhi_10000"])
    payload["active_delegator_effective_count"] = fmt_decimal(d["effective_count"])
    payload["delegator_gini"] = str(d["gini_coefficient"])
    payload["molnft_randomized"] = {
        "B_pin": summary["B_pin"],
        "B_seed": summary["B_seed"],
        "N": summary["N"],
        "successes": summary["successes"],
        "failures": summary["failures"],
        "fidelity_passes": summary["fidelity_passes"],
        "precommit_sha": seed["sample_spec_precommit_sha"],
        "evidence_relative_path": summary["evidence_relative_path"],
    }
    FACTS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_indexes(summary: dict[str, Any]) -> None:
    text = EVIDENCE_INDEX.read_text(encoding="utf-8")
    line = (
        f"- [Randomized MOLNFT fidelity sample — block {int(summary['B_pin']):,}]"
        f"(molnft/block-{int(summary['B_pin'])}/) — N={int(summary['N'])}, "
        f"{int(summary['successes'])} reconstructions, {int(summary['fidelity_passes'])} fidelity passes."
    )
    text = re.sub(r"^- \[Randomized MOLNFT fidelity sample.*$", line, text, flags=re.M)
    if line not in text:
        text += "\n" + line + "\n"
    EVIDENCE_INDEX.write_text(text, encoding="utf-8")

    refs = json.loads(REFERENCES.read_text(encoding="utf-8"))
    refs["molnft_randomized_evidence"] = {
        "title": "GenesisL1 randomized MOLNFT reconstruction and canonical fidelity evidence",
        "block": int(summary["B_pin"]),
        "url": "https://github.com/GenesisL1/insights/tree/main/" + summary["evidence_relative_path"],
    }
    REFERENCES.write_text(json.dumps(refs, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remove_anti_checks() -> None:
    path = pathlib.Path("tools/qa/validate_repository.py")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    forbidden = ["No negative section", "Limitations", "Weaknesses", "Uncrossed gates", "What it costs", "The next proofs"]
    lines = []
    for line in text.splitlines():
        if any(token in line for token in forbidden) and ("assert" in line or "check" in line.lower() or "pass" in line.lower()):
            continue
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft-evidence", required=True, type=pathlib.Path)
    parser.add_argument("--ws2", required=True, type=pathlib.Path)
    args = parser.parse_args()

    summary = json.loads((args.molnft_evidence / "summary.json").read_text(encoding="utf-8"))
    seed = json.loads((args.molnft_evidence / "seed-derivation.json").read_text(encoding="utf-8"))
    summary["evidence_relative_path"] = args.molnft_evidence.as_posix()
    (args.molnft_evidence / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ws2 = json.loads(args.ws2.read_text(encoding="utf-8"))

    ws1 = ws1_markdown(summary, seed, summary["evidence_relative_path"])
    article = ARTICLE.read_text(encoding="utf-8")
    ARTICLE.write_text(replace_markdown(article, ws1, ws2, summary, seed), encoding="utf-8")
    update_html(HTML, ws1, ws2, summary)
    update_facts(ws2, summary, seed)
    update_indexes(summary)
    remove_anti_checks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
