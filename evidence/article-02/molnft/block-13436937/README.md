# MOLNFT direct NFT-ID randomized fidelity evidence

**Pinned GenesisL1 block:** `13436937`  
**Pinned block hash:** `0xd1827056b63e4dd4ebf2e443a569f9a28ceb442a3f2943f8f30ce03908fcb896`  
**Future seed block:** `13436979`  
**Seed block hash:** `0x523c4b1c9ce0b3a581cff3901a10a32d01163026a43e1582d0d8c23c3dd88d02`  
**Sample-spec precommit:** `3cdd075f86a7ed1230d654cc8d0586bd56555c2a`

## Selection

The sample specification fixed `N = 100` before the seed block existed. The seed is `keccak256(blockhash(B_seed))`. The draw was made without replacement over the direct parent NFT-ID range `1..229271`, defined by pinned `nextNFTId() = 229272`. No GLAST or other off-chain token index was used.

## Results

| Measure | Result |
|---|---:|
| Selected records | **100** |
| Canonical-fidelity passes | **98** |
| Published failures | **2** |
| Exact normalized coordinate-hash matches | **97** |
| Byte-identical current RCSB BinaryCIF files | **0** |
| Coordinate tolerance | **1e-06 Å** |

Failure accounting: **2 RPC_OUT_OF_GAS**.

A fidelity pass requires equal atom counts, chain/entity sets, canonical atom identities and maximum paired coordinate deviation within the precommitted tolerance. Exact coordinate hashes and complete-file hashes are reported separately; they are not used to replace the tolerance test. BinaryCIF serialization and non-coordinate metadata may differ between the historical on-chain object and the current RCSB response even when the canonicalized structure agrees.

## Verify

```bash
sha256sum -c SHA256SUMS.txt
python tools/evidence/finalize_molnft_direct_evidence.py   --evidence evidence/article-02/molnft/block-13436937   --verify-byte-for-byte
```
