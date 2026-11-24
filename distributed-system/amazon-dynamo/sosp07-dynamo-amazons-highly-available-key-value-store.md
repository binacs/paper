---
title: 'Dynamo: Amazon''s Highly Available Key-value Store'
authors:
- Giuseppe DeCandia
- Deniz Hastorun
- Madan Jampani
- Gunavardhan Kakulapati
- Avinash Lakshman
- Alex Pilchin
- Swaminathan Sivasubramanian
- Peter Vosshall
affiliations: 'Amazon.com'
venue: 'SOSP'
year: 2007
abs_url: https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html
pdf_url: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Dynamo: Amazon's Highly Available Key-value Store

> **Why it matters:** Dynamo showed that a production store can trade consistency for an "always writeable" guarantee by combining consistent hashing, vector clocks, sloppy quorums, hinted handoff, Merkle-tree anti-entropy and gossip membership, all tuned for the 99.9th-percentile tail rather than the mean.

## Problem

Amazon's platform runs hundreds of services on tens of thousands of servers, where components fail continuously (Sec. 1, 2). Services like the shopping cart need a store that never rejects a write, even when nodes, links or a data center fail (Sec. 2.3). Access is primary-key get/put on small blobs (typically under 1 MB), with no multi-item transactions or schema. ACID stores gave poor availability, so Dynamo drops isolation and allows only single-key updates (Sec. 2.1). SLAs are set at the 99.9th percentile, because the mean hides heavy customers (Sec. 2.2). The system runs in one trusted domain with no authentication requirements (Sec. 2.1). Principles: incremental scalability, symmetry, decentralization, heterogeneity. Conflicts are resolved at **read** time so writes are never rejected (Sec. 2.3).

## Core design

### Partitioning and replication (Sec. 4.1–4.3)
- Keys are MD5-hashed (128-bit) onto a ring. Each physical node owns several **virtual nodes (tokens)**, so failure or join load spreads over many peers and token count can match capacity.
- The coordinator replicates a key to its N-1 clockwise successors. The **preference list** holds more than N nodes, skipping tokens so it lists only distinct physical nodes.

### Versioning (Sec. 4.4)
- Each put creates an immutable version with a **vector clock** of (node, counter) pairs. Ordered versions are reconciled syntactically; concurrent ones go to the client for semantic merging. In the cart, an "add" is never lost but deleted items can resurface.
- Clocks are truncated by dropping the oldest timestamped pair past a threshold (example: 10); the paper says this has not caused problems in production.

### Request path and quorums (Sec. 4.5, Sec. 5)
- Clients use a generic load balancer or a partition-aware library that contacts a coordinator directly.
- R + W > N gives quorum-like behaviour; latency is set by the slowest of the R (or W) replicas. A put needs the local write plus W-1 acks; a get waits for R replies and returns all causally unrelated versions.
- Each request is a state machine on a SEDA-like staged pipeline over Java NIO. The coordinator then does **read repair** on stale replicas (Sec. 5).
- The write coordinator is usually the replica that answered the preceding read fastest (carried in the opaque context); always using the first node had caused uneven load and SLA violations (Sec. 5).

### Failure handling (Sec. 4.6–4.8)
- **Sloppy quorum + hinted handoff:** operations use the first N *healthy* nodes; a write for a down node lands elsewhere with a **hint** and is handed back on recovery. Replicas span data centers.
- **Anti-entropy:** one Merkle tree per hosted key range; replicas compare top-down and transfer only differing keys.
- **Membership:** explicit admin join/leave (transient outages trigger no rebalancing), per-second gossip of membership and token maps, **seed** nodes against logical partitions, purely local failure detection.

### Implementation (Sec. 5)
Java throughout; pluggable local engines (BDB Transactional Data Store, BDB Java Edition, MySQL, in-memory buffer with persistent backing); most production instances use BDB Transactional Data Store.

### Operational refinements (Sec. 6)
- Usage patterns: business-logic reconciliation (cart), last-write-wins (session service), read engine with R=1, W=N (Sec. 6).
- **Write buffering:** in-memory buffer flushed by a writer thread; one of the N replicas does a durable write while the coordinator waits for only W (Sec. 6.1).
- **Partitioning (Sec. 6.2, Fig. 7–8):** Strategy 1 (T random tokens/node) coupled partitioning and placement, slowed bootstrap and forced Merkle recomputation; Strategy 2 (T random tokens, Q equal partitions) was an interim step; Strategy 3 (Q/S tokens/node, equal partitions) balanced best with the least metadata.
- **Client-driven coordination:** the library polls membership and coordinates itself, removing a hop (Sec. 6.4).
- **Admission control:** a feedback controller grants background tasks only spare resource slices based on foreground metrics (Sec. 6.5).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Example service SLA | 300 ms for 99.9% of requests at a peak of 500 req/s | Illustrative SLA | Sec. 2.2 |
| Services contacted per page render | over 150 | Amazon e-commerce page | Sec. 2.2 |
| Common (N,R,W) | (3,2,2) | Production instances | Sec. 6 |
| Measured system size | "a couple hundred nodes", homogeneous hardware | Live (3,2,2) system | Sec. 6 |
| 99.9th-percentile latency | around 200 ms, an order of magnitude above the averages | 30 days, Dec 2006 peak season | Sec. 6.1, Fig. 4 |
| Write-buffering effect | 99.9th-pct latency lowered by a factor of 5 at peak, with a buffer of about a thousand objects | 24 h | Sec. 6.1, Fig. 5 |
| Out-of-balance threshold | 15% deviation from average load | Load measured in 30-min intervals over 24 h | Sec. 6.2, Fig. 6 |
| Imbalance ratio | as high as 20% at low load; close to 10% at high load | Same | Sec. 6.2, Fig. 6 |
| Strategy-1 bootstrap time | almost a day | Busy shopping season | Sec. 6.2 |
| Membership metadata, Strategy 3 vs 1 | about three orders of magnitude smaller | Simulation | Sec. 6.2 |
| Partitioning simulation | S=30 nodes, N=3 | Strategy comparison | Fig. 8 |
| Requests seeing exactly one version | 99.94% | Shopping cart, 24 h | Sec. 6.3 |
| 99.9th-pct read / write latency | 68.9 / 68.5 ms (server-driven) vs 30.4 / 30.4 ms (client-driven) | 24 h | Table 2 |
| Average read / write latency | 3.9 / 4.02 ms (server-driven) vs 1.55 / 1.9 ms (client-driven) | 24 h | Table 2 |
| Client membership poll interval | 10 s | Client-driven coordination | Sec. 6.4 |
| Admission-control signal | 99th-pct DB read latency over the last 60 s vs a threshold (example 50 ms) | Background-task throttling | Sec. 6.5 |
| Successful (non-timeout) responses | 99.9995% of requests; no data loss event to date | "the past two years" | Sec. 6.6 |

Inconsistencies in the paper:
- Production history is given as "the past year" in Sec. 1 and Sec. 7 but "the past two years" in Sec. 6.6.
- The text in Sec. 6.4 says client-driven coordination "decreases the average by 3 to 4 milliseconds". The Table 2 averages do not obviously support that range, so read the table directly.

## Limitations

- Trusted environment only; no authentication or authorization (Sec. 2.1).
- Full routing table on every node; the paper says scaling to tens of thousands of nodes "is not trivial" (Sec. 6.6).
- Applications must handle conflicts; deleted items can resurface (Sec. 4.4). (Own analysis) Last-write-wins can silently drop concurrent updates.
- Clock truncation can lose causality; only "not seen in production" is offered (Sec. 4.4).
- No multi-key operations, isolation, or range queries over hashed keys (Sec. 2.1, 4.1).
- (Own analysis) Evaluation is observational: no controlled baselines and no failure-injection results for handoff or anti-entropy. Sloppy quorums also weaken what R + W > N guarantees, since acks may come from substitute nodes.

## Relation to other systems

- **Chord / Pastry (Sec. 3.1):** multi-hop structured overlays; Dynamo gossips full membership and is "a zero-hop DHT" (Sec. 3.3).
- **Bigtable / GFS (Sec. 3.2):** structured model and single-master metadata; Dynamo has no master or schema and favours write availability.
- **Bayou, Coda, Ficus (Sec. 3.2):** optimistic replication with conflict resolution; Dynamo applies this to a key-value store in one trusted domain.
- **FAB, Antiquity, OceanStore, PAST (Sec. 3):** block storage, Byzantine integrity, untrusted or immutable settings; Dynamo assumes trusted nodes and small mutable objects.
- **Cassandra, Riak (Own analysis):** reuse Dynamo-style rings, tunable N/R/W, hinted handoff and anti-entropy; Cassandra adds a Bigtable-like model and timestamp resolution, Riak keeps client-visible siblings closer to the paper.
- **Amazon DynamoDB (Own analysis):** a later managed service sharing the name, with a different public API; do not assume this paper describes its internals.

## Takeaways for practice

- Design for the 99.9th percentile; coordinator choice, write buffering and client routing are all justified by tail effects (Sec. 2.2, 5, 6.1, 6.4).
- Decouple partitioning from placement: fixed equal partitions eased bootstrap, recovery and archival (Sec. 6.2). (Own analysis) The same applies to shard maps in schedulers and KV-cache/state stores.
- Make membership changes explicit and handle transient failures locally to avoid rebalancing on flaps (Sec. 4.8).
- Throttle background repair with a controller tied to foreground latency (Sec. 6.5). (Own analysis) Rebuild and checkpoint traffic on training clusters needs the same.
- Expose consistency knobs (N, R, W, resolution policy) per service (Sec. 6).
- Partition-aware clients remove a hop and cut tail latency (Table 2).
- (Own analysis) Eventual consistency suits mergeable, high-volume data (sessions, caches, telemetry), not control-plane state like job leases.

## References

- Paper: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- Code / blog: https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html (Werner Vogels' announcement post, which also hosts an HTML version of the paper; no public code)
