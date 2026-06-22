---
paper_id: ea639e0bb4e4ef7ec5cbc7c0915033de4c89fd65
title: 'Monoxide: Scale out Blockchains with Asynchronous Consensus Zones'
authors:
- Jiaping Wang
- Hao Wang
venue: Symposium on Networked Systems Design and Implementation
year: 2019
citations: 519
abs_url: https://www.semanticscholar.org/paper/ea639e0bb4e4ef7ec5cbc7c0915033de4c89fd65
pdf_url: ''
analyzed_at: '2026-06-22T11:50:27+00:00'
model: deepseek-chat
---

# Monoxide: Scale out Blockchains with Asynchronous Consensus Zones

## TL;DR

Monoxide scales blockchain throughput linearly with the number of mining nodes by partitioning the network into independent consensus zones that process transactions asynchronously, while ensuring cross-zone atomicity via a novel relay transaction mechanism.

## Problem & Motivation

Existing blockchain systems like Bitcoin and Ethereum face a fundamental scalability bottleneck: every node must process every transaction, limiting throughput to O(1) regardless of the number of nodes. This prevents blockchains from matching the transaction throughput of centralized payment systems. The challenge is to scale out blockchain throughput linearly with mining power without sacrificing security or decentralization.

## Key Ideas

- Partition the blockchain into multiple independent shards called consensus zones, each with its own set of miners and ledger.
- Transactions within a zone are processed asynchronously and in parallel across zones, enabling linear throughput scaling.
- Introduce a relay transaction mechanism to atomically transfer assets across zones, ensuring cross-zone consistency without global coordination.
- Use a novel mining algorithm called "Chu-ko-nu mining" that allows miners to mine on multiple zones simultaneously without splitting their power, maintaining security.

## System Design

Monoxide consists of multiple consensus zones, each functioning as an independent blockchain with its own mempool, block proposers, and ledger. Miners can participate in multiple zones via Chu-ko-nu mining, which uses a single proof-of-work puzzle to generate blocks for all zones simultaneously. Cross-zone transactions are handled by relay transactions: a transaction locks assets in the source zone and generates a proof that is submitted to the destination zone, which then mints equivalent assets. The system does not require a global ordering or cross-zone consensus, relying on asynchronous processing.

## Evaluation

The paper evaluates Monoxide via analysis and simulation. It shows that throughput scales linearly with the number of zones (e.g., 1000 zones achieve 1000x throughput of a single zone). Security analysis demonstrates that Chu-ko-nu mining preserves the overall security level (adversarial power threshold remains 50%). No real-world deployment or comparison with other sharding proposals is presented in the abstract.

## Takeaways

- Asynchronous consensus zones can achieve linear scaling without global coordination.
- Chu-ko-nu mining enables miners to contribute to multiple shards without splitting hash power, maintaining security.
- Relay transactions provide atomic cross-shard transfers with minimal overhead.
- The design avoids complex cross-shard consensus protocols, simplifying implementation.

## Related Work

Monoxide is positioned as a sharding solution for blockchains, contrasting with earlier proposals like Elastico and OmniLedger that require synchronous cross-shard communication or complex protocols. It also differs from off-chain scaling solutions like Lightning Network.

## Open Questions

- How does the system handle zone imbalance or hotspots where one zone becomes overloaded?
- What are the practical overheads of relay transactions in terms of latency and storage?
- Can the Chu-ko-nu mining be adapted to proof-of-stake or other consensus mechanisms?
- How does the system ensure liveness and fairness under adversarial conditions?
