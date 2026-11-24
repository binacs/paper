---
title: 'Online, Asynchronous Schema Change in F1'
authors:
- Ian Rae
- Eric Rollins
- Jeff Shute
- Sukhdeep Sodhi
- Radek Vingralek
affiliations: 'Google, University of Wisconsin-Madison'
venue: 'VLDB'
year: 2013
abs_url: https://research.google/pubs/online-asynchronous-schema-change-in-f1/
pdf_url: https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41376.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Online, Asynchronous Schema Change in F1

> **Why it matters:** It shows how to change a shared database's schema across many stateless servers with no global barrier and no downtime: split each risky change into safe intermediate states, and use leases to guarantee that at most two adjacent schema versions are live at once.

## Problem

F1 is Google's relational layer over Spanner, serving AdWords. Many stateless F1 servers in several datacenters share one key-value store and have no global membership, so they cannot all switch schemas at the same instant (§1, Fig. 1). Availability is paramount: downtime costs revenue, and even taking part of the data offline (e.g. locking a column during an index build) is not acceptable. Schema changes are frequent, so they must barely affect response times (§1).

If servers on schema S1 and S2 write the same data at the same time, a naive change corrupts it. A server that knows about a new index inserts index entries; a server that does not know deletes the row and leaves an orphan index entry. Or a new server reads an index that old servers never maintained (§3.2–3.3, Claim 2). The question is which transitions are safe when two versions coexist, and how to make every change a chain of safe ones.

## Core design

### Data model (§2)
- Key-value store with `put`/`del`/`get`, commit timestamps and atomic test-and-set (§2.1).
- Each non-key column of a row is one KV pair keyed by (table, primary key, column). Each row also has a reserved `exists` pair. Index entries are keyed by (table, index, indexed values, primary key) (§2.3, Table 1).
- Optimistic, timestamp-based concurrency control "similar to Percolator". Locks are named schema objects, with each column covered by exactly one lock. The default is row-level and column-level is an option (§2.5).
- There is no DDL: the full schema is a protobuf file generated from sources in version control (§4.2).

### Formal model (§3)
- **States** (§3.1): `absent`, `delete-only` (the element cannot be read, and only deletes touch its pairs; index updates may remove entries but never create them), `write-only` (all writes maintain it, but reads ignore it and indexes are not used for seeks), `public`. Constraints have their own `write-only` state: new writes are checked, but existing data may still violate the constraint.
- **Consistency** (Def. 4): seven clauses. Violations are either *orphan data anomalies* (extra pairs) or *integrity anomalies* (missing pairs or violated constraints).
- **Consistency-preserving change** (Def. 5): operations under either schema keep a database that is consistent with both schemas consistent with the other one. The relation is symmetric (Claim 1), so every add sequence reversed is a valid drop sequence.
- **Sequences:**
  - Optional element (e.g. optional column): absent → delete-only → public. A drop reverses this and needs a reorganization to remove pairs while only delete-only is live (§3.3.1, Claims 4–5).
  - Required element (e.g. index, required column): absent → delete-only → write-only → *backfill* → public (§3.3.2, Claims 6–7).
  - Theorem 1: any add or drop of a structural element is a sequence of consistency-preserving changes plus at most one reorganization.
  - Constraint: absent → write-only → public. The proof is omitted for space (§3.3.3).
  - Lock coverage L1 → L2: a direct switch admits non-serializable schedules (Claim 8). The fix is a *dual-coverage* state in which operations read, validate and update both locks, plus a reorganization that atomically sets L2's timestamp to the larger of the two lock timestamps per row, then a move to L2 alone (§3.4, Claim 9).
- Fig. 3 shows how transitions for different elements are batched into shared intermediate schemas.

### Implementation (§4)
- **Leases** (§4.3): each server holds a schema lease of "multiple minutes" and renews it by re-reading the schema from a well-known location in Spanner. A server that cannot renew terminates, and the cluster manager restarts it elsewhere. At most one new schema is written per lease period, so after one lease period every server either uses the new schema or cannot commit. This is the two-version bound. Allowing k+1 versions was considered and rejected as too complex.
- **Write fencing** (§4.1, §4.3): writes carry a Spanner-enforced deadline, so a write cannot commit after its schema's lease expires. The paper calls this necessary for correctness. Transactions may span renewals, but each write must use a schema with an active lease.
- **Garbage collection** (§4.1): Spanner's own schema makes pairs of dropped elements inaccessible and collects them, so drops need no explicit delete pass. The paper treats this as a convenience, not a correctness requirement.
- **Process** (§4.2): administrators apply the schema from version control twice a week. An analysis step derives the intermediate schemas and reorganizations, and an execution step applies them in order, waiting at least one lease period between steps.
- **Reorganizer** (§4.4): built on MapReduce. It is resumable and idempotent, and runs alongside full user traffic. Map tasks read rows at a snapshot taken when the change starts and add or remove pairs. A row that a user transaction updated after that point is left alone (Thomas write rule).
- **Schema repository** (§4.5): servers hold several versions in memory, each with its lease times. New writes use the newest version, and pending writes finish under their original one. Writes fenced at lease expiry are resubmitted, which wastes work. The paper calls renewal at half the lease remaining a reasonable setting. The canonical schema is replicated and updated by test-and-set, and servers skip the full re-read if its commit timestamp has not changed (§4.3).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Max schema versions in use | 2 | Protocol invariant | §1, §4.3 |
| Schema lease length | "multiple minutes" (typical) | Production F1 | §4.3 |
| Lease renewal point | Half of lease period remaining | Suggested setting | §4.5 |
| Schema change cadence | Twice per week | AdWords F1 | §4.2 |
| Typical change without reorganization | 10–20 min | Bounded by lease waits | §4 (see doubts) |
| Production fleet | ~1,500 F1 servers, 5 datacenters | Log study | §5 |
| Log study span | 19 schema changes, ~10 weeks | AdWords logs | §5 |
| Operations observed | >1 billion without change; >50 million during change | Log study | §5 |
| Operation mix | ~75% queries, ~25% writes | Log study | §5 |
| Query latency p50 | 2.84 → 2.94 ms | No change → during change | Table 2 |
| Query latency p90 | 79.82 → 74.23 ms | No change → during change | Table 2 |
| Query latency p99 | 170.33 → 178.05 ms | No change → during change | Table 2 |
| Write latency p50 | 107.16 → 179.26 ms | No change → during change | Table 3 |
| Write latency p90 | 497.27 → 616.08 ms | No change → during change | Table 3 |
| Write latency p99 | 965.69 → 1076.69 ms | No change → during change | Table 3 |
| Bugs found by formal model | 2 subtle bugs | Production implementation | §3, §7 |
| Schema changes run in production | "hundreds" | Lifetime | §7 |

## Limitations

- **Change latency scales with the lease.** Each intermediate state costs at least one lease period, so even trivial changes take minutes. Backfill duration and throughput are not reported (§4.2–4.4).
- **Fencing costs writes.** Writes that outlive their lease are killed and resubmitted (§4.5). Median write latency rises from 107.16 ms to 179.26 ms during changes (Table 3), and §5 explains neither this nor the lower p90 query latency.
- **Correctness needs store support.** A server that cannot renew must terminate, and safety relies on Spanner-enforced write deadlines (§4.1, §4.3).
- **Scope.** It covers adds and drops of tables, columns, indexes and constraints, plus lock coverage. It does not cover type changes, renames or data migrations, and the constraint proof is omitted (§3.3.3).
- **Delayed usefulness.** A write-only index serves no reads until its backfill finishes, and write-only constraints tolerate old violations (§3.1).
- **Thin evaluation.** There is one workload and no breakdown of the 19 changes by type or by need for reorganization (§5).

## Relation to other systems

- **Spanner** (§6): supports schema changes, but makes them synchronous through synchronized clocks and global membership. F1 needs neither: its asynchrony comes from leases and the two-version invariant, and it uses Spanner only for storage, write deadlines and GC.
- **Ronström's soft schema change** (§6): old transactions finish on the replaced schema. F1 works per operation rather than per transaction, and generalizes Ronström's intermediate index state into the write-only state.
- **Mariposa** (§6): argued that distributed schema change should not depend on global membership. F1 is a concrete protocol built on that premise.
- **PRISM / SQL/SE** (§6): schema-evolution languages and query rewriting. The paper calls them complementary and implements neither.
- **Percolator** (§2.5): F1's optimistic, timestamp-based locking is modeled on it, and the lock-coverage protocol (§3.4) exists because of that design.

## Takeaways for practice

- (Own analysis) Two versions plus leases is a general recipe for rolling out any shared contract (API schema, scheduler policy, shard map) with no barrier. Bound how far a node can lag, then make each step safe between adjacent versions only.
- (Own analysis) Define per step what old-version and new-version writers may do (delete-only, write-only). This is the expand/contract discipline of service rollouts, made formal.
- (Own analysis) Leases need fencing in the shared store, such as a write deadline or epoch check. A node's own good behaviour is not enough.
- (Own analysis) Make backfill idempotent, resumable and deferential to live writers (snapshot read plus Thomas write rule), so it can run under full traffic.
- (Own analysis) Batch changes to amortize the fixed lease-period cost per step, as F1 does with its twice-weekly schema push (§4.2).
- (Own analysis) A small formal model of a rollout state machine pays off: here it found two real bugs (§3, §7).

## References

- Paper: https://research.google/pubs/online-asynchronous-schema-change-in-f1/
- PDF (Google Research): https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41376.pdf
- Proceedings: PVLDB Vol. 6, No. 11 (2013), p. 1045, front matter at http://www.vldb.org/pvldb/vol6/FrontMatterVol6No11.pdf
