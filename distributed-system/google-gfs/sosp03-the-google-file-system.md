---
title: 'The Google File System'
authors:
- Sanjay Ghemawat
- Howard Gobioff
- Shun-Tak Leung
affiliations: 'Google'
venue: 'SOSP'
year: 2003
abs_url: https://research.google/pubs/the-google-file-system/
pdf_url: https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/gfs-sosp2003.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# The Google File System

> **Why it matters:** It showed that one in-memory metadata master kept off the data path, large replicated chunks, primary-replica leases and a deliberately relaxed, append-oriented consistency model are enough to run hundreds of terabytes on failure-prone commodity machines, and set the template HDFS and Google's successor Colossus started from.

## Problem

Google's data-processing workloads broke classic distributed-FS assumptions (Sec. 1, 2.1):

- **Failures are the norm**: with many commodity machines and disks, something is always down, so detection and automatic recovery must be built in.
- **Files are huge**: a few million files, typically 100 MB or larger.
- **Mutations are mostly appends**, often from many concurrent producers (queues, merges), followed by sequential reads; random overwrites are rare.
- **Throughput over latency**, and **co-design is allowed**: Google owns the applications, so it can drop POSIX and push some burden (duplicates) into client libraries.

## Core design

### Architecture (Sec. 2.3-2.6)

- One **master**, many **chunkservers**, many clients. Files are split into **64 MB chunks** named by immutable 64-bit handles, stored as Linux files and replicated **3x by default**.
- **All metadata in master memory**: namespace, file-to-chunk map, replica locations; under 64 bytes per chunk and typically under 64 bytes per file (Sec. 2.6.1).
- **Operation log + checkpoints** persist namespace and file-to-chunk map; a mutation commits only once its log record is flushed locally and on remote replicas (Sec. 2.6.3, 5.1.3). Checkpoints are a compact B-tree-like form mappable into memory.
- **Chunk locations are not persisted**: the master polls chunkservers at startup and tracks them via HeartBeats, since the chunkserver "has the final word" on what it stores (Sec. 2.6.2).
- **Master off the data path**: clients fetch and cache chunk locations, then talk to chunkservers directly. No file-data caching on clients or chunkservers (Sec. 2.3-2.4).

### Leases and write path (Sec. 3.1-3.2)

- The master grants a **lease** (initial 60 s timeout, extended via HeartBeats) to one replica, the **primary**, which serializes all mutations on that chunk; secondaries apply the same order.
- **Data flow is decoupled from control flow**: the client pushes data along a linear chain of chunkservers ordered by network distance, buffered in LRU caches; then it sends the write to the primary, which assigns serial numbers and forwards to secondaries. Ideal push time for B bytes to R replicas is B/T + RL.

### Consistency and record append (Sec. 2.7, 3.3)

- Namespace mutations are atomic. A file region is **consistent** (all replicas equal), **defined** (consistent and reflects one whole mutation) or **inconsistent** (Table 1). Concurrent successful writes give consistent-but-undefined regions; failures give inconsistent ones.
- **Record append**: GFS chooses the offset and appends **atomically at least once**. Failed replicas trigger client retries, so replicas can contain duplicates and padding. Records that do not fit cause the chunk to be padded and the client to retry on the next chunk; records are capped at one quarter of the chunk size.
- Applications cope with checkpoints, self-validating self-identifying records and unique IDs to drop duplicates (Sec. 2.7.2).

### Master operations (Sec. 3.4, 4)

- **Snapshot**: revoke leases, log, duplicate metadata; reference-counted copy-on-write chunks, copied locally on the same chunkservers.
- **Namespace locking**: the namespace is a lookup table of full pathnames with read/write locks taken in a consistent order, so concurrent creates in one directory are allowed.
- **Placement**: favour below-average disk utilization, limit recent creations per chunkserver, spread across racks.
- **Re-replication priority**: furthest from replication goal first, live before deleted files, boost for chunks blocking clients; active clones are limited per cluster and per chunkserver. Periodic **rebalancing**.
- **Lazy GC**: delete renames to a hidden timestamped name; a background scan reclaims it after a configurable delay (default more than three days); orphaned chunks are found by matching HeartBeat reports against master metadata (Sec. 4.4).
- **Stale replicas**: the chunk version is bumped on every new lease; replicas reporting old versions are ignored and collected (Sec. 4.5).

### Fault tolerance (Sec. 5)

- Fast restart; external monitoring starts a new master from the replicated log, reachable via a DNS alias. **Shadow masters** serve read-only metadata, lagging typically by fractions of a second.
- Each chunkserver keeps **32-bit checksums per 64 KB block**, verifies on read and scans idle chunks; replicas are not compared because record append lets them legitimately differ.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Largest cluster | over 1000 storage nodes, over 300 TB disk, hundreds of clients | production | Sec. 1 |
| Read throughput | 10 MB/s (80% of per-client limit) at 1 client; 94 MB/s (75% of 125 MB/s link limit, 6 MB/s per client) at 16 | 16 chunkservers, 16 clients, 100 Mbps NICs, 1 Gbps inter-switch link | Sec. 6.1, Fig. 3a |
| Write throughput | 6.3 MB/s at 1 client; 35 MB/s (2.2 MB/s per client) at 16, about half the 67 MB/s limit | same | Sec. 6.1, Fig. 3b |
| Record append, one file | 6.0 MB/s at 1 client, 4.8 MB/s at 16 | same | Sec. 6.1, Fig. 3c |
| Clusters A / B | 342 / 227 chunkservers; 55 / 155 TB used; 735 k / 737 k files; 992 k / 1550 k chunks | production | Table 2 |
| Master metadata | 48 MB (A) / 60 MB (B) | production | Table 2 |
| Read rate, last hour | 562 MB/s (A) / 384 MB/s (B) | production | Table 3 |
| Master ops, last hour | 381 / 518 ops/s (A / B) | production | Table 3 |
| Master restart degraded period | typically 30 to 60 s | production | Sec. 6.2.2 |
| One chunkserver lost | ~15,000 chunks / 600 GB restored in 23.2 min (effective 440 MB/s); 91 concurrent clones at 6.25 MB/s each | Cluster B | Sec. 6.2.5 |
| Two chunkservers lost | 266 chunks at one replica restored to at least 2x within 2 min | Cluster B | Sec. 6.2.5 |
| Append : write | 108:1 bytes, 8:1 ops (X); 3.7:1 and 2.5:1 (Y) | research (X) vs. production (Y) | Sec. 6.3 |
| FindLocation share of master requests | 64.3% (X) / 65.8% (Y) | same | Table 6 |

**Note:** Sec. 6.2.4 gives a typical master load of "around 200 to 500 operations per second"; Table 3 shows Cluster B slightly above that range (533 ops/s last minute, 518 last hour).

## Limitations

- **Single master's memory and request rate bound scale.** The paper notes an earlier master was bottlenecked by sequential directory scans (Sec. 6.2.4). Google's Cloud blog says Colossus was built "to solve scaling limits we experienced with ... GFS when trying to accommodate metadata related to Search".
- **Failover is external, not built in** (Sec. 5.1.3), and a restarted master is degraded for 30 to 60 s while it gathers chunk locations; shadow masters serve reads only.
- **Relaxed consistency leaks into applications**: duplicates, padding and undefined regions must be handled by client libraries.
- **Small-file hot spots**: a single-chunk executable launched on hundreds of machines overloaded its chunkservers; fixed with higher replication and staggered starts (Sec. 2.5).
- **Replication-only storage** uses more raw capacity than striped schemes like xFS and Swift (Sec. 8).
- **Throughput, not latency**: writes reach about half the network limit, which the authors blame on their network stack interacting poorly with pipelining (Sec. 6.1); no tail-latency study.
- (Own analysis) Numbers reflect 2003 hardware (100 Mbps NICs, IDE disks, Linux 2.2/2.4 issues in Sec. 7); only the trade-offs transfer.

## Relation to other systems

- **NASD** (Sec. 8): closest prior work; GFS uses commodity chunkservers instead of a changed device model and adds replication, rebalancing and recovery.
- **xFS, Frangipani, GPFS, Minnesota GFS** (Sec. 8): decentralize metadata with distributed algorithms; GFS keeps a central master for simplicity and better placement, and replicates instead of striping with parity.
- **Lustre / AFS** (Sec. 8): Lustre shares the aggregate-throughput goal, but GFS drops POSIX; AFS shares a location-independent namespace but does not spread a file across servers and relies on client caching.
- **HDFS** (Own analysis, from the Apache r3.2.0 architecture guide): same shape (NameNode/DataNodes, EditLog/FsImage, rack-aware 3-way replication, write-once plus append), 128 MB blocks, and optional multi-NameNode HA; the guide cites Nutch, not GFS, as its origin.
- **Colossus** (Google Cloud blog, 2021): called GFS's successor; metadata served by horizontally scaling "Curators" on Bigtable, data flowing directly between clients and "D" servers, "Custodians" doing background balancing and reconstruction. The post claims Colossus scaled "over 100x over the largest GFS clusters".

## Takeaways for practice

(Own analysis.)

- **Keep the control plane off the data path and coarse-grained.** Large units plus client-cached metadata let one master serve a cluster; the same holds for checkpoint stores, dataset services and KV-cache stores.
- **Leases plus epoch numbers** are a compact pattern for leader-ordered replicated state where rejoining members must be fenced.
- **At-least-once append with idempotent consumers** fits training logs, metrics streams and RL trajectory buffers better than strong overwrite semantics.
- **Recovery is a scheduling problem**: prioritize by distance from goal and blocked clients, and throttle repair bandwidth so it does not starve foreground jobs; apply the same to checkpoint restore and job restarts on GPU clusters.
- **Plan to shard metadata early**; GFS's own successor was driven by metadata scale.
- **Synchronized starts create hot spots** (container images, model weights): replicate more or stagger, as in Sec. 2.5.

## References

- Paper: https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/gfs-sosp2003.pdf
- Google Research page: https://research.google/pubs/the-google-file-system/
- Colossus (Google Cloud blog, 2021): https://cloud.google.com/blog/products/storage-data-transfer/a-peek-behind-colossus-googles-file-system
- HDFS Architecture (Apache Hadoop r3.2.0): https://hadoop.apache.org/docs/r3.2.0/hadoop-project-dist/hadoop-hdfs/HdfsDesign
