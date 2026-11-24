---
title: 'F1: A Distributed SQL Database That Scales'
authors:
- Jeff Shute
- Radek Vingralek
- Bart Samwel
- Ben Handy
- Chad Whipkey
- Eric Rollins
- Mircea Oancea
- Kyle Littlefield
affiliations: 'Google, University of Wisconsin-Madison'
venue: 'VLDB'
year: 2013
abs_url: https://www.vldb.org/pvldb/vol6/p1068-shute.pdf
pdf_url: https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41344.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# F1: A Distributed SQL Database That Scales

> **Why it matters:** F1 showed in production that a full-SQL, ACID database on top of synchronously geo-replicated storage (Spanner) can replace a sharded MySQL fleet for a large business, provided the schema and client are designed to hide high commit latency.

## Problem

Google's AdWords ran on a manually sharded MySQL deployment that was "hard to scale up, and even more difficult to rebalance", and resharding "without breaking applications was challenging" (§1). The authors wanted four properties at once that are often treated as trade-offs: scalability (add resources, no manual resharding), availability (survive datacenter outages and maintenance), consistency (full ACID transactions, consistent indexes), and usability (full SQL, indexes, ad hoc queries). AdWords is "100s of applications and 1000s of users, all sharing the same database" (§1), so the database must also serve both OLTP and OLAP from one copy of the data.

The core tension: Spanner's synchronous cross-datacenter Paxos replication makes commits slow (50-150 ms, §2), so naive ORM-style access patterns with many serial round trips would make user-facing latency unacceptable.

## Core design

### Architecture (§2, §2.1)
- **Stateless F1 servers** front Spanner: "F1 servers do not own any data and hence a server addition (or removal) requires no data movement" (§2). A client may talk to a different F1 server per request.
- **Slave pool + F1 master**: a shared pool of F1 processes runs parts of distributed query plans; the F1 master tracks membership and health (§2).
- **Storage stack**: Spanner servers in each datacenter read from the Colossus File System, which is not globally replicated; Spanner provides replication, Paxos groups per directory, 2PC across groups, and globally ordered commit timestamps (§2.1). 2PC "usually doubles observed commit latency" and degrades with 100s of participants (§2.1).

### Hierarchical schema (§3.1)
- Tables are arranged in a hierarchy; a root row (e.g., AdWords `Customer`) and all its descendant rows (`Campaign`, `AdGroup`, keyed with the root's key as prefix) are clustered in one Spanner directory.
- Consequences: single-root transactions avoid 2PC; parent-child joins become a single range read in interleaved key order (the cluster join, §8.5).

### Protocol Buffer columns (§3.2, §8.7)
- Columns can hold structured Protocol Buffers, treated as first-class values in SQL with path expressions. This reduces the object-relational impedance mismatch, but F1 "always" fetches whole Protocol Buffer columns from Spanner (§8.7), so wide protos cost network, disk and parsing.

### Indexes (§3.3)
- **Local indexes** use the root key as a prefix and live with the root's rows: cheap to update transactionally.
- **Global indexes** are sharded independently and need 2PC; the paper warns that a transaction touching many rows can spread entries "across 100s of index directories", so global indexes are used sparingly and large transactions should be avoided on globally indexed tables.

### Schema changes (§4)
- Applied asynchronously on different F1 servers at different times, and "fully non-blocking". Correctness rests on keeping "at most two different schemas" active across servers, enforced via schema leases (§4); details are in the companion paper.
- Companion paper ("Online, Asynchronous Schema Change in F1", Rae et al., PVLDB 6(11)): a change is split into steps through intermediate states, delete-only (§3.1, Def. 1) and write-only (§3.1, Def. 2), so that any two adjacent versions are mutually compatible; adding an index goes delete-only, then write-only, then a resumable, idempotent reorganization that backfills entries for existing rows, then public (§3.3.2, §4.4). Servers write at most one schema per lease period, with leases of "multiple minutes" (§4.3).

### Transactions (§5, §5.1)
Three kinds, all on Spanner transactions:
- **Snapshot** (read-only) at a fixed timestamp, by default Spanner's global safe timestamp, typically 5-10 s old (§2.1, §5).
- **Pessimistic**: hold Spanner locks through a stateful protocol; idle ones are killed within ten seconds, so long-running ones often cannot commit (§5).
- **Optimistic** (the client default): unbounded lock-free read phase, then a short write phase that re-reads each row's hidden lock column holding its last-modification timestamp and aborts on change (§5). Downsides stated: insertion phantoms are not prevented, and high contention gives many failed commits.
- **Lock granularity is a schema decision** (§5.1): one default lock column per row, optionally per-column lock columns, or a parent-table lock column covering child columns to deliberately serialize.
- On hot rows, the paper notes a 50 ms commit caps exclusive updates to 20 per second, so applications must batch (§5).

### Change history (§6)
Every transaction writes one or more `ChangeBatch` protocol buffers (primary key, before and after values of changed columns) into normal child tables of each root. Consumers use it for incremental processing and cache invalidation; it is part of the database, not a side channel.

### Client design (§7)
- A new ORM that does no joins and never implicitly traverses relationships; requests need "a fixed number (fewer than 10) of reads, independent of request size or data size" (§7.1).
- A NoSQL key/value API with batched multi-table reads (§7.2) next to full SQL (§7.3). Applications rely on batching, parallelism and asynchronous reads (§1).

### Query processing (§8)
- **Central** execution on one F1 server for short OLTP queries; **distributed** execution across slave-pool workers for OLAP (§8.1).
- Storage is remote, so operators are designed around batching and pipelining: the lookup join batches outer keys until "50MB worth of data or 100,000 unique lookup key values" (§8.3), then issues the lookups together.
- Only hash repartitioning, no range partitioning, because input is not range-partitioned and statistics are unreliable (§8.4).
- Operators run in memory, spill hash tables to disk when needed, and do not checkpoint; failed queries are retried transparently (§8.4).
- **Partitioned consumers**: multiple client processes (e.g., MapReduce) read sharded result streams of one query in parallel; a slow reader can stall the others, and disk-backed buffering is "so far unimplemented" (§8.6).

### Deployment (§9)
Five read/write replicas: two on the US east coast, two on the west coast, one central, with a preferred leader on the east coast; heavy writers sit near the leader. Five rather than three because with three, a planned outage of one datacenter leaves no margin: a second failure makes the database unavailable (§9). Read-only replicas serve snapshot reads, separating OLAP from OLTP (§9).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Database size | over 100 TB | AdWords production | §1 |
| Request rate | up to hundreds of thousands of requests/s | AdWords production | §1 |
| Availability | five nines | AdWords, including unplanned outages | §1 |
| In production since | early 2012 | all AdWords campaign data | §1 |
| Commit latency | 50-150 ms | synchronous cross-datacenter replication | §2, §10 |
| Read latency | 5-10 ms | AdWords configuration | §10 |
| Global safe timestamp lag | typically 5-10 s | default snapshot read point | §2.1, §5 |
| Idle pessimistic txn timeout | within ten seconds | lock leak protection | §5 |
| ORM reads per request | fixed, fewer than 10 | new F1 ORM | §7.1 |
| Lookup join batch | 50 MB or 100,000 unique keys | batched lookup join | §8.3 |
| Distributed query cluster | several hundred worker processes | full-bisection network | §8.4 |
| Reliable query duration | up to an hour | no checkpointing | §8.4 |
| Replication | 5-way Paxos, five US datacenters | AdWords deployment | §9 |
| User-facing latency (F1) | averages about 200 ms | main interactive AdWords app | §10 |
| User-facing latency (old system) | typically 200-300 ms average | sharded MySQL with old ORM | §7.1 |
| Bulk update job | billions of rows/day; txns of up to 500 rows; aiming for 500 txn/s | non-interactive batch app | §10 |
| Small central queries | under 10 ms | OLTP-style | §10 |
| CPU vs MySQL | often an order of magnitude more | similar queries | §10 |

## Limitations

- **High commit latency is a given**, pushed onto application design (clustering, batching, asynchronous reads). Hot rows remain bounded by commit latency (§5).
- **Optimistic default** allows insertion phantoms and suffers under contention (§5).
- **Global indexes are expensive** (2PC, many participants) and must be used sparingly (§3.3).
- **Distributed queries are not fault-tolerant**: no checkpointing, whole-query retry, practical ceiling around an hour; cluster size is bounded by switch hardware (§8.4).
- **CPU efficiency**: often an order of magnitude more CPU than MySQL, attributed to decompression, recompression and network steps; the paper says it has focused on "functionality and parity", not absolute query performance, and gives no throughput benchmark (§10).
- **Whole Protocol Buffer columns are always fetched** (§8.7); partitioned consumers can stall on slow readers (§8.6).
- Results are from one large tenant (AdWords) on Google-internal infrastructure; there is no controlled comparison with other systems.

## Relation to other systems

- **Spanner**: F1 is the SQL, index, schema-change, and query layer; Spanner supplies replication, timestamps and transactions (§2.1). The value of F1 is showing how to make a high-latency store usable for a large application.
- **Sharded MySQL (predecessor)**: F1 removes manual resharding and keeps SQL, at the cost of higher commit latency and CPU (§1, §10).
- **Megastore**: the paper says its hierarchical schema and clustering are "similar to Megastore", but Megastore makes global indexes scalable by giving up consistency, which F1 does not (§11).
- **Percolator**: cited alongside Megastore as another system using optimistic transactions (§11); F1 adds SQL and per-schema lock granularity.
- **Bigtable / HBase / Dynamo**: F1's NoSQL interface shares properties with these key/value stores (§11), but F1 adds ACID transactions and consistent secondary indexes.
- **CockroachDB, TiDB, YugabyteDB** (Own analysis): all follow the same broad recipe of a stateless SQL layer over a replicated, range-sharded transactional KV store with online schema change. F1 differs mainly in leaning on a user-declared table hierarchy for co-location rather than leaving placement to automatic range splitting, and in running on Google-internal Spanner rather than an open-source storage layer. No quantitative comparison is made here.

## Takeaways for practice

- Treat locality as a schema-level contract: if most transactions and joins stay within one root, you avoid 2PC and get cheap joins. The scheduler analogue is placing tightly coupled state (a job's tasks, a session's KV cache) in one failure and consistency domain.
- Hide latency structurally: bound round trips per request (F1's ORM needs a fixed number, fewer than 10), batch lookups, and issue reads in parallel. This is the same approach that makes control planes on consensus stores fast enough.
- Make concurrency granularity explicit and tunable per entity, instead of relying on one global isolation setting.
- An in-database change log (`ChangeBatch`) is a clean way to drive caches, downstream pipelines and rate-limited consumers without dual writes.
- Online schema change via intermediate states plus leases (at most two live versions) generalises to any fleet that rolls out config or API versions asynchronously.
- Size replication for maintenance plus one failure: the 5-vs-3 replica argument (§9) applies directly to control-plane quorum sizing.
- Expect a CPU cost for compression, remote storage and extra layers, and budget for it (§10).

## References

- Paper (Google PDF): https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41344.pdf
- Paper (PVLDB 6(11), pp. 1068-1079): http://www.vldb.org/pvldb/vol6/p1068-shute.pdf
- Companion: "Online, Asynchronous Schema Change in F1", Rae et al., PVLDB 6(11): https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41376.pdf
- Code / blog: none official
