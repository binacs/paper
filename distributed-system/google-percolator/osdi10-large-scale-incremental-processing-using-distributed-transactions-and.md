---
title: 'Large-scale Incremental Processing Using Distributed Transactions and Notifications'
authors:
- Daniel Peng
- Frank Dabek
affiliations: 'Google'
venue: 'OSDI'
year: 2010
abs_url: https://www.usenix.org/conference/osdi10/large-scale-incremental-processing-using-distributed-transactions-and
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36726.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Large-scale Incremental Processing Using Distributed Transactions and Notifications

> **Why it matters:** Percolator showed that cross-row ACID transactions (snapshot isolation via client-coordinated two-phase commit with a primary lock and a timestamp oracle) can be layered on a plain sharded key-value store with no central transaction manager, and paired them with change-triggered "observers" to replace a 100-stage MapReduce indexing pipeline.

## Problem

Google's web index was built by a series of MapReduces over the whole repository; because new pages link to old ones, every refresh rescanned everything, so latency grew with repository size rather than update size. A DBMS cannot hold the data: tens of petabytes on thousands of machines, billions of updates per day (Abstract, §1). Bigtable scales but has only single-row transactions, so cross-row invariants (e.g. content hash vs. duplicates table) cannot be kept under concurrent updates. Target workloads: huge, decomposable into small mutations, strongly consistent, latency-tolerant (§1).

## Core design

**Architecture (§2, Fig. 1).** Each machine runs a Percolator worker (all observers linked in), a Bigtable tablet server and a GFS chunkserver, plus two small services: a timestamp oracle and an advisory, non-persistent lock service for the notification scan. Percolator is a *client library*: no transaction-manager tier, no global deadlock detector.

**Data layout (§2.2, Fig. 5).** Each Percolator column `c` is stored as several Bigtable columns, using Bigtable's timestamp dimension for MVCC:
- `c:data` holds the value, written at the transaction's start timestamp.
- `c:lock` marks an uncommitted write and stores the location of the primary lock.
- `c:write` is the commit record. It sits at the commit timestamp and points to the start timestamp of the data.
- `c:notify` is a non-transactional hint that an observer may need to run.
- `c:ack_O` holds the start timestamp of observer O's last successful run.

Locks live in in-memory Bigtable columns, inheriting Bigtable's durability and sharding, and are read/written inside Bigtable row transactions.

**Transaction protocol (§2.2, Figs. 4 and 6).**
1. The constructor fetches `start_ts` from the oracle. `Set()` calls are buffered on the client.
2. *Prewrite.* One write is picked arbitrarily as the primary. For each cell, in a row transaction, the transaction aborts if it finds a `write` record at or after `start_ts` (a write-write conflict) or a `lock` at *any* timestamp. Otherwise it writes `data@start_ts` and `lock@start_ts`, which points to the primary.
3. *Commit.* The transaction gets `commit_ts`. In one row transaction on the primary it checks that its lock still exists, writes `write@commit_ts → start_ts` and erases the lock. This is the commit point. Secondaries then get write records and lock erasures via plain Bigtable writes, outside a row transaction (Fig. 6).
4. *Get.* If any lock exists in `[0, start_ts]`, the read backs off and possibly cleans up. Otherwise it reads the latest `write` in that range and follows its pointer to the data. Reads take no locks; the paper names more efficient reads as SI's main advantage over a serializable protocol, at the cost of write skew (§2.2).

**Lazy crash recovery (§2.2).** A client that hits a stranded lock checks the primary. If the primary has been replaced by a write record, the lock is rolled forward. If the primary lock is still present, the transaction is rolled back. Because commit and cleanup both mutate the primary under a Bigtable row transaction, only one of them can win. Locks are cleaned only if the owner's Chubby liveness token is gone or the wall time written in the lock is too old (refreshed during long commits).

**Timestamp oracle (§2.3).** The oracle persists only the high end of each allocated range and serves from memory (jumping forward on restart). Each worker keeps one outstanding oracle RPC, so batching grows with load. Since a writer writes all locks before requesting `commit_ts`, any later reader sees the lock or the commit record.

**Observers and notifications (§2.4).** An observer registers a function on a set of columns and runs in a *separate* transaction from the write that triggered it. So, unlike database triggers, observers do not maintain invariants. They structure a computation. Guarantees:
- At most one observer transaction commits per change, enforced by a conflict on the ack column.
- Several writes may collapse into a single run ("message collapsing").

Dirty cells are found by a distributed scan of `notify`, kept in its own locality group so the scan touches millions of dirty cells, not trillions of cells. Scanners start at random keys and, to avoid "bus clumping", jump elsewhere when they catch another thread. *Weak notifications* write only `notify` (no conflicts) and are used to split hotspot observers.

**Engineering choices (§2.5).** Conditional mutations (one-RPC lock read-modify-write), several-second batching of lock writes and reads per tablet server, history-based read prefetching, and thread-per-request with thousands of blocking threads per machine.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Average age of documents in search results | Reduced by 50% (Abstract); "nearly 50 percent" (§1) | Caffeine vs. batch indexer | Abstract, §1 |
| Document processing latency | "factor of 100" lower on average (§1); median "over 100x faster" (§3.1) | Production indexing | §1, §3.1 |
| Old pipeline | 100 MapReduces; each document spent 2–3 days being indexed | Pre-Percolator base index | §3.1 |
| Observers in Caffeine | ~10 (vs. 100 MapReduces) | Production | §2.4, §3.1 |
| Document collection size | 3x larger than the previous system | Production | §3.1 |
| Resource use | Roughly twice as many resources for the same crawl rate | Production | §3.1 |
| Bigtable ops per document | ~50 | Percolator indexing | §2.5 |
| Bigtable reads saved by prefetching plus cache | Factor of 10 | Percolator | §2.5 |
| Timestamp oracle throughput | ~2 million timestamps/s | Single machine | §2.3 |
| Clustering benchmark setup | 1B-document repository, 3 clustering keys from 750M keys, 3.3 documents per cluster on average, 93% in non-singleton clusters, 240 machines | Synthetic | §3.1 |
| Clustering delay at 1% crawl rate per hour | MapReduce ~20 min of processing, ~30 min crawl-to-cluster delay; Percolator ~2 s average, "about 1000x faster" | Fig. 7 | §3.1 |
| Percolator saturation | Latency goes to effectively infinite at a 40% per hour crawl rate; MapReduce sustains more than 100% | Fig. 7 | §3.1 |
| Read throughput | Bigtable 15,513/s; Percolator 14,590/s; relative 0.94 | Single tablet server, data cached, batching off | Fig. 8, §3.2 |
| Write throughput | Bigtable 31,003/s; Percolator 7,232/s; relative 0.23 ("roughly a factor of four overhead") | Single-cell write transactions | Fig. 8, §3.2 |
| TPC-E-like scaling | Essentially linear from 11 to 15,000 cores | Synthetic TPC-E | Fig. 9, §3.3 |
| TPC-E-like throughput | 11,200 tps on 15,000 cores; reference commercial system 3,183 tpsE on 64 Nehalem cores | Synthetic TPC-E | §3.3 |
| CPU per transaction vs. the reference DBMS | Authors' estimate: roughly 30x more | Synthetic TPC-E | §3.3, §5 |
| TPC-E-like transaction latency | 2–5 s average; outliers can take several minutes | Synthetic TPC-E | §3.3 |
| Fault injection | Killed 1/3 of 15 tablet servers at 17:09; tps dips, then recovers as tablets are reloaded | Fig. 10 | §3.3 |

Consistency notes: the paper calls the 100x latency gain an *average* in §1 and a *median* in §3.1. Fig. 7 is labelled as *median* clustering delay, while the §3.1 text gives the MapReduce delay (~30 min) and the Percolator delay (2 s) as *averages*.

## Limitations

- **Latency is not a goal.** Lazy cleanup can delay commits by tens of seconds; batching and backoff give multi-second transactions with minute-long outliers (§2, §2.5, §3.3).
- **Snapshot isolation only.** Write skew is possible (§2.2).
- **Aggressive aborts, no deadlock detector**, acceptable only under low contention (§2.2, §2.5). Hot counters (the omitted TPC-E broker update) need side tables or weak notifications (§3.3, §2.4).
- **Efficiency.** ~4x write overhead and an estimated ~30x CPU per transaction vs. a shared-memory DBMS (§3.2, §3.3).
- **Single point of ordering.** Every transaction contacts one timestamp oracle twice (§2.3).
- **Single datacenter.** Bigtable's per-tablet cross-datacenter replication would break transactional invariants, so Percolator accepts single-datacenter availability (§4).
- **Weak observer semantics.** Triggering is not atomic with the triggering write, and infinite notification cycles are the user's responsibility (§2.4).
- **Not for bulk work.** When the update rate approaches the size of the repository, streaming wins over random lookups and MapReduce is better (§3.1).

## Relation to other systems

- **MapReduce** (paper's comparison). Cheaper per byte for whole-corpus work, but latency is bounded by full scans and stragglers; Percolator trades ~2x resources for far lower latency at single-digit crawl rates (§3.1).
- **Bigtable** (paper's comparison). The substrate; Percolator adds multi-row transactions and observers but loses cross-datacenter replication (§2.1, §4).
- **Sinfonia, CloudTPS, ElasTraS** (paper's comparison). Sinfonia's mini-transactions must declare their read and write sets up front. CloudTPS coordinates through an intermediate tier of local transaction managers, while Percolator's clients coordinate directly. ElasTraS offers only mini-transaction semantics and nothing for structuring computation (§4).
- **DryadInc / incremental MapReduce** (paper's comparison). A middle ground reusing prior batch computation; Percolator works per document (§4).
- **Spanner** (Own analysis). It keeps transactions on a sharded store but replaces the single timestamp oracle with TrueTime-bounded clocks. It adds Paxos replication and serializable, externally consistent transactions, which addresses Percolator's single-datacenter and SI-only limits.
- **TiKV/TiDB** (Own analysis). Their transaction layer is widely described as Percolator-style. This note does not detail it, because it was not checked against an official TiKV page here.

## Takeaways for practice

- Strong consistency can be layered on an existing replicated KV store: keep lock state in the data's rows and make one primary cell the atomic commit/abort arbiter.
- Reader-driven lazy cleanup with liveness tokens and wall-time leases avoids a recovery service, at the cost of tail latency; it suits bookkeeping/batch paths more than request paths.
- A central sequencer scales far if it persists only range high-water marks and clients keep one in-flight request (§2.3).
- For reconcilers in schedulers/job platforms: at-most-once commit per change, message collapsing, a separately stored dirty set, and randomized scanner repositioning against convoying.
- Fix hotspots structurally (split observers, side-table aggregation) rather than with retries.
- Budget for the layering tax: the overheads were acceptable only because they bought horizontal scale and freshness.

## References

- Paper (Google PDF): https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36726.pdf
- USENIX OSDI 2010 page: https://www.usenix.org/conference/osdi10/large-scale-incremental-processing-using-distributed-transactions-and
- Code / blog: none official
