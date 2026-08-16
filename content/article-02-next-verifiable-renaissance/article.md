# GenesisL1: Public Infrastructure for Verifiable AI and Sovereign Science

*A current, evidence-backed account of public ownership, network decentralization, molecular-data integrity and institution-operated scientific infrastructure.*

Scientific computing is becoming more capable, more autonomous and more difficult to audit. A result may depend on a dataset version, model checkpoint, execution environment, access right and sequence of machine actions distributed across services that can later change or disappear.

GenesisL1 is designed to make that computational lineage durable. It is a live public Layer 1 where scientific objects, models, rights, transactions and governance can share one independently verifiable history.

The central proposition is practical: **institutions should be able to verify scientific computation without surrendering control of the data that must remain private.**

## Public ownership is part of the architecture

GenesisL1 launched without a token sale, private round, venture allocation, founder allocation, team allocation, advisor allocation or private unlock schedule. Its disclosed bootstrap distributor retained no allocation after the public one-to-one transition. <sup><a href="#source-1">1</a></sup>

That origin does not by itself guarantee decentralization. It does remove a structural layer of private ownership and future insider vesting beneath the protocol. For scientific infrastructure, that matters: the system preserving evidence should disclose not only how it reaches consensus, but also whose reserved economic claims sit behind it.

The network’s community pool provides a second public mechanism. Protocol-funded resources can be allocated through on-chain governance for shared infrastructure, research tooling and ecosystem development. This is public patronage with a visible ledger rather than a private cap table.

## Current network state

<!-- CURRENT_NETWORK_BEGIN -->
The Article 02 evidence is now deliberately **longitudinal**. The August 11 snapshot remains preserved as a historical measurement rather than being overwritten; a second delegation-focused snapshot records the network four days later. Together they show why decentralization is better treated as a dynamic, reproducible process than as a permanent label.

At GenesisL1 block **13,466,645**, dated **August 15, 2026**, the active consensus set contained **29 validators** out of a protocol maximum of 50. The largest validator held **8.69%** of voting power; the top three held **22.62%**, the top five **31.78%**, and the top ten **49.73%**. **6 validators** were required to reach one third of voting power and **16** to reach two thirds. Validator HHI was **426.59**, corresponding to an effective validator count of **23.44**. <sup><a href="#source-2b">2b</a></sup>

| Latest observable state — block 13,466,645 | Result |
|---|---:|
| Active consensus validators | **29 / 50** |
| Largest / top-three / top-five share | **8.69% / 22.62% / 31.78%** |
| Validators required for one third / two thirds | **6 / 16** |
| Validator HHI / effective validator count | **426.59 / 23.44** |
| Bonded stake / native supply bonded | **24,794,964.00 L1 / 52.94%** |
| Active delegator addresses / relationships | **1,372 / 2,099** |
| Largest / top-five / top-ten active-delegator share | **5.78% / 18.26% / 29.76%** |
| Active-delegator HHI / effective address count | **177.68 / 56.28** |
| Delegator one-third / two-thirds coefficients | **12 / 35** |

The delegation layer is visible separately from validator voting power. At the latest snapshot, **1,372 addresses** delegated to active validators across **2,099 active delegation relationships**; **224** addresses delegated across multiple active validators. The largest active-delegator address represented **5.78%** of active delegated stake, while the top five represented **18.26%**, the top ten **29.76%**, and the top 25 **55.08%**. Active-delegator HHI was **177.68**, with an effective address count of **56.28**.

An address is not an entity. Exchanges, custodians and multisigs can aggregate many beneficiaries into one address, while one party can control many addresses. Address-level dispersion is therefore neither an upper nor a lower bound on beneficial-owner dispersion; it is a distinct, weaker measurement of observable ledger distribution.

### Decentralization as an observed trajectory

| Pinned measurement | Active validators | Largest | Top 5 | ⅓ coefficient | ⅔ coefficient | HHI | Effective validators |
|---|---:|---:|---:|---:|---:|---:|---:|
| July whitepaper reference | **20** | **13.09%** | **51.07%** | **3** | **8** | — | — |
| Aug. 11 · block 13,439,825 | **28** | **9.03%** | **35.89%** | **5** | **11** | **520.73** | **19.20** |
| Aug. 15 · block 13,466,645 | **29** | **8.69%** | **31.78%** | **6** | **16** | **426.59** | **23.44** |

From the whitepaper reference to the latest pinned state, the active set expanded from **20 to 29 validators**; the largest-validator share declined from **13.09% to 8.69%** and the top-five share from **51.07% to 31.78%**. The one-third cohort widened from **3 to 6 validators**, while the two-thirds cohort expanded from **8 to 16**. Between the two reproducible August snapshots, top-five share moved from **35.89% to 31.78%**, HHI from **520.73 to 426.59**, and effective validator count from **19.20 to 23.44**.

These are measurements, not guarantees about future topology or organizational independence. Their value is precisely that they can be measured again. The repository preserves both August snapshots, raw responses, complete validator and delegation tables, calculations and SHA-256 manifests so later states can be compared without erasing earlier ones.
<!-- CURRENT_NETWORK_END -->

This is a snapshot, not a permanent label. Validator power, delegations and supply change continuously. The repository preserves the pinned block, raw responses, complete CSV tables, exact calculations and checksums so the published figures can be reproduced rather than trusted as screenshots.

## A common state for data, models, rights and agents

GenesisL1 combines several primitives that are usually separated across private databases and mutable APIs.

### MOLNFT: molecular records with durable identity

<!-- CURRENT_MOLNFT_BEGIN -->
At the current evidence block, the MOLNFT PDB v2 contract reported **229,271 parent molecular records** and **265,786 total ERC-721 tokens**, including **36,515 child chunks** used to extend larger payloads. Legacy PDB v1 and AlphaFold/Swiss-Prot v1 collections are reported separately because they represent a different storage generation and may overlap scientifically; they are not added to the PDB v2 parent count as one corpus total. <sup><a href="#source-2">2</a></sup>

A separate randomized audit tested reconstruction fidelity rather than merely reading counters. The sample specification records an announcement time of 19:15:22Z, before block 13,436,979 existed; that time is self-recorded and not independently timestamped. What any third party can verify from the published record is that the draw is fully determined by the hash of block 13,436,979 and the specification's contents. The resulting 100 IDs were drawn without replacement from the pinned PDB v2 parent range, with no off-chain token index and no replacement draws. The finalized result was **100 successful reconstructions, 100 of 100 canonical structural-fidelity passes and zero final failures**. <sup><a href="#source-3">3</a></sup>

One sampled record, 5KCS, had 4 atom-name labels changed by a documented later RCSB nomenclature revision. Stable atom IDs, every non-name identity field and all **148,945 Cartesian coordinates** remained aligned, with maximum deviation of **0 Å**. It is therefore recorded as a structural-fidelity pass, with the nomenclature revision retained transparently as provenance—not as a second score.
<!-- CURRENT_MOLNFT_END -->

The important distinction is between **identity and storage syntax**. A scientific object can remain the same molecular structure even when an external reference archive later normalizes a label. The audit therefore evaluates declared structural criteria—atom counts, chain and entity sets, atom identity and coordinate agreement—while preserving the exact reconstructed and canonical objects for independent inspection.

### Model NFTs and GL1F: replayable computational instruments

Model NFTs can bind a model’s identity, serialized parameters, access rules and invocation history. GL1F adds deterministic on-chain inference for supported model classes, so the same model bytes, input and execution rules can produce a replayable result across independent nodes. <sup><a href="#source-4">4</a></sup>

This does not make a model scientifically correct. It makes the computational instrument identifiable: another party can determine which model was used, under which rules, and what the network recorded.

### CIPNFT: protected disclosure with public provenance

CIPNFT provides a rights layer for confidential scientific assets. Its public implementation encrypts content client-side, records ciphertext and provenance on-chain, and supports recipient-bound disclosure without requiring a private application server to hold the scientific plaintext. <sup><a href="#source-5">5</a></sup>

Public verification and confidentiality are not opposites. The ledger can preserve object identity, rights, commitments and authorized outputs while raw genomes, clinical records, proprietary methods and personal identifiers remain under institutional custody.

### AI agents: action under inspectable rules

AI agents can discover registered objects, verify model and rights metadata, invoke deterministic computation and record authorized actions against the same public history. The value is not autonomy alone; it is **accountable autonomy**—machine action whose inputs, permissions and outputs can be inspected after the interface that initiated it has disappeared.

## Institutional sovereignty without isolation

A national genome program, public biobank, university or health-research authority should not need to upload sensitive source data to a common public database in order to participate in a shared verification system.

GenesisL1 supports a three-layer boundary:

1. **Sovereign custody.** Raw data, identities, consent records, encryption keys and internal access systems remain local.
2. **Protected disclosure.** CIPNFT can carry encrypted assets, rights and recipient-bound access when information must cross institutional boundaries.
3. **Common verification.** Public objects, commitments, model and method identities, authorized outputs and transaction history can be independently verified from any node.

An institution can therefore run an approved model within its own environment, publish only a permitted aggregate or commitment, and tie that output to a specific model, method and authorization record. Another institution can verify the lineage without receiving the underlying personal data.

This is **local custody, selective disclosure and shared proof**.

## What the ledger proves—and what it does not

On-chain verification can establish:

- which object, model, code, account and rights state were referenced;
- which transaction and execution path produced a recorded output;
- whether the same public state and deterministic rules reproduce that output;
- when a claim or asset entered the shared history and what later changed.

It cannot establish scientific truth by itself. Biological validity, clinical utility and causal interpretation still require appropriate datasets, experimental design, independent reproduction, peer review and, where applicable, laboratory or clinical testing.

The ledger is an evidence and coordination layer—not a substitute for science.

## L1 coin: protocol resource, not a private claim

L1 coin is the native resource used for transaction fees, smart-contract execution, staking security, governance and the community pool. Scientific applications may also use it for authorized access, model invocation or machine-to-machine settlement. <sup><a href="#source-1">1</a></sup>

L1 coin is not equity, a revenue claim or a promise of return. Its role is operational: it meters and secures the public protocol.

## A concrete institutional operating model

Participation should mean operation rather than endorsement. An institution can contribute by:

- running an independently controlled validator;
- preserving an archive node and local indexer;
- verifying one bounded scientific workflow from explicit inputs to authorized output;
- defining a memorandum covering custody, security, scientific scope, publication and continuity.

The objective is not to place every scientific byte on a blockchain. It is to make the identity, provenance, rights and permitted computational history of important scientific objects durable enough to survive individual applications, vendors and sponsors.

## The verifiable scientific renaissance

The printing press made knowledge portable. Scientific journals made claims inspectable. Networked computing made collaboration global. The next step is to make computational scientific history independently verifiable.

GenesisL1 brings public ownership, measurable consensus, molecular-data provenance, deterministic model execution, encrypted rights and accountable agents into one live scientific Layer 1.

The result is not a promise that every claim is true. It is a stronger foundation for discovering **what was used, who was authorized, what was executed and whether another institution can verify it**.

---

## Frequently asked questions

### What is the current GenesisL1 validator state?

At the latest delegation-focused snapshot, GenesisL1 had 29 active consensus validators. The largest held 8.69% of voting power; 6 validators were required to reach one third and 16 to reach two thirds. The earlier block-13,439,825 snapshot remains preserved as a historical comparison point.

### What did the randomized MOLNFT audit find?

The published 100-record audit produced 100 successful reconstructions, 100 canonical structural-fidelity passes, zero final failures and no replacement draws. The documented 5KCS atom-name revision is preserved as provenance and does not represent structural loss.

### Can sensitive scientific data remain local?

Yes. Raw data, identities, consent records and keys can remain under local institutional custody while the shared ledger carries permitted commitments, encrypted assets, model and method identities, rights and authorized outputs.

### Is blockchain verification the same as scientific validation?

No. Blockchain verification establishes the computational and rights record. Scientific validity still depends on domain evidence, experimental design, reproduction, peer review and appropriate laboratory or clinical validation.

### What is L1 coin used for?

L1 coin pays network fees, meters smart-contract execution, secures consensus through staking, participates in governance and supports the community pool. It is not equity or a promise of return.

## Sources and verification

<!-- CURRENT_SOURCES_BEGIN -->
1. <span id="source-1"></span>**GenesisL1 Technical Whitepaper, Version 1.0, July 2026.** Public distribution, protocol architecture, L1 coin utility, governance and institutional operation. [Whitepaper ↗](https://genesisl1.com/whitepaper.pdf)
2. <span id="source-2"></span>**GenesisL1 preserved network and protocol-state snapshot at block 13,439,825.** Raw CometBFT, Cosmos and EVM responses; complete validator and delegation tables; current MOLNFT counters; calculations and SHA-256 manifest. [Current evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/network-state/block-13439825)
2b. <span id="source-2b"></span>**GenesisL1 latest delegation-focused snapshot at block 13,466,645.** Raw validator and delegation responses, complete tables, concentration metrics and SHA-256 manifest. [Latest delegation evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/delegation-state/block-13466645)
3. <span id="source-3"></span>**GenesisL1 randomized MOLNFT reconstruction evidence at block 13,436,937.** Published sample specification, future-block seed, direct NFT-ID calls, reconstructed and canonical BinaryCIF objects, per-record outcomes and checksums. [Audit evidence ↗](https://github.com/GenesisL1/insights/tree/main/evidence/article-02/molnft/block-13436937)
4. <span id="source-4"></span>**GenesisL1 Forest / GL1F.** Deterministic model representation and inference tooling. [Source ↗](https://github.com/GenesisL1/Forest) · [Technical paper ↗](https://gl1f.com/GL1F.pdf)
5. <span id="source-5"></span>**GenesisL1 CIPNFT.** Client-side encryption, on-chain ciphertext provenance and recipient-bound disclosure. [Source ↗](https://github.com/GenesisL1/cipnft)
6. **CometBFT consensus specification, v0.38.** Voting-power and commit-threshold model. [Specification ↗](https://docs.cometbft.com/v0.38/spec/consensus/consensus)
<!-- CURRENT_SOURCES_END -->

<!-- CURRENT_MEASUREMENT_BEGIN -->
**Measurement note.** Current validator, delegator, stake and MOLNFT counter figures are pinned to GenesisL1 block 13,439,825. Publication comparisons use two-decimal displayed values consistently; exact integers and higher-precision calculations remain in the machine-readable snapshot. The randomized MOLNFT reconstruction audit is a separate immutable experiment pinned to block 13,436,937.
<!-- CURRENT_MEASUREMENT_END -->

This article is informational and published by GenesisL1 about GenesisL1. Nothing here is an offer, a promise of return or investment advice.
