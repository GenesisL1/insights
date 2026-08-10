#!/usr/bin/env python3
"""Acceptance validation for the Article 02 WS-1 / WS-2 evidence upgrade."""
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
    assert seed["sample_spec_precommit_sha"] == summary["sample_spec_precommit_sha"]
    assert int(seed["B_seed"]) == int(spec["B_seed"])
    block_hash = bytes.fromhex(seed["B_seed_block_hash"].removeprefix("0x"))
    digest = keccak.new(digest_bits=256)
    digest.update(block_hash)
    assert seed["derived_seed_hex"].lower() == "0x" + digest.hexdigest()

    with gzip.open(mol / "parent-id-enumeration.csv.gz", "rt", encoding="ascii", newline="") as handle:
        enumerated = list(csv.DictReader(handle))
    assert len(enumerated) == int(summary["enumerated_parent_count"])
    assert len({row["token_id"] for row in enumerated}) == len(enumerated)
    assert len({row["pdb_id"] for row in enumerated}) == len(enumerated)

    with (mol / "drawn-ids.csv").open(newline="", encoding="ascii") as handle:
        drawn = list(csv.DictReader(handle))
    with (mol / "results.csv").open(newline="", encoding="utf-8") as handle:
        results = list(csv.DictReader(handle))
    assert len(drawn) == int(spec["N"])
    assert len(results) == int(spec["N"])
    assert len({row["token_id"] for row in drawn}) == len(drawn)
    enum_pairs = {(row["token_id"], row["pdb_id"]) for row in enumerated}
    assert all((row["token_id"], row["pdb_id"]) in enum_pairs for row in drawn)

    for row in results:
        raw_dir = mol / "raw" / f"{row['pdb_id']}-token-{row['token_id']}"
        assert (raw_dir / "eth-call-combined.request.json").is_file()
        assert (raw_dir / "eth-call-combined.response.json").is_file()
        if row["outcome"] == "SUCCESS":
            assert (mol / "reconstructed" / f"{row['pdb_id']}-token-{row['token_id']}.bcif").is_file()
            assert (mol / "canonical" / f"{row['pdb_id']}.bcif").is_file()
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

    # Recompute on a copy and require byte-identical results.csv.
    with tempfile.TemporaryDirectory() as tmp:
        copied = pathlib.Path(tmp) / mol.name
        shutil.copytree(mol, copied)
        before = (copied / "results.csv").read_bytes()
        subprocess.run(
            ["python", "tools/evidence/capture_molnft_randomized_sample.py", "--recompute", str(copied)],
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
    assert f"{float(ws2['validator_concentration']['hhi_10000']):.2f}" in article
    assert f"{float(ws2['stake']['bonded_ratio_percent']):.2f}%" in article
    assert "address-level—not entity-level" in article

    methodology = pathlib.Path("methodology/consensus.md").read_text(encoding="utf-8")
    required = "an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement."
    assert required in methodology

    qa = pathlib.Path("tools/qa/validate_repository.py").read_text(encoding="utf-8")
    for forbidden in ["No negative section", "Uncrossed gates", "What it costs", "The next proofs"]:
        assert forbidden not in qa

    print("WS-1 / WS-2 acceptance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
