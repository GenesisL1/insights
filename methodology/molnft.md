# MOLNFT randomized reconstruction and fidelity methodology

This methodology governs the randomized PDB v2 reconstruction package used by Article 02. It separates three claims that must not be conflated:

1. contract counters describe the size of an on-chain collection;
2. reconstruction proves that selected contract payloads can be recovered as BinaryCIF objects;
3. fidelity testing compares each recovered object with the corresponding canonical RCSB entry.

A successful sample does not prove that every parent record was downloaded. It estimates the behavior of a selection drawn by a publicly committed procedure.

## Pre-commit and future block seed

Before the seed block exists, the repository commits only `evidence/article-02/molnft/sample-spec.json`. The specification fixes:

- GenesisL1 chain and EVM chain ID;
- PDB v2 contract address;
- reconstruction height `B_pin`;
- future seed height `B_seed`;
- sample size `N`;
- parent-ID enumeration method;
- random-draw algorithm;
- fidelity tolerance and canonical source.

The commit containing the unchanged specification is recorded in `seed-derivation.json` and the evidence manifest.

After `B_seed` is produced:

```text
seed = keccak256(bytes.fromhex(evm_block_hash(B_seed)))
```

The complete EVM block response and block hash are preserved. Because the block did not exist when the specification was committed, a different seed cannot be selected without leaving a visible repository history.

## Parent-ID enumeration

The draw is not over the integer interval `1..parent_count`.

The capture reconstructs the actual parent-token index at `B_pin` from the PDB v2 contract's parent-mint event or another explicit contract index described in `sample-spec.json`. Event decoding uses the verified contract ABI when available. The resulting `(token_id, pdb_id)` set is sorted deterministically, persisted as `parent-id-enumeration.csv.gz`, and reconciled against the contract's pinned parent counter. Duplicate token IDs, duplicate PDB identifiers, malformed identifiers or a counter mismatch are fatal errors.

Raw enumeration responses are preserved in compressed form and included in the SHA-256 manifest.

## Random draw

The enumerated rows are ordered by numeric token ID and uppercase PDB identifier. Selection is without replacement.

For draw counter `c = 0, 1, ...`, the implementation computes:

```text
r_c = SHA-256(seed || uint64_be(c))
```

The 256-bit integer is mapped to the current remaining-list length using rejection sampling, avoiding modulo bias. The selected row is removed and the process continues until `N` rows have been drawn. `drawn-ids.csv` records draw order, token ID and PDB ID.

## Reconstruction pipeline

For every drawn record, the pipeline preserves the exact JSON-RPC request and response and applies:

```text
eth_call at B_pin
→ ABI decode
→ base64 decode
→ gzip decompression when flagged or identified by magic bytes
→ BinaryCIF parse
```

The reconstructed bytes are written to `reconstructed/<PDB_ID>-token-<TOKEN_ID>.bcif`.

Failures are never removed from the sample. Each row in `results.csv` has an outcome and a reason code such as:

- `RPC_TIMEOUT`
- `RPC_ERROR`
- `ABI_DECODE_FAIL`
- `BASE64_DECODE_FAIL`
- `CHUNK_MISSING`
- `DECOMPRESS_FAIL`
- `PARSE_FAIL`
- `CANONICAL_UNAVAILABLE`
- `FIDELITY_MISMATCH`
- `SUCCESS`

## Canonical source and loss model

The canonical comparator is the RCSB BinaryCIF object retrieved from `https://models.rcsb.org/<PDB_ID>.bcif`. Retrieval URL, UTC time, HTTP metadata and SHA-256 are preserved, and the canonical bytes are stored under `canonical/`.

PDB v2 is intended to preserve the complete RCSB BinaryCIF payload after reversible base64 and gzip transformations. The declared loss model is therefore **lossless** for the stored BinaryCIF bytes. Fidelity is evaluated after deterministic atom ordering normalization, not by assuming the source and reconstruction arrive in the same row order.

For each record the pipeline reports:

| Check | Pass condition |
|---|---|
| BinaryCIF parse | both objects parse and contain `_atom_site` |
| Atom count | equal `_atom_site` row counts |
| Chain IDs | equal normalized `label_asym_id` sets |
| Entity IDs | equal normalized `label_entity_id` sets |
| Atom identity | equal canonical atom-key multisets after sorting |
| Coordinates | maximum paired Euclidean deviation `≤ 1e-6 Å` |
| Coordinate hash | SHA-256 of the canonicalized coordinate stream is equal |
| Complete-byte hash | reported for both objects; equality is additionally recorded |

The canonical atom key includes model number, entity ID, label and author chain IDs, residue identifiers, insertion code, atom name, alternate-location identifier and element where available. Missing CIF values (`.` and `?`) are normalized to an empty string. Coordinates are serialized in sorted atom-key order as IEEE-754 float64 big-endian triples for the coordinate hash.

If a future contract intentionally introduces quantization or metadata removal, its bounded loss model must be committed in a new specification before sampling. The present run does not silently relax exactness.

## Failure accounting

`summary.json` reports:

- declared `N`;
- successful reconstructions;
- failures by reason code;
- fidelity successes and mismatches;
- tolerances;
- byte-identical count;
- wall-clock start and end;
- Python version;
- exact library versions;
- RPC endpoint and provider;
- canonical endpoint;
- pre-commit SHA and seed-block hash.

A clean `100/100` is accepted only if all 100 predetermined rows, raw calls and fidelity comparisons are present. Any failure remains visible in `results.csv` and the summary.

## Deterministic recomputation

Capture depends on external RPC and RCSB availability. Recalculation does not. Once raw calls, reconstructed objects and canonical objects are preserved, the following mode recomputes `results.csv`, `summary.json`, `MANIFEST.json` and `SHA256SUMS.txt` from local evidence in deterministic order:

```bash
python tools/evidence/capture_molnft_randomized_sample.py \
  --recompute evidence/article-02/molnft/block-<B_pin>
```

The environment is pinned in `requirements.lock`. The summary records the realized interpreter and package versions.

## Scope

The randomized package establishes reconstruction and canonical fidelity for its declared sample at one pinned GenesisL1 height. It does not establish biological correctness, clinical validity, completeness of external annotations, or independent beneficial ownership of network operators. Those require separate scientific and institutional evidence.
