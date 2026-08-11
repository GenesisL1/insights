#!/usr/bin/env python3
"""Final acceptance validation for Article 02 WS-1 and WS-2."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from Crypto.Hash import keccak

ROOT_RPC = "https://rpca.genesisl1.org"
API_PATH = "https://rpca.genesisl1.org/api"
EXPECTED_REQUERY = {(124713, "5KCS"), (162649, "6QFB")}
REVISION_AWARE_RECORD = (124713, "5KCS")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sums(directory: pathlib.Path) -> None:
    for line in (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = directory / relative
        assert path.is_file(), f"manifest file missing: {relative}"
        assert sha256(path) == digest, f"checksum mismatch: {relative}"


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def endpoint_slug(url: str) -> str:
    return url.removeprefix("https://").replace("/", "__")


def is_true(value: str) -> bool:
    return value.lower() == "true"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft", required=True, type=pathlib.Path)
    parser.add_argument("--network", required=True, type=pathlib.Path)
    args = parser.parse_args()
    mol = args.molnft.resolve()
    network = args.network.resolve()

    spec = json.loads((mol / "sample-spec.json").read_text(encoding="utf-8"))
    seed = json.loads((mol / "seed-derivation.json").read_text(encoding="utf-8"))
    summary = json.loads((mol / "summary.json").read_text(encoding="utf-8"))
    report = json.loads((mol / "targeted-requery.json").read_text(encoding="utf-8"))
    results = read_csv(mol / "results.csv")
    drawn = read_csv(mol / "drawn-ids.csv")

    assert int(spec["N"]) == 100
    assert len(results) == len(drawn) == int(spec["N"]) == int(summary["N"])
    assert int(summary["successes"]) + int(summary["failures"]) == int(summary["N"])
    assert int(summary["successes"]) == int(summary["fidelity_passes"]) == 100
    assert int(summary["failures"]) == 0
    assert summary["failures_by_reason"] == {}
    assert int(summary["coordinate_tolerance_passes"]) == 100
    assert len(summary["revision_aware_records"]) == 1
    assert summary["direct_nft_id_queries"] is True
    assert summary["off_chain_index_used"] is False
    assert summary["deterministic_finalization"] is True
    assert "serialized_object_hash_role" in summary

    assert seed["sample_spec_precommit_sha"] == summary["sample_spec_precommit_sha"]
    assert int(seed["B_seed"]) == int(spec["B_seed"])
    digest = keccak.new(digest_bits=256)
    digest.update(bytes.fromhex(seed["B_seed_block_hash"].removeprefix("0x")))
    assert seed["derived_seed_hex"].lower() == "0x" + digest.hexdigest()

    enum = spec["id_enumeration"]
    first_id = int(enum["parent_id_start"])
    last_id = int(enum["parent_id_end"])
    count = int(enum["parent_count"])
    assert enum["off_chain_index_used"] is False
    assert first_id == 1
    assert last_id == int(enum["parent_counter_value"]) - 1
    assert last_id - first_id + 1 == count == int(summary["enumerated_parent_count"])

    with gzip.open(mol / "parent-id-enumeration.csv.gz", "rt", encoding="ascii", newline="") as handle:
        population = [int(row["token_id"]) for row in csv.DictReader(handle)]
    assert population == list(range(first_id, last_id + 1))
    assert len({row["token_id"] for row in drawn}) == len(drawn)
    assert all(first_id <= int(row["token_id"]) <= last_id for row in drawn)

    final_failures = [row for row in results if row["outcome"] != "SUCCESS"]
    assert final_failures == []
    revision_row = next(row for row in results if (int(row["token_id"]), row["pdb_id"]) == REVISION_AWARE_RECORD)
    assert int(revision_row["draw_order"]) == 71
    assert revision_row["outcome"] == "SUCCESS"
    assert revision_row["reason_code"] == "SUCCESS"
    assert int(revision_row["reconstructed_atom_count"]) == 148945
    assert int(revision_row["canonical_atom_count"]) == 148945
    assert is_true(revision_row["atom_count_equal"])
    assert is_true(revision_row["chain_ids_equal"])
    assert is_true(revision_row["entity_ids_equal"])
    assert is_true(revision_row["atom_identity_agreement"])
    assert revision_row["atom_identity_comparison_method"] == "stable_atom_site_id_with_documented_rcsb_atom_name_revision"
    assert is_true(revision_row["stable_atom_site_id_sets_equal"])
    assert int(revision_row["stable_identity_field_mismatch_count"]) == 0
    assert is_true(revision_row["rcsb_atom_name_revision_documented"])
    assert revision_row["rcsb_atom_name_revision_date"] == "2026-07-01"
    assert revision_row["reconstructed_latest_structure_revision_date"] == "2024-11-06"
    assert revision_row["canonical_latest_structure_revision_date"] == "2026-07-01"
    assert int(revision_row["atom_name_change_count"]) == 4
    changes = json.loads(revision_row["atom_name_changes"])
    assert {(item["from_label_atom_id"], item["to_label_atom_id"], int(item["count"])) for item in changes} == {
        ("O1P", "OP2", 2),
        ("O2P", "OP1", 2),
    }
    assert is_true(revision_row["coordinate_agreement"])
    assert float(revision_row["max_coordinate_deviation_angstrom"]) == 0.0
    assert is_true(revision_row["coordinate_hash_equal"])
    assert is_true(revision_row["fidelity_pass"])

    for row in results:
        token_id = row["token_id"]
        pdb_id = row["pdb_id"] or "UNKNOWN"
        raw = mol / "raw" / f"{pdb_id}-token-{token_id}"
        if not raw.exists():
            raw = mol / "raw" / f"token-{token_id}"
        assert (raw / "eth-call-metadata.request.json").is_file()
        assert (raw / "eth-call-metadata.response.json").is_file()
        assert (raw / "eth-call-combined.request.json").is_file()
        assert (raw / "eth-call-combined.response.json").is_file()
        assert (mol / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif").is_file()
        assert (mol / "canonical" / f"{pdb_id}.bcif").is_file()

        assert row["outcome"] == "SUCCESS"
        assert row["reason_code"] == "SUCCESS"
        assert is_true(row["fidelity_pass"])
        for key in [
            "atom_count_equal",
            "chain_ids_equal",
            "entity_ids_equal",
            "atom_identity_agreement",
            "coordinate_agreement",
        ]:
            assert is_true(row[key]), f"{key} failed for token {token_id}"
        assert float(row["max_coordinate_deviation_angstrom"]) <= float(row["coordinate_tolerance_angstrom"])

    six_qfb = next(row for row in results if int(row["token_id"]) == 162649)
    assert six_qfb["pdb_id"] == "6QFB"
    assert six_qfb["outcome"] == "SUCCESS"
    assert is_true(six_qfb["fidelity_pass"])

    assert report["requested_endpoints"] == [ROOT_RPC, API_PATH]
    assert int(report["initial_sample_size"]) == 100
    assert int(report["initial_successes"]) == 98
    assert int(report["initial_failures"]) == 2
    assert report["initial_failures_by_reason"] == {"RPC_OUT_OF_GAS": 2}
    assert int(report["replacement_draws"]) == 0
    assert int(report["successful_requeries"]) == 2
    assert set(report["queried_token_ids"]) == {124713, 162649}
    assert report["endpoint_observations"][ROOT_RPC]["chain_id"] == 29
    assert report["endpoint_observations"][API_PATH]["probe"]["http_status"] == 404
    assert report["endpoint_observations"][API_PATH]["classification"] == "not a working GenesisL1 EVM JSON-RPC route"

    records = report["record_results"]
    assert {(int(item["token_id"]), item["pdb_id"]) for item in records} == EXPECTED_REQUERY
    for item in records:
        token_id = int(item["token_id"])
        pdb_id = item["pdb_id"]
        assert item["replacement_draw"] is False
        assert item["original_failure"]["reason_code"] == "RPC_OUT_OF_GAS"
        root = item["endpoint_calls"][ROOT_RPC]
        api = item["endpoint_calls"][API_PATH]
        assert "out of gas" in str(root["combined_default"]["error_message"]).lower()
        assert int(root["combined_explicit_gas"]["http_status"]) == 200
        assert int(root["combined_explicit_gas"]["result_hex_characters"]) > 1000
        assert int(api["metadata"]["http_status"]) == 404
        assert int(api["combined_default"]["http_status"]) == 404
        final = item["final_reconstruction"]
        assert final["endpoint"] == ROOT_RPC
        assert final["gas_override"] == report["gas_override"]
        assert final["serialized_hashes_are_integrity_identifiers_only"] is True
        raw_requery = mol / "raw" / f"{pdb_id}-token-{token_id}" / "targeted-requery"
        root_dir = raw_requery / endpoint_slug(ROOT_RPC)
        api_dir = raw_requery / endpoint_slug(API_PATH)
        assert (root_dir / "getCombinedData-default.response.json").is_file()
        assert (root_dir / "getCombinedData-explicit-gas.response.json").is_file()
        assert (api_dir / "getCombinedData-default.response.txt").read_text(encoding="utf-8") == "404 page not found\n"

    targeted = summary["targeted_requery"]
    assert int(targeted["initial_failures"]) == 2
    assert int(targeted["successful_requeries"]) == 2
    assert int(targeted["replacement_draws"]) == 0
    assert set(targeted["queried_token_ids"]) == {124713, 162649}

    verify_sums(mol)
    verify_sums(network)
    with tempfile.TemporaryDirectory() as tmp:
        copied = pathlib.Path(tmp) / mol.name
        shutil.copytree(mol, copied)
        before = {
            name: (copied / name).read_bytes()
            for name in ["results.csv", "summary.json", "README.md", "MANIFEST.json", "SHA256SUMS.txt"]
        }
        subprocess.run(
            [
                sys.executable,
                "tools/evidence/finalize_molnft_structural_evidence.py",
                "--evidence",
                str(copied),
                "--verify-deterministic",
            ],
            check=True,
        )
        for name, content in before.items():
            assert content == (copied / name).read_bytes(), f"deterministic output changed: {name}"

    ws2 = json.loads((network / "WS2_METRICS.json").read_text(encoding="utf-8"))
    article = pathlib.Path("content/article-02-next-verifiable-renaissance/article.md").read_text(encoding="utf-8")
    html = pathlib.Path("site/insights/genesisl1-decentralization-scientific-renaissance.html").read_text(encoding="utf-8")
    root_readme = pathlib.Path("README.md").read_text(encoding="utf-8")
    evidence_readme = (mol / "README.md").read_text(encoding="utf-8")
    methodology = pathlib.Path("methodology/molnft.md").read_text(encoding="utf-8")
    facts = json.loads(pathlib.Path("content/article-02-next-verifiable-renaissance/network-state.json").read_text(encoding="utf-8"))

    for text in [article, html]:
        assert "no GLAST or other off-chain token index was used" in text
        assert "100 of 100 canonical structural-fidelity passes" in text
        assert "one published final mismatch" not in text
        assert "5KCS" in text and "124713" in text
        assert "6QFB" in text and "162649" in text
        assert "148,945 atoms" in text
        assert "2026-07-01" in text
        assert "4 labels" in text or "four 6MZ atom-name labels" in text
        assert "maximum deviation was" in text or "all coordinates were unchanged" in text
        assert ROOT_RPC in text and API_PATH in text
        assert "HTTP 404" in text
        assert "no replacement id was drawn" in text.lower()
        assert f"{int(summary['B_pin']):,}" in text
        assert "strict atom" not in text.lower()
        assert f"{float(ws2['validator_concentration']['hhi_10000']):.2f}" in text
        assert f"{float(ws2['validator_concentration']['effective_count']):.2f}" in text
        assert f"{float(ws2['stake']['bonded_ratio_percent']):.2f}%" in text
        assert "address-level—not entity-level" in text

    randomized_facts = facts["molnft_randomized"]
    assert int(randomized_facts["successes"]) == 100
    assert int(randomized_facts["failures"]) == 0
    assert randomized_facts["failures_by_reason"] == {}
    assert int(randomized_facts["successful_same_id_payload_requeries"]) == 2
    assert set(randomized_facts["targeted_requery_token_ids"]) == {124713, 162649}
    assert int(randomized_facts["requested_api_path_http_status"]) == 404
    assert int(randomized_facts["replacement_draws"]) == 0
    assert randomized_facts["final_failure_records"] == []
    fact_revisions = randomized_facts["revision_aware_records"]
    assert len(fact_revisions) == 1
    assert (int(fact_revisions[0]["token_id"]), fact_revisions[0]["pdb_id"]) == REVISION_AWARE_RECORD
    assert fact_revisions[0]["rcsb_atom_name_revision_date"] == "2026-07-01"
    assert int(fact_revisions[0]["atom_name_change_count"]) == 4
    assert float(fact_revisions[0]["max_coordinate_deviation_angstrom"]) == 0.0

    assert "Targeted requery of provider-level failures" in methodology
    assert "5KCS" in methodology and "124713" in methodology
    assert "6QFB" in methodology and "162649" in methodology
    assert "Both recovered structures passed" in methodology
    assert "Documented RCSB atom-name revision reconciliation" in methodology
    assert "O1P→OP2" in methodology and "O2P→OP1" in methodology
    assert "No PDB-specific alias list is used" in methodology
    assert "--verify-deterministic" in methodology
    assert "1..nextNFTId(B_pin)-1" in methodology
    assert "Exact coordinate-hash equality is an additional reproducibility statistic" in methodology

    consensus_methodology = pathlib.Path("methodology/consensus.md").read_text(encoding="utf-8")
    caveat = "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement."
    assert caveat in consensus_methodology

    print(
        "Final WS-1/WS-2 acceptance passed: 100/100 structural-fidelity passes, zero failures; "
        "5KCS reconciled through documented 2026-07-01 RCSB atom-name revision metadata with zero coordinate deviation; "
        "two same-ID RPCA payload recoveries; no replacement draw"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
