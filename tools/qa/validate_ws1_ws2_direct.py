#!/usr/bin/env python3
"""Acceptance validation for direct-NFT-ID WS-1 and complete WS-2."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import pathlib
import shutil
import subprocess
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft", required=True, type=pathlib.Path)
    parser.add_argument("--network", required=True, type=pathlib.Path)
    args = parser.parse_args()

    mol = args.molnft
    spec = json.loads((mol / "sample-spec.json").read_text(encoding="utf-8"))
    seed = json.loads((mol / "seed-derivation.json").read_text(encoding="utf-8"))
    summary = json.loads((mol / "summary.json").read_text(encoding="utf-8"))

    assert int(spec["N"]) >= 100
    assert int(summary["N"]) == int(spec["N"])
    assert int(summary["successes"]) + int(summary["failures"]) == int(spec["N"])
    assert summary["off_chain_index_used"] is False
    assert summary["direct_nft_id_queries"] is True
    assert seed["sample_spec_precommit_sha"] == summary["sample_spec_precommit_sha"]
    assert int(seed["B_seed"]) == int(spec["B_seed"])
    block_hash = bytes.fromhex(seed["B_seed_block_hash"].removeprefix("0x"))
    digest = keccak.new(digest_bits=256)
    digest.update(block_hash)
    assert seed["derived_seed_hex"].lower() == "0x" + digest.hexdigest()

    enum_spec = spec["id_enumeration"]
    assert enum_spec["off_chain_index_used"] is False
    first_id = int(enum_spec["parent_id_start"])
    last_id = int(enum_spec["parent_id_end"])
    expected = int(enum_spec["parent_count"])
    assert first_id == 1
    assert last_id - first_id + 1 == expected
    assert int(enum_spec["parent_counter_value"]) - 1 == last_id

    with gzip.open(mol / "parent-id-enumeration.csv.gz", "rt", encoding="ascii", newline="") as handle:
        enumerated = [int(row["token_id"]) for row in csv.DictReader(handle)]
    assert len(enumerated) == expected == int(summary["enumerated_parent_count"])
    assert enumerated[0] == first_id and enumerated[-1] == last_id
    assert enumerated == list(range(first_id, last_id + 1))

    with (mol / "drawn-ids.csv").open(newline="", encoding="ascii") as handle:
        drawn = list(csv.DictReader(handle))
    with (mol / "results.csv").open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))
    assert len(drawn) == len(results) == int(spec["N"])
    assert len({row["token_id"] for row in drawn}) == len(drawn)
    assert all(first_id <= int(row["token_id"]) <= last_id for row in drawn)

    for row in results:
        token_id = row["token_id"]
        pdb_id = row["pdb_id"] or "UNKNOWN"
        raw_dir = mol / "raw" / f"{pdb_id}-token-{token_id}"
        if not raw_dir.exists():
            raw_dir = mol / "raw" / f"token-{token_id}"
        assert (raw_dir / "eth-call-metadata.request.json").is_file(), f"metadata request missing for token {token_id}"
        assert (raw_dir / "eth-call-metadata.response.json").is_file(), f"metadata response missing for token {token_id}"
        if pdb_id != "UNKNOWN":
            assert (raw_dir / "eth-call-combined.request.json").is_file()
            assert (raw_dir / "eth-call-combined.response.json").is_file()
        if row["outcome"] == "SUCCESS":
            assert len(pdb_id) == 4
            assert (mol / "reconstructed" / f"{pdb_id}-token-{token_id}.bcif").is_file()
            assert (mol / "canonical" / f"{pdb_id}.bcif").is_file()
            assert row["fidelity_pass"].lower() == "true"
            assert row["atom_count_equal"].lower() == "true"
            assert row["chain_ids_equal"].lower() == "true"
            assert row["entity_ids_equal"].lower() == "true"
            assert row["coordinate_hash_equal"].lower() == "true"
            assert row["coordinate_agreement"].lower() == "true"
        else:
            assert row["reason_code"] not in {"", "UNKNOWN", "SUCCESS"}

    verify_sums(mol)
    verify_sums(args.network)

    with tempfile.TemporaryDirectory() as tmp:
        copied = pathlib.Path(tmp) / mol.name
        shutil.copytree(mol, copied)
        before = (copied / "results.csv").read_bytes()
        subprocess.run(
            ["python", "tools/evidence/capture_molnft_direct_randomized_sample.py", "--recompute", str(copied)],
            check=True,
        )
        after = (copied / "results.csv").read_bytes()
        assert before == after, "results.csv is not byte-for-byte reproducible"

    article = pathlib.Path("content/article-02-next-verifiable-renaissance/article.md").read_text(encoding="utf-8")
    ws2 = json.loads((args.network / "WS2_METRICS.json").read_text(encoding="utf-8"))
    assert "Validator HHI (0–10,000)" in article
    assert "Effective validator count" in article
    assert "Bonded / native supply" in article
    assert f"**{int(summary['successes'])} of {int(summary['N'])}**" in article
    assert f"block **{int(summary['B_pin']):,}**" in article
    assert "no GLAST or other off-chain token index was used" in article
    assert f"{float(ws2['validator_concentration']['hhi_10000']):.2f}" in article
    assert f"{float(ws2['stake']['bonded_ratio_percent']):.2f}%" in article
    assert "address-level—not entity-level" in article

    methodology = pathlib.Path("methodology/consensus.md").read_text(encoding="utf-8")
    required = "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement."
    assert required in methodology
    mol_method = pathlib.Path("methodology/molnft.md").read_text(encoding="utf-8")
    assert "No GLAST or other off-chain token index is used" in mol_method
    assert "1..nextNFTId(B_pin)-1" in mol_method

    qa = pathlib.Path("tools/qa/validate_repository.py").read_text(encoding="utf-8")
    for forbidden in ["No negative section", "Uncrossed gates", "What it costs", "The next proofs"]:
        assert forbidden not in qa

    print("Direct NFT-ID WS-1 / WS-2 acceptance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
