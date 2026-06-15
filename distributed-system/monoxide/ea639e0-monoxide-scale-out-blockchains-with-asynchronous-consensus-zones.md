---
paper_id: ea639e0bb4e4ef7ec5cbc7c0915033de4c89fd65
title: 'Monoxide: Scale out Blockchains with Asynchronous Consensus Zones'
authors:
- Jiaping Wang
- Hao Wang
venue: Symposium on Networked Systems Design and Implementation
year: 2019
citations: 518
abs_url: https://www.semanticscholar.org/paper/ea639e0bb4e4ef7ec5cbc7c0915033de4c89fd65
pdf_url: ''
analyzed_at: '2026-06-15T12:09:33+00:00'
model: deepseek-chat
---

# Monoxide: Scale out Blockchains with Asynchronous Consensus Zones

## TL;DR

Monoxide scales blockchain throughput linearly with the number of mining nodes by partitioning the network into independent asynchronous consensus zones, each processing its own shard of transactions, while introducing eventual atomicity for cross-shard transactions via a novel relay transaction mechanism.

## Problem & Motivation

Existing blockchain systems like Bitcoin and Ethereum face a fundamental scalability bottleneck: throughput is limited by the sequential block production rate of a single consensus group. Increasing block size or reducing block interval leads to higher orphan rates and centralization risks. Sharding approaches in permissioned settings or with complex cross-shard coordination suffer from high overhead or reduced security. Monoxide aims to achieve linear scaling of throughput without compromising decentralization or security.

## Key Ideas

- Partition the blockchain into multiple independent consensus zones, each with its own set of miners and transaction ledger.
- Each zone runs its own consensus protocol (e.g., Proof-of-Work) asynchronously, processing transactions within its shard.
- Introduce eventual atomicity for cross-zone transactions using a relay transaction mechanism: a transaction is first committed in the source zone, then relayed to the target zone via a relay transaction that includes a proof of the source commitment.
- Use a novel 'Chu-ko-nu mining' technique to allow miners to mine on multiple zones simultaneously without splitting hash power, ensuring security across zones.

## System Design

Monoxide consists of multiple consensus zones, each maintaining its own blockchain and transaction pool. Miners can participate in multiple zones by running Chu-ko-nu mining, which uses a single hash computation to generate proofs for all zones simultaneously. Cross-zone transactions are handled via relay transactions: a user submits a transaction to the source zone; after it is confirmed, a relay transaction containing the Merkle proof is submitted to the target zone, which verifies and executes the transfer. The system ensures eventual atomicity: either both zones commit or the transaction is rolled back via timeout.

## Evaluation

The paper evaluates Monoxide using a custom simulator and a prototype implementation. It compares against Bitcoin and Ethereum under various network sizes. Headline results: Monoxide achieves near-linear scaling of throughput (e.g., 1000+ tx/s with 1000 nodes) while maintaining low confirmation latency (tens of seconds). The Chu-ko-nu mining technique reduces the security degradation of sharding: an attacker controlling 25% of total hash power can only control at most 25% of zones, compared to 50% in naive sharding.

## Takeaways

- Asynchronous consensus zones can scale blockchain throughput linearly without requiring global coordination.
- Chu-ko-nu mining enables miners to secure multiple shards without splitting hash power, preserving security.
- Eventual atomicity via relay transactions is a practical approach for cross-shard transactions with low overhead.
- The design is compatible with existing Proof-of-Work blockchains and can be adapted to other consensus mechanisms.

## Related Work

Monoxide is positioned as a sharding solution for public blockchains, contrasting with earlier sharding proposals like Elastico and OmniLedger that require synchronous communication or complex cross-shard protocols. It also differs from sidechain approaches (e.g., Plasma) by providing native cross-shard atomicity. Compared to Ethereum's planned sharding, Monoxide's asynchronous zones reduce coordination overhead.

## Open Questions

- The security model under adaptive adversaries or network partitions is not fully analyzed.
- The relay transaction mechanism may introduce latency for cross-zone transactions; optimization for low-latency applications is needed.
- Chu-ko-nu mining assumes all zones use the same hash function; heterogeneity may complicate the design.
- The system's performance under high cross-zone transaction ratios is not thoroughly evaluated.
