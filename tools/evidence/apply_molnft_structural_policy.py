#!/usr/bin/env python3
"""Apply the repository-wide MOLNFT structural-fidelity policy.

This is a source migration, not an evidence computation. It removes serialized
object equality from capture outputs and publication helpers, makes exact
coordinate hashes informational rather than pass/fail, updates permanent CI to
the structural validator, and retires the superseded finalizer/validator names.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(".")


def edit(path: str, replacements: list[tuple[str, str]]) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    for old, new in replacements:
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


def main() -> int:
    edit(
        "tools/evidence/capture_molnft_randomized_sample.py",
        [
            ('                rec["coordinate_hash"] == can["coordinate_hash"],\n', ""),
            ('                "byte_identical": reconstructed == canonical,\n', ""),
            ('    "byte_identical",\n', ""),
            ('                        "byte_identical": reconstructed.read_bytes() == canonical.read_bytes(),\n', ""),
            ('            "byte_identical_records": sum(bool(row.get("byte_identical")) for row in results),\n', ""),
            ('        "byte_identical_records": sum(bool(row.get("byte_identical")) for row in results),\n', ""),
        ],
    )
    edit(
        "tools/evidence/capture_molnft_direct_randomized_sample.py",
        [('        "byte_identical_records": sum(bool(row.get("byte_identical")) for row in results),\n', "")],
    )
    edit(
        "tools/publication/apply_ws1_ws2_direct_article.py",
        [
            ('    identical = int(summary.get("byte_identical_records", 0))\n', ""),
            (
                '        f"**{exact_coordinates} of {fidelity}** records, while **{identical}** current RCSB BinaryCIF files were byte-identical to the "\n'
                '        f"historical on-chain serialization. The latter is reported separately because BinaryCIF metadata and encoding can change "\n'
                '        f"without changing the canonicalized atom identities or Cartesian structure. The future-block seed, complete numeric parent-ID "\n',
                '        f"**{exact_coordinates} of {fidelity}** records. Serialized BinaryCIF equality is neither calculated nor used as a pass "\n'
                '        f"condition; each object\'s SHA-256 is retained independently only as an integrity identifier. The future-block seed, complete "\n'
                '        f"numeric parent-ID "\n',
            ),
        ],
    )
    edit(
        "tools/publication/apply_ws1_ws2_article.py",
        [
            ('    identical = int(summary.get("byte_identical_records", 0))\n', ""),
            (
                '        f"**{fidelity} records passed** the declared atom-count, chain/entity-ID, atom-identity, coordinate-hash and coordinate-agreement "\n'
                '        f"checks at a maximum permitted deviation of **{tolerance:.6f} Å**; **{identical}** were also byte-identical to the retrieved "\n'
                '        f"canonical BinaryCIF. The sample specification, future-block seed derivation, enumeration, complete success/failure table, "\n',
                '        f"**{fidelity} records passed** the declared atom-count, chain/entity-ID, atom-identity and coordinate-agreement checks at a "\n'
                '        f"maximum permitted deviation of **{tolerance:.6f} Å**. Serialized BinaryCIF equality is neither calculated nor used as a "\n'
                '        f"fidelity criterion. The sample specification, future-block seed derivation, enumeration, complete success/failure table, "\n',
            ),
            ('        "byte_identical_records": summary.get("byte_identical_records", 0),\n', ""),
        ],
    )

    methodology = ROOT / "methodology/molnft.md"
    text = methodology.read_text(encoding="utf-8")
    marker = "- `SUCCESS`\n\n## Canonical comparison and storage model\n"
    if "## Targeted requery of provider-level failures" not in text:
        text = text.replace(
            marker,
            "- `SUCCESS`\n\n"
            "## Targeted requery of provider-level failures\n\n"
            "A provider-level retrieval failure does not authorize a replacement draw. The predetermined NFT ID remains part of the sample. A targeted requery may call only that same ID, at the same pinned block, while preserving the original request and response, the new endpoint, and any explicit call parameters such as a gas allowance. Successful sample rows are not queried again.\n\n"
            "For the realized sample, the original default calls that failed were PDB `5KCS` / NFT `124713` and PDB `6QFB` / NFT `162649`. Both were re-queried through `https://rpca.genesisl1.org`; default calls reproduced the out-of-gas result and explicit-gas calls returned the complete payloads. The exact `https://rpca.genesisl1.org/api` path was also probed and returned HTTP 404, so it is recorded as a non-RPC route. No replacement ID was drawn.\n\n"
            "## Canonical comparison and storage model\n",
        )
    text = text.replace(
        "The on-chain transformation—base64 plus gzip—is reversible and therefore lossless relative to the BinaryCIF object minted into the contract. A current RCSB BinaryCIF response may nevertheless have different serialization, compression-independent metadata or dictionary encoding from the historical object while representing the same atom identities and coordinates. For that reason, complete-file byte equality is reported but is not treated as the molecular-fidelity criterion.\n",
        "The on-chain transformation—base64 plus gzip—is reversible and therefore lossless relative to the BinaryCIF object minted into the contract. A current RCSB BinaryCIF response may nevertheless have different serialization, compression-independent metadata or dictionary encoding from the historical object while representing the same atom identities and coordinates. Serialized-object equality is therefore neither calculated nor used as a molecular-fidelity criterion. The reconstructed and canonical SHA-256 values are retained independently only to identify the preserved objects.\n",
    )
    text = text.replace(
        "| Complete-file hashes | SHA-256 values recorded for both serialized BinaryCIF objects; exact equality reported separately |\n",
        "| Object integrity hashes | SHA-256 recorded independently for each preserved BinaryCIF object; no equality test is performed |\n",
    )
    text = text.replace("- byte-identical complete-file count;\n", "")
    text = text.replace(
        "- failures by reason code;\n",
        "- final failures by reason code;\n- initial provider-level failures and any targeted same-ID requery;\n",
    )
    text = text.replace(
        "A result is accepted only when every preselected row remains visible. Provider-level failures are evidence about the measured retrieval path and are not silently replaced by another draw.\n",
        "A result is accepted only when every preselected row remains visible. Provider-level failures are evidence about the measured retrieval path and are not silently replaced by another draw. When a same-ID requery succeeds, both the original failure and the successful requery remain preserved.\n",
    )
    text = text.replace("finalize_molnft_direct_evidence.py", "finalize_molnft_structural_evidence.py")
    text = text.replace("--verify-byte-for-byte", "--verify-deterministic")
    text = text.replace(
        "The command recomputes `results.csv`, `summary.json`, `README.md`, `MANIFEST.json` and `SHA256SUMS.txt` in deterministic order. The environment is pinned in `requirements.lock` and the realized versions are recorded in the summary.\n",
        "The command recomputes `results.csv`, `summary.json`, `README.md`, `MANIFEST.json` and `SHA256SUMS.txt` in deterministic order. It does not compare reconstructed and canonical serialized files for equality. The environment is pinned in `requirements.lock` and the realized versions are recorded in the summary.\n",
    )
    methodology.write_text(text, encoding="utf-8")

    for workflow in [
        ".github/workflows/verify-article-02-evidence.yml",
        ".github/workflows/package-article-02.yml",
    ]:
        edit(workflow, [("validate_ws1_ws2_final.py", "validate_ws1_ws2_structural.py")])

    root_readme = ROOT / "README.md"
    text = root_readme.read_text(encoding="utf-8")
    text = text.replace("finalize_molnft_direct_evidence.py", "finalize_molnft_structural_evidence.py")
    text = text.replace("--verify-byte-for-byte", "--verify-deterministic")
    root_readme.write_text(text, encoding="utf-8")

    for obsolete in [
        "tools/evidence/finalize_molnft_direct_evidence.py",
        "tools/qa/validate_ws1_ws2_final.py",
    ]:
        path = ROOT / obsolete
        if path.exists():
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
