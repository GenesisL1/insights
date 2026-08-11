#!/usr/bin/env python3
"""Apply the same-ID RPCA requery and revision-aware MOLNFT result to Article 02."""
from __future__ import annotations

import argparse
import csv
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
ROOT_RPC = "https://rpca.genesisl1.org"
API_PATH = "https://rpca.genesisl1.org/api"


def read_results(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def structure_label(record: dict[str, Any]) -> str:
    structure = record.get("structure") or {}
    compound = str(structure.get("compound") or "structure").strip()
    return f"PDB **{record['pdb_id']}** / NFT **{record['token_id']}** ({compound})"


def revision_record(summary: dict[str, Any]) -> dict[str, Any]:
    records = summary.get("revision_aware_records") or []
    if len(records) != 1:
        raise RuntimeError(f"expected exactly one revision-aware record, found {len(records)}")
    record = records[0]
    if (int(record["token_id"]), record["pdb_id"]) != (124713, "5KCS"):
        raise RuntimeError("revision-aware record is not 5KCS / NFT 124713")
    return record


def change_text(record: dict[str, Any]) -> str:
    parts = []
    for item in record.get("atom_name_changes") or []:
        parts.append(
            f"{item.get('from_label_atom_id')}→{item.get('to_label_atom_id')} for "
            f"{int(item.get('count') or 0)} atoms"
        )
    return "; and ".join(parts)


def publication_paragraphs(summary: dict[str, Any], report: dict[str, Any]) -> tuple[str, str]:
    records = report.get("record_results") or []
    if not records:
        raise RuntimeError("targeted-requery.json contains no record results")
    revision = revision_record(summary)
    record_text = "; and ".join(structure_label(record) for record in records)
    fidelity = int(summary["fidelity_passes"])
    n = int(summary["N"])
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
        f"The root `{ROOT_RPC}` endpoint reported EVM chain ID 29; its default calls reproduced the out-of-gas responses, while "
        f"explicit-gas calls at the same pinned block returned both complete payloads. The exact `{API_PATH}` path returned HTTP "
        f"404 and is not a JSON-RPC route. Both recovered structures pass. For PDB **5KCS** / NFT **124713**, the current RCSB file documents a later **{revision['rcsb_atom_name_revision_date']}** revision "
        f"to `_atom_site.label_atom_id` and `_atom_site.auth_atom_id`: **{int(revision['atom_name_change_count'])} labels** in "
        f"component **6MZ** changed ({change_text(revision)}). `_atom_site.id`, every non-name identity field, all "
        f"**148,945 atoms**, and every Cartesian coordinate remained aligned; maximum deviation was **0 Å**. The comparator "
        f"therefore treats this documented nomenclature remediation as identity-preserving rather than as a molecular mismatch. "
        f"The finalized audit records **{fidelity} of {n} canonical structural-fidelity passes**. "
        f"<sup><a href=\"#source-15\">15</a></sup>"
    )
    paragraph2 = (
        f"A fidelity pass required equal atom counts, chain and entity sets, atom-identity agreement, and a maximum paired "
        f"coordinate deviation no greater than the precommitted **{float(summary['coordinate_tolerance_angstrom']):.6f} Å** "
        f"tolerance. All **{fidelity}** comparisons passed. For 5KCS, the documented later RCSB atom-name revision was reconciled "
        f"only because `_atom_site.id` remained unique and unchanged, every non-name identity field agreed, and all 148,945 "
        f"coordinates paired at **0 Å** deviation. No PDB-specific alias table was used. Exact normalized coordinate hashes remain "
        f"available per record as an auxiliary reproducibility check, not as a fidelity criterion. Serialized BinaryCIF equality is "
        f"neither calculated nor used as a pass condition; reconstructed and canonical SHA-256 values are retained independently "
        f"only to identify the preserved objects. The future-block seed, complete parent-ID population, immutable draw, original "
        f"provider errors, targeted same-ID calls, reconstructed and canonical objects, RCSB revision evidence, environment "
        f"fingerprint and SHA-256 manifest are preserved in the evidence package."
    )
    return paragraph1, paragraph2


def faq_text(summary: dict[str, Any]) -> str:
    revision = revision_record(summary)
    return (
        f"The counters package at block 13,412,747 reports collection state. A separately precommitted randomized sample of "
        f"{int(summary['N'])} parent records at block {int(summary['B_pin']):,} used a future block hash and direct NFT-ID calls. "
        f"Two default provider calls initially ran out of gas; only those same predetermined IDs were re-queried through the RPCA "
        f"root endpoint with an explicit call-gas allowance, with no replacement draw. Both payloads were recovered and all "
        f"{int(summary['fidelity_passes'])} records passed. For 5KCS, four 6MZ atom-name labels changed in a documented RCSB "
        f"revision dated {revision['rcsb_atom_name_revision_date']}; stable atom IDs, all other identity fields and all coordinates "
        f"were unchanged, so this is recorded as nomenclature remediation rather than structural loss."
    )


def replace_article(article: str, paragraph1: str, paragraph2: str, summary: dict[str, Any]) -> str:
    pattern = re.compile(
        r"A (?:later )?randomized evidence package fixed \*\*N = 100\*\*.*?preserved in the evidence package\.",
        re.S,
    )
    article, count = pattern.subn(paragraph1 + "\n\n" + paragraph2, article, count=1)
    if count != 1:
        raise RuntimeError("could not replace the current MOLNFT audit paragraphs")
    faq_pattern = re.compile(r"(### What does the pinned MOLNFT evidence prove\?\n\n).*?(?=\n### )", re.S)
    article, count = faq_pattern.subn(lambda match: match.group(1) + faq_text(summary) + "\n", article, count=1)
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
            if paragraph.get_text(" ", strip=True).startswith(("A randomized evidence package fixed", "A later randomized evidence package fixed"))
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
        faq_heading.find_next_sibling("p").string = faq_text(summary)
    modified = soup.find("meta", attrs={"property": "article:modified_time"})
    if modified is not None:
        modified["content"] = report["performed_at_utc"]
    path.write_text(str(soup), encoding="utf-8")


def update_facts(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["molnft_randomized"] = {
        "B_pin": summary["B_pin"],
        "B_seed": summary["B_seed"],
        "N": summary["N"],
        "successes": summary["successes"],
        "failures": summary["failures"],
        "failures_by_reason": summary["failures_by_reason"],
        "fidelity_passes": summary["fidelity_passes"],
        "revision_aware_records": summary["revision_aware_records"],
        "precommit_sha": summary["sample_spec_precommit_sha"],
        "evidence_relative_path": summary["evidence_relative_path"],
        "initial_failures": report["initial_failures"],
        "initial_failure_reason": "RPC_OUT_OF_GAS",
        "successful_same_id_payload_requeries": report["successful_requeries"],
        "targeted_requery_token_ids": report["queried_token_ids"],
        "targeted_requery_endpoint": ROOT_RPC,
        "requested_api_path_http_status": 404,
        "replacement_draws": report["replacement_draws"],
        "final_failure_records": [],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_latest(path: pathlib.Path, summary: dict[str, Any], report: dict[str, Any]) -> None:
    previous = json.loads(path.read_text(encoding="utf-8"))
    payload = {
        "schema": previous.get("schema", "org.genesisl1.molnft_evidence_pointer.v1"),
        "evidence_block": summary["B_pin"],
        "path": f"block-{summary['B_pin']}",
        "sample_size": summary["N"],
        "fidelity_passes": summary["fidelity_passes"],
        "failures": summary["failures"],
        "selection": previous.get("selection", "future-block-seeded direct NFT-ID sample without replacement"),
        "off_chain_token_index_used": False,
        "sample_spec_precommit_sha": summary["sample_spec_precommit_sha"],
        "failures_by_reason": summary["failures_by_reason"],
        "initial_failures": report["initial_failures"],
        "successful_same_id_payload_requeries": report["successful_requeries"],
        "targeted_requery_token_ids": report["queried_token_ids"],
        "replacement_draws": report["replacement_draws"],
        "final_failure_records": [],
        "revision_aware_records": summary["revision_aware_records"],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_indexes(summary: dict[str, Any]) -> None:
    revision = revision_record(summary)
    evidence_index = EVIDENCE_INDEX.read_text(encoding="utf-8")
    evidence_index = re.sub(
        r"- \[Randomized MOLNFT fidelity sample — block 13,436,937\].*$",
        f"- [Randomized MOLNFT fidelity sample — block 13,436,937](molnft/block-13436937/) — "
        f"N={summary['N']}; {summary['fidelity_passes']} structural-fidelity passes; only the two initial provider failures "
        f"were re-queried by the same NFT IDs; 5KCS used documented RCSB atom-name revision reconciliation; no replacement draw.",
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

At `{ROOT_RPC}`, default `getCombinedData` calls reproduced the provider-level out-of-gas errors. Explicit-gas calls for those same IDs at the same pinned block returned both payloads. The exact `{API_PATH}` path returned HTTP 404 and is not a JSON-RPC route. No successful row was requeried and no replacement ID was drawn.

Both recovered structures pass. **5KCS is not a structural mismatch.** Its current RCSB comparator documents a `{revision['rcsb_atom_name_revision_date']}` revision to `_atom_site.label_atom_id` and `_atom_site.auth_atom_id`. Four component-6MZ labels changed (`O1P→OP2` twice and `O2P→OP1` twice), while unique `_atom_site.id` values, every non-name identity field, all 148,945 atoms and all coordinates remained aligned at a maximum deviation of `0 Å`.

The finalized audit reports:

- **{summary['fidelity_passes']} of {summary['N']} canonical structural-fidelity passes**;
- **zero final failures**, with the 5KCS atom-name revision fully documented and all 148,945 coordinates aligned at `0 Å`;
- per-record normalized coordinate hashes retained as auxiliary reproducibility evidence;
- complete raw requests and responses for the original calls and targeted same-ID requery;
- reconstructed and current RCSB BinaryCIF objects, per-record outcomes, revision evidence, environment versions, manifest, and SHA-256 checksums.

The revision-aware path is accepted only when the current RCSB audit history explicitly lists both atom-name fields, stable atom-site IDs are unique and unchanged, every non-name identity field agrees and paired coordinates remain within the original `1e-6 Å` tolerance. It uses no PDB-specific alias table. Serialized-object equality is not calculated; each object's SHA-256 is retained independently as an integrity identifier only.

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
    ROOT_README.write_text(readme, encoding="utf-8")

    notes = DEPLOY_NOTES.read_text(encoding="utf-8")
    notes = re.sub(
        r"- MOLNFT:.*$",
        f"- MOLNFT: {summary['fidelity_passes']} of {summary['N']} canonical structural-fidelity passes after targeted "
        f"same-ID RPCA recovery of 5KCS/NFT 124713 and 6QFB/NFT 162649; 5KCS reconciled through documented RCSB "
        f"atom-name revision metadata with zero coordinate deviation; no replacement draw; "
        f"per-record coordinate hashes retained as auxiliary evidence; no off-chain token index",
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
    results = read_results(evidence / "results.csv")
    failures = [row for row in results if row["outcome"] != "SUCCESS"]
    if failures:
        raise RuntimeError(f"final revision-aware evidence still has {len(failures)} failures")
    summary.setdefault("evidence_relative_path", evidence.as_posix())

    paragraph1, paragraph2 = publication_paragraphs(summary, report)
    ARTICLE.write_text(
        replace_article(ARTICLE.read_text(encoding="utf-8"), paragraph1, paragraph2, summary),
        encoding="utf-8",
    )
    update_html(HTML, paragraph1, paragraph2, summary, report)
    update_facts(FACTS, summary, report)
    update_latest(LATEST, summary, report)
    update_indexes(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
