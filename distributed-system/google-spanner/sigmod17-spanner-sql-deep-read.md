---
title: 'Spanner: Becoming a SQL System'
authors:
- David F. Bacon
- Nathan Bales
- Nico Bruno
- Brian F. Cooper
- Adam Dickinson
- Andrew Fikes
- Campbell Fraser
- Andrey Gubarev
affiliations: 'Google'
venue: 'SIGMOD'
year: 2017
doi: 10.1145/3035918.3056103
abs_url: https://dl.acm.org/doi/10.1145/3035918.3056103
pdf_url: https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/46103.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Spanner: Becoming a SQL System

> **Why it matters:** (Own analysis) It shows how a sharded, Paxos-replicated, transactional key-value core was turned into a SQL database without static partitioning, by making every operator restartable and every plan aware that shard boundaries can move under it.

## Problem

The OSDI'12 Spanner paper covered the systems side: sharding, replication, TrueTime, fault tolerance. This paper covers the database side. Over roughly seven years Spanner evolved from a key-value-style store into a relational system (Section 1), because developers building OLTP applications wanted schemas, cross-row transactions and a real query language. The difficulties are specific to Spanner's substrate (Section 2):

- Tables are row-range sharded on key prefixes (child tables can be interleaved in their parent), and shards are split and moved between Paxos groups for load balancing at any time, including mid-query.
- Concurrency control is strict two-phase locking within a Paxos group plus two-phase commit across groups; snapshot reads run at a timestamp.
- Storage was a Bigtable-derived SSTable format on Colossus, a poor fit for typed, columnar access (Section 7).

The question is how to compile, distribute and execute SQL when data placement is never fixed, and how to keep long queries alive across failures, resharding and rolling upgrades.

## Core design

### Distributed Union and partitionability (Section 3.1-3.2)

- Every table scan is compiled as `DistributedUnion[shard ⊆ T](Scan(shard))`. The optimizer then pulls Distributed Union up the tree, pushing as much work as possible below it, close to the data.
- An operator F may go below Distributed Union only if it is partitionable: `F(Scan(T)) = OrderedUnionAll[shard ⊆ T](F(Scan(shard)))`. Projection and filtering always qualify. Grouping and sorting qualify "when the sharding columns are a proper subset of grouping or sorting columns", which range sharding makes possible. Joins between interleaved tables on the shared key prefix run locally on each shard.
- Non-partitionable operators (general Top, GroupBy) run in multiple stages: partial results below the union, final merge above it. In the Figure 1 top-k example, everything runs on the shards except selecting TOP 5 from the per-shard TOP 5 sets.
- The plan never encodes shard identities. At runtime, sharding-key filters gathered during the pull-up become key ranges, mapped to the minimal set of shards and sent via the coprocessor framework to a nearby replica. When ranges cover the whole table, one call goes per server hosting a group of shards rather than one per shard.

### Distributed Apply (Section 3.3)

Joins against a remote table (typically secondary index to base table, and inner / left outer / semi joins correlated on the remote table's keys) are executed by batching left-side rows. For each batch, the operator extracts sharding-key ranges per row, merges them, finds the intersecting shards, and sends each shard only the rows that touch it, where the apply then runs locally (Figure 2). This replaces one remote call per row with one call per (batch, shard).

### Routing and APIs (Section 3.4)

- Any server holding data can act as root. A location hint (the plan's outermost sharding-key expression) is cached on the client so later point lookups go straight to the owning server.
- Single-consumer API: results stream through the root to one client.
- Parallel-consumer API: a root-partitionable query (Distributed Union at the plan root) is split into opaque partition descriptors that different machines execute independently; the union of their outputs equals the single-consumer result as an unordered set.

### Range extraction (Section 4)

Range extraction computes the primary-key intervals a query touches, for three uses that differ in key-prefix length:

- Distribution ranges: which shards to contact (prefix length 1 in the example; a heuristic that may hit an irrelevant shard, which just returns nothing).
- Seek ranges: which key fragments to read within a shard (prefix length 3 in the example), turning scans into seeks.
- Lock ranges: what to lock in pessimistic transactions, or what to check for pending writes in snapshot transactions; trades one coarse lock for several fine ones.

Compile time (Section 4.2): after normalization (push NOT to leaves without CNF/DNF blowup, isolate key references, enumerate small integer intervals, drop complex conditions), a filtered scan becomes a chain of correlated cross-applies, one scan per successive key column (Figure 3: Scan1 over a constant, Scan2 and Scan3 correlated). A post-filter preserves semantics for whatever is not absorbed.

Runtime (Section 4.3): a shared filter tree computes ranges bottom-up by interval arithmetic (intersection for AND, union for OR), prunes branches that become unsatisfiable or tautological once a prefix value is bound, memoizes unchanged predicate results, and evaluates post-filters (Figure 4). It is runtime because parameter values and earlier scans' outputs (e.g. the next document path found by Scan2) are only known then.

### Query restarts (Section 5)

- Each result batch carries an opaque restart token; resubmitting the request with it resumes without re-emitting returned rows. There is no repeatability guarantee, only no duplicates and no gaps.
- Tokens capture the distributed state of the executing plan, must be small and cheap, and record progress in the table's key space rather than by shard, so a query interrupted on shard [20, 30) can resume on a merged shard [10, 40) (Section 5.2).
- Restarts hide generic failures (disconnects, reboots, crashes), distributed waits (overload, missing data, lagging replica), data movement, and internal retry codes for memory/CPU overuse or bad shards.
- Requirements: compensating for non-determinism (load-dependent ordering of parallel subqueries, memory-dependent ordering in blocking operators, order-sensitive floating point); versioned token wire format readable by adjacent server versions; a restarted query must run the same operator tree even if the new binary would compile a different plan; operators must interpret tokens identically across versions.
- Read-modify-write transactions are different: a failure usually loses in-memory locks, so the transaction aborts and retries.

### Common SQL dialect (Section 6)

Spanner, F1, Dremel and BigQuery share "Standard SQL" (ANSI-based, with ARRAY/STRUCT and first-class protocol buffers). Shared pieces: the compiler front end (emits a Resolved AST that each engine lowers into its own algebra), the scalar function library, compliance tests, a random query generator, and a reference implementation that annotates results as ordered/unordered and imprecise.

### Ressi storage (Section 7)

Ressi keeps the LSM structure but stores blocks PAX-style: row-major across blocks, column-major within a block, with columns as typed vectors that can be operated on compressed. Child rows sit in the same or nearby blocks as their parent. Each layer has an active file (latest versions) and an inactive file (older versions), so current-data reads skip history; large values live in separate files. Migration reuses data movement: change a Paxos group's per-replica storage format and move data into it, with mixed-format replicas for verification and conversion back to SSTables for rollback, while serving traffic.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Time to evolve into a relational system | 7 years | Spanner overall | Section 1 |
| Production databases | over 5,000 | Production instances, teams across Google and Alphabet | Section 1 |
| Serving load | tens of millions of QPS | Across all Spanner databases | Section 1 |
| Data managed | hundreds of petabytes | Across all Spanner databases | Section 1 |
| Rolling upgrade duration | "within a week or so" | Machines upgraded gradually, few versions running concurrently | Section 5.1 |
| Random queries without verification | around 10% | Unit tests; reference implementation finds no unique annotated result | Section 6 |
| Random query volume | millions per day | Continuously running random-query tests | Section 6 |
| Ressi production date | first half of 2017 (planned) | New low-level storage format | Section 7 |
| SQL query volume growth, year before common dialect | factor of two | Spanner SQL queries | Section 8 |
| SQL query volume growth, year after common dialect | factor of five | Spanner SQL queries | Section 8 |
| Internal distribution calls in queries | 4-fold increase | Same year after the dialect release | Section 8 |
| Release cadence | roughly bi-weekly | New Spanner versions | Section 8 |

## Limitations

- No performance evaluation: no latency, throughput or Ressi-vs-SSTable measurements; claims about seeks, pruning and restarts are qualitative.
- Restarts cover snapshot queries; read-write transactions still abort and retry on failure (Section 5.2), and all updates must come last in a read-modify-write transaction (Section 8; the team plans to allow reading uncommitted writes).
- Range extraction is approximate by design; distribution ranges may contact irrelevant shards, and complex predicates fall back to post-filtering (Section 4).
- Optimizer changes on a bi-weekly release cycle can cause large performance swings; the paper names this as an open challenge rather than solving it (Section 8).
- Mixed OLTP/OLAP/full-text workloads still span systems with different guarantees and release cycles (Section 8).
- (Own analysis) The restart contract pushes a large compatibility burden onto every operator and every release; the paper calls the cost "considerable" but gives no measure of it.

## Relation to other systems

- **Spanner (OSDI'12):** this paper builds on its sharding, Paxos and TrueTime; it notes TrueTime epsilon kept improving, which simplified timestamp selection for SQL queries (Section 8).
- **F1:** shares the Standard SQL dialect; per Section 9, F1 showed a transactional NoSQL core can carry a SQL layer, and Spanner now takes on that layer itself.
- **Dremel / BigQuery:** analytical engines sharing the same front end, function library and test suite; the shared Resolved AST is what keeps semantics aligned while each engine keeps its own algebra and executor (Section 6).
- **Bigtable SSTables:** Spanner's original file format; self-describing and redundant, inefficient for reading single columns, which motivated Ressi (Section 7).
- **PAX:** Ressi applies PAX's row-group/column-within-block layout and adds active/inactive version files for multi-versioned data (Section 7).
- **PostgreSQL:** its front end was considered and rejected, because protocol-buffer types had to be first-class and a UTF-8 STRING type was wanted (Section 6).

## Takeaways for practice

(Own analysis)

- Do not bake placement into plans. Compile against logical key ranges and resolve to shards or workers at execution time; it is what lets resharding, rebalancing and upgrades happen under running work.
- Make long-running work resumable with small tokens that record progress in a stable logical space (key space, step index, sample offset), not in terms of the physical unit that held it. The same idea applies to checkpointing training jobs or batch inference across preemption and rescheduling.
- A restart contract needs a version contract: tokens and plans must survive across adjacent binary versions if rolling upgrades are routine.
- Absorb transient failures (overload, lagging replica, moved shard) in the server with a retry code instead of blocking, so clients need no retry loops; be explicit about where that stops (here, read-write transactions).
- Push computation to data under an explicit algebraic condition (partitionability), aggregate in two phases otherwise, and batch remote lookups per destination rather than per item.

## References

- Paper: https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/46103.pdf
- ACM DL: https://dl.acm.org/doi/10.1145/3035918.3056103
