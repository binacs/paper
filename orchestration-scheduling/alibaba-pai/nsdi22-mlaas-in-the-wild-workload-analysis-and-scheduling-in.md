---
title: 'MLaaS in the Wild: Workload Analysis and Scheduling in Large-Scale Heterogeneous GPU Clusters'
authors:
- Qizhen Weng
- Wencong Xiao
- Yinghao Yu
- Wei Wang
- Cheng Wang
- Jian He
- Yong Li
- Liping Zhang
affiliations: 'Hong Kong University of Science and Technology, Alibaba Group'
venue: 'NSDI'
year: 2022
abs_url: https://www.usenix.org/conference/nsdi22/presentation/weng
pdf_url: https://www.usenix.org/system/files/nsdi22-paper-weng.pdf
code_url: https://github.com/alibaba/clusterdata
note_type: deep-read
written_at: '2026-11-25'
---

# MLaaS in the Wild: Workload Analysis and Scheduling in Large-Scale Heterogeneous GPU Clusters

> **Why it matters:** It is the reference public trace for a shared, heterogeneous, training-plus-inference GPU cluster. It shows that most work there is fractional-GPU, recurring and often CPU-bound, while a small set of NVLink-hungry tasks dominates the queueing pain.

## Problem

Earlier public GPU-cluster studies, most notably Microsoft Philly (2017 trace), cover training only, mostly single-GPU jobs, and small or nearly homogeneous clusters (Table 1 compares Philly, Tiresias, Gandiva-fair, Themis, HiveD and AntMan). Alibaba PAI is a machine-learning-as-a-service platform. It runs TensorFlow, PyTorch, Graph-Learn and RLlib jobs from many tenants on several GPU generations, with both training and inference. The paper asks what such a workload looks like and why the cluster has low GPU utilisation alongside long queues. It then asks which scheduling changes help and which problems are still open (§1, §2).

## Core design

This is a characterisation paper with three evaluated scheduling remedies, not a new system.

### Cluster and trace (§2, §3.1, Table 1)
- **Hardware:** 6,742 GPUs in total. 1,295 two-GPU nodes: 798 with P100 (64 vCPU) and 497 with T4 (96 vCPU). 519 eight-GPU nodes: 280 "Misc" (older parts such as K40m, K80 and M60), 135 with V100M32 and 104 with V100, the V100 nodes using NVLink. There are also 83 CPU-only nodes.
- **Hierarchy:** a *job* splits into *tasks* with roles (parameter server, worker, evaluator). Each task runs one or more *instances*, usually as Docker containers. Many tasks need all their instances gang-scheduled.
- **Trace:** July–August 2020. It records arrival and completion times plus requested and used CPU, GPU, GPU memory and memory at job, task and instance level. Daemons on each machine read the kernel and NVML and sample machine utilisation every 15 s. The scheduler sees only containers, so application semantics such as framework or train-versus-infer are missing, apart from some application-name labels (§3.1).
- GPU usage is measured as a fraction of streaming-multiprocessor (SM) compute, expressed in "GPUs" (§1, §4).

### Workload findings
- **Skew and gangs (§3.1):** a few heavy users dominate, and most instances and GPU demand come from gang-scheduled tasks.
- **Requests versus use (§3.3, Fig. 5):** the median request is under one GPU, and actual use is far below request on every resource. CPU is the resource most often used beyond its request.
- **Time (§3.2, Fig. 3–4):** submissions follow a daily cycle. Queueing delay grows sharply with GPU request size and on V100s.
- **Machines (§4):** tail GPU utilisation is high on both node types. CPU is much less used on two-GPU nodes (32–48 vCPU per GPU). Network and I/O are light, and iowait is negligible.
- **High-GPU tasks (§6.1):** NLP (BERT, ALBERT, XLNet) and ResNet with 100k classes need large-memory GPUs, with all workers on one NVLink node.
- **Low-GPU tasks (§6.2):** CTR (mostly inference), GNN and RL are CPU-bound. The CPU work is batch preparation, graph sampling (30–90% of a GNN iteration) or simulation.

### Remedies evaluated
1. **GPU sharing (§5.1):** instances may request a fraction of a GPU. The GPU-memory share is reserved at scheduling time and spare memory can be borrowed at run time. SM compute is not reserved and is time-shared among co-located instances. Fine-grained isolation comes from AntMan, for TensorFlow and PyTorch only. The paper replays allocations to estimate the GPUs saved and uses utilisation samples to argue that contention is rare.
2. **Predictable-duration scheduling (§5.2):** recurring tasks are identified by a "Group" tag, a hash of entry script, command-line parameters and data sources/sinks. A CART regression tree (at most 10 splits, MAE criterion) predicts run-time from Group, User and Resource features, trained on 80% of tasks that recur at least 5 times. A discrete-time simulator, assuming homogeneous GPUs, compares SJF using predicted durations against FIFO and against SJF with true durations.
3. **Reserving-and-packing (§6.3):** a performance model scores each task's computation efficiency, and tasks above a threshold are classed as high-GPU. V100/V100M32 NVLink nodes are reserved for them, and other work is packed with GPU sharing onto T4 and Misc nodes. Each task gets an ordered list of allocation plans, each with a timeout. High-GPU tasks try high-end GPUs first, and other tasks try the same list in reverse order. The policy runs on Fuxi, a locality-tree scheduler. The baseline is load-balancing that always picks the least-allocated node, using a weighted sum of CPU, memory and GPU allocation. The comparison uses the §5.2 simulator on 100,000 sampled tasks.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Cluster GPUs | 6,742 | PAI, Jul–Aug 2020 | §1, Table 1 |
| Trace size | >7.5M instances, 1.2M tasks, >1,300 users | 2 months | §3.1 |
| Instances from top 5% of users | ~77% | — | §3.1, Fig. 2a |
| Instances needing gang scheduling | ~85% | — | §3.1, Fig. 2b |
| Share of GPU demand from gang-scheduled tasks | 79% | — | §3.1 |
| Tasks requiring a specific GPU type | ~6% | — | §3.1 |
| Median instance request | 6 vCPU, 0.5 GPU, 29 GiB | — | §3.3, Fig. 5 |
| Median instance usage | 1.4 vCPU, 0.042 GPU, 3.5 GiB | — | §3.3 |
| Instances using more than requested | 19% CPU, 9% memory, 3% GPU | — | §3.3, Fig. 5d |
| Median / P90 instance run-time | 23 min / 4.5 h (Philly: 26 min / 25 h) | — | §3.2, Fig. 4a |
| Short instances queued >50% of completion time | ~9% (long: 3%) | — | §3.2, Fig. 4b |
| P90 queueing delay by request | 497 s (<1 GPU), 1,150 s (1 GPU), 8,286 s (>1 GPU) | — | §3.2, Fig. 4c |
| Queueing delay median / P90 | V100: 113 s / 13,709 s; Misc: 11 s / 360 s | — | §3.2, Fig. 4d |
| Avg P90 GPU / CPU utilisation | 82% / 77% (8-GPU); 77% / 42% (2-GPU) | machine level | §4.1, Fig. 6 |
| GPUs needed with sharing | ~50% on average; up to 73% saved at peak | simulated no-sharing vs measured | §5.1, Fig. 8 |
| GPU samples ≥95% busy / of those, multi-instance | 7% / 4.5% | 2 months | §5.1, Fig. 9 |
| Tasks recurring ≥5 times | ~65% | — | §5.2, Fig. 10 |
| Prediction error <25% | 78% of instances | Group+User+Resource features | §5.2, Fig. 12 |
| SJF avg completion-time reduction vs FIFO | 63–77% | simulator, 1,000–6,500 GPUs | §5.2, Fig. 13 |
| NVLink vs PCIe per-epoch speedup | 1.12× DenseNet-121, 3.94× VGG, 10.54× ResNet-100k | 8-GPU node | §6.1, Fig. 14b |
| CTR training slowdown under CPU stress | up to 28% | DeepFM, 8 vCPU container | §6.2, Fig. 16b |
| Reserving-and-packing queueing delay reduction | 45% all tasks; 68% V100 tasks | simulator, 100k tasks | §6.3, Fig. 19 |
| Misc 8-GPU nodes allocated vs used | CPU 77% / 43%, GPU 74% / 18% | — | §6.4, Fig. 20a |
| vCPU per GPU, provisioned vs requested | 12.0 vs 22.8 (8-GPU); 38.1 vs 18.1 (2-GPU) | — | §6.4, Table 2 |

## Limitations

Stated or implied by the paper:
- Load imbalance across heterogeneous machine types and CPU contention slowing GPU tasks are left as open problems (§6.4). The paper proposes a multi-resource scheduler but does not build one.
- Compute isolation for GPU sharing depends on framework support (AntMan, TensorFlow/PyTorch only). Hardware partitioning (MIG) was A100-only and fixed-size at the time (§5.1, §8).
- The trace lacks application semantics because the scheduler sees only containers (§3.1).
- Elastic jobs would ease gang scheduling but make final accuracy non-deterministic (§7).

*Own analysis (not claims the paper makes):*
- The remedies are evaluated in a trace-driven simulator, not with production A/B measurements. The SJF simulator assumes homogeneous GPUs, which is the very property the paper says makes PAI hard to schedule.
- The "sharing causes little contention" argument rests on a utilisation proxy (how often a ≥95%-busy GPU hosts more than one instance), not on measured per-job slowdown.
- Duration prediction covers only recurring tasks. The roughly 35% of tasks that recur fewer than 5 times fall back to an unspecified policy.
- The 2020 workload predates LLM-scale pretraining and serving, so its fractional-GPU, CPU-bound profile may not hold for today's long, thousand-GPU jobs. Acme's 2024 trace points that way.

## Relation to other systems

- **Philly study (ATC 2019):** a two-month, training-only Microsoft trace. It treats the GPU as an unshareable unit and studies gang/locality effects on queueing and utilisation, and failures. PAI adds inference, fractional sharing, heterogeneity and CPU bottlenecks. Its median run-time is similar, but its tail is much shorter.
- **Gandiva (OSDI 2018):** uses predictability within a job to time-slice and migrate jobs on GPUs. PAI uses predictability across recurring *tasks* to order a queue.
- **AntMan (OSDI 2020):** Alibaba's framework–scheduler co-design for packing jobs onto a shared GPU. PAI's sharing builds on it, and this paper measures the fleet-level gain and its training-only, framework-specific limits.
- **Sia (SOSP 2023):** matches elastic jobs to GPU type and count with learned throughput models. PAI handles that matching with a static reserve-and-fallback list.
- **Acme (NSDI 2024):** a six-month LLM-development trace focused on failures, parallelisation and evaluation scheduling. It shows the problems that replaced fractional sharing.

## Takeaways for practice

- Measure request versus use per resource. A median 0.042-GPU use against a 0.5-GPU request is the main argument for fractional GPU allocation with reserved memory and shared SMs.
- Recurrence is a usable signal. Hash script, arguments and data source into a stable task identity, and even a small regression tree gives run-time estimates good enough for SJF-like ordering.
- Protect scarce, topology-sensitive hardware. Reserve NVLink nodes for tasks that benefit and give everything else a reverse-ordered fallback list with timeouts. Plain least-loaded placement fragments the nodes that large gang jobs need.
- Provision CPU per GPU by machine class. 8-GPU nodes were CPU-starved and 2-GPU nodes CPU-rich, and slowed tasks correlated with host CPU utilisation rather than GPU utilisation. A GPU scheduler must track CPU, memory bandwidth and cache interference.
- Treat queueing delay by GPU type and gang size as a first-class metric. Fleet-average utilisation hides the V100 tail.

## References

- Paper: https://www.usenix.org/conference/nsdi22/presentation/weng
- PDF: https://www.usenix.org/system/files/nsdi22-paper-weng.pdf
- Trace: https://github.com/alibaba/clusterdata
