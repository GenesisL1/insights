# Article 02 evidence

The current validator, delegator and bonded-stake package is pinned to GenesisL1 block `13,431,722` with block hash `DB6953F971F56420374FAF84FEE98A1BFB280A723462F0D05774C76BCDD6535A`. The MOLNFT reconstruction package remains pinned to its original block because it supports a separate scientific claim.

- [`network-state/block-13431722/`](network-state/block-13431722/) — current CometBFT voting-power distribution, all registered validators, complete returned delegation relationships, staking-pool state, native supply, raw responses and SHA-256 checksums.
- [`consensus/block-13412747/`](consensus/block-13412747/) — historical consensus-only snapshot used by the previous Article 02 edition.
- [`molnft/block-13412747/`](molnft/block-13412747/) — contract counters, raw JSON-RPC, runtime-code hashes, eight predeclared reconstructed BinaryCIF objects and SHA-256 checksums.

These directories are immutable observations. Publication prose rounds percentages to two decimal places; the snapshots retain exact state.
