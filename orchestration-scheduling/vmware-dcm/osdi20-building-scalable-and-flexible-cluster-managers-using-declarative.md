---
title: 'Building Scalable and Flexible Cluster Managers Using Declarative Programming'
authors:
- Lalith Suresh
- João Loff
- Faria Kalim
- Sangeetha Abdu Jyothi
- Nina Narodytska
- Leonid Ryzhyk
- Sahan Gamage
- Brian Oki
affiliations: 'VMware, IST (ULisboa) / INESC-ID, UIUC, UC Irvine'
venue: 'OSDI'
year: 2020
abs_url: https://www.usenix.org/conference/osdi20/presentation/suresh
pdf_url: https://www.usenix.org/system/files/osdi20-suresh.pdf
code_url: https://github.com/vmware/declarative-cluster-management
note_type: deep-read
written_at: '2026-11-25'
---

# Building Scalable and Flexible Cluster Managers Using Declarative Programming

> **Why it matters:** DCM shows that a production-style scheduler (Kubernetes) can be rebuilt as "cluster state in SQL tables + constraints as SQL views + a compiler that emits a CP-SAT model", which gets better placement quality and features like global preemption without writing a custom heuristic for each policy.

## Problem

Cluster managers such as Kubernetes, VMware DRS, OpenStack and OpenShift keep solving combinatorial problems (initial placement, load balancing, reconfiguration) under many hard and soft constraints. In practice developers solve them with system-specific best-effort heuristics. The paper calls this "a software engineering dead-end" (§2):

- **Decision quality.** kube-scheduler places one pod at a time from a queue and "only considers a random subset of nodes". It can therefore miss feasible nodes, and it can commit to placements that block pods still waiting in the queue (§2).
- **Missing features.** Global reconfiguration, such as preempting a lower-priority pod on *another* node so a high-priority pod fits, cannot be expressed in the per-pod architecture (§2, Fig. 3).
- **Extensibility.** Kubernetes has "30 policies for driving initial placement alone" (§1); the paper lists them as hard constraints H1–H20 and soft constraints S1–S9 (§2, Fig. 2; the text also calls this Table 2). Inter-pod affinity and service affinity depend on fragile caching and precomputation. The paper cites upstream issues about both, and says adding VMs alongside pods would need "a complete rewrite". Policy-level feature additions took "multiple months' worth of effort" (§1, §2).

## Core design

### Programming model (§3)

- **State as relations.** The developer designs a schema and keeps cluster state (pods, nodes, labels, reservations) in a relational database. The prototype uses H2 in memory, fed by the scheduler's subscriptions to the Kubernetes API (§5).
- **Decision variables as columns.** A table annotated `-- @variable_columns (node_name)` marks the columns the solver fills in. In `pods_to_assign`, for example, `node_name` is unknown and every other column is an input (§3, Fig. 4).
- **Hard constraints** are SQL views annotated `@hard_constraint` that use a `check` clause, for example "every pending pod's node is in `valid_nodes`" (Fig. 5), or membership in a computed `candidate_nodes_for_pods` view for affinity (Fig. 7).
- **Soft constraints** are views annotated `@soft_constraint` that return a single integer. DCM maximizes the sum of all soft constraints. Load balancing is written as "maximize the minimum spare CPU across nodes" (Fig. 6).
- **Runtime API** (Fig. 8). `DCM.compile(schema)` generates an encoder, `model.connect(db)` binds it to the database over JDBC, and `model.solve(timeout)` returns the tables with the variable columns filled in. The database is the input to every `solve()`. DCM does not assume the caller applied the last solution, because the caller may reject it or the reconfiguration may fail.
- **Search scope is a data decision.** The developer controls problem size by choosing which rows go into the input tables. Incremental placement uses a bounded batch of new pods. Preemption also inserts already-placed pods into the same table, and a bounded number of them may be assigned to a "null node", which means preempted (§3, §6.2).

### Compiler (§4.1)

- **Front end.** The compiler parses SQL tables and views and evaluates in the database every part that does not touch a variable column. Supported SQL includes joins, anti-joins, group-by, aggregates, (correlated) subqueries and ARRAY columns, plus user-defined aggregates such as `all_different` (§4.1.1–4.1.2).
- **IR.** The remaining query is lowered to a list-comprehension IR, where standard rewrites such as subquery unnesting are easy to apply (§4.1.2).
- **Back ends.** The main back end is OR-tools CP-SAT. It generates Java that reads state from the database and builds the model, using hash-based lookups where possible and nested loops otherwise. A MiniZinc back end was the first prototype. It "could not scale" beyond 50–100 nodes and is now used mainly for debugging (§4.1.2).
- **Rewrite rules that make the model tractable** (§4.1.3, Figs. 10–11):
  - *Fixed arity*: sums of predicates replace option-type encodings of "sum over a filtered subset of a variable column".
  - *Scalar products*: linear expressions are emitted directly.
  - *Global constraints*: capacity joins are encoded with `cumulative`, which needs O(|pods|+|nodes|) auxiliary variables.
  - *Half reification*: used when only one direction of an implication is needed.

### Debugging (§4.2)

When there is no feasible solution, DCM maps the solver's unsatisfiable core back to the responsible SQL constraints and table records. In the paper's example, a new affinity policy turned out to conflict with a capacity constraint; the policy itself was not buggy.

### Case studies (§5)

1. **Kubernetes scheduler.** It runs as a pod against the same APIs as the default scheduler and schedules pods in batches (at most 50 in the evaluation, §6.1). It implements H1–H20 except the cloud-specific volume policies H16–H20. The main performance-engineering work was index selection in H2: an OR in a join predicate defeated the index, so the query was split into a UNION, and triggers emulate materialized views for per-node reservation counters.
2. **VM load balancer** for a commercial VM management product.
3. **Management plane** for a distributed transactional datastore.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| p95 end-to-end pod creation latency, DCM vs default | 5.9 s vs 12.45 s ("improves ... by 53%") | 500-node AWS cluster, Azure 2019 trace at 20× speed, anti-affinity fraction F = 100% | §6.1, Fig. 12 |
| p95 end-to-end latency, default scheduler | 4.14 s at F = 0 rising to 12.45 s at F = 100 | same | §6.1, Fig. 12 |
| p95 end-to-end latency, DCM at F = 0 | 5.33 s (slower than the default at this point) | same | §6.1, Fig. 12 |
| Per-pod scheduling latency median (p95), F = 0 | DCM 3.11 ms (14.46 ms) vs default 2.55 ms (6.19 ms) | same | §6.1, Fig. 13 |
| Average per-pod scheduling latency, F = 100 | DCM 5.13 ms vs default 8.04 ms ("1.6×") | same | §6.1, Fig. 13 |
| p95 batch scheduling latency, DCM | under 250 ms in all cases | same | §6.1 |
| DCM latency components per pod | DB fetch mean 0.58 ms (F = 0) to 0.88 ms; model creation avg 450 µs; solver 2.8 ms; presolve ~2.5 ms for 95% of cases | 500 nodes | §6.1, Fig. 14 |
| Model variables before presolve (avg) | 5,524 / 45,983 / 91,010 | N = 500 / 5K / 10K nodes | §6.1, Table 1 |
| Per-pod latency at 5K nodes | under 13 ms (690 ms per batch) 99% of the time | simulation, trace at 100× speed, F = 100% | §6.1, Fig. 15 |
| Per-pod latency at 10K nodes | p99 30 ms, 1.6 s per batch (the paper calls this "high") | same | §6.1, Fig. 15 |
| Pods fully placed (packing) | DCM 29 of 35 runs (worst case ≥93% of pods); baseline 3 of 35 | 35 runs × 30 nginx/Redis apps × 10 pods | §6.2 |
| Preemption convergence | DCM just under 50 s vs baseline almost 100 s | high-priority pods arriving | §6.2 |
| VM load balancing spread | baseline 39%–85% host utilization; DCM 52%–67%, with 20 migrations | production cluster, 16 hosts, 524 VMs | §6.2, Figs. 16–17 |
| VM load balancer decision time | DCM ~1 s vs heuristic ~5 s | same | §6.2 |
| Headline load-balancing claim | "4× better load balancing" | commercial VM resource manager | §1 |
| Code size, K8s scheduler | ~1.5K LoC Java (+1.8K tests); ~550 lines SQL for all tables, views and policies | | §5 |
| Datastore policies | each < 10 lines of SQL | | §5 |
| DCM library | 6.1K LoC Java (+2.7K tests); OR-tools / MiniZinc back ends ~2K / ~1K LoC | | §4.3 |
| Adding VM placement to the K8s scheduler | four constraints added | | §6.3 |

Note: the intro (§1) describes the 53% result as "p99 placement latency", while §6.1 and Fig. 12 report it as the 95th percentile. The table follows §6.1.

## Limitations

- **Solver scale.** At 10K nodes, latency is dominated by presolve, partly because of an OR-tools API limitation with interval variables (§6.1). For hyperscale clusters (e.g. 100K nodes) the paper suggests partitioning into Borg-cell-like sub-clusters, but DCM does not automate it (§7). Returning good-enough solutions early is left unexplored.
- **Batch vs. latency.** At F = 0, DCM is slower than the default scheduler (Fig. 12/13). The solver path has a fixed cost that pays off only when constraints are hard.
- **Database layer.** H2 has no incremental view maintenance, so the authors emulate it with triggers and hand-tuned SQL. They mention moving toward Differential Datalog (§5, §7).
- **Usability.** DCM cannot stop users from writing SQL that compiles into an inefficient model; it warns only on some patterns, such as unindexed cross products. Developers also have to learn to state intent instead of algorithms (§7).
- **Evaluation scope.** The real cluster has 500 nodes with t3.small workers, and the evaluation focuses on the master-side scheduler. 5K/10K nodes are simulated. The datastore case study reports no performance data (§5, §6).
- (Own analysis) There is no GPU, gang/topology-aware or multi-tenant quota workload. Batch placement of up to 50 pods is incremental, so global optimality is limited to the rows the developer puts into the model.

## Relation to other systems

- **kube-scheduler (default)**: per-pod filter/score plugins over a sampled node subset. DCM replaces them with batched, solver-based placement over all nodes and adds cross-node preemption. The paper says kube-scheduler evaluates "only ... half the nodes" at this scale; when the baseline evaluates all nodes, its average latency doubles relative to DCM (§6.1).
- **Firmament / Quincy (Poseidon)**: min-cost-flow formulations scale well but make constraints such as inter-pod affinity hard to express. The paper cites Poseidon as "up to 3× slower than the default scheduler evaluating all nodes" (§8).
- **Medea, Tetrisched, other MIP/CP schedulers (Entropy)**: these also use solvers, but each has a hand-written encoder built by optimization experts. DCM's contribution is generating the encoder from SQL (§8).
- **Wrasse**: a balls-and-bins DSL whose low-level modeling language makes complex constraints hard to express (§8).
- **Meta-heuristics (VMware DRS hill-climbing, Service Fabric simulated annealing; Apollo, Hydra, Quasar, Paragon)**: DCM swaps the hand-tuned search for a general solver plus generated models (§8).
- **Declarative systems (Boom Analytics, P2, Ravel, SQCK; NetComplete, ConfigAssure, Alloy)**: earlier systems use relational or logic languages for implementation or configuration. DCM adds code generation for searching configurations with optimization objectives on standard SQL (§8).

## Takeaways for practice

- Model scheduler state relationally and make "which rows enter the solve" an explicit knob. Batch size, candidate-node filtering and "include running pods for preemption" all become data choices rather than algorithm rewrites.
- Encoding matters more than the choice of solver. The rewrite rules (fixed arity, `cumulative`, half reification) took the benchmark from minutes to 6.2 s with fixed arity alone, and later rules cut it further (Fig. 11). Anyone generating CP-SAT/MIP models should own this layer.
- Solver-based placement wins when constraints are tight (high affinity, packing, preemption). For unconstrained, high-rate placement, a greedy fast path can still be faster (F = 0 results). (Own analysis) A hybrid with a greedy fast path plus a solver for constrained batches is a natural design.
- Unsat-core-to-SQL explanations are an operational feature, not a research nicety. They answer "why is this pod pending?" in policy terms.
- Expect presolve and model construction to dominate at 10K+ nodes. Plan for partitioning (cells or sub-clusters) and incremental model maintenance from the start.
- (Own analysis) The same pattern fits GPU fleet schedulers. Gang, topology and quota constraints map naturally to views, but encoding must keep variables linear in pods + nodes to stay tractable.

## References

- Paper: https://www.usenix.org/conference/osdi20/presentation/suresh (PDF: https://www.usenix.org/system/files/osdi20-suresh.pdf)
- Code: https://github.com/vmware/declarative-cluster-management (cited as ref. [17] in the paper)
