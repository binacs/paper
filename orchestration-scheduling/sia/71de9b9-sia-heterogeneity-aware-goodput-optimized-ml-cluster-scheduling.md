---
title: 'Sia: Heterogeneity-aware, Goodput-optimized ML-cluster Scheduling'
authors:
- Suhas Jayaram Subramanya
- Daiyaan Arfeen
- Shouxu Lin
- Aurick Qiao
- Zhihao Jia
- Gregory R. Ganger
affiliations: 'Carnegie Mellon University, Cornell University, Petuum Inc.'
venue: 'SOSP'
year: 2023
paper_id: 71de9b9cb83dcf53a86c7a3cb3ff7b36b3917978
doi: 10.1145/3600006.3613175
abs_url: https://dl.acm.org/doi/10.1145/3600006.3613175
pdf_url: https://www.pdl.cmu.edu/PDL-FTP/BigLearning/sia_sosp23-final.pdf
code_url: https://github.com/siasosp23/artifacts
note_type: deep-read
written_at: '2026-11-25'
---

# Sia: Heterogeneity-aware, Goodput-optimized ML-cluster Scheduling

> **Why it matters:** Sia is the first scheduler to co-optimize GPU type, GPU count and batch size for elastic DL jobs on a mixed-GPU cluster, with an ILP small enough to solve in about a second at 2000+ GPUs.

## Problem

Earlier schedulers handle one of two degrees of freedom. Heterogeneity-aware schedulers such as Gavel pick GPU types but treat jobs as rigid, with a user-fixed GPU count and batch size. Adaptivity-aware schedulers such as Pollux resize jobs and tune the batch size, but assume all GPUs are the same. When both are present, each leaves a lot of performance unused (Fig. 1). They also scale poorly: Gavel with contention, and Pollux with cluster size, because its genetic algorithm searches a space that is exponential in nodes and GPUs per node (§2). Combining the two raises two problems. The joint (type × count × batch size × placement) space is huge. And profiling every job on every type and size is too expensive, because jobs scale differently on different GPU types (Fig. 2).

## Core design

**Round-based, preemptive loop (§3.1, Fig. 3).** A job is submitted with `max_bsz` and `max_ngpus`, and optionally `min_ngpus`. Each round (60 s by default) runs the same pipeline:
- the **Profiler** measures new jobs on one GPU of each type;
- the **Goodput Estimator** keeps the models;
- the **Policy** solves the allocation;
- the **Placer** maps the allocation to physical GPUs and tries to avoid migrations.

Adaptive Executors report gradient and throughput statistics every 30 s and pick the batch size that maximizes goodput. A job starts on 1 GPU and grows by at most 2× per round. If a placement cannot be found, the Placer evicts jobs and retries; this is rare.

**Goodput model.** Goodput = throughput × statistical efficiency, inherited from Pollux. Statistical efficiency comes from the gradient noise scale and is kept as one model per job. Throughput is kept as one model per (job, GPU type) (§3.2). Learning rates are rescaled with the square-root rule for AdamW and with AdaScale for SGD (§3.5).

**Bootstrapping throughput on heterogeneous GPUs (§3.2).**
- *Initial profiling:* run each job on one GPU of each type, increasing the batch size until GPU memory runs out. This is typically 10 batch sizes per type, at under 20 GPU-seconds per type per job.
- *Assumption:* compute time per sample does not depend on GPU count (data parallelism with all-reduce), so only communication time has to be learned.
- *First multi-GPU allocation on type A:* assume perfect scaling (zero communication), then refine with measured communication once the job runs.
- *Unexplored type B:* `est_xput_B(N) = xput_B(1)/xput_A(1) × xput_A(N)` (Eq. 1). This assumes B's compute-to-communication scaling matches A's. The estimate is dropped once the job has run multi-GPU on B.

**Configuration space (§3.3).** A configuration is a tuple (n nodes, r GPUs, type t).
- Single-node configurations use power-of-two GPU counts up to R GPUs per node.
- Multi-node configurations use whole nodes only.
- That gives N + log₂R configurations per GPU type, instead of Pollux's full count × placement space.
- Because distributed jobs take whole nodes, two distributed jobs never share a node, which also avoids NIC contention.
- Partial-node allocations never span nodes.

**ILP (§3.4).**
- G_ij is the estimated goodput of job i on configuration j. Each row is normalized by the job's minimum-GPU configuration, so values are comparable across jobs.
- A binary A_ij selects at most one configuration per job, subject to the GPU count available per type.
- Objective: `max Σ_i Σ_j A_ij · (r_i · G_ij^p) + λ(1 − ||A_i||₁)` (Eq. 2, Eq. 4).
  - λ is a reward for scheduling every job (default 1.1, §4.3).
  - p is a fairness knob (default −0.5). When p < 0 the objective is flipped to a minimization, which favors helping the jobs that are worst off.
- The solver is GLPK_MI through CVXPY. The Policy runs as a Kubernetes service inside AdaptDL, replacing Pollux's scheduler (§3.5).

**Restart / reconfiguration cost (Eq. 3).** Each job carries a restart factor `r_i = (T_i − N_i·S_i)/(T_i + S_i)`:
- T_i is the job's age;
- S_i is the wasted GPU-seconds per restart, model-specific, 25–250 s across the Table 2 models;
- N_i is the number of past restarts.

Every configuration other than the job's current one is multiplied by r_i. Young or restart-heavy jobs are therefore pinned unless a move pays off. Preemption waits for the current minibatch to finish, checkpoints the weights, optimizer state and data-loader state, and resumes from the checkpoint on the new GPUs.

**Limited-adaptivity jobs and extensions.**
- *Strong-scaling jobs* (fixed batch size) use throughput in place of goodput.
- *Rigid jobs* get an extra binary term that chooses only the GPU type (Eq. 5).
- *Non-preemptible jobs and reservations* are added as constraints.
- *Hybrid-parallel jobs* (pipeline stages × data-parallel replicas) scale in units of P GPUs, one pipeline. The paper claims this makes Sia the first scheduler to elastically scale hybrid-parallel jobs. The parallelism degrees inside a replica stay fixed.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Avg JCT vs Gavel / Pollux | 50% / 35–50% lower | 44-GPU physical cluster (24× 2080Ti, 16× A100, 4× RTX6000), 30-job trace | §5.1 |
| Simulator fidelity | <5% error in avg JCT and makespan | Sia and Gavel, physical vs simulated | §5.1 |
| Avg JCT reduction | 30–93% | vs Pollux and Gavel, 64-GPU heterogeneous sim, Philly/Helios/newTrace | Abstract, §5.2 |
| p99 JCT and makespan reduction | 28–95% | same | Abstract, Conclusion |
| Avg JCT, Sia / Pollux / Gavel+TJ | 0.6h / 1.0h / 1.9h | Philly, heterogeneous sim | Table 3 |
| Avg JCT, Sia / Pollux / Gavel+TJ | 0.7h / 1.5h / 11.3h | newTrace (48 h, bursts up to 100 jobs/hr) | Table 3 |
| Avg GPU-hours per job, Sia / Pollux / Gavel+TJ | 4.0 / 5.6 / 9.0 | Philly | Table 3 |
| Restarts per job, Sia / Pollux | 2.9 / 5.8 | Philly | Table 3 |
| Homogeneous-cluster avg JCT, Sia / Pollux | 1.9h / 2.0h | 64× T4 | Table 4 |
| Rigid jobs, heterogeneous, vs Gavel | ~25% better | Gavel's home setting | §5.4 |
| Worst FTF ratio / unfair-job fraction | Sia 1.2 / <0.3%; Pollux 4.6 / 28%; Gavel 27.8 / 15%; Shockwave 3.3 / 14% | heterogeneous sim | §5.5, Fig. 8 |
| Policy runtime, median / p95 | Sia 96 ms / 426 ms; Pollux 2.2 s / 4.8 s; Gavel 13 ms / 28 ms | 64-GPU heterogeneous | §5.6 |
| Policy runtime at scale | ~1 s for Sia; Pollux GA ~100× slower | Helios, scaled to 2048 GPUs | §5.6, Fig. 9 |
| Bootstrap vs No-Prof / Oracle | 30% better / 8% worse | Helios | §5.7 |
| Profiling cost | ≈0.1 GPU-hr per job (exhaustive: 1–10 GPU-hr per job) | Helios | §5.7 |
| Round length 60 s → 300 s | avg JCT +333 s (12%) | sensitivity | §5.7 |
| Adding GPU count to GPU-type choice | avg JCT −56%; adding batch size: a further −13% | Philly | §5.7, Fig. 11 |

## Limitations

- Bootstrapping relies on DP compute time being independent of GPU count, and on communication scaling transferring across types (Eq. 1). That fits all-reduce DP, but is weaker for jobs that are communication-bound or limited by the interconnect.
- Configurations are coarse: power-of-two counts within a node, whole nodes across nodes, no cross-type jobs. That is what makes the ILP small, but it rules out mixed-type data parallelism.
- Hybrid-parallel support only adds or removes whole pipeline replicas. Re-planning the pipeline or tensor degrees when resources change is left as future work, because parallelism optimizers are too slow to run each round (Conclusion).
- Most headline results are from simulation. The physical run is one 30-job trace repeated four times on 44 GPUs, and Pollux varied widely there.
- The baselines had to be adapted. Gavel needed hand-tuned "TunedJobs". Pollux was given a heterogeneity heuristic that the authors call "not perfect", which splits 8-GPU nodes into 4-GPU virtual nodes and runs each job on its majority GPU type.
- The paper reports the unfair-job reduction as 99% in §1 but as 22–31% in the conclusion. No sensitivity study for λ is given.
- Workloads are training only, with checkpoint-restart elasticity. There is no inference, no co-location or packing, and no network-topology model beyond whole-node placement.

## Relation to other systems

- **Pollux (OSDI 2021):** Sia keeps Pollux's goodput model and AdaptDL runtime. It replaces the genetic-algorithm search over arbitrary placements with an ILP over a compact configuration set, and adds per-type throughput models. It roughly matches Pollux on homogeneous clusters (Table 4), restarts about half as often, and runs the policy far faster at scale.
- **Gavel (OSDI 2020):** Gavel solves an optimization over a (job × GPU-type) throughput matrix and time-shares jobs across types in rounds, but jobs stay rigid. Sia argues that adding count and batch-size choices to Gavel would need too much profiling and too large a program (§2). Sia beats Gavel even on rigid jobs, which it credits to optimizing goodput rather than raw throughput (§5.4).
- **Tiresias (NSDI 2019):** Tiresias is a duration-agnostic, two-dimensional least-attained-service / Gittins-index scheduler for rigid jobs on homogeneous GPUs. It does not adapt resources or model performance per job. Sia's fairness knob p is a different lever: an exponent on normalized goodput rather than a priority queue.
- **Gandiva (OSDI 2018):** Gandiva introduced introspective time-slicing, suspend/resume, migration and packing of DL jobs. Sia relies on the same checkpoint-based preemption, but decides allocations by solving a global optimization instead of reacting with heuristics, and it does not pack jobs onto shared GPUs.
- **Lucid (ASPLOS 2023):** Lucid is non-intrusive: it does not change job configurations. It uses a short profiler, interpretable models of throughput and duration, and job packing. Sia is the opposite in that it *does* change jobs (count, type, batch size) and needs an adaptive executor. Lucid suits clusters where users will not accept elastic jobs.
- **Shockwave / Themis:** Shockwave and Themis are fairness-oriented baselines for rigid jobs. Sia beats both on JCT even in the homogeneous setting (Table 4), and beats Shockwave on worst-case FTF (Fig. 8).

## Takeaways for practice

- Restrict placements to a small set of shapes (power-of-two in a node, whole nodes across nodes). This shrinks the solver and removes NIC contention with little loss.
- Don't profile the full (type × count × batch size) cube. Measure one GPU per type, assume compute is constant per GPU, learn communication online, and transfer the scaling ratio across types. In Sia this gets within 8% of an oracle for about 0.1 GPU-hr per job.
- Put the restart cost in the objective (the r_i multiplier) rather than adding hysteresis afterwards. Making resize steps node-sized halves restarts compared with resizing one GPU at a time.
- Normalize each job's utility to its own minimum configuration before summing. Otherwise large jobs dominate, and an exponent knob (p < 0) gives a usable trade-off between efficiency and fairness.
- An off-the-shelf MILP solver with 60 s rounds is fast enough at a few thousand GPUs. Policy latency is not the bottleneck at that scale, so a genetic algorithm or custom heuristic is not needed.
- Elastic hybrid parallelism is still open. Adding or removing whole pipeline replicas is the easy part; re-planning the parallelism degrees online is not solved.

## References

- Paper: https://dl.acm.org/doi/10.1145/3600006.3613175 (PDF: https://www.pdl.cmu.edu/PDL-FTP/BigLearning/sia_sosp23-final.pdf)
- Code / artifact: https://github.com/siasosp23/artifacts ; SOSP'23 artifact summary: https://sysartifacts.github.io/sosp2023/summaries/sia
- Pollux: https://arxiv.org/abs/2008.12260 ; Lucid code: https://github.com/S-Lab-System-Group/Lucid
