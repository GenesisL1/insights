# GenesisL1 Insights

Long-form GenesisL1 publications, source graphics, reproducible evidence snapshots, and verification tooling for public scientific infrastructure.

## Article 02

**GenesisL1 and the Next Verifiable Renaissance** connects the history of scientific institutions with verifiable AI, MOLNFT molecular data, CIPNFT-protected disclosure, institutional data sovereignty, measurable consensus decentralization, and the operational utility of L1 coin.

- [Editable article source](content/article-02-next-verifiable-renaissance/article.md)
- [Production HTML](site/insights/genesisl1-decentralization-scientific-renaissance.html)
- [Current validator, delegator and stake evidence](evidence/article-02/network-state/block-13431722/)
- [Randomized MOLNFT reconstruction and fidelity evidence](evidence/article-02/molnft/block-13436937/)
- [Consensus and delegator methodology](methodology/consensus.md)
- [MOLNFT methodology](methodology/molnft.md)

## Current evidence state

### Network distribution — block 13,431,722

The preserved network snapshot records 27 active validators, validator HHI of 547.05, an effective validator count of 18.28, 24,954,378.94 L1 bonded, a 53.37% bonded/native-supply ratio, and address-level concentration calculated from the published delegator CSVs.

### MOLNFT direct-ID audit — block 13,436,937

The MOLNFT sample specification was committed before future seed block 13,436,979 existed. Its block hash selected 100 NFT IDs without replacement from the contract-defined range `1..nextNFTId(B_pin)-1`, comprising 229,271 parent IDs. No GLAST or other off-chain token index was used.

The initial retrieval completed 98 comparisons. Only the two failed predetermined rows were queried again:

- **5KCS / NFT 124713** — Cryo-EM structure of the *Escherichia coli* 70S ribosome in complex with Evernimycin, mRNA, TetM and P-site tRNA;
- **6QFB / NFT 162649** — human ATP citrate lyase holoenzyme in complex with citrate, coenzyme A and Mg·ADP.

At `https://rpca.genesisl1.org`, default `getCombinedData` calls reproduced the provider-level out-of-gas errors. Explicit-gas calls for those same IDs at the same pinned block returned both payloads. The exact `https://rpca.genesisl1.org/api` path returned HTTP 404 and is not a JSON-RPC route. No successful row was requeried and no replacement ID was drawn.

After payload recovery, **6QFB passed** the canonical structural comparator. **5KCS remained the one final mismatch**: reconstructed and current RCSB objects each contained 148,945 atoms and had equal chain and entity sets, but their canonical atom-identity keys differed, so paired coordinate agreement could not be established.

The finalized audit reports:

- **99 of 100 canonical structural-fidelity passes**;
- **1 published final structural mismatch: 5KCS / NFT 124713**;
- **98 of 99 exact normalized coordinate-hash matches among passing records**;
- complete raw requests and responses for the original calls and targeted same-ID requery;
- reconstructed and current RCSB BinaryCIF objects, per-record outcomes, environment versions, manifest, and SHA-256 checksums.

A fidelity pass requires equal atom counts, chain/entity sets, canonical atom identities, and paired Cartesian coordinates within the precommitted `1e-6 Å` tolerance. Serialized-object equality is not calculated. Each object's SHA-256 is retained independently as an integrity identifier only.

## Repository boundaries

- `content/` contains editable editorial and figure sources.
- `site/` contains static files ready to deploy to `genesisl1.com`.
- `evidence/` contains immutable, block-pinned observations used by the article.
- `methodology/` defines measurements, evidence scope, and limitations.
- `tools/` contains graphics, evidence-capture, deterministic finalization, and QA code.

This repository is intentionally separate from [`GenesisL1/web3desk`](https://github.com/GenesisL1/web3desk), which remains the stateless browser dApp for staking, governance, IBC, explorer, and wallet interaction.

## Verify Article 02 evidence

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock

MOLNFT=evidence/article-02/molnft/block-13436937
NETWORK=evidence/article-02/network-state/block-13431722

(cd "$MOLNFT" && sha256sum -c SHA256SUMS.txt)
(cd "$NETWORK" && sha256sum -c SHA256SUMS.txt)

python tools/evidence/upgrade_ws2_metrics_direct.py \
  --snapshot "$NETWORK/snapshot.json" \
  --validators "$NETWORK/validators.csv" \
  --delegators "$NETWORK/delegators.csv" \
  --verify-only

python tools/qa/validate_ws1_ws2_final.py \
  --molnft "$MOLNFT" \
  --network "$NETWORK"
```

Recompute the MOLNFT comparison from preserved local evidence without contacting an RPC endpoint or RCSB:

```bash
python tools/evidence/finalize_molnft_structural_evidence.py \
  --evidence "$MOLNFT" \
  --verify-deterministic
```

The permanent GitHub Actions workflow [Verify Article 02 evidence](.github/workflows/verify-article-02-evidence.yml) runs the same acceptance checks.

## Licensing

Code is MIT licensed. Original editorial content and figures are CC BY 4.0. Original evidence tables and derived metrics are dedicated under CC0 1.0, subject to any rights retained in third-party raw responses. See [`LICENSES.md`](LICENSES.md).
