# MOLNFT direct-ID randomized reconstruction and fidelity methodology

This methodology governs the randomized PDB v2 reconstruction package used by Article 02. It separates three claims that must not be conflated:

1. contract counters describe the size of an on-chain collection;
2. reconstruction proves that selected contract payloads can be recovered as BinaryCIF objects;
3. fidelity testing compares each recovered object with the corresponding canonical RCSB entry.

A successful sample does not prove that every parent record was downloaded. It measures the behavior of a sample selected by a publicly committed procedure.

## Pre-commit and future-block seed

Before the seed block exists, the repository commits only `evidence/article-02/molnft/sample-spec.json`. The specification fixes:

- GenesisL1 chain and EVM chain ID;
- PDB v2 contract address;
- reconstruction height `B_pin`;
- future seed height `B_seed`;
- sample size `N`;
- the direct parent NFT-ID population;
- random-draw algorithm;
- fidelity tolerance and canonical source.

The commit containing the unchanged specification is recorded in `seed-derivation.json` and the evidence manifest.

After `B_seed` is produced:

```text
seed = keccak256(bytes.fromhex(evm_block_hash(B_seed)))
```

The complete EVM block response and block hash are preserved. Because the block did not exist when the specification was committed, a different seed cannot be selected without leaving visible repository history.

## Direct parent NFT-ID population

No GLAST or other off-chain token index is used.

At `B_pin`, the capture calls the PDB v2 contract's `nextNFTId()` function. This contract allocates parent record IDs sequentially from `1`; therefore the announced population is the inclusive range:

```text
1..nextNFTId(B_pin)-1
```

The observed counter, first and last IDs, population size and boundary metadata checks are fixed in `sample-spec.json`. The complete numeric range is persisted as `parent-id-enumeration.csv.gz`, and the pinned `nextNFTId()` request and response are preserved under `raw/enumeration/`.

Only the randomly drawn IDs are queried for `getMetadata(tokenId)` and `getCombinedData(tokenId)`. The PDB identifier used for canonical comparison comes directly from the selected token's on-chain metadata, not from an external lookup service.

This direct range is specific to the present PDB v2 contract's parent-ID allocation. A future contract with non-sequential parent IDs would require a different precommitted enumeration method.

## Random draw

The numeric parent IDs are ordered ascending. Selection is without replacement.

For draw counter `c = 0, 1, ...`, the implementation computes:

```text
r_c = SHA-256(seed || uint64_be(c))
```

The 256-bit integer is mapped to the current remaining-list length using rejection sampling, avoiding modulo bias. The selected ID is removed and the process continues until `N` IDs have been drawn. `drawn-ids.csv` records draw order, token ID and the PDB ID read from contract metadata.

## Reconstruction pipeline

For every drawn NFT ID, the pipeline preserves the exact JSON-RPC requests and responses and applies:

```text
eth_call getMetadata(tokenId) at B_pin
→ read PDB ID directly from contract metadata
→ eth_call getCombinedData(tokenId) at B_pin
→ ABI decode
→ base64 decode
→ gzip decompression when flagged or identified by magic bytes
→ BinaryCIF parse
```

The reconstructed bytes are written to `reconstructed/<PDB_ID>-token-<TOKEN_ID>.bcif`.

Failures are never removed from the sample. Each row in `results.csv` has an outcome and a reason code such as:

- `RPC_TIMEOUT`
- `RPC_ERROR`
- `METADATA_MISSING`
- `METADATA_ID_INVALID`
- `ABI_DECODE_FAIL`
- `BASE64_DECODE_FAIL`
- `CHUNK_MISSING`
- `DECOMPRESS_FAIL`
- `PARSE_FAIL`
- `CANONICAL_UNAVAILABLE`
- `FIDELITY_MISMATCH`
- `SUCCESS`

## Canonical source and loss model

The canonical comparator is the RCSB BinaryCIF object retrieved from `https://models.rcsb.org/<PDB_ID>.bcif`. Retrieval URL, UTC time, HTTP metadata and SHA-256 are preserved, and canonical bytes are stored under `canonical/`.

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
- direct NFT-ID population and counter;
- tolerances;
- byte-identical count;
- wall-clock start and end;
- Python version;
- exact library versions;
- RPC endpoint and provider;
- canonical endpoint;
- pre-commit SHA and seed-block hash.

A clean `100/100` is accepted only if all 100 predetermined rows, metadata calls, payload calls and fidelity comparisons are present. Any failure remains visible in `results.csv` and the summary.

## Deterministic recomputation

Capture depends on external RPC and RCSB availability. Recalculation does not. Once raw calls, reconstructed objects and canonical objects are preserved, the following mode recomputes `results.csv`, `summary.json`, `MANIFEST.json` and `SHA256SUMS.txt` from local evidence in deterministic order:

```bash
python tools/evidence/capture_molnft_direct_randomized_sample.py \
  --recompute evidence/article-02/molnft/block-<B_pin>
```

The environment is pinned in `requirements.lock`. The summary records the realized interpreter and package versions.

## Scope

The randomized package establishes reconstruction and canonical fidelity for its declared sample at one pinned GenesisL1 height. It does not establish biological correctness, clinical validity, completeness of external annotations, or independent beneficial ownership of network operators. Those require separate scientific and institutional evidence.
