# Current network-state methodology

Article 02 uses one height-pinned GenesisL1 snapshot. The publication keeps only the latest network/protocol package under `evidence/article-02/network-state/`; `LATEST.json` identifies it.

## Data sources

At one block height, the capture preserves:

- the CometBFT active validator set and voting power;
- Cosmos staking validator records and staking-pool balances;
- native staking-denomination supply;
- every returned validator–delegator relationship;
- current MOLNFT contract counters from EVM JSON-RPC;
- raw provider responses and SHA-256 checksums.

CometBFT voting power is the basis for validator concentration. Staking balances and delegation balances are supporting cross-checks, not substitutes for consensus power.

## Validator metrics

For validator voting-power shares `s₁ … sₙ`, sorted largest first:

- **Top-k share:** cumulative share of the largest `k` validators.
- **One-third coefficient:** smallest `k` whose cumulative share is at least one third.
- **Two-thirds coefficient:** smallest `k` whose cumulative share is at least two thirds; the snapshot also retains strict-threshold variants.
- **HHI:** `10,000 × Σsᵢ²`.
- **Effective validator count:** `1 / Σsᵢ²`.
- **Gini coefficient** and **normalized entropy:** additional concentration descriptors.

Article values are rounded consistently to two decimals. Exact integer state and higher-precision decimal strings remain in `snapshot.json`.

## Stake and delegator metrics

The bonded ratio is the staking pool’s bonded amount divided by native staking-denomination supply at the same height.

Delegation balances are aggregated by delegator address across active validators. The package reports address-level top shares, HHI, effective count and threshold coefficients. `delegations.csv` contains each validator–delegator relationship; `delegators.csv` contains the deterministic address aggregation.

An address is not an entity. Custodians can aggregate many beneficiaries, while one party can control multiple addresses. Validator monikers likewise do not prove independent ownership, key custody, hosting or jurisdiction. The snapshot measures observable ledger distribution only.

## Verification

```bash
cd evidence/article-02/network-state/<current-block>
sha256sum -c SHA256SUMS.txt
```

The publication workflow also runs repository-level consistency checks before committing a new current snapshot.
