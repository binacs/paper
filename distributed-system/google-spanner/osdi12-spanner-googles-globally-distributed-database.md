---
title: 'Spanner: Google''s Globally-Distributed Database'
authors:
- James C. Corbett
- Jeffrey Dean
- Michael Epstein
- Andrew Fikes
- Christopher Frost
- JJ Furman
- Sanjay Ghemawat
- Andrey Gubarev
affiliations: 'Google'
venue: 'OSDI'
year: 2012
abs_url: https://www.usenix.org/conference/osdi12/technical-sessions/presentation/corbett
pdf_url: https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Spanner: Google's Globally-Distributed Database

> **Why it matters:** Spanner shows that a clock API with an explicit, bounded error lets a sharded, Paxos-replicated database give externally consistent distributed transactions and lock-free global snapshot reads, at the cost of a few milliseconds of commit wait.

## Problem

Bigtable gave Google scale but only single-row atomicity and eventually consistent cross-datacenter replication. Megastore added synchronous replication and a semi-relational model, but its write throughput was poor (§2.3, §6). Applications such as Google's advertising backend wanted schemas, cross-shard transactions, synchronous geo-replication with controllable placement, and globally consistent reads, on a system designed for millions of machines across hundreds of datacenters (§1). The hard part is ordering transactions on disjoint Paxos groups without a central sequencer.

## Core design

**Data model and directories (§2, §2.2, §2.3, Fig. 4).** A universe has zones; each zone has a zonemaster and 100 to several thousand spanservers, each serving 100–1000 tablets of `(key, timestamp) -> value` data on Colossus (§2, §2.1). Tables are schematized and semi-relational. A `DIRECTORY` table's row plus child rows declared `INTERLEAVE IN PARENT` form a *directory*: contiguous keys sharing a prefix, the unit of placement and movement. Applications tag directories with administrator-defined placement "menus" (replica count, regions). `Movedir` copies a directory between Paxos groups in the background and finishes with a short transaction for the last nominal data, so clients are not blocked. Large directories split into *fragments* that can live in different groups.

**Paxos groups, leader and lock table (§2.1, §4.1.1).** Each tablet is replicated by one Paxos state machine. A group has a long-lived leader holding time-based leases (default 10 s) whose intervals are disjoint across leaders; a leader abdicates only after `TT.after(s_max)`. Only the leader keeps the lock table (key ranges to 2PL state); transactional operations lock there, others bypass it. Leaders of groups in distributed transactions also run a transaction manager, so every 2PC participant is itself replicated.

**TrueTime (§3, Table 1).** `TT.now()` returns `[earliest, latest]`, guaranteed to contain absolute time; `TT.after(t)` / `TT.before(t)` test whether `t` has definitely passed / not arrived. Epsilon is half the interval width. Time masters per datacenter use GPS or, for "Armageddon masters", atomic clocks, and cross-check each other. Each machine's daemon polls several masters, rejects outliers with a Marzullo variant, and between polls grows epsilon at an assumed worst-case drift, giving a sawtooth. Machines exceeding the drift bound are evicted.

**Commit wait (§4.1.2).** With all locks held, the coordinator picks commit timestamp `s >= TT.now().latest` (start rule), then waits until `TT.after(s)` before the data is visible (commit-wait rule). Timestamp order thus matches real-time order: external consistency. Expected wait is at least 2×epsilon-bar and overlaps Paxos replication.

**Read-write transactions with 2PC across groups (§4.2.1).** Clients buffer writes and read under wound-wait locking. At commit the client picks a coordinator group and sends buffered writes to all participant leaders. Each participant takes write locks, picks a prepare timestamp above any it has issued, logs prepare via Paxos and notifies the coordinator. The coordinator skips prepare, picks `s` at least every prepare timestamp, above `TT.now().latest` and its own prior timestamps, logs commit via Paxos, commit-waits, then notifies client and participants, which apply at `s` and release locks.

**Lock-free snapshot reads and safe time (§4.1.3, §4.1.4, §4.2.2, §4.2.4).** Each replica tracks `t_safe = min(t_safe^Paxos, t_safe^TM)`: the highest applied Paxos write, and (if transactions are prepared) the minimum prepare timestamp minus one. Any replica serves reads at `t <= t_safe` without locks. A single-group read-only transaction reads at the leader's `LastTS()`; a multi-group one reads at `TT.now().latest` without negotiation and may wait for safe time. Snapshot reads take a timestamp or staleness bound. Leaders issue `MinNextTS(n)` promises to advance safe time on idle groups; prepared timestamps are tracked per key range in the lock table.

**Schema changes (§4.2.3).** A schema change is a non-blocking transaction at an explicit *future* timestamp `t`, registered during prepare. Operations before `t` proceed; those at or after `t` wait for it. Plain 2PC is infeasible because a database may span millions of groups.

**F1 (§5.4).** F1, the rewritten advertising backend, replaced manually sharded MySQL whose last resharding took more than two years across dozens of teams. A directory roughly corresponds to one customer. The only schema-level tuning reported was preferred leader placement, and automatic failover during unplanned cluster failures was nearly invisible to F1.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Clock uncertainty | generally < 10 ms | production TrueTime | §1 |
| epsilon, typical | about 4 ms most of the time; sawtooth 1–7 ms per poll interval (0–6 ms drift, about 1 ms comms) | timeslave daemons | §3 |
| Poll interval / assumed drift | 30 s / 200 µs/s | timeslave daemon | §3 |
| Paxos leader lease | 10 s default | per group | §2.1, §4.1.1 |
| Directory move | 50 MB in a few seconds | Movedir | §2.2 |
| Idle-group safe-time advance | every 8 s (worst case about 8 s stale) | MinNextTS | §4.2.4 |
| Write latency, 1 replica | 14.4 ± 1.0 ms vs 9.4 ± 0.6 ms with commit wait disabled ("1D") | 4 KB ops, 1 spanserver/zone | Table 3 |
| Commit wait / Paxos latency | about 5 ms / about 9 ms | 1-replica microbenchmark | §5.1 |
| Snapshot-read throughput | 13.5 → 38.5 → 50.0 Kops/s | 1 → 3 → 5 replicas | Table 3 |
| Read-only txn latency | 1.3–1.4 ms | 1–5 replicas | Table 3 |
| 2PC latency, mean / p99 | 17.0 / 75.0 ms (1 participant); 42.7 / 93.7 ms (50); 150.5 / 320.3 ms (200) | 3 zones × 25 spanservers | Table 4 |
| Leader-zone hard kill | all groups have leaders again about 10 s after the kill; soft kill (handoff first) costs about 3–4% throughput | 5 zones × 25 spanservers, 1,250 groups, 50K reads/s | §5.2, Fig. 5 |
| F1 dataset | tens of TB uncompressed | production | §5.4 |
| F1 replication | 5 replicas: 2 US west coast, 3 US east coast | production | §5.4 |
| F1 fragments | >100M directories with 1 fragment; 7 with 100–500 fragments (secondary indexes) | production | Table 5 |
| F1 latency (mean, count) | all reads 8.7 ms, 21.5B; single-site commit 72.3 ms, 31.2M; multi-site commit 103.0 ms, 32.1M | 24 h, east-coast F1 servers | Table 6 |

## Limitations

- Correctness rests on the epsilon bound; commit wait scales with it, and keeping it tight needs GPS/atomic-clock hardware and operational discipline. Sub-1 ms epsilon is only predicted (§7).
- Hard leader failure costs about one lease (10 s) of unavailability; lease release on leader failure was still being designed (§5.2).
- Multi-group read-only transactions do no timestamp negotiation and may block on safe time; prepared transactions hold back `t_safe` (§4.1.3, §4.2.2).
- Pessimistic 2PL gives fat write tails from lock conflicts (§5.4), and 2PC latency climbs past about 50 participants (Table 4).
- No automatic secondary indexes or load-based resharding yet, and node-local structures were weak for complex SQL (§7). Microbenchmarks ran on timeshared machines with one spanserver per zone (§5.1).

## Relation to other systems

- **Bigtable (OSDI 2006).** A sparse, persistent, multidimensional sorted map with only single-row atomic read-modify-write; timestamps may be client-assigned, and cross-datacenter replication was future work (Bigtable §2, §3, §11). Spanner adds global timestamps, Paxos replication and cross-row transactions.
- **Megastore (CIDR 2011).** ACID within an *entity group*, whose log is replicated by Paxos per log position with no dedicated master; cross-group work uses queues or discouraged 2PC, and it suggests a few writes per second per group (Megastore §2.2.1, §3.3, §4.4.2, §4.8). Spanner keeps the hierarchical schema but uses long-lived leaders with lock tables; its §6 says Megastore throughput "collapses" at several writes per second per group.
- **Percolator (OSDI 2010).** Snapshot-isolation transactions on Bigtable, with locks in Bigtable columns, a central timestamp oracle, lazy cleanup and relaxed latency (Percolator §2.2, §2.3). Spanner is serializable and externally consistent, replaces the oracle with TrueTime, and targets OLTP latency across datacenters.
- **Calvin (SIGMOD 2012).** Orders transaction inputs in 10 ms epochs before execution, locks deterministically, replicates inputs rather than effects and avoids a commit protocol, but needs read/write sets up front (Calvin §3). Spanner supports interactive transactions at the cost of 2PC and commit wait; its §6 notes Calvin lacks external consistency.
- **CockroachDB (official docs).** Hybrid logical clocks (physical time plus a logical counter, propagated on messages) instead of bounded-error hardware. A read hitting a value in its uncertainty window pushes its timestamp and refreshes reads, or retries; a node whose clock is off from at least half its peers by 80% of the maximum offset crashes itself. Serializability holds regardless of skew, but excess skew can break single-key linearizability for causally dependent transactions. Spanner pays commit wait on every write; CockroachDB pays uncertainty restarts and gives a weaker real-time guarantee.

## Takeaways for practice

- Put uncertainty in the clock API. An interval with a hard bound turns "wait out the error" into a provable rule; the same applies to leases and fencing in schedulers.
- Make placement a schema concept. Interleaving keeps most work single-group: in F1, more than 100M directories have one fragment (Table 5). Shard by the tenant or job key transactions actually touch.
- Long-lived leaders that own lock and transaction state make replicated 2PC affordable and remove the blocking coordinator.
- Safe time lets followers serve consistent reads; plan for prepared transactions and idle groups holding it back.
- Future-timestamped schema changes avoid a global barrier, which also fits control-plane config rollouts.
- Lease length is a trade-off: 10 s leases gave stable leaders but about 10 s recovery on hard failure (§5.2).

## References

- Paper: https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf (landing page: https://www.usenix.org/conference/osdi12/technical-sessions/presentation/corbett)
- Bigtable (OSDI 2006): https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/
- Megastore (CIDR 2011): https://research.google/pubs/megastore-providing-scalable-highly-available-storage-for-interactive-services/
- Percolator (OSDI 2010): https://www.usenix.org/conference/osdi10/large-scale-incremental-processing-using-distributed-transactions-and
- CockroachDB transaction layer docs: https://docs.cockroachlabs.com/docs/stable/architecture/transaction-layer.md
