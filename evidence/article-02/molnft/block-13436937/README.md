# MOLNFT direct NFT-ID randomized fidelity evidence

**Pinned GenesisL1 block:** `13436937`  
**Pinned block hash:** `0xd1827056b63e4dd4ebf2e443a569f9a28ceb442a3f2943f8f30ce03908fcb896`  
**Future seed block:** `13436979`  
**Seed block hash:** `0x523c4b1c9ce0b3a581cff3901a10a32d01163026a43e1582d0d8c23c3dd88d02`  
**Sample-spec precommit:** `3cdd075f86a7ed1230d654cc8d0586bd56555c2a`

## Selection

The sample specification fixed `N = 100` before the seed block existed. The seed is `keccak256(blockhash(B_seed))`. The draw was made without replacement over the direct parent NFT-ID range `1..229271`, defined by pinned `nextNFTId() = 229272`. No GLAST or other off-chain token index was used.

## Final results

| Measure | Result |
|---|---:|
| Selected records | **100** |
| Canonical structural-fidelity passes | **100** |
| Final failures | **0** |
| Exact normalized coordinate-hash matches | **99** |
| Coordinate tolerance | **1e-06 Å** |

Final failure accounting: **none**.

A fidelity pass requires equal atom counts, chain/entity sets, atom-identity agreement and maximum paired coordinate deviation within the precommitted tolerance. A documented later RCSB atom-name revision may be reconciled only under the narrow, evidence-preserving conditions described below. Serialized-object equality is not calculated or reported. The separately recorded SHA-256 value for each object is an integrity identifier only.

## Targeted same-ID requery

Only the failed predetermined draws were queried again; no successful sample row was queried and no replacement ID was drawn. The root `https://rpca.genesisl1.org` URL reported GenesisL1 EVM chain ID 29. Its default calls reproduced the provider-level out-of-gas response, while the same calls at the same pinned block succeeded with the preserved explicit gas allowance. The exact `https://rpca.genesisl1.org/api` path returned HTTP 404 and is not a JSON-RPC route.

| PDB | NFT ID | Structure | Initial result | Same-ID RPCA result |
|---|---:|---|---|---|
| 5KCS | 124713 | Cryo-EM structure of the Escherichia coli 70S ribosome in complex with antibiotic Evernimycin, mRNA, TetM and P-site tRNA at 3.9A resolution | RPC_OUT_OF_GAS | reconstructed |
| 6QFB | 162649 | Structure of the human ATP citrate lyase holoenzyme in complex with citrate, coenzyme A and Mg.ADP | RPC_OUT_OF_GAS | reconstructed |

## Documented RCSB atom-name revisions

A later RCSB atom-name revision is not a structural mismatch. The revision-aware path is accepted only when the current RCSB audit history explicitly lists both atom-name fields, `_atom_site.id` remains unique and unchanged, every non-name identity field agrees, and paired coordinates meet the original tolerance. No PDB-specific alias table is used.

- **5KCS / NFT 124713** — current RCSB revision 2026-07-01 changed 4 atom-name labels (6MZ: O1P→OP2 ×2; 6MZ: O2P→OP1 ×2); all non-name identity fields matched by `_atom_site.id`, with maximum coordinate deviation 0 Å.

## Verify

```bash
sha256sum -c SHA256SUMS.txt
python tools/evidence/finalize_molnft_structural_evidence.py \
  --evidence evidence/article-02/molnft/block-13436937 \
  --verify-deterministic
```
