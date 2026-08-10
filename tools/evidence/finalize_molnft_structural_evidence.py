#!/usr/bin/env python3
"""Finalize the direct-ID MOLNFT sample from preserved local evidence.

A fidelity pass is structural. It requires equal atom counts, chain/entity sets,
canonical atom identity agreement, including narrowly documented post-deposition
RCSB atom-name revisions, and paired coordinates within the precommitted tolerance. Serialized BinaryCIF equality is neither evaluated nor reported.
Individual SHA-256 values remain as integrity identifiers for each preserved
object, without turning equality between those values into a criterion.

The finalizer also incorporates a preserved targeted requery, when present. A
provider-level failure may be retried only for the same predetermined NFT ID;
replacement draws are never permitted.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import pathlib
import sys
from collections import Counter
from typing import Any

import molnft_structural_compare as structural_compare

BASE_PATH = pathlib.Path(__file__).with_name("capture_molnft_randomized_sample.py")
SPEC = importlib.util.spec_from_file_location("genesisl1_ws1_finalize_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def compare_bcif(reconstructed: pathlib.Path, canonical: pathlib.Path, tolerance: float) -> dict[str, Any]:
    return structural_compare.compare_bcif(reconstructed, canonical, tolerance)


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
        return "CANONICAL_UNAVAILABLE", "canonical RCSB BinaryCIF was unavailable"
    if not reconstructed.is_file():
        return "PARSE_FAIL", "reconstructed BinaryCIF is absent despite the preserved draw"
    return "MISSING_FILE", "required comparison object is absent"


def targeted_summary(report: dict[str, Any]) -> dict[str, Any]:
    records = []
    for item in report.get("record_results") or []:
        structure = item.get("structure") or {}
        endpoint_calls = item.get("endpoint_calls") or {}
        root = endpoint_calls.get("https://rpca.genesisl1.org") or {}
        api = endpoint_calls.get("https://rpca.genesisl1.org/api") or {}
        records.append(
            {
                "draw_order": item.get("draw_order"),
                "token_id": item.get("token_id"),
                "pdb_id": item.get("pdb_id"),
                "compound": structure.get("compound"),
                "experiment_type": structure.get("experiment_type"),
                "resolution": structure.get("resolution"),
                "original_reason_code": (item.get("original_failure") or {}).get("reason_code"),
                "root_default_error": (root.get("combined_default") or {}).get("error_message"),
                "root_explicit_gas_success": bool(
                    (root.get("combined_explicit_gas") or {}).get("result_hex_characters")
                ),
                "api_http_status": (api.get("combined_default") or {}).get("http_status"),
                "replacement_draw": bool(item.get("replacement_draw")),
            }
        )
    return {
        "schema": report.get("schema"),
        "performed_at_utc": report.get("performed_at_utc"),
        "requested_endpoints": report.get("requested_endpoints") or [],
        "gas_override": report.get("gas_override"),
        "initial_successes": report.get("initial_successes"),
        "initial_failures": report.get("initial_failures"),
        "initial_failures_by_reason": report.get("initial_failures_by_reason") or {},
        "queried_token_ids": report.get("queried_token_ids") or [],
        "queried_failed_record_count": len(report.get("queried_token_ids") or []),
        "successful_requeries": report.get("successful_requeries"),
        "replacement_draws": report.get("replacement_draws"),
        "records": records,
    }


def write_report(directory: pathlib.Path, summary: dict[str, Any]) -> None:
    failure_lines = summary.get("failures_by_reason") or {}
    failures = ", ".join(f"{value} {key}" for key, value in sorted(failure_lines.items())) or "none"
    enum = summary["enumeration_method"]
    targeted = summary.get("targeted_requery") or {}
    targeted_records = targeted.get("records") or []
    targeted_text = ""
    if targeted_records:
        rows = []
        for record in targeted_records:
            rows.append(
                f"| {record['pdb_id']} | {record['token_id']} | {record.get('compound') or '—'} | "
                f"{record.get('original_reason_code') or '—'} | "
                f"{'reconstructed' if record.get('root_explicit_gas_success') else 'not reconstructed'} |"
            )
        targeted_text = (
            "\n## Targeted same-ID requery\n\n"
            "Only the failed predetermined draws were queried again; no successful sample row was queried and no replacement ID was drawn. "
            "The root `https://rpca.genesisl1.org` URL reported GenesisL1 EVM chain ID 29. Its default calls reproduced the provider-level "
            "out-of-gas response, while the same calls at the same pinned block succeeded with the preserved explicit gas allowance. "
            "The exact `https://rpca.genesisl1.org/api` path returned HTTP 404 and is not a JSON-RPC route.\n\n"
            "| PDB | NFT ID | Structure | Initial result | Same-ID RPCA result |\n"
            "|---|---:|---|---|---|\n"
            + "\n".join(rows)
            + "\n"
        )

    revision_rows = summary.get("revision_aware_records") or []
    revision_text = ""
    if revision_rows:
        lines = []
        for record in revision_rows:
            changes = "; ".join(
                f"{item.get('label_comp_id') or item.get('auth_comp_id')}: "
                f"{item.get('from_label_atom_id')}→{item.get('to_label_atom_id')} ×{item.get('count')}"
                for item in record.get("atom_name_changes") or []
            )
            lines.append(
                f"- **{record['pdb_id']} / NFT {record['token_id']}** — current RCSB revision "
                f"{record.get('rcsb_atom_name_revision_date') or 'unknown date'} changed "
                f"{record.get('atom_name_change_count', 0)} atom-name labels ({changes}); all non-name identity fields "
                f"matched by `_atom_site.id`, with maximum coordinate deviation "
                f"{float(record.get('max_coordinate_deviation_angstrom') or 0):.6g} Å."
            )
        revision_text = (
            "\n## Documented RCSB atom-name revisions\n\n"
            "A later RCSB atom-name revision is not a structural mismatch. The revision-aware path is accepted only when "
            "the current RCSB audit history explicitly lists both atom-name fields, `_atom_site.id` remains unique and "
            "unchanged, every non-name identity field agrees, and paired coordinates meet the original tolerance. "
            "No PDB-specific alias table is used.\n\n" + "\n".join(lines) + "\n"
        )

    text = f"""# MOLNFT direct NFT-ID randomized fidelity evidence

**Pinned GenesisL1 block:** `{summary['B_pin']}`  
**Pinned block hash:** `{summary['B_pin_block_hash']}`  
**Future seed block:** `{summary['B_seed']}`  
**Seed block hash:** `{summary['B_seed_block_hash']}`  
**Sample-spec precommit:** `{summary['sample_spec_precommit_sha']}`

## Selection

The sample specification fixed `N = {summary['N']}` before the seed block existed. The seed is `keccak256(blockhash(B_seed))`. The draw was made without replacement over the direct parent NFT-ID range `{enum['parent_id_start']}..{enum['parent_id_end']}`, defined by pinned `nextNFTId() = {enum['parent_counter_value']}`. No GLAST or other off-chain token index was used.

## Final results

| Measure | Result |
|---|---:|
| Selected records | **{summary['N']}** |
| Canonical structural-fidelity passes | **{summary['fidelity_passes']}** |
| Final failures | **{summary['failures']}** |
| Exact normalized coordinate-hash matches | **{summary['coordinate_hash_matches']}** |
| Coordinate tolerance | **{summary['coordinate_tolerance_angstrom']} Å** |

Final failure accounting: **{failures}**.

A fidelity pass requires equal atom counts, chain/entity sets, atom identity agreement and maximum paired coordinate deviation within the precommitted tolerance. Atom identity agreement is either raw canonical-key equality or the narrowly documented RCSB revision-aware path described below. Serialized-object equality is not calculated or reported. The separately recorded SHA-256 value for each object is an integrity identifier only.
{targeted_text}{revision_text}
## Verify

```bash
sha256sum -c SHA256SUMS.txt
python tools/evidence/finalize_molnft_structural_evidence.py \\
  --evidence evidence/article-02/molnft/block-{summary['B_pin']} \\
  --verify-deterministic
```
"""
    (directory / "README.md").write_text(text, encoding="utf-8")


def finalize(directory: pathlib.Path) -> None:
    spec = json.loads((directory / "sample-spec.json").read_text(encoding="utf-8"))
    old_summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    targeted_path = directory / "targeted-requery.json"
    targeted_report = json.loads(targeted_path.read_text(encoding="utf-8")) if targeted_path.is_file() else None
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
                            "atom_identity_agreement",
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
    for obsolete in ["byte_identical_records", "complete_file_hash_role"]:
        summary.pop(obsolete, None)
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
            "strict_atom_key_matches": sum(bool(row.get("atom_keys_equal")) for row in rows),
            "revision_aware_atom_identity_passes": sum(
                bool(row.get("fidelity_pass")) and bool(row.get("rcsb_atom_name_revision_documented")) for row in rows
            ),
            "revision_aware_records": [
                {
                    "draw_order": row.get("draw_order"),
                    "token_id": row.get("token_id"),
                    "pdb_id": row.get("pdb_id"),
                    "rcsb_atom_name_revision_date": row.get("rcsb_atom_name_revision_date"),
                    "reconstructed_latest_structure_revision_date": row.get("reconstructed_latest_structure_revision_date"),
                    "canonical_latest_structure_revision_date": row.get("canonical_latest_structure_revision_date"),
                    "atom_name_change_count": row.get("atom_name_change_count"),
                    "atom_name_changes": row.get("atom_name_changes") or [],
                    "max_coordinate_deviation_angstrom": row.get("max_coordinate_deviation_angstrom"),
                }
                for row in rows
                if row.get("rcsb_atom_name_revision_documented")
            ],
            "fidelity_pass_definition": [
                "atom_count_equal",
                "chain_ids_equal",
                "entity_ids_equal",
                "atom_identity_agreement_by_raw_key_or_documented_rcsb_atom_name_revision",
                "coordinate_agreement_within_precommitted_tolerance",
            ],
            "coordinate_hash_role": "exact normalized coordinate hashes are recorded separately in the accepted atom-pairing order; equality is not required when the declared coordinate tolerance passes",
            "coordinate_hash_algorithm": "SHA-256 over big-endian float64 XYZ triples in accepted atom-pairing order with signed zero normalized",
            "serialized_object_hash_role": "reconstructed and canonical SHA-256 values are independent integrity identifiers only; equality is neither evaluated nor used for fidelity",
            "deterministic_finalization": True,
        }
    )
    if targeted_report is not None:
        summary["targeted_requery"] = targeted_summary(targeted_report)
    (directory / "summary.json").write_bytes(base.stable_json(summary))
    write_report(directory, summary)
    seed = json.loads((directory / "seed-derivation.json").read_text(encoding="utf-8"))
    base.integrity(
        directory,
        {
            "precommit_sha": seed["sample_spec_precommit_sha"],
            "seed_block_hash": seed["B_seed_block_hash"],
            "finalization": "deterministic local structural comparison v4 with documented RCSB atom-name revision reconciliation",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=pathlib.Path)
    parser.add_argument("--verify-deterministic", action="store_true")
    args = parser.parse_args()
    directory = args.evidence.resolve()
    observed = {}
    if args.verify_deterministic:
        for name in ["results.csv", "summary.json", "README.md", "MANIFEST.json", "SHA256SUMS.txt"]:
            path = directory / name
            observed[name] = path.read_bytes() if path.is_file() else None
    finalize(directory)
    if args.verify_deterministic:
        for name, before in observed.items():
            path = directory / name
            after = path.read_bytes() if path.is_file() else None
            if before != after:
                raise SystemExit(f"{name} changed during deterministic verification")
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
