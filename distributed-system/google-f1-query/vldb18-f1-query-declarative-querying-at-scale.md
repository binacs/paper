---
title: 'F1 Query: Declarative Querying at Scale'
authors:
- Bart Samwel
- John Cieslewicz
- Ben Handy
- Jason Govig
- Petros Venetis
- Chanjun Yang
- Keith Peters
- Jeff Shute
affiliations: 'Google LLC'
venue: 'VLDB'
year: 2018
doi: 10.14778/3229863.3229871
abs_url: https://doi.org/10.14778/3229863.3229871
pdf_url: https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/fa380016eccb33ac5e92c84f7b5eec136e73d3f1.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# F1 Query: Declarative Querying at Scale

> **Why it matters:** F1 Query shows that one fully disaggregated SQL engine with stateless servers and three execution tiers (single-node, in-memory distributed, MapReduce batch) can serve OLTP point lookups, interactive OLAP and multi-hour ETL over storage systems it does not own.

## Problem

Data for a single Google application is often split across Spanner, Bigtable, Mesa and files on Colossus (Sec. 1). Separate engines covered transactional queries, analysis and ETL, and many ETL pipelines were hand-written MapReduce/FlumeJava code that missed optimizations like filter pushdown and attribute pruning (Sec. 4). F1 Query grew out of the F1 database's query engine. Its goals are a unified relational view over all sources, a datacenter-scale design with storage fully decoupled from compute, scaling from tiny to huge queries, and native-code business logic inside SQL. The key difficulty the paper names is high-variance latency from remote data sources (Sec. 1).

## Core design

### Control plane and modes
- A client library sends a query to any **stateless F1 server**, and an F1 Master monitors each datacenter. Servers and workers hold no data, so scaling out needs no redistribution (Sec. 2).
- If the data is closer to F1 servers in another datacenter, the server **bounces the query back to the client**, which resends it there (Sec. 2).
- **Central mode**: a single-threaded, pull-based kernel (8 KiB tuple batches) runs on the receiving server (Sec. 3.1).
- **Distributed interactive mode**: the receiving server coordinates fragments on a pool of multi-threaded workers, with pipelining and bushy parallelism. There is no checkpointing, and the client library retries failed queries (Sec. 3.2, 3.4).
- **Batch mode**: the plan is stored and run asynchronously on MapReduce. Each fragment becomes an MR stage writing to Colossus, and identity maps are inserted so map-reduce-reduce chains fit MR (Sec. 4.1).
- The optimizer picks central or distributed with heuristics. A scan too expensive for central mode, such as a full table scan, makes the whole query distributed. The client picks interactive or batch (Sec. 2, 5.3). All modes share the plan, the kernel and a common fragment I/O interface (RPC streams or staging files) (Sec. 4.1).

### Parallelism and skew
- Fragment boundaries are derived bottom-up from each operator's input-distribution requirement, with an exchange wherever the requirement is unmet. Width starts at the leaf scans, with an upper bound, and propagates up the plan. A 50-worker and a 100-worker input join on 100 workers (Sec. 3.2, 5.4).
- A scan is asked for N partitions and may return more. The extras are **handed dynamically to free workers** to cut skew-driven tail latency (Sec. 3.3).
- Exchange uses all-to-all RPC with flow control. DAG forks buffer in memory and spill to Colossus to avoid distributed deadlock (Sec. 3.3).
- **Lookup joins** take large outer batches. This deduplicates keys, groups keys by remote partition and keeps many requests in flight, hiding the storage tail (Sec. 3.4).
- **Dynamic range repartitioning**: each sender builds a range function from its local key distribution. This gives locality on Spanner and Bigtable and spreads hot keys, and the authors observed it beating statically ideal ranges on skewed inputs (Sec. 3.4).
- Joins use broadcast hash join or a recursive hybrid hash join spilling to Colossus. Batch mode can turn a join's smaller side into SSTables for lookup joins (Sec. 3.1, 3.4, 4.1).

### Batch service
A global Spanner **Query Registry** holds all batch state. A replicated, master-elected **Query Distributor** places queries by load and data availability. Per-datacenter **Schedulers** build task dependency graphs and dispatch ready tasks to **Executors** on the MR worker pool. Since every component is stateless, a stalled query (for example, after a datacenter outage) is reassigned and restarted from scratch (Sec. 4.2).

### Optimizer and extensibility
- The optimizer is Cascades-inspired and shares principles with Catalyst. It runs AST → relational algebra (rule batches to a fixed point) → physical strategies with distribution, ordering and cardinality properties → fragments. It is **mostly heuristic**, using statistics only where they are feasible to collect (Sec. 5).
- Plan trees are immutable, arena-allocated and generated code. Rules understand protobuf fields, so field extraction is pushed into scans (Sec. 5.1–5.2, 7.2).
- SQL UDFs, UDAs and TVFs are inlined before optimization. Lua runs in a sandboxed interpreter (Sec. 6.1).
- **UDF servers** are client-owned RPC services with their own release and provisioning that isolate F1 from failures in custom code. Calls are batched and pipelined. Remote UDAs add Reaccumulate for partial aggregation. Remote TVFs stream in both directions and expose schema and partitioning properties, enabling uses like in-query model training (Sec. 6).

### Robust performance
Operators degrade gradually instead of switching modes. Sort spills only what it must, and merge-step cliffs are removed in sorting and aggregation (Sec. 7.1, Fig. 10).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Jupiter bandwidth | ≥10 Gb/s sustained, any-to-any | Clusters of tens of thousands of hosts | Sec. 3.3 |
| RPC exchange scale | well up to thousands of partitions per fragment | Distributed interactive | Sec. 3.3 |
| Interactive reliability | queries up to an hour "sufficiently reliable" | In-memory with retry | Sec. 3.4 |
| Sort cliff | runtime up 2x or more on spill | Before removal | Sec. 7.1, Fig. 10 |
| Plan-tree codegen | ~3K lines Python + ~5K lines Jinja2 → ~600K lines C++ | Optimizer | Sec. 5.1 |
| MR stage fusion | 3 stages vs. 6 by default | Example plan | Sec. 4.1, Fig. 6 |
| Weekly users | over 10,000 | Production | Sec. 8 |
| Interactive throughput | mean ~450,000 QPS (~40 billion/day); peaks to 2X without latency impact | Two-week period | Sec. 8, Fig. 11 |
| Central latency p50/p90/p99 | <10 / <50 / <300 ms | Interactive | Sec. 8, Fig. 12 |
| Distributed latency p50/p90/p99 | 50 / 200 / 1000+ ms | Interactive | Sec. 8, Fig. 12 |
| Batch volume | ~55,000 queries/day; ~8–16 PB input/day | Batch | Sec. 8, Fig. 13 |
| Batch latency | mean well below 500 s; max 10,000+ s | Batch | Sec. 8 |
| QPS growth | almost doubled in four quarters, latency unaffected | Long-term | Sec. 8, Figs. 14–15 |
| vs. Tenzing | latency under high load roughly 45% of Tenzing's | Batch service | Sec. 9.1 |

## Limitations

- The **row-oriented kernel** trails vectorized columnar engines such as Vectorwise (Sec. 10).
- There is **no local data caching** and no locality-aware scheduling. The engine relies on caches in the sources or TableCache (Sec. 10).
- The optimizer is **heuristic**. Statistics from remote sources are hard to get, and cost-based rules are future work (Sec. 5, 10).
- **Fault tolerance is coarse**: interactive queries retry whole, and a stalled batch query restarts from the beginning (Sec. 3.4, 4.2, 9.1).
- **Batch mode runs on classic MapReduce**, with no pipelining and every exchange materialized. A FlumeJava/Dataflow port is in progress (Sec. 4.1, 9.1).
- Scale-in for medium-sized queries is weak (Sec. 10).
- The metrics cover a "representative subset" of production, with no workload breakdown, resource cost or head-to-head benchmark (Sec. 8).

## Relation to other systems

- **Dremel / BigQuery**: shares the SQL dialect. Dremel targets columnar analytics, and F1 adds OLTP-style lookup joins (Sec. 9.1).
- **Spanner SQL**: built on a transactional core with fine-grained restartability, whereas F1 is loosely coupled to its sources (Sec. 9.1).
- **Tenzing**: its SQL-on-MapReduce workloads moved to Dremel or F1 batch mode, which has better fault tolerance, isolation and fairness (Sec. 9.1).
- **Impala / Snowflake**: decouple storage from compute but expect their own storage layer or ingested data, and focus on analytics (Sec. 9).
- **Hive / Pig / Spark**: batch paradigms, while F1 runs the same SQL interactively or in batch (Sec. 9). The optimizer shares principles with Catalyst (Sec. 5). (Own analysis) Spark SQL later grew interactive use, and F1's distinction is its tiered execution and out-of-process UDFs.
- **Presto** (not in the paper). (Own analysis) Presto is similar as a federated, connector-based, in-memory pipelined engine. F1 adds a fault-tolerant batch tier and OLTP-style lookup joins.

## Takeaways for practice

- **Tier execution by size and runtime behind one planner**: local for small requests, a streaming DAG for medium ones, a durable restartable tier for long ones.
- **Keep the schedulers and distributors stateless and put job state in a consistent registry.** Recovery from a datacenter failure then becomes reassignment.
- **Over-partition and assign work dynamically** to fix skew-driven tails cheaply.
- **Batch remote calls and keep many in flight.** Learning key ranges locally improves locality and absorbs hot keys.
- **Run user code in separately deployed RPC servers or sandboxed interpreters**, with batched, pipelined calls. This is a template for agent tool sandboxes and model-serving plugins.
- **Route the job to the datacenter that holds the data.** Fast fabrics remove locality concerns within a datacenter, not across datacenters.
- **Design out performance cliffs** so that estimation errors and load imbalance do not blow up runtime.

## References

- Paper (Google-hosted PDF): https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/fa380016eccb33ac5e92c84f7b5eec136e73d3f1.pdf
- DOI: https://doi.org/10.14778/3229863.3229871 (PVLDB 11(12):1835–1848, 2018)
- Code / blog: none official
