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
    results = read_csv(mol / "results.csv")
    drawn = read_csv(mol / "drawn-ids.csv")

    assert int(spec["N"]) >= 100
    assert len(results) == len(drawn) == int(spec["N"]) == int(summary["N"])
    assert int(summary["successes"]) + int(summary["failures"]) == int(summary["N"])
    assert int(summary["fidelity_passes"]) == int(summary["successes"])
    assert int(summary["coordinate_tolerance_passes"]) == int(summary["successes"])
    assert int(summary["coordinate_hash_matches"]) <= int(summary["successes"])
    assert summary["direct_nft_id_queries"] is True
    assert summary["off_chain_index_used"] is False
    assert summary["deterministic_finalization"] is True

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

    failures: dict[str, int] = {}
    coordinate_hash_matches = 0
    byte_identical = 0
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

        if row["outcome"] == "SUCCESS":
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
            byte_identical += row["byte_identical"].lower() == "true"
        else:
            reason = row["reason_code"]
            assert reason not in {"", "UNKNOWN", "SUCCESS", "MISSING_FILE"}
            failures[reason] = failures.get(reason, 0) + 1

    assert coordinate_hash_matches == int(summary["coordinate_hash_matches"])
    assert byte_identical == int(summary["byte_identical_records"])
    assert failures == summary["failures_by_reason"]
    # The realized sample has two preserved provider-level out-of-gas failures.
    assert failures == {"RPC_OUT_OF_GAS": 2}
    assert int(summary["successes"]) == 98

    verify_sums(mol)
    verify_sums(network)
    with tempfile.TemporaryDirectory() as tmp:
        copied = pathlib.Path(tmp) / mol.name
        shutil.copytree(mol, copied)
        before_results = (copied / "results.csv").read_bytes()
        before_summary = (copied / "summary.json").read_bytes()
        subprocess.run(
            [
                sys.executable,
                "tools/evidence/finalize_molnft_direct_evidence.py",
                "--evidence",
                str(copied),
                "--verify-byte-for-byte",
            ],
            check=True,
        )
        assert before_results == (copied / "results.csv").read_bytes()
        assert before_summary == (copied / "summary.json").read_bytes()

    ws2 = json.loads((network / "WS2_METRICS.json").read_text(encoding="utf-8"))
    article = pathlib.Path("content/article-02-next-verifiable-renaissance/article.md").read_text(encoding="utf-8")
    html = pathlib.Path("site/insights/genesisl1-decentralization-scientific-renaissance.html").read_text(encoding="utf-8")
    for text in [article, html]:
        assert "no GLAST or other off-chain token index was used" in text
        assert "98 of 100 canonical structural-fidelity passes" in text
        assert "2 RPC out-of-gas responses" in text
        assert f"{int(summary['B_pin']):,}" in text
        assert f"{int(summary['coordinate_hash_matches'])} of 98" in text
        assert f"{float(ws2['validator_concentration']['hhi_10000']):.2f}" in text
        assert f"{float(ws2['validator_concentration']['effective_count']):.2f}" in text
        assert f"{float(ws2['stake']['bonded_ratio_percent']):.2f}%" in text
        assert "address-level—not entity-level" in text

    methodology = pathlib.Path("methodology/consensus.md").read_text(encoding="utf-8")
    caveat = "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement."
    assert caveat in methodology
    mol_method = pathlib.Path("methodology/molnft.md").read_text(encoding="utf-8")
    assert "No GLAST or other off-chain token index is used" in mol_method
    assert "1..nextNFTId(B_pin)-1" in mol_method
    assert "Exact coordinate-hash equality is an additional reproducibility statistic" in mol_method

    repository_qa = pathlib.Path("tools/qa/validate_repository.py").read_text(encoding="utf-8")
    for forbidden in ["No negative section", "Uncrossed gates", "What it costs", "The next proofs"]:
        assert forbidden not in repository_qa

    print(
        f"Final WS-1/WS-2 acceptance passed: {summary['successes']}/{summary['N']} fidelity passes, "
        f"{summary['coordinate_hash_matches']} exact coordinate hashes, {summary['failures']} preserved failures"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
