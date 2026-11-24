---
title: 'Bigtable: A Distributed Storage System for Structured Data'
authors:
- Fay Chang
- Jeffrey Dean
- Sanjay Ghemawat
- Wilson C. Hsieh
- Deborah A. Wallach
- Mike Burrows
- Tushar Chandra
- Andrew Fikes
affiliations: 'Google'
venue: 'OSDI'
year: 2006
abs_url: https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/
pdf_url: https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/bigtable-osdi06.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Bigtable: A Distributed Storage System for Structured Data

> **Why it matters:** Bigtable is the reference design for a range-partitioned, log-structured wide-column store. A master handles placement only, tablet servers sit on a shared distributed file system, and a lock service handles membership. Many later stores and metadata services copy this split.

(Ninth author, omitted above: Robert E. Gruber.)

## Problem

Google products such as web indexing, Earth, Analytics, Orkut and Personalized Search all needed structured storage, at very different sizes and latency targets. Some workloads were throughput-bound batch jobs and others served users directly. The goal was one system "designed to reliably scale to petabytes of data and thousands of machines" (§1). Full relational semantics were deliberately out of scope. Clients get a simpler model in which they control layout and locality, and there are no cross-row transactions.

## Core design

### Data model and API (§2–3)

- A table is "a sparse, distributed, persistent multidimensional sorted map": (row, column, timestamp) → bytes.
- **Rows** are kept in lexicographic order, and any operation under a single row key is atomic. Row ranges are cut into **tablets**, the unit of distribution and load balancing. Locality comes from key choice. Webtable, for example, stores pages under reversed hostnames (`com.google.maps/...`).
- **Column families** (`family:qualifier`) are few and declared up front. Access control and accounting are per family. **Timestamps** version cells, and per-family garbage collection keeps either the last *n* versions or the versions that are new enough.
- **API:** single-row transactions, counters, cross-row write batching without atomicity, read-only Sawzall scripts that run on the server, and MapReduce adapters.

### Building blocks (§4)

- **GFS** stores the logs and data files.
- **SSTable:** an immutable ordered map made of blocks (64 KB typical) plus an index at the end of the file. The index is loaded on open, so a lookup costs one disk seek.
- **Chubby:** a lock service with five replicas and Paxos. It holds the single-master lock, the location of the root tablet, the tablet-server directory, schemas and ACLs.

### Architecture (§5)

- **Roles:** a client library, one master and many tablet servers. The master assigns tablets, balances load, garbage-collects files and applies schema changes. Data never flows through it.
- **Three-level location:** a Chubby file points to the root tablet, which points to METADATA tablets, which point to user tablets. The root tablet is never split. Clients cache locations and prefetch them: a cold lookup takes 3 round-trips and a stale one up to 6.
- **Membership (§5.2):** each tablet server creates and locks a uniquely named file in a Chubby directory. When a server seems dead, the master tries to take that server's lock itself. Success shows that Chubby is reachable and the server is not, so the master deletes the file and reassigns the server's tablets. The master "kills itself if its Chubby session expires." Tablet servers commit splits by writing METADATA.
- **Write and read path (§5.3), LSM-style:** a write is checked against a Chubby-stored writer list, appended to the commit log with group commit, then applied to the in-memory **memtable**. A read merges the memtable with the tablet's SSTables. Recovery replays the log from the **redo points** recorded in METADATA.
- **Compactions (§5.4):** a *minor* compaction writes the memtable out as an SSTable. A *merging* compaction combines a few SSTables and the memtable. A *major* compaction rewrites everything into one SSTable and drops deletion entries and deleted data, which non-major compactions may keep.

### Refinements (§6)

- **Locality groups:** families grouped into separate SSTables, so scans read only the groups they need. A group can be set in-memory; the METADATA location family is.
- **Per-block compression:** a Bentley–McIlroy long-window pass followed by a fast 16 KB-window pass.
- **Scan Cache** (key-value pairs) and **Block Cache** (SSTable blocks), plus optional per-locality-group **Bloom filters** to skip SSTables that cannot hold a key.
- **One commit log per tablet server.** Before recovery the log is sorted by (table, row, log sequence number) in parallel 64 MB segments. Two writer threads run, one active at a time, and a slow log switches to the other.
- **Tablet moves:** the source runs a minor compaction, stops serving, runs a second minor compaction, then unloads, so the destination replays no log.
- **Immutability:** SSTable reads need no locks, the master reclaims obsolete SSTables by mark-and-sweep, and child tablets share the parent's SSTables after a split. Memtable rows are copy-on-write.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Products and projects using it | more than sixty | Aug 2006 | §1, §11 |
| In production since | April 2005, after about seven person-years of work | — | §11 |
| Non-test clusters / tablet servers | 388 / about 24,500 | Aug 2006 | §8 |
| Clusters with >500 tablet servers | 12 (259 have 0–19) | — | Table 1 |
| Default tablet size | about 100–200 MB | — | §5 |
| Server hours lost to Chubby outages | 0.0047% average, 0.0326% worst cluster | 14 clusters, 11 Chubby instances | §4 |
| Compressor speed | encode 100–200 MB/s, decode 400–1000 MB/s | 2006 hardware | §6 |
| Compression space reduction | 10-to-1 (Gzip on HTML: 3–4 to 1) | Documents in a compressed locality group, one version each | §6 |
| Random reads, single server | 1212 ops/s (text: "approximately 1200"), about 75 MB/s from GFS | 1000-byte values | Fig. 6, §7 |
| Random reads per server, 1/50/250/500 servers | 1212 / 593 / 479 / 241 | 1000-byte ops/s | Fig. 6 |
| Random reads (mem) per server | 10811 / 8511 / 8000 / 6250 | 100 MB per server | Fig. 6 |
| Random writes per server | 8850 / 3745 / 3425 / 2000 | same | Fig. 6 |
| Sequential reads per server | 4425 / 2463 / 2625 / 2469 | same | Fig. 6 |
| Sequential writes per server | 8547 / 3623 / 2451 / 1905 | same | Fig. 6 |
| Scans per server | 15385 / 10526 / 9524 / 7843 | same | Fig. 6 |
| Aggregate scaling, 1 → 500 servers | "over a factor of a hundred"; mem reads "almost a factor of 300" | — | §7 |
| Benchmark GFS cell | 1786 machines | 1 GB memory per tablet server | §7 |
| Largest listed table | Crawl: 800 TB, 1000 billion cells | — | Table 2 |
| Google Earth serving index | about 500 GB, "tens of thousands of queries per second per datacenter" | — | §8.2 |

## Limitations

- Atomicity is single-row only. Secondary indices and cross-datacenter replication are future work (§11).
- Disk-backed random reads scale poorly. Each 1000-byte read fetches a 64 KB block, which saturates shared 1 Gbps links (§7). Load imbalance and contention with other processes also lower per-server rates. The paper reports no tail latencies.
- Availability depends on Chubby and GFS by construction (§4).
- There is one master per cluster, and failover goes through Chubby locks.
- Clients do the schema tuning (keys, locality groups, compression, in-memory flags), and hot spots from key design are their problem.
- The evaluation is narrow: synthetic 1000-byte values, no skewed or mixed workloads, no measured recovery times.
- (Own analysis) Sharing one log per server makes recovery heavier, since the log must be sorted before replay. The paper does not measure how long that takes.

## Relation to other systems

- **GFS and Chubby** (§4): Bigtable does no replication of its own. Durability comes from GFS and coordination from Chubby.
- **Boxwood** (§10): also layered on lower-level services, but its components sit lower than Bigtable's client API.
- **DHTs such as Chord and Pastry** (§10): Bigtable has no goal of decentralized or Byzantine-tolerant operation. It keeps keys ordered so that range scans work.
- **Oracle RAC and DB2 Parallel Edition** (§10): both are full relational systems with transactions, and RAC uses shared disks. Bigtable gives up both features to scale on GFS.
- **C-Store and LSM-trees** (§10): locality groups get column-store-like I/O benefits behind a lower-level API. The memtable/SSTable path matches LSM buffering.
- (Own analysis) **HBase** follows the same design in open source, with HDFS and ZooKeeper in place of GFS and Chubby. **Cassandra** keeps the data model and LSM engine but uses leaderless, hash-partitioned replication. **Spanner** adds the cross-row and cross-datacenter transactions that Bigtable left out.

## Takeaways for practice

- Keep the coordinator off the data path and have clients cache placement. One master can then serve thousands of workers, which also applies to scheduler and metadata services.
- Use a lease or lock service for membership. Taking the suspect's lock yourself distinguishes a dead worker from a partitioned coordinator, and a coordinator that exits when its session expires avoids split-brain.
- Keep durable state in shared storage plus a log, so that serving nodes can move freely. Checkpoint (minor compaction) before migrating.
- Immutable files simplify concurrency, garbage collection and splits. The same holds for checkpoints, cache spill files and sandbox snapshots.
- Batch small writes through a shared log with group commit, and design the recovery path at the same time.
- From §9: expect corruption, clock skew, hung machines and asymmetric partitions. Defer features until users need them (general transactions were dropped). Build in RPC tracing early. Replace complex protocols with simpler ones.

## References

- Paper (Google-hosted PDF): https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/bigtable-osdi06.pdf
- Google Research publication page: https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/
