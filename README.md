# GenesisL1 Insights

Long-form GenesisL1 publications, source graphics, reproducible evidence snapshots, and verification tooling for public scientific infrastructure.

## Article 02

**GenesisL1 and the Next Verifiable Renaissance** connects the history of scientific institutions with verifiable AI, MOLNFT molecular data, CIPNFT-protected disclosure, institutional data sovereignty, measurable consensus decentralization, and the operational utility of L1 coin.

- [Editable article source](content/article-02-next-verifiable-renaissance/article.md)
- [Production HTML](site/insights/genesisl1-decentralization-scientific-renaissance.html)
- [Current validator, delegator and stake evidence](evidence/article-02/network-state/block-13431705/)
- [MOLNFT evidence](evidence/article-02/molnft/block-13412747/)
- [Consensus methodology](methodology/consensus.md)
- [MOLNFT methodology](methodology/molnft.md)

## Repository boundaries

- `content/` contains editable editorial and figure sources.
- `site/` contains static files ready to deploy to `genesisl1.com`.
- `evidence/` contains immutable, block-pinned observations used by the article.
- `methodology/` defines measurements, evidence scope, and limitations.
- `tools/` contains graphics, evidence-capture, and QA code.

This repository is intentionally separate from [`GenesisL1/web3desk`](https://github.com/GenesisL1/web3desk), which remains the stateless browser dApp for staking, governance, IBC, explorer, and wallet interaction.

## Rebuild and verify

```bash
python -m pip install -r requirements.txt
python tools/graphics/create_graphics.py
python tools/qa/validate_repository.py
python tools/qa/validate_svg_layout.py
```

The current network-state evidence is pinned to GenesisL1 block `13,431,705`. The MOLNFT reconstruction package remains independently pinned to block `13,412,747`.

## Licensing

Code is MIT licensed. Original editorial content and figures are CC BY 4.0. Original evidence tables and derived metrics are dedicated under CC0 1.0, subject to any rights retained in third-party raw responses. See [`LICENSES.md`](LICENSES.md).
