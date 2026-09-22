# GenesisL1 Insights

Source publications, deployable pages and reproducible evidence for GenesisL1 scientific infrastructure.

## Publications

- [GenesisL1: The DeSci Layer 1 Where Scientific Data, Verifiable AI and Digital Rights Become One System](content/initial/article.md)
- [GenesisL1 and the Next Verifiable Renaissance](content/renaissance/article.md)
- [GenesisL1 Stake Distribution and Decentralization](content/stake-distribution/article.md)

## Current evidence

The latest stake and delegation package is pinned to GenesisL1 block **13,690,968**.

- **33** active validators
- largest validator share: **9.27%**
- top-five validator share: **27.38%**
- **25,555,236.79 L1** bonded
- **1,402** active delegator addresses
- validator HHI: **373.47**
- effective validator count: **26.78**

Historical snapshots are preserved for longitudinal comparison.

[Open the current evidence package](evidence/stake-distribution/block-13690968)

## Verify

```bash
cd evidence/stake-distribution/block-13690968
sha256sum -c SHA256SUMS.txt
```

## Preserved evidence

- `evidence/stake-distribution/history/` — the August 11, August 15 and August 29 stake snapshots (blocks 13,439,825 / 13,466,645 / 13,553,561), kept for longitudinal comparison.
- `evidence/article-02/molnft/block-13436937` — the randomized MOLNFT reconstruction audit (100 of 100 structural-fidelity passes, 853 checksummed files); `methodology/molnft.md` describes it.
- `evidence/article-02/network-state/` and `evidence/article-02/delegation-state/` — the original August network and delegation snapshots at the paths earlier publications cite.

## Licensing

Code is MIT licensed; original editorial text and figures are CC BY 4.0; original derived evidence tables and metrics are CC0 1.0. See [`LICENSES.md`](LICENSES.md).
