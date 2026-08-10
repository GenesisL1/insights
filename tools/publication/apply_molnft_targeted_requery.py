#!/usr/bin/env python3
"""Apply the same-ID RPCA requery result to Article 02 and evidence indexes."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from typing import Any

from bs4 import BeautifulSoup

ARTICLE = pathlib.Path("content/article-02-next-verifiable-renaissance/article.md")
HTML = pathlib.Path("site/insights/genesisl1-decentralization-scientific-renaissance.html")
FACTS = pathlib.Path("content/article-02-next-verifiable-renaissance/network-state.json")
LATEST = pathlib.Path("evidence/article-02/molnft/LATEST.json")
EVIDENCE_INDEX = pathlib.Path("evidence/article-02/README.md")
ROOT_README = pathlib.Path("README.md")
DEPLOY_NOTES = pathlib.Path("deployment/WS1_WS2_DEPLOYMENT_NOTES.md")


def structure_label(record: dict[str, Any]) -> str:
    structure = record.get("structure") or {}
    compound = str(structure.get("compound") or "structure").strip()
    return f"PDB **{record['pdb_id']}** / NFT **{record['token_id']}** ({compound})"


def publication_paragraphs(summary: dict[str, Any], report: dict[str, Any]) -> tuple[str, str]:
    records = report.get("record_results") or []
    if not records:
        raise RuntimeError("targeted-requery.json contains no record results")
    record_text = "; and ".join(structure_label(record) for record in records)
    fidelity = int(summary["fidelity_passes"])
    n = int(summary["N"])
    exact = int(summary["coordinate_hash_matches"])
    enum = summary["enumeration_method"]
    paragraph1 = (
        f"A randomized evidence package fixed **N = {n}** in an isolated repository commit before GenesisL1 seed block "
        f"**{int(summary['B_seed']):,}** existed. The resulting block hash selected IDs without replacement from the PDB v2 "
        f"contract's pinned parent NFT-ID range **{int(enum['parent_id_start']):,}–{int(enum['parent_id_end']):,}** "
        f"(**{int(summary['enumerated_parent_count']):,} IDs**), defined directly by `nextNFTId()` at block "
        f"**{int(summary['B_pin']):,}**. Each PDB identifier came from `getMetadata(tokenId)` and each payload from "
        f"`getCombinedData(tokenId)`; **no GLAST or other off-chain token index was used**. The initial retrieval completed 98 "
        f"comparisons and produced provider-level out-of-gas responses for exactly two predetermined draws: {record_text}. "
        f"Only those same two NFT IDs were queried again—no successful row was queried and no replacement ID was drawn. "
        f"The root `https://rpca.genesisl1.org` endpoint reported EVM chain ID 29; its default calls reproduced the out-of-gas "
        f"responses, while explicit-gas calls at the same pinned block returned both complete payloads. The exact "
        f"`https://rpca.genesisl1.org/api` path returned HTTP 404 and is not a JSON-RPC route. The finalized audit therefore "
        f"records **{fidelity} of {n} canonical structural-fidelity passes**. <sup><a href=\"#source-15\">15</a></sup>"
    )
    paragraph2 = (
        f"For every record, fidelity required equal atom counts, chain and entity sets, canonical atom identities, and a maximum "
        f"paired coordinate deviation no greater than the precommitted **{float(summary['coordinate_tolerance_angstrom']):.6f} Å** "
        f"tolerance. All **{fidelity}** comparisons passed those conditions. Exact normalized coordinate hashes additionally matched "
        f"for **{exact} of {fidelity}** records. Serialized BinaryCIF equality is neither calculated nor used as a pass condition; "
        f"the reconstructed and canonical SHA-256 values are retained independently only to identify the preserved objects. The "
        f"future-block seed, complete parent-ID population, immutable draw, original provider errors, targeted same-ID calls, "
        f"reconstructed and canonical objects, environment fingerprint and SHA-256 manifest are preserved in the evidence package."
    )
    return paragraph1, paragraph2


def replace_article(article: str, paragraph1: str, paragraph2: str, summary: dict[str, Any]) -> str:
    pattern = re.compile(
        r"A later randomized evidence package fixed \*\*N = 100\*\*.*?preserved in the evidence package\.",
        re.S,
    )
    replacement = paragraph1 + "\n\n" + paragraph2
    article, count = pattern.subn(replacement, article, count=1)
    if count != 1:
        raise RuntimeError("could not replace the current MOLNFT audit paragraphs")

    faq_pattern = re.compile(
        r"(### What does the pinned MOLNFT evidence prove\?\n\n).*?(?=\n### )",
        re.S,
    )
    faq = (
        f"The counters package at block 13,412,747 reports collection state. A separately precommitted randomized sample of "
        f"{int(summary['N'])} parent records at block {int(summary['B_pin']):,} used a future block hash and direct NFT-ID calls. "
        f"Two default provider calls initially ran out of gas; the same two predetermined IDs were re-queried without replacement "
        f"through the RPCA root endpoint with an explicit call-gas allowance. All {int(summary['fidelity_passes'])} records passed "
        f"the declared atom, chain/entity, atom-identity and coordinate-tolerance checks, and the original errors plus requery calls "
        f"remain published.\n"
    )
    article, count = faq_pattern.subn(lambda match: match.group(1) + faq, article, count=1)
    if count != 1:
        raise RuntimeError("could not update the MOLNFT FAQ")
    return article


def markdown_to_html_paragraph(text: str) -> Any:
    converted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    converted = re.sub(r"`([^`]+)`", r"<code>\1</code>", converted)
    return BeautifulSoup(f"<p>{converted}</p>", "html.parser").p


def update_html(path: pathlib.Path, paragraph1: str, paragraph2: str, summary: dict[str, Any], report: dict[str, Any]) -> None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    target = next(
        (
            paragraph
            for paragraph in soup.find_all("p")
            if paragraph.get_text(" ", strip=True).startswith("A later randomized evidence package fixed")
        ),
        None,
    )
    if target is None:
        raise RuntimeError("production HTML MOLNFT paragraph was not found")
    following = target.find_next_sibling("p")
    target.replace_with(markdown_to_html_paragraph(paragraph1))
    if following is None:
        raise RuntimeError("production HTML MOLNFT fidelity paragraph was not found")
    following.replace_with(markdown_to_html_paragraph(paragraph2))

    faq_heading = next(
        (
            heading
            for heading in soup.find_all(["h3", "h4"])
            if heading.get_text(" ", strip=True) == "What does the pinned MOLNFT evidence prove?"
        ),
        None,
    )
    if faq_heading is not None and faq_heading.find_next_sibling("p") is not None:
        faq_heading.find_next_sibling("p").string = (
            f"The counters package at block 13,412,747 reports collection state. A separately precommitted randomized sample of "
            f"{int(summary['N'])} parent records at block {int(summary['B_pin']):,} used a future block hash and direct NFT-ID calls. "
            f"Two default provider calls initially ran out of gas; the same predetermined IDs were re-queried without replacement "
            f"through the RPCA root endpoint with an explicit call-gas allowance. All {int(summary['fidelity_passes'])} records passed "
            f"the declared structural checks, and the original errors plus requery calls remain published."
        )

    modified = soup.find("meta", attrs={"property": "article:modified_time"})
    if modified is not None:
        modified["content"] = report["performed_at_utc"]
    path.write_text(str(soup), encoding="utf-8")


def update_facts(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    current = dict(payload.get("molnft_randomized") or {})
    current.pop("byte_identical_records", None)
    current.update(
        {
            "B_pin": summary["B_pin"],
            "B_seed": summary["B_seed"],
            "N": summary["N"],
            "successes": summary["successes"],
            "failures": summary["failures"],
            "fidelity_passes": summary["fidelity_passes"],
            "coordinate_hash_matches": summary["coordinate_hash_matches"],
            "precommit_sha": summary["sample_spec_precommit_sha"],
            "evidence_relative_path": summary["evidence_relative_path"],
            "initial_failures": report["initial_failures"],
            "initial_failure_reason": "RPC_OUT_OF_GAS",
            "targeted_requery_token_ids": report["queried_token_ids"],
            "targeted_requery_endpoint": "https://rpca.genesisl1.org",
            "requested_api_path_http_status": 404,
            "replacement_draws": report["replacement_draws"],
        }
    )
    payload["molnft_randomized"] = current
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_latest(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("failure_reason", None)
    payload.update(
        {
            "sample_size": summary["N"],
            "fidelity_passes": summary["fidelity_passes"],
            "failures": summary["failures"],
            "coordinate_hash_matches": summary["coordinate_hash_matches"],
            "initial_failures": report["initial_failures"],
            "targeted_requery_token_ids": report["queried_token_ids"],
            "replacement_draws": report["replacement_draws"],
        }
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_indexes(summary: dict[str, Any], report: dict[str, Any]) -> None:
    evidence_index = EVIDENCE_INDEX.read_text(encoding="utf-8")
    evidence_index = re.sub(
        r"- \[Randomized MOLNFT fidelity sample — block 13,436,937\].*$",
        f"- [Randomized MOLNFT fidelity sample — block 13,436,937](molnft/block-13436937/) — "
        f"N={summary['N']}, {summary['fidelity_passes']} structural-fidelity passes; the two original provider-level failures "
        f"were re-queried by the same NFT IDs with no replacement draw.",
        evidence_index,
        flags=re.M,
    )
    EVIDENCE_INDEX.write_text(evidence_index, encoding="utf-8")

    readme = ROOT_README.read_text(encoding="utf-8")
    section = f"""### MOLNFT direct-ID audit — block 13,436,937

The MOLNFT sample specification was committed before future seed block 13,436,979 existed. Its block hash selected 100 NFT IDs without replacement from the contract-defined range `1..nextNFTId(B_pin)-1`, comprising 229,271 parent IDs. No GLAST or other off-chain token index was used.

The initial retrieval completed 98 comparisons. Only the two failed predetermined rows were queried again:

- **5KCS / NFT 124713** — Cryo-EM structure of the *Escherichia coli* 70S ribosome in complex with Evernimycin, mRNA, TetM and P-site tRNA;
- **6QFB / NFT 162649** — human ATP citrate lyase holoenzyme in complex with citrate, coenzyme A and Mg·ADP.

At `https://rpca.genesisl1.org`, default `getCombinedData` calls reproduced the provider-level out-of-gas errors. Explicit-gas calls for those same IDs at the same pinned block returned both payloads. The exact `https://rpca.genesisl1.org/api` path returned HTTP 404 and is not a JSON-RPC route. No successful row was requeried and no replacement ID was drawn.

The finalized audit reports:

- **{summary['fidelity_passes']} of {summary['N']} canonical structural-fidelity passes**;
- **{summary['coordinate_hash_matches']} of {summary['fidelity_passes']} exact normalized coordinate-hash matches**;
- complete raw requests and responses for the original calls and targeted same-ID requery;
- reconstructed and current RCSB BinaryCIF objects, per-record outcomes, environment versions, manifest, and SHA-256 checksums.

A fidelity pass requires equal atom counts, chain/entity sets, canonical atom identities, and paired Cartesian coordinates within the precommitted `1e-6 Å` tolerance. Serialized-object equality is not calculated. Each object's SHA-256 is retained independently as an integrity identifier only.

"""
    readme, count = re.subn(
        r"### MOLNFT direct-ID audit — block 13,436,937\n.*?(?=## Repository boundaries)",
        section,
        readme,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("could not replace the root README MOLNFT section")
    readme = readme.replace("finalize_molnft_direct_evidence.py", "finalize_molnft_structural_evidence.py")
    readme = readme.replace("--verify-byte-for-byte", "--verify-deterministic")
    ROOT_README.write_text(readme, encoding="utf-8")

    notes = DEPLOY_NOTES.read_text(encoding="utf-8")
    notes = re.sub(
        r"- MOLNFT:.*$",
        f"- MOLNFT: {summary['fidelity_passes']} of {summary['N']} canonical structural-fidelity passes after a targeted "
        f"same-ID RPCA requery of 5KCS/NFT 124713 and 6QFB/NFT 162649; no replacement draw; "
        f"{summary['coordinate_hash_matches']} exact normalized coordinate-hash matches; no off-chain token index",
        notes,
        flags=re.M,
    )
    DEPLOY_NOTES.write_text(notes, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft-evidence", required=True, type=pathlib.Path)
    args = parser.parse_args()
    evidence = args.molnft_evidence
    summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
    report = json.loads((evidence / "targeted-requery.json").read_text(encoding="utf-8"))
    summary.setdefault("evidence_relative_path", evidence.as_posix())

    paragraph1, paragraph2 = publication_paragraphs(summary, report)
    ARTICLE.write_text(
        replace_article(ARTICLE.read_text(encoding="utf-8"), paragraph1, paragraph2, summary),
        encoding="utf-8",
    )
    update_html(HTML, paragraph1, paragraph2, summary, report)
    update_facts(FACTS, summary, report)
    update_latest(LATEST, summary, report)
    update_indexes(summary, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
