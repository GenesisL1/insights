# MOLNFT randomized reconstruction methodology

The immutable Article 02 audit keeps three claims separate:

1. current contract counters describe collection state at the latest publication block;
2. reconstruction proves that a selected on-chain payload can be recovered as a BinaryCIF object;
3. structural-fidelity testing compares that recovered object with the corresponding preserved RCSB BinaryCIF.

## Sample specification and selection

The sample specification records an announcement time of 19:15:22Z, before block 13,436,979 existed; that time is self-recorded and not independently timestamped. What any third party can verify from the published record is that the draw is fully determined by the hash of block 13,436,979 and the specification's contents.

The seed was derived from the future EVM block hash. Parent IDs were sampled without replacement from `1..nextNFTId(B_pin)-1` with rejection sampling. No GLAST or other off-chain token index was used, and no failed row could be replaced by another draw.

## Reconstruction

For each selected NFT ID, the audit preserved the exact calls and applied:

```text
getMetadata(tokenId) at B_pin
→ getCombinedData(tokenId) at B_pin
→ ABI decode
→ base64 decode
→ gzip decompress when applicable
→ BinaryCIF parse
```

The reconstructed BinaryCIF, current canonical BinaryCIF, raw calls and independent SHA-256 integrity identifiers are preserved per record.

## Structural-fidelity condition

A pass requires:

- equal atom counts;
- equal normalized chain and entity sets;
- atom-identity agreement across the preserved structural context;
- maximum paired coordinate deviation no greater than `1e-6 Å`.

Serialized BinaryCIF equality is not a pass condition. Different BinaryCIF serialization or dictionary encoding can represent the same atom identities and coordinates.

A later RCSB atom-name revision may be reconciled only when stable `_atom_site.id` values remain unique and unchanged, every non-name identity field agrees, the current RCSB audit history documents the later atom-name revision, and all coordinates satisfy the original tolerance. No PDB-specific alias table is used.

For 5KCS, the current RCSB revision dated `2026-07-01` changed four labels in component `6MZ`. Both objects contain 148,945 atoms; stable IDs and all non-name identity fields agree; maximum coordinate deviation is `0 Å`. The record is therefore a structural-fidelity pass, with the nomenclature change retained as provenance.

## Final result

The declared sample remains visible in full:

- selected records: **100**;
- successful reconstructions: **100**;
- canonical structural-fidelity passes: **100/100**;
- final failures: **0**;
- replacement draws: **0**.

## Deterministic verification

```bash
python tools/evidence/finalize_molnft_structural_evidence.py \
  --evidence evidence/article-02/molnft/block-13436937 \
  --verify-deterministic
```

The package establishes reconstruction and declared structural fidelity for the selected sample. It does not establish biological interpretation, experimental validity, clinical utility or completeness of external annotations.
