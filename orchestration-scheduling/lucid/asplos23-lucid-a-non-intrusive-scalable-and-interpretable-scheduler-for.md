---
title: 'Lucid: A Non-intrusive, Scalable and Interpretable Scheduler for Deep Learning Training Jobs'
authors:
- Qinghao Hu
- Meng Zhang
- Peng Sun
- Yonggang Wen
- Tianwei Zhang
affiliations: 'S-Lab and Nanyang Technological University, Shanghai AI Laboratory, SenseTime Research'
venue: 'ASPLOS'
year: 2023
paper_id: d5fe97309afdf0da633e04b5da4212a054661ecf
doi: 10.1145/3575693.3575705
abs_url: https://dl.acm.org/doi/10.1145/3575693.3575705
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3575693.3575705
code_url: https://github.com/S-Lab-System-Group/Lucid
note_type: deep-read
written_at: '2026-11-25'
---

# Lucid: A Non-intrusive, Scalable and Interpretable Scheduler for Deep Learning Training Jobs

> **Why it matters:** Lucid shows that a training scheduler needs no user-code or framework changes to beat a preemptive LAS scheduler, deciding in milliseconds. It uses black-box GPU telemetry, conservative packing and small interpretable models.

## Problem

Schedulers such as Gandiva, Tiresias, Optimus, Gavel, Horus and Pollux need hooks into the job, such as preemption or checkpointing, framework patches, ONNX extraction, or adaptive batch size and learning rate. §1 names five gaps:

- G1: intrusive code changes.
- G2: integration and maintenance cost.
- G3: model-quality loss.
- G4: poor scalability.
- G5: opaque decisions.

§2 points to opportunities in production traces. Only about 16% of GPUs exceed 50% utilization in an Alibaba PAI week (Fig. 1a). More than 95% of Microsoft and SenseTime jobs are single-node, and about 90% recur. This suggests that packing single-node jobs is cheap and that durations are predictable from history.

## Core design

### Two-dimensional profiler (§3.2)
- Every new job first runs on a small, separate profiling cluster for at most `T_prof` (default 200 s; 60 s on the testbed). Lucid records GPU utilization, memory footprint and memory utilization through NVIDIA tools, with no code changes.
- **Space dimension (least-GPU-first):** the profiling queue is sorted by GPU demand, smallest first, which avoids head-of-line blocking. Jobs above a scale limit `N_prof` skip profiling and are measured online.
- **Time dimension (auto-scaling):** the throughput forecast sets the scale limit, `T_prof` and capacity. During bursts Lucid borrows idle-VC nodes and shortens `T_prof`.
- Jobs that overrun are evicted to the main queue. Many debug jobs finish inside the profiler. Users can tag long cold-start jobs.

### Indolent packing (§3.3, §3.5.1)
- A pruned decision tree (the Packing Analyze Model) maps the profiled metrics plus a mixed-precision flag to a **Sharing Score**: Tiny 0, Medium 1, Jumbo 2. The labels come from co-location speed thresholds, default (0.85, 0.95).
- The Affine-jobpair Binder packs only under strict rules:
  - The summed score on a GPU stays within a per-GPU capacity GSS (default 2).
  - At most two jobs share a GPU.
  - Packed jobs have equal GPU demand.
  - A hard memory limit prevents OOM.
  - Distributed jobs are not packed.
  - A pair is split if its utilization becomes unstable.
- The text says the sum must be *below* GSS, while the Fig. 5 legend reads "≤". So it is ambiguous whether two Medium jobs may pair.
- **Dynamic mode:** when forecast throughput is low, the binder drops to an "apathetic" mode (capacity 1) or turns sharing off.

### Orchestrator (§3.4)
Priority is GPU count × predicted duration, the QSSF idea from Helios. Jobs are taken in priority order and either placed exclusively or bound to a partner (Algorithm 2). Nothing is preempted.

### Throughput and workload estimators (§3.5.2–3.5.3)
- Both are **GA2M** models: an intercept, one shape function per feature, and a few pairwise terms. Each term can be plotted on its own and the prediction is their sum, so operators can see why the model decided as it did (G5).
- **Throughput Predict Model:** forecasts job and GPU-request arrivals from calendar features (hour, date, trend, seasonality) and rolling statistics. It drives profiler scaling and the binder's mode.
- **Workload Estimate Model:** predicts duration from user, job name, GPU demand and submit time. Names are clustered by Levenshtein distance and affinity propagation.

### System Optimizer (§3.6)
- **System Tuner:** operators tune `T_prof`, the thresholds and GSS in trace simulation. They can also inject priors, for example forcing a monotonic shape for `gpu_num` via Pool Adjacent Violators.
- **Update Engine:** periodically fine-tunes the models on fresh logs.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Avg JCT, Lucid vs Tiresias | 6.84 vs 9.02 h (~1.3×) | Philly, simulation | §4.3, Table 4 |
| Avg JCT, Lucid vs Tiresias | 3.58 vs 4.09 h; 1.79 vs 1.89 h | Venus; Saturn | Table 4 |
| Avg JCT vs FIFO | 5.2–7.9× lower | three traces | §1, Table 4 |
| Avg queuing, Lucid vs Tiresias | 0.25/0.82, 0.16/0.28, 0.29/2.62 h | Venus/Saturn/Philly | §4.3 |
| Queuing, debug jobs ≤60 s | 4.1–24.8× lower than Tiresias | three traces | §4.3 |
| GPU util. / memory usage vs Tiresias | +9–17% / +7–24% | three traces | §4.3 |
| Physical avg JCT | 3.64 h (Lucid), 4.03 h (Tiresias), 8.17 h (FIFO) | 32× RTX 3090, 120 jobs | §4.2, Table 3 |
| Simulator error vs physical | < 4.6% | makespan, JCT | §4.2 |
| Scheduling latency | < 3 ms at 2,048 jobs (Gavel LP ~30 min) | incl. inference | §4.4, Fig. 10 |
| Indolent vs naive bin-packing | 1.4× lower queuing | ablation | §4.5, Fig. 11 |
| No duration estimator | ~2.2× more queuing | ablation | §4.5 |
| Space-aware vs naive profiling | up to 11.6× lower queuing | ablation | §4.5 |
| Jobs finishing in profiler | 23.3–55.4% | across traces | §4.5 |
| `T_prof` 100 → 600 s | finish rate 27.65% → 64.40% | sensitivity | Table 6 |
| Model updates | weekly −4.8% queuing vs static; daily ~1.6% more | — | §4.5 |
| Throughput MAE | 4.125 (GA2M) vs 4.491 (LightGBM), 5.132 (DNN) | — | Table 7 |
| Duration R² | 0.413 (GA2M) vs 0.332 (XGBoost) | — | Table 7 |
| Packing classifier accuracy | 94.1% | decision tree | §4.6 |
| Pollux solver time | ~30 min @160 jobs; >3 h @320 | — | §4.7 |
| EfficientNet val. accuracy | 89.84% (Lucid) vs 87.63% (Pollux) | — | §4.7, Fig. 14b |

## Limitations

- *(Own analysis, from Table 4)* The "up to 1.3×" headline is the Philly trace; the JCT gain over Tiresias on Venus and Saturn is much smaller. Most of the benefit appears in queuing delay and on short jobs.
- Scope is single-node jobs on homogeneous GPUs. Heterogeneity, fairness and SLOs are future work (§5–6).
- There is no preemption, so ordering is only as good as duration prediction (R² 0.413).
- Profiling adds a cold start to every job.
- Pollux wins at light load (Fig. 14a). The paper gives no crossover point.
- Large-scale results come from simulation; the testbed has 32 GPUs. The Saturn data is unreleased (repo README).
- The traces are from 2017–2020, before LLM training.

## Relation to other systems

- **Gandiva (OSDI 2018):** introspects iterative jobs, time-slices GPUs and migrates jobs, for up to about 10× faster hyperparameter search and 26% higher utilization (abstract). Lucid keeps the introspection but drops time-slicing and migration, which need framework support. It packs only after black-box profiling.
- **Tiresias (NSDI 2019):** discretized 2D-LAS or Gittins scheduling with little job information, up to 5.5× lower JCT than YARN (abstract). It relies on preemption, which Lucid calls intrusive (§4.1). Lucid replaces preemption with predicted GPU-time ordering and packing.
- **Pollux (OSDI 2021):** co-adapts resources and training configuration for goodput, 37–50% lower JCT (abstract). Lucid argues that this costs accuracy and scalability (§4.7).
- **Sia (SOSP 2023):** extends goodput scheduling to heterogeneous GPUs and elastic hybrid-parallel jobs. It reports 30–93% lower JCT and scaling to at least 2,000 GPUs (abstract). It covers what Lucid omits, but keeps the intrusive adaptivity.
- **Helios (SC 2021):** about 3.36M jobs over six months on SenseTime's Venus, Earth, Saturn and Uranus clusters. It introduced QSSF with GBDT and history-based duration estimates (Helios §2–4). Lucid reuses the QSSF priority, the traces and the simulator, and swaps GBDT for GA2M.
- **Philly study (ATC 2019):** about two months of Microsoft's multi-tenant cluster, showing how gang scheduling, locality and failures hurt queuing and utilization (abstract). Philly is Lucid's third trace and its largest win (Table 4).

## Takeaways for practice

- A short sandboxed run reading black-box GPU counters is enough to make safe co-location decisions.
- Pack conservatively and only when forecast demand says queues will build.
- A separate triage pool absorbs short debug jobs cheaply.
- QSSF-style ordering recovers much of SJF's benefit without preemption, given recurring jobs.
- Additive models matched or beat GBDT and DNN here, and they accept operator priors.
- Keep scheduling decisions to milliseconds, and retrain about weekly.

## References

- Paper: https://dl.acm.org/doi/10.1145/3575693.3575705 (author copy: https://tianweiz07.github.io/Papers/23-asplos.pdf)
- Code: https://github.com/S-Lab-System-Group/Lucid
