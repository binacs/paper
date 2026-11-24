---
title: 'Tiresias: A GPU Cluster Manager for Distributed Deep Learning'
authors:
- Juncheng Gu
- Mosharaf Chowdhury
- Kang G. Shin
- Yibo Zhu
- Myeongjae Jeon
- Junjie Qian
- Hongqiang Liu
- Chuanxiong Guo
affiliations: 'University of Michigan, Microsoft, UNIST, Alibaba, Bytedance'
venue: 'NSDI'
year: 2019
abs_url: https://www.usenix.org/conference/nsdi19/presentation/gu
pdf_url: https://www.usenix.org/system/files/nsdi19-gu.pdf
code_url: https://github.com/SymbioticLab/Tiresias
note_type: deep-read
written_at: '2026-11-25'
---

# Tiresias: A GPU Cluster Manager for Distributed Deep Learning

> **Why it matters:** Tiresias showed that a GPU cluster can cut average JCT sharply without knowing job durations, by applying least-attained-service scheduling over GPU-time with a small number of discretized priority queues. It also showed that strict GPU consolidation is only needed for a minority of models. Most later DL schedulers use it as a baseline.

## Problem

DL training jobs do not fit the big-data schedulers that were then managing GPU clusters (the paper's baseline is a YARN Capacity Scheduler derivative, "YARN-CS"). The paper's analysis of a Microsoft production cluster ("cluster P", 10 weeks, Oct–Dec 2017) names three problems (§2.2):

- **Unpredictable job duration.** Users do not know how long training will run, because jobs are killed early, tuned and restarted. So SJF/SRTF-style schedulers, which need remaining time, cannot be used directly.
- **Over-aggressive job consolidation.** Schedulers insist on packing a job's GPUs onto as few servers as possible. Jobs then wait even when enough GPUs are free elsewhere, which hurts queueing delay and fragments the cluster.
- **Time overhead of preemption.** GPU jobs are gang-scheduled (all-or-nothing), and preemption goes through checkpoint and restore, which takes seconds. Fine-grained preemption is therefore costly.

The incumbent scheduler is also non-preemptive, so long jobs cause head-of-line blocking; the paper reports an average queueing delay of 4102 s across all jobs in cluster P.

## Core design

Tiresias is a centralized resource manager. Its scheduler, placement module and profiler are all built into the master (§3.1, §4). Job lifecycle:

1. A submitted job enters a WAITQUEUE. Its GPU count (PS and worker count) is known at submission and fixed for the job's life.
2. The scheduler periodically picks jobs to run and preempts running jobs when priorities change.
3. When a job starts or resumes, the placement module chooses GPUs.
4. On a job's first run, the profiler determines whether it is sensitive to consolidation.

### Two-dimensional attained service (2DAS)

- A job's **attained service** is GPUs × time executed so far. The paper argues that using only the temporal dimension or only the spatial dimension is insufficient (§3.2.2).
- **2D-LAS** (information-agnostic): the job with the least attained GPU-time gets the highest priority. It is a multi-dimensional generalization of least-attained-service / foreground-background scheduling, which performs well when durations are highly variable or heavy-tailed.
- **2D-Gittins** (partial information): if the operator can supply a job-duration distribution from history, priority is the Gittins index G_J = sup_Δ P(S − a_J ≤ Δ | S > a_J) / E[min(S − a_J, Δ) | S > a_J], where a_J is attained 2D service. Without a distribution, Tiresias falls back to 2D-LAS.

### Priority discretization (multi-level feedback queue)

- Continuous LAS would preempt constantly, which GPU checkpointing makes too expensive. Tiresias instead keeps K logical queues separated by attained-service thresholds (§3.2.3). A job is demoted when its attained service crosses a threshold.
- Within a queue, LAS orders jobs FIFO by first start time. Gittins orders them by Gittins index, with Δ_i set to queue i's upper threshold and Δ_K = ∞.
- Preemption happens only between queues. The default is K = 2: the testbed uses a 3200 GPU-second threshold and simulations use 1 hour (§5).
- **Starvation control (PROMOTEKNOB):** a job whose waiting time δ_J ≥ PROMOTEKNOB × t_J (t_J = its total execution time so far) is promoted to the top queue, and both counters reset. Setting PROMOTEKNOB = ∞ disables promotion. A smaller value trades average JCT for fairness.

### Preemption mechanism

A preempted job is paused, and its chief worker checkpoints the model to a cluster-wide shared file system. On resume, the job reloads the latest checkpoint, possibly on different GPUs (§4). This uses the checkpointing the frameworks already provide, so no framework changes are needed.

### Skew-aware placement

- Consolidation matters mainly for models whose parameters are dominated by a few very large tensors. Under parameter-server synchronization those tensors concentrate traffic on one PS. In the paper's Table 6, the largest tensor is 61.0–77.3% of model size for AlexNet and the VGG family, but at most 14.6% for the other models (for example, ResNet152 at 3.9%).
- A profiler library intercepts RDMA ibverbs calls during the job's first run and reports message sizes to a central profiler, which estimates the job's tensor skew S_J (§3.3, §4).
- If S_J > PACKLIMIT, the job is consolidated. Otherwise it may be spread out to reduce fragmentation and queueing. PACKLIMIT is updated periodically from job history with a simple linear classifier.
- An ILP placement (Appendix D) was rejected as too slow and not clearly better.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Average queueing delay in production (all jobs) | 4102 s | Microsoft cluster P, YARN-like scheduler | §2 |
| DDL job growth | 10.5× year over year; large (>8 GPU) jobs 9.4× | cluster P | §2 |
| Avg JCT improvement, Tiresias-L vs YARN-CS | 5.5× | 60 P100 testbed (15×4 GPUs), 480 jobs | §5.2.1, Fig. 10 |
| Tiresias-G relative to Tiresias-L | 1.06× avg, 1.05× median | testbed | §5.2.1 |
| Makespan, Tiresias-L vs YARN-CS | 1.21× smaller | testbed | §5.2.2, Fig. 11 |
| Avg queueing delay of DDL jobs | YARN-CS 8146 s, SRTF 593 s, Tiresias-G 1005 s, Tiresias-L 963 s | testbed | Table 4 |
| Median queueing delay of DDL jobs | YARN-CS 7464 s vs Tiresias-L 13 s | testbed | Table 4 |
| Preemptions (total overhead) | Tiresias-L 221 (13724 s), Tiresias-G 297 (17425 s), SRTF 316 (18057 s) | testbed | §5.2.4 |
| Placement gain vs random placement | up to 1.67× | testbed | Fig. 12 |
| Avg JCT, Tiresias-L vs YARN-CS / Best-effort / Gandiva | 2.4× / 1.5× / 2× | trace-driven simulation, Microsoft trace | §5.3, Table 5 |
| Median JCT, Tiresias-L vs YARN-CS / Best-effort | 30.8× / 9× | simulation | §5.3, Table 5 |
| SRTF (perfect knowledge) normalized to Tiresias-L | 1.00× avg, 1.00× median, 0.84× p95 | simulation | Table 5 |
| Tiresias-G normalized to Tiresias-L | 0.97× avg, 1.00× median, 0.85× p95 | simulation | Table 5 |
| Simulator fidelity check | 5.11× avg improvement over YARN-CS when replaying the testbed workload | simulator vs testbed | §5.3 |
| Using 3 or 4 queues instead of 2 | ~1% better avg JCT | simulation sensitivity | §5.4 |

## Limitations

- **Fixed, rigid GPU demand.** Each job keeps the GPU count requested at submission, allocated all-or-nothing. Tiresias does not resize jobs or tune batch size. Elastic schedulers (Optimus, Pollux, Sia) exploit exactly this lever.
- **Average JCT is the only objective.** Fairness is handled only indirectly, through PROMOTEKNOB. The paper argues that fair-sharing schedulers cannot minimize average JCT. Themis later made fairness across users the primary goal.
- **Heavy preemption.** Checkpoint-to-shared-FS preemption costs seconds per event, and the testbed run accumulates thousands of seconds of overhead (§5.2.4). The paper itself lists lightweight preemption as future work (§6), since Gandiva-style suspend/resume needs framework changes.
- **Placement model is PS-specific.** The skew heuristic follows from parameter-server traffic on RDMA (TensorFlow 1.3.1 in the evaluation). *Own analysis:* with all-reduce (NCCL/ring) or model-parallel and hybrid-parallel LLM training, the bottleneck is bandwidth along the ring or topology rather than a hot PS. The skew signal and PACKLIMIT classifier would then need to be redesigned rather than reused.
- **Intra-server interference is ignored.** Effects such as PCIe contention are not modelled. The paper lists fine-grained placement as future work (§6).
- **No formal bounds.** The paper says formal analysis of when discretized 2DAS works well is still open (§6).
- **Simulator caveat.** The paper states its simulator omits preemption overhead, placement effects and cluster dynamics, so Table 5 is optimistic on those axes.
- **Homogeneous GPUs.** *Own analysis:* the design assumes one GPU type. GPU heterogeneity and the goodput of a job on different GPU types are outside its model, as later heterogeneity-aware work (for example, Sia) emphasises.

## Relation to other systems

- **Gandiva (OSDI 2018):** Its abstract describes exploiting intra-job predictability of mini-batch iterations to time-slice GPUs across jobs for low latency, plus introspection and transparent migration to better-fitting GPUs. It reports up to an order-of-magnitude faster hyper-parameter search and 26% higher cluster utilization on 180 GPUs. Gandiva changes the execution mechanism (fast suspend/resume, packing, migration, with framework support). Tiresias changes the policy (which job runs next) using framework-native checkpoints. Tiresias's simulation reports 2× better average JCT than a Gandiva baseline (Table 5).
- **Optimus (EuroSys 2018):** Its abstract describes online fitting of convergence and resource-performance models to decide how many PS/workers each job gets and where to place them. It reports about 139% better JCT and 63% better makespan than representative schedulers. Optimus needs convergence predictions and resizes jobs. Tiresias assumes durations are unknown and job sizes fixed, which is the realistic case for exploratory training.
- **Themis (NSDI 2020):** Its abstract introduces finish-time fairness, enforced by a two-level design in which jobs bid in auctions run by a central arbiter. It reports more than 2.25× better fairness and 5–250% better efficiency. Tiresias optimizes cluster-wide average JCT and treats fairness only as a starvation knob.
- **Pollux (OSDI 2021):** Its abstract defines goodput (throughput × statistical efficiency) and co-adapts each job's resources and training configuration, reporting 37–50% lower average JCT than state-of-the-art DL schedulers. Tiresias neither reallocates GPUs within a job nor touches training hyper-parameters.
- **Sia (SOSP 2023):** Its abstract describes heterogeneity-aware, goodput-optimized allocation of elastic jobs (including hybrid-parallel ones) across GPU types, with low-overhead throughput modelling. It reports 30–93% lower average JCT, scaling to 2,000+ GPUs. Sia generalizes what Tiresias holds fixed: GPU type, GPU count and parallelism.

## Takeaways for practice

- When durations are unknown, two-level LAS over GPU-time (GPUs × seconds) is a strong default for a training queue. It needs no user estimates and, in simulation, comes close to SRTF with perfect knowledge (Table 5).
- Discretize priorities. Two queues with a coarse threshold capture most of the benefit, and more queues gave only about 1% more (§5.4). This keeps checkpoint-based preemption affordable.
- Include a starvation-promotion knob (waiting time relative to service received) and expose it as the operator's dial between fairness and efficiency.
- Treat consolidation as a per-job property learned by profiling, not a global rule. Relaxing it for insensitive jobs cuts queueing and fragmentation. Re-derive the sensitivity signal for your communication pattern (all-reduce, tensor or pipeline parallel).
- Build preemption on framework checkpoint/restore so jobs run unmodified, and track preemption count and overhead as first-class metrics.
- Validate the simulator against the testbed (§5.3) and state what it omits.

## References

- Paper: https://www.usenix.org/conference/nsdi19/presentation/gu
- PDF: https://www.usenix.org/system/files/nsdi19-gu.pdf
- Code: https://github.com/SymbioticLab/Tiresias
