#!/usr/bin/env python3
"""Apply the direct-NFT-ID WS-1 result and WS-2 metrics to Article 02."""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from decimal import Decimal
from typing import Any

BASE_PATH = pathlib.Path(__file__).with_name("apply_ws1_ws2_article.py")
SPEC = importlib.util.spec_from_file_location("genesisl1_ws_article_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def failure_phrase(summary: dict[str, Any]) -> str:
    failures = int(summary["failures"])
    if failures == 0:
        return "no recorded failures"
    details = summary.get("failures_by_reason") or {}
    rendered = ", ".join(f"{value} {key}" for key, value in sorted(details.items()))
    return f"{failures} published failures ({rendered})"


def ws1_markdown(summary: dict[str, Any], seed: dict[str, Any]) -> str:
    n = int(summary["N"])
    successes = int(summary["successes"])
    fidelity = int(summary["fidelity_passes"])
    identical = int(summary.get("byte_identical_records", 0))
    enumerated = int(summary["enumerated_parent_count"])
    tolerance = Decimal(str(summary["coordinate_tolerance_angstrom"]))
    enum = summary["enumeration_method"]
    return (
        f"A later randomized evidence package fixed **N = {n}** in an isolated repository commit before GenesisL1 seed block "
        f"**{int(seed['B_seed']):,}** existed. The resulting block hash was transformed by the declared Keccak-256 rule, and "
        f"the draw was made without replacement over the PDB v2 contract's pinned parent NFT-ID range "
        f"**{int(enum['parent_id_start']):,}–{int(enum['parent_id_end']):,}** (**{enumerated:,} IDs**), defined directly by "
        f"`nextNFTId()` at block **{int(summary['B_pin']):,}**. Each selected PDB identifier was read from "
        f"`getMetadata(tokenId)` and its payload from `getCombinedData(tokenId)`; **no GLAST or other off-chain token index was used**. "
        f"The pipeline reconstructed **{successes} of {n}** selected records and published {failure_phrase(summary)} with raw RPC "
        f"responses for every draw. <sup><a href=\"#source-15\">15</a></sup>\n\n"
        f"Canonical fidelity was tested record by record against RCSB BinaryCIF objects after deterministic atom-order normalization. "
        f"**{fidelity} records passed** the declared atom-count, chain/entity-ID, atom-identity, coordinate-hash and coordinate-agreement "
        f"checks at a maximum permitted deviation of **{tolerance:.6f} Å**; **{identical}** were also byte-identical to the retrieved "
        f"canonical BinaryCIF. The future-block seed derivation, complete numeric parent-ID population, draw, success/failure table, "
        f"reconstructed and canonical objects, environment fingerprint and SHA-256 manifest are preserved in the evidence package."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft-evidence", required=True, type=pathlib.Path)
    parser.add_argument("--ws2", required=True, type=pathlib.Path)
    args = parser.parse_args()

    summary_path = args.molnft_evidence / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    seed = json.loads((args.molnft_evidence / "seed-derivation.json").read_text(encoding="utf-8"))
    summary["evidence_relative_path"] = args.molnft_evidence.as_posix()
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ws2 = json.loads(args.ws2.read_text(encoding="utf-8"))

    ws1 = ws1_markdown(summary, seed)
    article = base.ARTICLE.read_text(encoding="utf-8")
    base.ARTICLE.write_text(base.replace_markdown(article, ws1, ws2, summary, seed), encoding="utf-8")
    base.update_html(base.HTML, ws1, ws2, summary)
    base.update_facts(ws2, summary, seed)
    base.update_indexes(summary)
    base.remove_anti_checks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
