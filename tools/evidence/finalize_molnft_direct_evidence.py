#!/usr/bin/env python3
"""Finalize the direct-ID MOLNFT sample from preserved evidence.

The capture stage preserves every selected token's raw RPC response, reconstructed
BinaryCIF and retrieved RCSB BinaryCIF. This deterministic stage performs the
publication-facing comparison without any network access:

* atom count, chain/entity IDs and atom identities must agree;
* maximum paired coordinate deviation must not exceed the precommitted tolerance;
* exact normalized coordinate hashes are recorded for both objects and reported
  separately, but are not substituted for the declared tolerance test;
* capture-layer failures are recovered from the preserved raw RPC response rather
  than being relabeled as generic missing files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import struct
import sys
from collections import Counter
from typing import Any

BASE_PATH = pathlib.Path(__file__).with_name("capture_molnft_randomized_sample.py")
SPEC = importlib.util.spec_from_file_location("genesisl1_ws1_finalize_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def normalized_coordinate_hash(rows: list[tuple[tuple[str, ...], tuple[float, float, float]]]) -> str:
    """Hash the coordinate array in canonical atom-key order.

    IEEE-754 signed zero is normalized because +0.0 and -0.0 are geometrically
    identical yet have different byte encodings. The hash intentionally excludes
    metadata and atom-key text; atom-key equality is tested independently.
    """
    stream = bytearray()
    for _, coordinate in rows:
        for value in coordinate:
            normalized = 0.0 if value == 0.0 else float(value)
            stream.extend(struct.pack(">d", normalized))
    return hashlib.sha256(bytes(stream)).hexdigest()


def compare_bcif(reconstructed: pathlib.Path, canonical: pathlib.Path, tolerance: float) -> dict[str, Any]:
    rec = base.atom_table(reconstructed)
    can = base.atom_table(canonical)
    rec_keys = [row[0] for row in rec["rows"]]
    can_keys = [row[0] for row in can["rows"]]
    max_deviation: float | None = None
    coordinate_agreement = False
    if rec_keys == can_keys:
        deviations: list[float] = []
        for (_, left), (_, right) in zip(rec["rows"], can["rows"]):
            deviations.append(math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right))))
        max_deviation = max(deviations, default=0.0)
        coordinate_agreement = max_deviation <= tolerance

    rec_coordinate_hash = normalized_coordinate_hash(rec["rows"])
    can_coordinate_hash = normalized_coordinate_hash(can["rows"])
    atom_count_equal = rec["count"] == can["count"]
    chain_ids_equal = rec["chains"] == can["chains"]
    entity_ids_equal = rec["entities"] == can["entities"]
    atom_keys_equal = rec_keys == can_keys
    fidelity_pass = all(
        [
            atom_count_equal,
            chain_ids_equal,
            entity_ids_equal,
            atom_keys_equal,
            coordinate_agreement,
        ]
    )
    return {
        "reconstructed_atom_count": rec["count"],
        "canonical_atom_count": can["count"],
        "atom_count_equal": atom_count_equal,
        "reconstructed_chain_ids": rec["chains"],
        "canonical_chain_ids": can["chains"],
        "chain_ids_equal": chain_ids_equal,
        "reconstructed_entity_ids": rec["entities"],
        "canonical_entity_ids": can["entities"],
        "entity_ids_equal": entity_ids_equal,
        "atom_keys_equal": atom_keys_equal,
        "reconstructed_coordinate_sha256": rec_coordinate_hash,
        "canonical_coordinate_sha256": can_coordinate_hash,
        "coordinate_hash_equal": rec_coordinate_hash == can_coordinate_hash,
        "max_coordinate_deviation_angstrom": max_deviation,
        "coordinate_tolerance_angstrom": tolerance,
        "coordinate_agreement": coordinate_agreement,
        "fidelity_pass": fidelity_pass,
    }


def read_draw(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def classify_preserved_failure(directory: pathlib.Path, token_id: int, pdb_id: str) -> tuple[str, str]:
    raw_dir = directory / "raw" / f"{pdb_id}-token-{token_id}"
    if not raw_dir.exists():
        raw_dir = directory / "raw" / f"token-{token_id}"
    combined = raw_dir / "eth-call-combined.response.json"
    if combined.is_file():
        try:
            payload = json.loads(combined.read_text(encoding="utf-8"))
            error = payload.get("error") if isinstance(payload, dict) else None
            if error:
                message = str(error.get("message") if isinstance(error, dict) else error)
                lowered = message.lower()
                if "out of gas" in lowered:
                    return "RPC_OUT_OF_GAS", message
                if "timeout" in lowered or "timed out" in lowered:
                    return "RPC_TIMEOUT", message
                return "RPC_ERROR", message
            if payload.get("result") in (None, "", "0x"):
                return "CHUNK_MISSING", "getCombinedData returned no payload"
        except Exception as exc:  # noqa: BLE001
            return "RPC_ERROR", f"could not parse preserved RPC response: {type(exc).__name__}: {exc}"

    reconstructed = directory / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif"
    canonical = directory / "canonical" / f"{pdb_id}.bcif"
    if reconstructed.is_file() and not canonical.is_file():
        return "CANONICAL_UNAVAILABLE", "canonical RCSB BinaryCIF was unavailable during the pinned capture"
    if not reconstructed.is_file():
        return "PARSE_FAIL", "reconstructed BinaryCIF is absent despite the preserved draw"
    return "MISSING_FILE", "required comparison object is absent"


def write_report(directory: pathlib.Path, summary: dict[str, Any]) -> None:
    failure_lines = summary.get("failures_by_reason") or {}
    failures = ", ".join(f"{value} {key}" for key, value in sorted(failure_lines.items())) or "none"
    enum = summary["enumeration_method"]
    text = f"""# MOLNFT direct NFT-ID randomized fidelity evidence

**Pinned GenesisL1 block:** `{summary['B_pin']}`  
**Pinned block hash:** `{summary['B_pin_block_hash']}`  
**Future seed block:** `{summary['B_seed']}`  
**Seed block hash:** `{summary['B_seed_block_hash']}`  
**Sample-spec precommit:** `{summary['sample_spec_precommit_sha']}`

## Selection

The sample specification fixed `N = {summary['N']}` before the seed block existed. The seed is `keccak256(blockhash(B_seed))`. The draw was made without replacement over the direct parent NFT-ID range `{enum['parent_id_start']}..{enum['parent_id_end']}`, defined by pinned `nextNFTId() = {enum['parent_counter_value']}`. No GLAST or other off-chain token index was used.

## Results

| Measure | Result |
|---|---:|
| Selected records | **{summary['N']}** |
| Canonical-fidelity passes | **{summary['fidelity_passes']}** |
| Published failures | **{summary['failures']}** |
| Exact normalized coordinate-hash matches | **{summary['coordinate_hash_matches']}** |
| Byte-identical current RCSB BinaryCIF files | **{summary['byte_identical_records']}** |
| Coordinate tolerance | **{summary['coordinate_tolerance_angstrom']} Å** |

Failure accounting: **{failures}**.

A fidelity pass requires equal atom counts, chain/entity sets, canonical atom identities and maximum paired coordinate deviation within the precommitted tolerance. Exact coordinate hashes and complete-file hashes are reported separately; they are not used to replace the tolerance test. BinaryCIF serialization and non-coordinate metadata may differ between the historical on-chain object and the current RCSB response even when the canonicalized structure agrees.

## Verify

```bash
sha256sum -c SHA256SUMS.txt
python tools/evidence/finalize_molnft_direct_evidence.py \
  --evidence evidence/article-02/molnft/block-{summary['B_pin']} \
  --verify-byte-for-byte
```
"""
    (directory / "README.md").write_text(text, encoding="utf-8")


def finalize(directory: pathlib.Path) -> None:
    spec = json.loads((directory / "sample-spec.json").read_text(encoding="utf-8"))
    old_summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    tolerance = float(spec["fidelity"]["coordinate_tolerance_angstrom"])
    rows: list[dict[str, Any]] = []

    for draw in read_draw(directory / "drawn-ids.csv"):
        draw_order = int(draw["draw_order"])
        token_id = int(draw["token_id"])
        pdb_id = str(draw["pdb_id"]).upper()
        row: dict[str, Any] = {
            "draw_order": draw_order,
            "token_id": token_id,
            "pdb_id": pdb_id,
            "outcome": "FAILURE",
            "reason_code": "UNKNOWN",
            "reason_detail": "",
        }
        reconstructed = directory / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif"
        canonical = directory / "canonical" / f"{pdb_id}.bcif"
        if reconstructed.is_file() and canonical.is_file():
            try:
                comparison = compare_bcif(reconstructed, canonical, tolerance)
                row.update(comparison)
                row.update(
                    {
                        "reconstructed_bytes": reconstructed.stat().st_size,
                        "canonical_bytes": canonical.stat().st_size,
                        "reconstructed_sha256": base.sha256_file(reconstructed),
                        "canonical_sha256": base.sha256_file(canonical),
                        "byte_identical": reconstructed.read_bytes() == canonical.read_bytes(),
                    }
                )
                if comparison["fidelity_pass"]:
                    row["outcome"] = "SUCCESS"
                    row["reason_code"] = "SUCCESS"
                else:
                    row["reason_code"] = "FIDELITY_MISMATCH"
                    failed = [
                        key
                        for key in [
                            "atom_count_equal",
                            "chain_ids_equal",
                            "entity_ids_equal",
                            "atom_keys_equal",
                            "coordinate_agreement",
                        ]
                        if not comparison[key]
                    ]
                    row["reason_detail"] = "failed checks: " + ", ".join(failed)
            except Exception as exc:  # noqa: BLE001
                row["reason_code"] = "PARSE_FAIL"
                row["reason_detail"] = f"{type(exc).__name__}: {exc}"
        else:
            row["reason_code"], row["reason_detail"] = classify_preserved_failure(directory, token_id, pdb_id)
        rows.append(row)

    rows.sort(key=lambda row: int(row["draw_order"]))
    base.write_results(directory / "results.csv", rows)
    reasons = Counter(str(row["reason_code"]) for row in rows)
    summary = dict(old_summary)
    summary.update(
        {
            "N": len(rows),
            "successes": sum(row["outcome"] == "SUCCESS" for row in rows),
            "failures": sum(row["outcome"] != "SUCCESS" for row in rows),
            "failures_by_reason": dict(sorted((key, value) for key, value in reasons.items() if key != "SUCCESS")),
            "fidelity_passes": sum(bool(row.get("fidelity_pass")) for row in rows),
            "canonical_comparisons": sum(bool(row.get("canonical_sha256")) for row in rows),
            "coordinate_tolerance_passes": sum(bool(row.get("coordinate_agreement")) for row in rows),
            "coordinate_hash_matches": sum(bool(row.get("coordinate_hash_equal")) for row in rows),
            "byte_identical_records": sum(bool(row.get("byte_identical")) for row in rows),
            "fidelity_pass_definition": [
                "atom_count_equal",
                "chain_ids_equal",
                "entity_ids_equal",
                "atom_keys_equal",
                "coordinate_agreement_within_precommitted_tolerance",
            ],
            "coordinate_hash_role": "exact normalized coordinate hashes are recorded and compared separately; equality is not required when the declared coordinate tolerance passes",
            "coordinate_hash_algorithm": "SHA-256 over big-endian float64 XYZ triples in canonical atom-key order with signed zero normalized",
            "complete_file_hash_role": "informational comparison of serialized BinaryCIF objects; current RCSB encoding and metadata may differ from the historical on-chain object",
            "deterministic_finalization": True,
        }
    )
    (directory / "summary.json").write_bytes(base.stable_json(summary))
    write_report(directory, summary)
    seed = json.loads((directory / "seed-derivation.json").read_text(encoding="utf-8"))
    base.integrity(
        directory,
        {
            "precommit_sha": seed["sample_spec_precommit_sha"],
            "seed_block_hash": seed["B_seed_block_hash"],
            "finalization": "deterministic local evidence comparison v2",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=pathlib.Path)
    parser.add_argument("--verify-byte-for-byte", action="store_true")
    args = parser.parse_args()
    directory = args.evidence.resolve()
    before = (directory / "results.csv").read_bytes() if args.verify_byte_for_byte else None
    finalize(directory)
    if before is not None and before != (directory / "results.csv").read_bytes():
        raise SystemExit("results.csv changed during byte-for-byte verification")
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
