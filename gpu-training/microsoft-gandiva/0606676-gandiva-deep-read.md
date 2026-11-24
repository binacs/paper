---
title: 'Gandiva: Introspective Cluster Scheduling for Deep Learning'
authors:
- Wencong Xiao
- Romil Bhardwaj
- Ramachandran Ramjee
- Muthian Sivathanu
- Nipun Kwatra
- Zhenhua Han
- Pratyush Patel
- Xuan Peng
affiliations: 'Microsoft Research, Beihang University, The University of Hong Kong, Huazhong University of Science and Technology, Peking University'
venue: 'OSDI'
year: 2018
paper_id: 0606676f16d581fa453f6b7b8a14fc7c4af8d025
abs_url: https://www.usenix.org/conference/osdi18/presentation/xiao
pdf_url: https://www.usenix.org/system/files/osdi18-xiao.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Gandiva: Introspective Cluster Scheduling for Deep Learning

> **Why it matters:** Gandiva was an early scheduler to treat a GPU training job as a white box: it used the mini-batch loop to time-slice, pack and migrate jobs cheaply, and to check whether each decision helped.

## Problem

YARN- and Kubernetes-style schedulers treat a deep learning training (DLT) job as an opaque gang that holds its GPUs until it finishes (§1–2). This fits DL badly in two ways:

- **Feedback-driven exploration.** Users run multi-jobs (hyper-parameter searches such as HyperOpt or Hyperband) and kill most configurations early. Exclusive, run-to-completion allocation causes head-of-line blocking, so a new configuration can wait hours before it reports any accuracy.
- **Heterogeneity.** Jobs differ in locality sensitivity, interference and GPU utilization, and a placement chosen at admission time is never corrected.

The key observation (§3) is **intra-job predictability**. A job repeats the same mini-batch millions of times, and its GPU memory use rises and falls in a regular cycle within each mini-batch.

## Core design

The scheduler is co-designed with modified PyTorch and TensorFlow (§1, §5). Each job runs in a Docker container on Kubernetes, and a custom central scheduler, itself a container, makes the decisions (§5.1).

### Mechanisms (§4.1)

- **Suspend-resume / time-slicing.** To suspend, the framework waits for the memory-cycle *minimum*, copies the GPU objects that remain to the host and frees the GPU, so a suspend is delayed by at most one mini-batch. Suspend plus resume takes under 100 ms for image models and up to about 1 s for large translation models, which the paper puts at 2% or less of a 60 s slice. The scheduler tracks the delay to keep slices fair.
- **Packing.** Several jobs share one GPU concurrently, without MPS, which the authors found to add significant overhead on P40/P100 (§6.1). Each job is profiled while it runs alone, then packed, then unpacked back to time-slicing if the packing hurts.
- **Migration.** Generic CRIU checkpoints run to GBs and cost about 8–10 s for 1-GPU PyTorch jobs. The framework-aware path warms up the destination and moves only the training state, which takes "a second or two". In TensorFlow the checkpoint goes to a ramdisk, and a data-parallel job saves only one GPU's model replica (§5.2).
- **Grow-shrink.** A job that declares itself adaptive can use idle GPUs and returns them on demand.
- **Introspection.** Mini-batch time is measured as the time between two memory-cycle minima. Comparing it before and after each decision (pack, migrate, grow) tells the scheduler whether the decision worked, with no model-specific knowledge.

### Scheduling policy (§4.2)

The paper assumes a dedicated DLT cluster and power-of-two GPU requests. The primary goal is **early feedback**, the secondary goal is efficiency, and cluster-level fairness is explicitly not a goal; fairness is enforced only within a server.

- **Height and affinity.** A server's *height* is its allocated GPUs divided by its total GPUs; a height above 1 means it is over-subscribed and time-sliced. Its *affinity* is the job size (GPU count) it hosts.
- **Reactive mode** (arrivals, departures, failures; Algorithm 1). A new job is placed on:
  1. the least-loaded same-affinity server with height below 1;
  2. failing that, an unaffinitized server with enough free GPUs;
  3. failing that, any free GPUs, accepting fragmentation that migration fixes later;
  4. failing that, a same-affinity server over-subscribed with suspend-resume.
  
  If none of these works, the job is queued. In effect, 1-GPU jobs share servers while 2- and 4-GPU jobs stay apart (Fig. 7). Over-subscribed servers run weighted round-robin.
- **Introspective mode** runs continuously:
  - *Packing*, considered only during overload. A greedy heuristic pairs the lowest-utilization job with the least-utilized GPU if their combined memory fits, and keeps the pair only if its throughput beats time-slicing.
  - *Migration*, to improve locality on every departure and to defragment in the background. The defragmenter empties the non-idle server with the most free GPUs when the performance loss is negligible, and stops below a threshold (3 of 4 free GPUs in the experiments).
  - *Grow-shrink*, only when the cluster is under-utilized and only within one server. A job grows after an idle period, to avoid thrashing, and shrinks immediately when a new job needs the GPUs.
  - *Priorities.* A higher-priority job is never suspended for a lower-priority one; the lower-priority job may be migrated away instead.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| GPU memory swing within a mini-batch | 23 GB to 0.3 GB (77x) | ResNet-50, ImageNet, 4x K80, batch 128 | §3 |
| Worst-placement throughput | ~60% of best | 2-GPU TF VGG16 across CPU sockets; ResNet-50 unaffected | §3 |
| Interference slowdown | up to 47% (ResNet-50), 30% (InceptionV3), 5% (DeepSpeech) | 2-GPU jobs spread across servers | §3, Fig. 4 |
| Suspend + resume latency | <100 ms (image classification), up to ~1 s (large translation) | PyTorch | §4.1 |
| Time-slicing aggregate throughput loss | <2% | 6 ResNet-50 1-GPU jobs on 4 P100 | §6.1, Fig. 9 |
| Packing gain | +412% (VAE), +260% (SuperResolution), +46% (RHN); −16% (LSTM), −13% (ResNet-50), −11% (ResNext-50) | single P40, no MPS | Table 1 |
| Migration time | most models ≤1 s; DeepSpeech (1,405 MB ckpt) ~3.5 s | TF, 8x P100 server | §6.1, Fig. 13 |
| Migration overhead saved | 98% of 35 s | 8-GPU TF jobs | §6.1, Fig. 12 |
| Configs explored in hyper-parameter search | ~10x baseline | 4 and 16 P40 | §6.2, Fig. 14 |
| Time to find qualified config | 5.51x–7.04x faster (4 GPU); 3.40x–5.96x (16 GPU) | AutoML search | Table 3 |
| Time to first 100 mini-batches | 2,203 s → 498 s (−77%) | 180 GPUs (45 servers, P100/P40), time-slicing + packing only | §6.3 |
| Average cluster GPU utilization | 50.1% → 62.8% ("26%") | same | §6.3 |
| Avg JCT / makespan | 832 → 656 min (26.8%) / 13,371 → 11,349 min (17.8%) | 100-GPU replay of a 2,000-GPU trace, vs. YARN capacity scheduler | §6.4, Table 5 |
| Migrations during replay | 470 | same | §6.4 |
| Multi-job speedup | 13.6x and 12.9x | two 8-GPU multi-jobs, 40 configs each, in the replay | §6.4 |

## Limitations

- **Framework coupling.** Gandiva needs modified frameworks (TF: 400+ lines, plus 200+ lines for a migration helper; §5.2), so opaque training loops get no benefit. *(Own analysis:)* it assumes one regular mini-batch loop; evaluation phases or dynamic shapes weaken both the cheap-suspend point and the progress signal.
- **No cluster-level fairness or multi-tenancy** (§4.2): the paper assumes a dedicated cluster.
- **Narrow elasticity.** Grow-shrink is opt-in and limited to one server (§4.2.2); Gandiva borrows idle GPUs but never decides a job's right size.
- **Reactive packing.** Interference is found by measurement, not predicted, and packing was evaluated without MPS. *(Own analysis:)* each bad packing costs throughput until it is reverted.
- **Evaluation scope.** The 180-GPU experiment disables migration and grow-shrink, and its baseline is an unnamed bin-packing scheduler that does not over-subscribe (§6.3). The trace replay runs on 100 GPUs with 10 public models mixed to match the trace's category ratios, because the production jobs were unavailable (§6.4).
- **Centralized scheduler.** The paper notes a hierarchical design may be needed at scale (§5.1). It claims no generality beyond DL (§7).

## Relation to other systems

- **Optimus (EuroSys 2018).** Its abstract describes fitting convergence and resource-to-speed models online and resizing each job's parameter servers and workers to cut JCT. Optimus decides *how much* a job gets, from models; Gandiva keeps the user's request and changes *where and when* the job runs, from measurement.
- **Tiresias (NSDI 2019).** Its abstract describes Discretized 2D-LAS (information-agnostic) and 2D-Gittins (partial information) policies plus consolidation-relaxing placement, reporting up to 5.5x better average JCT than a YARN-based manager. Its preemption serves a cluster-wide JCT priority; Gandiva's time-slicing serves early feedback, with fairness only per server.
- **Philly trace study (ATC 2019).** This study shares authors with Gandiva. Its abstract analyses a two-month multi-tenant Microsoft GPU-cluster trace, covering gang scheduling and locality effects on queuing and utilization, and training failures. It confirms at production scale the problems Gandiva targets, and it adds failures and multi-tenancy, which Gandiva does not model.
- **AntMan (OSDI 2020).** This paper is from Gandiva's first author, at Alibaba. Its abstract describes dynamic scaling of GPU memory and compute inside the framework, so that jobs can share GPUs without interference, reporting 42% higher memory and 34% higher compute utilization in production. It turns "pack, then revert on slowdown" into framework-enforced resource limits.
- **Pollux (OSDI 2021).** Its abstract describes modelling each job's goodput (throughput combined with statistical efficiency) as a function of resources, reallocating across the cluster and retuning each job, reporting 37–50% lower average JCT. It extends Gandiva's introspection from mini-batch time to statistical progress, and from opportunistic grow-shrink to elasticity it actually optimizes.

## Takeaways for practice

- The iteration boundary is the cheapest point to preempt, checkpoint or migrate; for data-parallel jobs, checkpoint one replica. That makes minute-scale time-slicing affordable.
- Mini-batch time is a model-agnostic health metric. Measure it around every scheduling action and roll the action back if it hurt.
- Decide packing empirically, gated on observed utilization and memory fit: low-utilization jobs gain a lot, while compute-bound jobs lose 11–16% (Table 1).
- Over-subscription buys fast first feedback for hyper-parameter search; pair it with per-server weighted round-robin and priority rules.
- Run migration-based defragmentation continuously in the background; affinity-based placement fragments the cluster over time.
- Check how headline percentages are computed. Table 5's 26.8% and 17.8% gains match (baseline − Gandiva) / Gandiva; measured against the baseline they would be about 21% and 15% (own arithmetic).

## References

- Paper: https://www.usenix.org/conference/osdi18/presentation/xiao
- PDF: https://www.usenix.org/system/files/osdi18-xiao.pdf
- Slides: https://files.usenix.org/s3fs-public/cdn/osdi18_slides_sivathanu.pdf
