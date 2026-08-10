# MOLNFT direct-ID randomized reconstruction and fidelity methodology

This methodology governs the randomized PDB v2 reconstruction package used by Article 02. It keeps three claims separate:

1. contract counters describe the size of the on-chain collection;
2. reconstruction proves that a selected contract payload can be recovered as a BinaryCIF object;
3. fidelity testing compares the recovered molecular structure with the corresponding current RCSB BinaryCIF entry.

A randomized sample measures the selected population at one pinned height. It does not imply that every parent record was downloaded in the run.

## Precommit and future-block seed

Before the seed block existed, the repository committed only `evidence/article-02/molnft/sample-spec.json`. That specification fixed:

- GenesisL1 and EVM chain IDs;
- PDB v2 contract address;
- reconstruction height `B_pin`;
- future seed height `B_seed`;
- sample size `N`;
- direct parent NFT-ID population;
- random-draw algorithm;
- canonical source and coordinate tolerance.

The isolated commit SHA is recorded in `seed-derivation.json` and `MANIFEST.json`.

After `B_seed` was produced, the seed was derived as:

```text
seed = keccak256(bytes.fromhex(evm_block_hash(B_seed)))
```

The exact EVM block response and hash are preserved. A different seed or draw cannot be substituted without leaving a visible change in repository history.

## Direct parent NFT-ID population

**No GLAST or other off-chain token index is used.**

At `B_pin`, the capture calls the PDB v2 contract's `nextNFTId()` function. The contract allocates parent records sequentially from NFT ID `1`, so the announced draw population is:

```text
1..nextNFTId(B_pin)-1
```

The pinned counter, first and last IDs, population size and boundary metadata checks are fixed in `sample-spec.json`. The complete numeric range is saved as `parent-id-enumeration.csv.gz`; the exact `nextNFTId()` request and response are preserved under `raw/enumeration/`.

Only the randomly drawn IDs are queried through `getMetadata(tokenId)` and `getCombinedData(tokenId)`. The PDB identifier used for canonical comparison comes directly from the selected token's on-chain metadata.

This range rule is specific to the deployed PDB v2 contract. A future contract with non-sequential parent IDs would require a different enumeration method committed before its seed block.

## Random draw

The NFT IDs are ordered numerically and sampled without replacement. For draw counter `c = 0, 1, ...`:

```text
r_c = SHA-256(seed || uint64_be(c))
```

The 256-bit value is mapped to the current remaining-list length with rejection sampling, preventing modulo bias. The selected ID is removed before the next draw. `drawn-ids.csv` records draw order, NFT ID and the PDB ID read from contract metadata.

## Reconstruction pipeline

For every drawn NFT ID, the capture preserves the exact JSON-RPC request and response and applies:

```text
eth_call getMetadata(tokenId) at B_pin
→ read PDB ID from contract metadata
→ eth_call getCombinedData(tokenId) at B_pin
→ ABI decode
→ base64 decode
→ gzip decompress when flagged or identified by magic bytes
→ require one BinaryCIF MessagePack object with dataBlocks
→ parse BinaryCIF
```

The reconstructed object is saved as `reconstructed/<PDB_ID>-token-<TOKEN_ID>.bcif`.

Failures are not redrawn or removed. Each selected row receives an outcome and reason code, including:

- `RPC_TIMEOUT`
- `RPC_OUT_OF_GAS`
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

## Canonical comparison and storage model

The comparator is the RCSB BinaryCIF retrieved from `https://models.rcsb.org/<PDB_ID>.bcif`. Retrieval URL, time, response metadata and SHA-256 are preserved; the canonical bytes are stored under `canonical/`.

The on-chain transformation—base64 plus gzip—is reversible and therefore lossless relative to the BinaryCIF object minted into the contract. A current RCSB BinaryCIF response may nevertheless have different serialization, compression-independent metadata or dictionary encoding from the historical object while representing the same atom identities and coordinates. For that reason, complete-file byte equality is reported but is not treated as the molecular-fidelity criterion.

For every comparable record the pipeline reports:

| Dimension | Fidelity condition |
|---|---|
| BinaryCIF parse | both objects parse and contain `_atom_site` |
| Atom count | equal `_atom_site` row counts |
| Chain IDs | equal normalized `label_asym_id` sets |
| Entity IDs | equal normalized `label_entity_id` sets |
| Atom identities | equal canonical atom-key sequences after sorting |
| Coordinates | maximum paired Euclidean deviation `≤ 1e-6 Å` |
| Coordinate hashes | SHA-256 values recorded for both normalized coordinate arrays; exact equality reported separately |
| Complete-file hashes | SHA-256 values recorded for both serialized BinaryCIF objects; exact equality reported separately |

A **fidelity pass** requires the first five structural comparisons and the precommitted coordinate-tolerance condition. Exact coordinate-hash equality is an additional reproducibility statistic, not a replacement for the declared tolerance. This matters because IEEE-754 representations can differ by signed zero or sub-tolerance rounding while the measured Cartesian deviation remains zero or far below `1e-6 Å`.

The canonical atom key includes model number, entity ID, label and author chain IDs, residue identifiers, insertion code, atom name, alternate-location identifier and element where available. Missing CIF values (`.` and `?`) are normalized to an empty string. Coordinates are ordered by that key. For exact coordinate hashes, signed zero is normalized and XYZ values are serialized as big-endian IEEE-754 float64 triples.

If a future contract deliberately quantizes coordinates or drops structural fields, the bounded loss model must be committed in a new sample specification before selection. The present run does not change its tolerance after observing results.

## Failure accounting

`summary.json` reports:

- declared `N`;
- direct parent NFT-ID population and counter;
- successful fidelity comparisons;
- failures by reason code;
- coordinate-tolerance passes;
- exact coordinate-hash matches;
- byte-identical complete-file count;
- wall-clock start and end;
- Python and exact library versions;
- RPC and canonical endpoints;
- precommit SHA and seed-block hash.

A result is accepted only when every preselected row remains visible. Provider-level failures are evidence about the measured retrieval path and are not silently replaced by another draw.

## Deterministic local finalization

Network capture depends on the archive RPC and RCSB being reachable. Once raw calls, reconstructed objects and canonical objects are preserved, the publication result is reproducible without network access:

```bash
python tools/evidence/finalize_molnft_direct_evidence.py \
  --evidence evidence/article-02/molnft/block-<B_pin> \
  --verify-byte-for-byte
```

The command recomputes `results.csv`, `summary.json`, `README.md`, `MANIFEST.json` and `SHA256SUMS.txt` in deterministic order. The environment is pinned in `requirements.lock` and the realized versions are recorded in the summary.

## Scope

The package establishes reconstruction and canonical structural fidelity for the declared randomized sample at one pinned GenesisL1 height. It does not establish biological interpretation, experimental validity, clinical utility, completeness of external annotations or beneficial ownership of network participants. Those are separate questions requiring separate evidence.
