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


def assert_no_serialized_equality_language(text: str, label: str) -> None:
    lowered = text.lower()
    for forbidden in ["byte-identical", "byte identical", "byte-for-byte", "byte_to_byte"]:
        assert forbidden not in lowered, f"{label} still contains {forbidden!r}"


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

    assert int(spec["N"]) >= 100
    assert len(results) == len(drawn) == int(spec["N"]) == int(summary["N"])
    assert int(summary["successes"]) + int(summary["failures"]) == int(summary["N"])
    assert int(summary["successes"]) == int(summary["fidelity_passes"])
    assert int(summary["coordinate_tolerance_passes"]) == int(summary["successes"])
    assert int(summary["coordinate_hash_matches"]) <= int(summary["successes"])
    assert int(summary["successes"]) == int(summary["N"]) == 100
    assert int(summary["failures"]) == 0
    assert summary["failures_by_reason"] == {}
    assert summary["direct_nft_id_queries"] is True
    assert summary["off_chain_index_used"] is False
    assert summary["deterministic_finalization"] is True
    assert "byte_identical_records" not in summary
    assert "complete_file_hash_role" not in summary
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

    assert "byte_identical" not in results[0], "results.csv must not contain serialized equality"
    coordinate_hash_matches = 0
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
        assert row["outcome"] == "SUCCESS"
        assert row["reason_code"] == "SUCCESS"
        assert row["fidelity_pass"].lower() == "true"
        for key in [
            "atom_count_equal",
            "chain_ids_equal",
            "entity_ids_equal",
            "atom_keys_equal",
            "coordinate_agreement",
        ]:
            assert row[key].lower() == "true", f"{key} failed for token {token_id}"
        assert float(row["max_coordinate_deviation_angstrom"]) <= float(row["coordinate_tolerance_angstrom"])
        assert (mol / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif").is_file()
        assert (mol / "canonical" / f"{pdb_id}.bcif").is_file()
        coordinate_hash_matches += row["coordinate_hash_equal"].lower() == "true"
    assert coordinate_hash_matches == int(summary["coordinate_hash_matches"])

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

    for label, text in [
        ("article", article),
        ("production HTML", html),
        ("root README", root_readme),
        ("evidence README", evidence_readme),
        ("MOLNFT methodology", methodology),
    ]:
        assert_no_serialized_equality_language(text, label)

    for text in [article, html]:
        assert "no GLAST or other off-chain token index was used" in text
        assert "100 of 100 canonical structural-fidelity passes" in text
        assert "5KCS" in text and "124713" in text
        assert "6QFB" in text and "162649" in text
        assert ROOT_RPC in text and API_PATH in text
        assert "HTTP 404" in text
        assert "no replacement id was drawn" in text.lower()
        assert f"{int(summary['B_pin']):,}" in text
        assert f"{int(summary['coordinate_hash_matches'])} of 100" in text
        assert f"{float(ws2['validator_concentration']['hhi_10000']):.2f}" in text
        assert f"{float(ws2['validator_concentration']['effective_count']):.2f}" in text
        assert f"{float(ws2['stake']['bonded_ratio_percent']):.2f}%" in text
        assert "address-level—not entity-level" in text

    randomized_facts = facts["molnft_randomized"]
    assert "byte_identical_records" not in randomized_facts
    assert int(randomized_facts["successes"]) == 100
    assert int(randomized_facts["failures"]) == 0
    assert set(randomized_facts["targeted_requery_token_ids"]) == {124713, 162649}
    assert int(randomized_facts["requested_api_path_http_status"]) == 404

    assert "Targeted requery of provider-level failures" in methodology
    assert "5KCS" in methodology and "124713" in methodology
    assert "6QFB" in methodology and "162649" in methodology
    assert "--verify-deterministic" in methodology
    assert "1..nextNFTId(B_pin)-1" in methodology
    assert "Exact coordinate-hash equality is an additional reproducibility statistic" in methodology

    consensus_methodology = pathlib.Path("methodology/consensus.md").read_text(encoding="utf-8")
    caveat = "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement."
    assert caveat in consensus_methodology

    print(
        f"Final WS-1/WS-2 acceptance passed: {summary['successes']}/{summary['N']} structural-fidelity passes, "
        f"{summary['coordinate_hash_matches']} exact coordinate hashes, two same-ID RPCA recoveries, no replacement draw"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
