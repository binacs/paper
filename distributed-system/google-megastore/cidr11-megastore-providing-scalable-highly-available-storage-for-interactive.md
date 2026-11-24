---
title: 'Megastore: Providing Scalable, Highly Available Storage for Interactive Services'
authors:
- Jason Baker
- Chris Bond
- James C. Corbett
- JJ Furman
- Andrey Khorlin
- James Larson
- Jean-Michel Léon
- Yawei Li
affiliations: 'Google'
venue: 'CIDR'
year: 2011
abs_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36971.pdf
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36971.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Megastore: Providing Scalable, Highly Available Storage for Interactive Services

> **Why it matters:** Megastore showed that Paxos can replicate primary user data synchronously across datacenters on every write with interactive latency, as long as you shrink the unit of consistency to small, application-chosen "entity groups".

## Problem

Interactive services (email, collaborative documents, social apps) need scale, fast feature development, low latency, a consistent view (an acknowledged edit must never vanish), and availability through datacenter-wide outages (Sec. 1). RDBMSs do not scale. NoSQL stores (Bigtable, HBase, Cassandra) scale, but their thin APIs and loose consistency complicate applications.

The paper rejects asynchronous master/slave (data loss on failover), synchronous master/slave (external failure detection, heavyweight failover) and optimistic replication (no global order, so no transactions), and wants no distinguished master (Sec. 2.1.1).

## Core design

### Entity groups as the unit of consistency
- Data is split into many small **entity groups**. Each is a mini-database with its own Paxos-replicated write-ahead log (Sec. 2, 2.2.1, 3.3).
- Inside a group you get serializable ACID transactions. Across groups you use **asynchronous queues** (transactional messaging), or **two-phase commit** where needed, which the paper discourages because of latency and contention (Sec. 3.3.1, 3.3.2).
- Group boundaries are the application's job. Examples: one email account per group; blogs split into profile, blog and unique-name groups; maps split into fixed geographic patches, where the number of groups does not grow with usage (Sec. 2.2.2).
- Local indexes live inside a group and are ACID. Global indexes span groups and are only loosely consistent (Sec. 3.2.2).

### Data model and Bigtable mapping
- Strongly typed schema of tables, entities and properties. Properties can be protobufs and can be repeated. Tables are either entity-group root tables or child tables that declare `ENTITY GROUP KEY` (Sec. 3.2, Fig. 3).
- "Pre-joining with keys": primary keys are concatenated into the Bigtable row key, and `IN TABLE` colocates child rows next to their root, which gives hierarchical layout without joins (Sec. 3.2.1). `SCATTER` prepends a two-byte hash to avoid hotspots on monotonically increasing keys.
- Index features: `STORING` (denormalized covering columns), repeated indexes, and inline indexes (child data shown as a virtual repeated column on the parent) (Sec. 3.2.2).
- Each group's transaction and replication metadata, including the log, sits in the root entity's Bigtable row, so it can be updated atomically with a single-row Bigtable transaction (Sec. 3.2.3).
- The API is "cost-transparent". Joins are done in application code, with a library-provided merge-join phase (Sec. 3.1).

### Transactions
- MVCC on Bigtable cell timestamps. There are current, snapshot and inconsistent reads (Sec. 3.3).
- Lifecycle: read (last committed position and timestamp), then application logic, then **commit** (Paxos append), then **apply** to entities and indexes, then clean up. Concurrency control is optimistic: competing writers for the same log position lose, abort and retry. Advisory locks and session affinity reduce contention (Sec. 3.3).

### Replication: masterless Paxos tuned for WAN
- One Paxos instance per log position. Any replica can start reads and writes (Sec. 4.1, 4.6).
- **Fast reads (Sec. 4.4.1):** each datacenter runs a **Coordinator** that tracks which entity groups its replica has fully observed. If the group is up to date locally, a current read needs no inter-replica RPC. Writers must keep coordinator state conservative: a replica that did not accept a write must have its coordinator *invalidated* before the write counts as committed (Sec. 4.6.3).
- **Fast writes (Sec. 4.4.2):** this adapts master-style pre-prepare. The consensus value at position *n* nominates a **leader** for *n+1*. The first writer to reach that leader may use proposal number zero and skip Prepare. Others fall back to two-phase Paxos. The leader policy is "use the closest replica", because writes tend to come from the same region.
- **Write algorithm (Sec. 4.6.3, Fig. 8):** Accept Leader → (Prepare) → Accept → Invalidate the coordinators of non-accepting full replicas → Apply. The commit point (after Accept) differs from the visibility point (after Invalidate).
- **Read algorithm (Sec. 4.6.2, Fig. 7):** query the local coordinator, find the highest possibly committed position (local read, or majority read on a miss or timeout), catch up by fetching missing values or proposing no-ops, validate the coordinator asynchronously, then read data at that timestamp.
- **Replica types (Sec. 4.4.3):** *full* replicas; *witness* replicas, which vote and store the log but hold no data and have no coordinator; and *read-only* replicas, which do not vote and serve snapshot-consistent, possibly stale data.
- **Architecture (Sec. 4.5, Fig. 5):** Paxos runs in a client library. Remote Paxos operations go through stateless replication servers that sit beside each Bigtable. Those servers also scan for abandoned writes and complete them with no-ops.
- **Coordinator liveness (Sec. 4.7):** coordinators hold Chubby locks in remote datacenters. If one loses a majority of its locks, it marks all its groups out of date. Validate/invalidate races are resolved by log position, with higher invalidates beating lower validates, and by per-incarnation epoch numbers.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Daily write transactions | more than 3 billion | Production, across Google | Sec. 1 |
| Daily read transactions | 20 billion | Production | Sec. 1 |
| Primary data stored | nearly a petabyte | Across many global datacenters | Sec. 1 |
| Production applications | more than 100 | Internal and external users | Sec. 4.10, Sec. 7 |
| Availability | at least five nines for most customers | Per-application, per-operation | Sec. 4.10, Fig. 9 |
| Average write latency | 100–400 ms for most users | Depends on datacenter distance, write size, number of full replicas | Sec. 4.10 |
| Average read latency | tens of milliseconds | Most reads are local | Sec. 4.10, Fig. 10 |
| Write cost | about one WAN roundtrip | Healthy case, observed in deployment | Sec. 4.1, Sec. 5 |
| Per-entity-group write rate with insignificant conflicts | a few writes per second | Optimistic Paxos, same log position | Sec. 4.8 |
| Write outage when a datacenter with live coordinators disappears | brief (tens of seconds) | Waiting for Chubby lock expiry | Sec. 4.7.1 |
| Replica placement | triplet or quintuplet of replicas | Within the region that accesses the group most | Sec. 2.2.3 |
| Fault tolerance | F faults with 2F+1 replicas | Paxos majority | Sec. 4.2 |
| SCATTER key prefix | two-byte hash | Anti-hotspot key encoding | Sec. 3.2.1 |

The histograms in Fig. 9 and Fig. 10 did not extract cleanly from the PDF, so no per-bucket values are given here.

## Limitations

- **Low write throughput per group.** Optimistic, position-level conflicts limit each group to a few writes per second. WAN latency makes conflicts more likely (Sec. 4.8). Hot shared objects need finer sharding, advisory locks, batching, or replicas placed in the same region.
- **Cross-group work is second-class.** Queues are asynchronous. 2PC is slow and discouraged. Global indexes may not reflect recent writes (Sec. 3.2.2, 3.3). The application has to choose group boundaries correctly up front (Sec. 2.2.2, Sec. 5).
- **Coordinators cost availability.** Every full replica must accept or be invalidated, so an unreachable coordinator can stall writes until its Chubby locks expire. Asymmetric partitions need an operator to step in manually (Sec. 4.7.1).
- **Latency.** 100–400 ms writes are acceptable but not fast. Some apps have to hide write latency (Sec. 5).
- **Physical tuning is left to users.** Megastore exposes Bigtable block size, compression and locality groups instead of managing them (Sec. 5).
- **Operational hazards the authors name:** "fault tolerance is fault masking", which hides persistent problems; and "chain gang throttling", where tolerating slow replicas as faults lets the fast majority run ahead until laggards' catch-up load drags it down (Sec. 5).

## Relation to other systems

- **Bigtable:** Megastore is a layer on top, one Bigtable per datacenter. It adds schema, ACID within a group, indexes and queues, and maps groups to contiguous rows (Sec. 2.2.3, 3.2.3).
- **Cassandra / Dynamo / HBase / CouchDB:** these use asynchronous, eventually consistent replication. Megastore replicates synchronously with strong semantics (Sec. 6).
- **Yahoo PNUTS:** it offers per-record "timeline" consistency with asynchronous replication. Megastore offers serializable transactions per entity group (Sec. 6).
- **Amazon SimpleDB:** its "domain" transactional unit cannot cross tables or scale arbitrarily. Megastore's entity group spans a root and its child tables (Sec. 6).
- **Master-based Paxos (Chubby / "Paxos Made Live"):** Megastore borrows the pre-prepare trick but replaces the long-lived master with a per-position leader and local reads at any up-to-date replica (Sec. 4.3–4.4).
- **Spanner (Own analysis):** Google's later Spanner keeps Paxos-replicated groups but adds cross-group distributed transactions and globally ordered timestamps, removing Megastore's main weak point: weak cross-group consistency and low per-group write rates. It does so with long-lived leaders instead of Megastore's masterless, per-position leadership. This comparison is not made in the Megastore paper.

## Takeaways for practice

- **Make the consistency domain explicit and small.** Strong consistency inside a small domain plus asynchronous messaging across domains scales well, provided most operations stay inside one domain. The same shape fits per-job or per-tenant state in a scheduler.
- **Separate commit from visibility.** Megastore makes a write visible only after every non-accepting replica's read cache (the coordinator) is invalidated. That is a general pattern for serving fast local reads without leases on the data itself.
- **Keep the availability-critical sidecar dumb.** Stateless, dependency-free coordinators are more reliable than the storage they guard (Sec. 4.7).
- **Prefer per-operation failover to master failover.** A per-position leader and no-op catch-up avoid timer-driven failover state machines.
- **Monitor masked faults.** "Chain gang throttling" and fault masking affect any quorum system, not just user-visible errors.
- **Invest in deterministic simulation.** The paper credits a seeded pseudo-random network simulator, run for thousands of simulated hours each night, as the most effective bug-finder (Sec. 5).

## References

- Paper: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36971.pdf
- Code / blog: none official
