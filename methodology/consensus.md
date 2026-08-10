# Consensus, stake and delegator methodology

This methodology defines the measurements used by Article 02 at GenesisL1 block `13,431,722`. The complete raw responses, validator table, delegation relationships and derived address table are published under `evidence/article-02/network-state/block-13431722/`.

## Height pinning and primary data

Consensus distribution is calculated from the CometBFT validator set at one exact block height. Staking-validator records, staking-pool values and bank supply are queried for the same height where the provider exposes historical REST state. The evidence package preserves the unmodified responses, the requested height, block hash, block time, provider URL and cross-checks between consensus power, bonded validator tokens and delegation balances.

CometBFT voting power is the authoritative basis for validator concentration. Staking balances are supporting state and are not substituted for consensus voting power.

## Validator-level metrics

Let active validator voting-power shares, sorted from largest to smallest, be `s_1 ... s_n`, where `sum(s_i) = 1`.

- **Top-k share:** `sum(s_1 ... s_k)`.
- **One-third coefficient:** the smallest `k` whose cumulative share is at least one-third. It is primarily a liveness-oriented measure because the remaining voting power cannot then exceed two-thirds.
- **Strict two-thirds coefficient:** the smallest `k` whose cumulative share is greater than two-thirds, matching CometBFT's commit threshold.
- **HHI:** `10,000 * sum(s_i^2)`.
- **Effective validator count:** `1 / sum(s_i^2)`.
- **Gini coefficient:** the standard Gini coefficient over the voting-power share vector.
- **Normalized entropy:** `-sum(s_i * ln(s_i)) / ln(n)`.

Article values are rounded to two decimals. `snapshot.json` preserves full-precision decimal strings and integer voting power.

## Bonded ratio

The bonded ratio is:

```text
staking_pool.bonded_tokens / bank_module.total_supply(staking_denom)
```

The evidence also publishes `not_bonded_tokens` and the combined staking-pool total. The supply denominator is the native staking denomination at the pinned height, not a market-circulation estimate.

## Delegator-address metrics

Delegation balances are aggregated by delegator address across active validators at the pinned height. The resulting per-address totals are divided by the aggregate active delegation balance to form an address-share vector. The package reports top-1, top-5, top-10 and top-50 shares, HHI, effective address count, Gini coefficient, one-third coefficient and strict two-thirds coefficient.

The published `delegations.csv` contains one row per validator/delegator relationship. `delegators.csv` contains the deterministic aggregation used for the concentration calculations. A third party can reproduce the metrics from those two files without trusting the prose report.

> an address is not an entity. Exchanges, custodians and multisigs aggregate many beneficiaries into one address, and a single party can hold many addresses. Address-level dispersion is neither an upper nor a lower bound on beneficial-owner dispersion — it is a distinct, weaker measurement.

For the same reason, validator monikers do not prove distinct beneficial ownership, signing-key custody, hosting provider, jurisdiction or upgrade control. The measurements describe observable ledger distribution, not a complete social-independence audit.

## Deterministic recomputation

From a clean clone:

```bash
python tools/evidence/upgrade_ws2_metrics.py \
  --snapshot evidence/article-02/network-state/block-13431722/snapshot.json \
  --validators evidence/article-02/network-state/block-13431722/validators.csv \
  --delegators evidence/article-02/network-state/block-13431722/delegators.csv \
  --verify-only
```

The command recalculates every publication metric from the preserved CSV and JSON inputs and fails on any mismatch.
