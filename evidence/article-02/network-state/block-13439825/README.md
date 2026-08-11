# GenesisL1 current state snapshot

**Pinned block:** `13439825`  
**Block time:** `2026-08-11T07:10:47.423119293Z`  
**Block hash:** `D2028CA4D6752110FE8CA3362A6DCAF62CC1647E13824AF6DDDA0B50473EE487`  
**Provider:** `ANODE.TEAM`

| Metric | Result |
|---|---:|
| Active validators | **28** |
| Largest / top-three / top-five share | **9.03% / 23.20% / 35.89%** |
| One-third / two-thirds coefficient | **5 / 11** |
| Validator HHI / effective count | **520.73 / 19.20** |
| Bonded stake | **24,957,676.89 L1** |
| Native supply bonded | **53.36%** |
| Active delegator addresses | **1,371** |
| MOLNFT PDB v2 parents / total tokens | **229,271 / 265,786** |

`validators.csv`, `delegations.csv` and `delegators.csv` contain the complete current tables. `raw/` contains the unmodified provider responses. `snapshot.json` and `molnft-state.json` contain exact machine-readable metrics and contract counters.

Address-level distribution is not beneficial-owner distribution. Current contract counters are separate from the immutable randomized reconstruction audit.

## Verify

```bash
sha256sum -c SHA256SUMS.txt
```
