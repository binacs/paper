---
title: 'Monoxide: Scale out Blockchains with Asynchronous Consensus Zones'
authors:
- Jiaping Wang
- Hao Wang
affiliations: 'ICT/CAS, Sinovation AI Institute, Ohio State University'
venue: 'NSDI'
year: 2019
abs_url: https://www.usenix.org/conference/nsdi19/presentation/wang-jiaping
pdf_url: https://www.usenix.org/system/files/nsdi19-wang-jiaping.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Monoxide: Scale out Blockchains with Asynchronous Consensus Zones

> **Why it matters:** Monoxide shows a PoW blockchain can be partitioned into many independent consensus zones that scale throughput linearly, while it replaces two-phase commit for cross-zone transfers with a lock-free "eventual atomicity" and keeps per-zone attack cost high through merged mining across zones.

## Problem

Every full node replicates all consensus, communication, storage and state work, and blocks are produced sequentially, so throughput does not grow with node count (Sec. 1, 2). Sharding raises two problems (Sec. 1, 5): keeping cross-shard payments atomic without locking two-phase commit, and mining-power dilution, where an attacker focusing on one of n shards needs only about 1/n of the usual majority.

## Core design

### Asynchronous Consensus Zones (Sec. 3)

- **Partitioning.** 2^k zones (k = "sharding scale", fixed), indexed by the first k bits of an account/balance-model address (Sec. 2, 3.1).
- **Nodes and swarms.** A random persistent node ID fixes each node's zone. Miners compete only in their zone, and gossip stays in per-zone swarms. A global swarm carries only chain-forming data, and a DHT handles peer discovery (Sec. 3.1–3.3).
- **Block split.** A ~100-byte chaining-block (PoW, metadata, Merkle roots of confirmed and outbound relay transactions) goes to all zones. The transaction-block stays in its zone (Sec. 4, Fig. 2). PoW is used, though the design is said to be orthogonal to consensus (Sec. 2).

### Eventual atomicity via relay transactions (Sec. 4)

- An **initiative transaction** withdraws in the payer's zone, and an **outbound relay transaction** deposits in the payee's zone. Intra-zone payments need no relay (Sec. 4).
- **Verification.** The relay carries zone index, sharding scale, height, position and a Merkle path, which is checked against the outbound-relay root in the originating chaining-block on the origin's main chain (Sec. 4.1, Eq. 1). No zone needs another zone's transaction data.
- **Guarantee.** Once the withdraw is confirmed, the deposit eventually runs. Relays expire only if their initiative is invalidated, and there are no locks (Sec. 4.2).
- **Forks.** Each zone uses GHOST and labels blocks as available, unsolved or orphan (Sec. 4.3). A relay transaction can be included only once its originating block is available. If that block later leaves the winning path, the relay transaction is invalidated, the destination zone rebuilds its state without it, and dependent transactions may be invalidated too (Fig. 3).
- **λ-delay.** To contain those cascades, miners delay execution of inbound relay transactions by λ blocks. They keep a delayed state alongside the normal state, and a candidate cross-zone transaction must validate against both (Sec. 4.3).
- **Fees.** A simple payment's fee is split equally between the initiative and relay steps (Sec. 6.2).

### Chu-ko-nu mining (Sec. 5)

- A miner builds a Merkle tree over candidate chaining-headers of many zones. One nonce meeting the target over the root plus batch configuration yields a block in **every** batched zone (Sec. 5.1, Eq. 3–4, Fig. 4).
- Each zone verifies its header, Merkle path, configuration and nonce independently, with at most one block per zone per solution (Sec. 5.1–5.2). An equal PoW target is assumed, and mixed targets get partial dispatch plus re-probing (Sec. 5.2).
- **Security.** Chu-ko-nu power counts in full in each zone it covers, so the attack bar converges to 50% as such facilities dominate (Sec. 5.3, Eq. 5–6).
- **Mining system.** Full nodes track all zones and build headers. A Mining Coordinator recomputes the tree root on any change and broadcasts it to the PoW units (Sec. 5.4, Fig. 5).

**Implementation:** C++ with Botan, Intel IPP Cryptography, RocksDB and a Mainline DHT. No code repository is given (Sec. 7).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Testbed | 1,200 VMs, 8 cores / 32 GB each, 15 availability zones | Evaluation setup | Sec. 7 |
| Simulated network size | 48,000 nodes | On the 1,200-VM testbed | Abstract, Sec. 7 |
| Link limits | 30 Mbps peak; 102.48 ms avg end-to-end latency | Testbed | Sec. 7 |
| Workload | ERC20 payments up to Ethereum block 5,867,279; 16.5 M addresses; 75.8 M txs | Replayed trace | Sec. 7 |
| Block parameters | 32 KB blocks, 15 s interval | Default config | Sec. 7 |
| Per-zone throughput | ~15.6 TPS | One-to-one token transfers, default config | Sec. 7 |
| Zone population | 24 nodes, ~12 miners per zone on average | Scalability runs | Sec. 7.1 |
| Peak throughput | 11,694.89 TPS | 2,048 zones | Sec. 7.1, Fig. 6 |
| 1 to 2 zones speed-up | 1.88x | Attributed to relay overhead | Sec. 7.1 |
| Headline claim | 1,000x throughput, 2,000x capacity over Bitcoin and Ethereum | Paper's summary claim | Abstract, Sec. 1 |
| Cross-zone share | almost all txs become cross-zone | Above 64 zones | Sec. 7.2, Fig. 8 |
| Transaction volume overhead | at most double | Due to relay transactions | Sec. 7.2 |
| Chaining-block overhead | tens of KB in total, 6.2% of transaction data | 2,048 zones | Sec. 7.2, Fig. 9 |
| Avg connections per full node | 68.5 | Testbed | Sec. 7.3 |
| Relay first confirmation | 13–21 s | More than 30 zones | Sec. 7.3, Fig. 11 |
| Orphan rate | 8.3 per mille per zone, independent of zone count | Default config | Sec. 7 |
| Attack threshold example | ~49.5% of total hash rate needed | Facility with 99% of hash rate, 256 zones | Sec. 5.3 |
| Hotspot address | > 2% of all transactions | One exchange deposit address in the trace | Sec. 6.1 |

## Limitations

- **Chu-ko-nu is not evaluated.** Section 7 neither enables nor measures it. The security argument rests on the analysis in Sec. 5 and on miners adopting it for profit.
- **Liveness of relays depends on incentives.** Miners are not forced to include relay transactions, and empty-block mining can delay completion (Sec. 4.2). The fee split is proposed without quantitative economic analysis (Sec. 6.2).
- **No isolation.** Intermediate states, with the withdraw done and the deposit pending, are visible. Programmable transactions must be order-independent, and many-to-many payments are not supported (Appendix A.3, Sec. 6.3).
- **Fixed sharding scale.** k is assumed constant, and re-sharding is out of scope (Sec. 3).
- **Hotspots cannot be split.** A single heavy address stays in one zone. The paper's mitigation is for operators to use several deposit addresses (Sec. 6.1).
- **(Own analysis)** The defense works best when large facilities validate all zones (Sec. 5.4), which puts full-replication cost back on them and favors big operators.
- **No formal network model.** Honest majority per zone is assumed, but synchrony and adversarial delay of relay transactions are not formally modeled (Sec. 4–5).
- **Inconsistencies noticed in the paper.**
  - The chaining-block is "roughly 100 bytes" in Sec. 4 but "tens of bytes" per block in Sec. 7.2.
  - The 1,000x / 2,000x claim is never derived in Sec. 7, and "capacity" is not defined beyond a link to storage, computation and state memory in Sec. 1.
  - The text does not say which zone count the 48,000-node figure corresponds to, or how it fits the 24-nodes-per-zone setting in Sec. 7.1.
  - The title capitalization differs between the running header ("Scale out Blockchains") and the title block ("Scale Out Blockchain").
  - Jiaping Wang's second affiliation reads "Sinovation AI Institute" in the PDF and "Sinovation Ventures" on the USENIX page.

## Relation to other systems

- **Elastico:** per the paper, no cross-shard atomicity, and small committees raise the failure probability (Sec. 8).
- **OmniLedger:** uses Atomix, a lock-based two-phase commit. Monoxide commits the withdraw first and relays the deposit without locks (Sec. 8).
- **RapidChain:** BFT-committee sharding tolerating up to 1/3 Byzantine faults. Monoxide keeps PoW per zone and targets the lower per-shard attack bar that prior sharding leaves open (Sec. 8).
- **GHOST / Bitcoin-NG / Conflux:** single-chain or DAG designs that stay bandwidth-bound. Monoxide runs GHOST inside each zone (Sec. 4.3, Sec. 8).
- **PBFT / Algorand:** PBFT's communication cost limits scale, and Algorand's VRF selection is open to randomness bias (Sec. 8).

## Takeaways for practice

- **(Own analysis)** Split metadata from payload. A small header replicated everywhere gives each partition a verifiable view of the others without global state.
- **(Own analysis)** Verifiable, non-expiring messages can replace atomic commit when visible intermediate states and order-independent operations are acceptable.
- **(Own analysis)** Speculative consumption of upstream results needs a bounded rollback path, as the λ-delay provides.
- **(Own analysis)** Partitioning dilutes protection as well as load. Ask whether an adversary or noisy tenant can concentrate on one shard.
- Hot keys (Sec. 6.1) and near-universal cross-partition traffic at high zone counts (Sec. 7.2) make the cross-partition path the common case.

## References

- Paper: https://www.usenix.org/conference/nsdi19/presentation/wang-jiaping
- PDF: https://www.usenix.org/system/files/nsdi19-wang-jiaping.pdf
- Slides (official, USENIX): https://files.usenix.org/s3fs-public/cdn/nsdi19_slides_wang-jiaping.pdf
