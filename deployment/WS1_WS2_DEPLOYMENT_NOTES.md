# Article 02 WS-1 / WS-2 deployment notes

The publication files under `site/` include the finalized direct NFT-ID MOLNFT randomized audit and the block-13,431,722 concentration metrics.

Deploy:

- `site/insights/` to `/insights/`
- `site/decentralization/` to `/decentralization/`
- merge `deployment/sitemap-entry.xml`
- preserve the redirects supplied in this directory
- purge cached Article 02 HTML and social/hero assets

Expected evidence-dependent Article 02 values:

- MOLNFT: 98 of 100 canonical structural-fidelity passes; 2 preserved RPC out-of-gas failures; 97 of 98 exact normalized coordinate-hash matches; no off-chain token index
- Validator HHI: 547.05
- Effective validator count: 18.28
- Bonded/native-supply ratio: 53.37%
- Active-delegator-address top-5 share: 18.09%
- Effective active-delegator-address count: 56.26

Verify the repository evidence before deployment with `.github/workflows/verify-article-02-evidence.yml` or the commands in the root README.
