---
title: 'MapReduce: Simplified Data Processing on Large Clusters'
authors:
- Jeffrey Dean
- Sanjay Ghemawat
affiliations: 'Google'
venue: 'OSDI'
year: 2004
abs_url: https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/4449.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# MapReduce: Simplified Data Processing on Large Clusters

> **Why it matters:** It showed that a deliberately restricted programming model (map, then group-by-key, then reduce) lets one runtime own parallelization, locality, load balancing and fault tolerance on thousands of unreliable commodity machines, and set the master / fine-grained-task / re-execution / backup-task template later schedulers inherited.

## Problem

Google had hundreds of conceptually simple jobs over crawled documents and logs (inverted indices, web-graph data, per-host summaries) whose logic was buried under code for parallelization, data distribution, failure handling and load balancing (§1). The environment: dual-CPU x86 Linux boxes with 2-4 GB RAM, 100 Mb/s-1 Gb/s NICs with much lower bisection bandwidth, cheap IDE disks under GFS, and clusters of hundreds to thousands of machines where failure is routine, shared via a cluster scheduler (§3).

## Core design

**Programming model (§2).** The user writes `map(k1,v1) -> list(k2,v2)` and `reduce(k2, list(v2)) -> list(v2)`. The library groups all intermediate values by key and feeds them to Reduce through an iterator, so a value list need not fit in memory. The C++ implementation passes strings. Examples: grep, URL counts, reverse link graph, inverted index, sort.

**Execution flow (§3.1, Fig. 1).**
- Input is cut into M splits, typically 16-64 MB each. The intermediate key space is cut into R partitions by a partitioning function (default `hash(key) mod R`).
- One copy of the program becomes the **master**; the others are workers. The master assigns idle workers a map or reduce task.
- A map worker parses its split, calls Map, buffers output in memory, and periodically spills it to **local disk**, partitioned into R regions. It reports the region locations to the master.
- The master forwards locations to reduce workers, which pull the data from map workers' disks by RPC, sort by key (external sort if needed), call Reduce per unique key, and append to one output file per partition in the global file system.
- The R output files are usually fed to another MapReduce job rather than merged.

**Master state (§3.2).** For every task: its state (idle / in-progress / completed) and its worker. For every completed map task: the location and size of its R intermediate regions, pushed incrementally to in-progress reducers. The master makes O(M+R) scheduling decisions and holds O(M*R) state, about one byte per map/reduce task pair (§3.5).

**Fault tolerance (§3.3).**
- *Worker failure:* on a missed ping, the worker's in-progress tasks *and completed map tasks* return to idle (map output was on its local disk); completed reduces are safe in GFS. Reducers are redirected to the new map executor.
- *Master failure:* checkpointing is possible, but the implementation simply aborts the job and leaves retry to the client.
- *Semantics:* tasks write private temporary files; the master ignores duplicate map completions; a reduce commits by **atomic rename**. Deterministic operators give sequential-equivalent output; non-deterministic ones give per-partition equivalence only.

**Locality (§3.4).** The master schedules map tasks on a machine holding a GFS replica of the split (GFS uses 64 MB blocks, typically 3 copies), or failing that on the same switch. In large jobs most input is read locally.

**Task granularity (§3.5).** M and R should be much larger than the number of machines. That gives dynamic load balancing and spreads recovery work. M is chosen for roughly 16-64 MB per task; R is a small multiple of the number of workers and is constrained because each partition is one output file.

**Backup tasks (§3.6).** Near the end of a job, the master launches duplicate executions of the remaining in-progress tasks, and whichever copy finishes first wins. This is tuned to cost no more than a few percent of extra resources.

**Refinements (§4).** Custom partitioners (e.g. `hash(Hostname(urlkey)) mod R`); sorted keys within a partition; **combiners** (map-side partial reduce for commutative, associative Reduce); pluggable readers and writers. **Bad-record skipping:** a signal handler sends a "last gasp" UDP packet with the record's sequence number, and after more than one failure on a record the master has the next attempt skip it. Also a sequential local mode for gdb, a master HTTP status page, and **counters** piggybacked on pings and de-duplicated across re-executions.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Typical production job shape | M = 200,000, R = 5,000, 2,000 workers | "often" used at Google | §3.5 |
| Master state per map/reduce pair | ~1 byte | O(M*R) state | §3.5 |
| Benchmark cluster | ~1800 machines, 2x 2 GHz Xeon (HT), 4 GB RAM (1-1.5 GB used by other tasks), 2x 160 GB IDE, 1 GbE; 100-200 Gbps aggregate at root | §5 experiments | §5.1 |
| Grep | 10^10 100-byte records, M = 15000, R = 1; 92,337 matching records | ~1 TB scan | §5.2 |
| Grep peak scan rate | >30 GB/s with 1764 workers | Fig. 2 | §5.2 |
| Grep end-to-end | ~150 s, including ~1 min startup; map input rate reaches zero at ~80 s | Fig. 2 | §5.2 |
| Sort setup | 10^10 100-byte records, M = 15000, R = 4000, <50 lines of user code, 2-way replicated output (2 TB written) | TeraSort-style | §5.3 |
| Sort, normal run | 891 s total; input peak ~13 GB/s; output 2-4 GB/s | Fig. 3(a) | §5.3 |
| Best reported TeraSort result cited | 1057 s | comparison stated by the paper | §5.3 |
| Sort, backup tasks disabled | 1283 s, stated as +44%; 5 reduce tasks still running after 960 s | Fig. 3(b) | §5.4 (also §3.6) |
| Sort, 200 of 1746 worker processes killed | 933 s, stated as +5% | Fig. 3(c) | §5.5 |
| Jobs in August 2004 | 29,423 jobs; avg completion 634 s; 79,186 machine-days | Table 1 | §6 |
| Data volume, August 2004 | input 3,288 TB; intermediate 758 TB; output 193 TB | Table 1 | §6 |
| Per-job averages, August 2004 | 157 worker machines; 1.2 worker deaths; 3,351 map tasks; 55 reduce tasks | Table 1 | §6 |
| Indexing rewrite | >20 TB raw input; 5-10 chained MapReduces; one phase ~3800 → ~700 lines of C++ | production indexer | §6.1 |

Note: the cluster is "approximately 1800 machines" (§5.1), but runs cite 1764 workers (§5.2), "about 1700 machines" (§5.3) and 1746 worker processes (§5.5); the paper does not reconcile these per-run counts.

## Limitations

- **Single master, no failover:** a master failure aborts the job (§3.3).
- **Determinism assumed** for clean semantics. Non-deterministic operators get weaker, per-partition guarantees (§3.3). There is no atomic commit across multiple side-effect files (§4.5).
- **Barrier between phases:** reduce cannot finish until all maps are done, and multi-stage pipelines such as indexing are chains of separate jobs that materialize output to GFS between stages (§3.1, §6.1). (Own analysis) This is costly for iterative workloads such as ML or graph algorithms, which §6 lists as uses.
- **Shuffle depends on map-side local disk:** a lost map machine forces re-execution of *completed* maps (§3.3).
- **Partition skew:** R is user-set, and the sort benchmark relies on a partitioner with built-in key-distribution knowledge. A general sort would need a sampling pre-pass (§5.3).
- **Benchmarks ran on a mostly idle cluster** (§5.1); cluster scheduling is delegated to an in-house system that is "not the focus" (§7).
- **Backup tasks are a heuristic** (§3.6), with no stated policy for when to speculate. (Own analysis) Later work on speculation in heterogeneous clusters challenged naive straggler detection.

## Relation to other systems

- **MPI / BSP (§7):** these offer higher-level parallel abstractions, but fault handling stays with the programmer. MapReduce restricts the model so that it can parallelize automatically and recover transparently.
- **River (§7):** River balances heterogeneous hardware by carefully scheduling disk and network transfers over distributed queues. MapReduce instead over-partitions into many small tasks that faster workers pull, and adds end-of-job redundant execution.
- **NOW-Sort (§7):** its partition-then-local-sort design matches the MapReduce shuffle, but it has no user-defined map/reduce, so it lacks MapReduce's generality.
- **Charlotte eager scheduling and Condor (§7):** backup tasks resemble Charlotte's eager scheduling, and bad-record skipping fixes Charlotte's failure mode where one bad task fails the whole computation. The underlying cluster manager is likened to Condor.
- **Hadoop MapReduce (Own analysis):** an open-source reimplementation of this design (HDFS for GFS). YARN later split cluster resource management from the per-job master.
- **Dryad and Spark (Own analysis):** both generalize the two-stage dataflow: Dryad to arbitrary DAGs, Spark to in-memory datasets recovered from lineage, targeting the iterative cases where chained MapReduces are expensive.

## Takeaways for practice

- **Restrict the interface to buy runtime freedom.** Deterministic, side-effect-free tasks make re-execution, speculation and duplicate suppression safe.
- **Over-partition work.** Many small tasks per machine give load balancing and parallel recovery; keep per-task master metadata tiny.
- **Commit atomically.** Private temporaries plus atomic rename, with duplicate completions ignored, turn at-least-once execution into exactly-once output.
- **Plan for the tail.** Without backup tasks sort took 1283 s vs 891 s (§5.4). (Own analysis) Barrier-synchronized workloads such as all-reduce training need an explicit straggler strategy.
- **Schedule toward data.** Node-then-switch locality and combiners exist because network bandwidth is scarce (§8).
- **Know where failure state lives.** Local-disk output is cheap but makes "completed" work fragile; decide which artifacts must be durable.
- **Build observability into the coordinator** (status pages, failure attribution, de-duplicated counters, §4.8-4.9).

## References

- Paper: https://storage.googleapis.com/gweb-research2023-media/pubtools/4449.pdf (Google Research-hosted PDF, marked "To appear in OSDI 2004")
- Publication page: https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/
