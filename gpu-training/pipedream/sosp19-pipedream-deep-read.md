---
title: 'PipeDream: Generalized Pipeline Parallelism for DNN Training'
authors:
- Deepak Narayanan
- Aaron Harlap
- Amar Phanishayee
- Vivek Seshadri
- Nikhil R. Devanur
- Gregory R. Ganger
- Phillip B. Gibbons
- Matei Zaharia
affiliations: 'Microsoft Research, Carnegie Mellon University, Stanford University'
venue: 'SOSP'
year: 2019
doi: 10.1145/3341301.3359646
abs_url: https://doi.org/10.1145/3341301.3359646
pdf_url: https://www.microsoft.com/en-us/research/wp-content/uploads/2019/08/pipedream.pdf
code_url: https://github.com/msr-fiddle/pipedream
note_type: deep-read
written_at: '2026-11-25'
---

# PipeDream: Generalized Pipeline Parallelism for DNN Training

> **Why it matters:** It introduced the 1F1B schedule, weight stashing and a profile-driven, topology-aware partitioner. Together they made asynchronous pipeline parallelism (mixed with per-stage data parallelism) a practical alternative to plain data parallelism in communication-bound training.

Note: arXiv 1806.03377 ("PipeDream: Fast and Efficient Pipeline Parallel DNN Training") is an earlier preprint and a different paper. This note is based only on the SOSP 2019 text.

## Problem

Intra-batch parallelism (data, model or hybrid) splits one iteration across workers. With data parallelism (DP, meaning BSP all_reduce in this paper), the bytes exchanged scale with model size and worker count. Over 32 GPUs, communication stalls can take up to 90% of total time for some models, even with NCCL and NVLink (§1, Fig. 1). Dense LSTM and fully connected weights scale worse than compact convolutional ones, slow inter-server links dominate, and overhead grows with worker count and GPU speed (§2.1).

Model parallelism idles most GPUs (Fig. 2) and leaves partitioning to the programmer. GPipe-style pipelining flushes every m microbatches (Fig. 3). Training is bi-directional, so naive overlap computes gradients against mismatched weight versions (§3.3).

## Core design

Layers are split into **stages** of consecutive layers, each on one GPU or a replicated GPU group. Only activations and gradients cross stage boundaries, peer-to-peer and asynchronously, overlapping compute on other minibatches (§3, Fig. 5). Workflow: profiler → optimizer → runtime (Fig. 6).

### Profiler (§3.1)
- A single-GPU run of 1000 minibatches records per layer: T_l (forward+backward time), a_l (activation/gradient bytes), w_l (weight bytes). This relies on per-input compute varying little.
- Communication time = bytes / link bandwidth; DP weight sync over m workers assumes each worker sends and receives (m−1)/m of the weight bytes.

### Partitioner: hierarchical dynamic programming (§3.1)
- The topology is modeled as levels. Level k has m_k components of level k−1, joined by links of bandwidth B_k (Fig. 7: servers of 4 GPUs on B_1, servers joined by B_2).
- The objective is to minimize the time of the slowest stage. The authors argue the problem has optimal substructure: the best pipeline for m workers is the best sub-pipeline on fewer workers followed by one final, possibly replicated, stage.
- Each step takes the max of the sub-pipeline's slowest stage, the activation/gradient transfer at the cut, and the last stage's time (compute vs. DP weight sync, per replica), minimized over cut points and replica counts. (Equations extracted garbled; described in words only.)
- Solved bottom-up: within a server first, then across servers. Output: stage assignment, per-stage replication, in-flight minibatch count; runs in under 8 s (§3.1, §5.5).

### Scheduling: 1F1B and 1F1B-RR (§3.2)
- **Startup:** the input stage admits NOAM = ⌈#workers / #replicas of the input stage⌉ minibatches.
- **Steady state:** each stage strictly alternates one forward (newer minibatch) and one backward (older minibatch): no flushes, negligible stalls, even for non-integer backward:forward ratios such as 3:2 (§3.2, fn. 4).
- **Replicated stages:** deterministic round-robin by minibatch ID sends a minibatch's forward and backward to the same replica; a static schedule with no coordination (Fig. 8).

### Correctness: weight stashing and vertical sync (§3.3)
- **Weight stashing:** one weight version per in-flight minibatch; the forward pass uses and stashes the newest weights, the backward pass reuses them, so gradients within a stage are valid. Staleness is per stage: stage 1 is n steps delayed, stage 2 n−1, and so on.
- **Vertical sync (optional, off by default):** every stage uses the version seen at the input stage, giving cross-stage consistency; the paper likens it to BSP DP on n workers with the same staleness but gradients averaged over B instead of nB. Default semantics (stashing only) sit between single-worker SGD and BSP DP.
- **Memory:** each worker holds 1/n of the weights and stashes at most n versions, so the paper argues peak memory is on par with DP; recomputation, compression and gradient aggregation are complementary.

### Implementation (§4)
- ~3000-line Python library on PyTorch (Caffe proof of concept). A BFS over the stage-annotated graph generates one `torch.nn.Module` per stage.
- Old weights are freed only after a backward pass uses fresher ones; forward activations live until that minibatch's backward pass on the stage.
- Replicated stages use PyTorch DDP; pipeline traffic uses Gloo (faster than NCCL for small tensors; the two could not be mixed within a stage).
- Per-stage, uncoordinated checkpoints at epoch end; recovery restarts all stages from the last complete checkpoint.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Max DP comm. stall share | up to 90% of time | some models, over 32 GPUs, PyTorch 1.1 + NCCL, fp32 | §1, Fig. 1 |
| Time-to-accuracy (TTA) speedup vs DP, VGG-16 | 5.28× (config 15-1) | 4x4 Cluster-A (4×V100 PCIe, 10 Gbps) | Table 1 |
| TTA speedup vs DP, VGG-16 | 2.46× (epoch 2.98×) | 2x8 Cluster-B (8×V100 NVLink, 25 Gbps) | Table 1 |
| TTA speedup vs DP, GNMT-16 | 3.14×, straight pipeline | 2x8 Cluster-B | Table 1 |
| TTA speedup vs DP, AWD LM | 4.25×, straight | 1x4 Cluster-A | Table 1 |
| TTA speedup vs DP, S2VT | 3.01× (config 2-1-1) | 4x1 Cluster-C (Titan X, 40 Gbps) | Table 1 |
| ResNet-50 | 1× (optimizer picks pure DP) | 4x4 A and 2x8 B | Table 1, §5.5 |
| AlexNet epoch-time speedup | 4.92× (A), 2.04× (B) | synthetic data, 16 GPUs | Table 1 |
| Communication reduction vs DP | 88% (AWD LM), 85% (S2VT) | chosen configs | §5.2 |
| vs fastest LARS large-batch DP | over 2.4× faster to target | VGG-16, Cluster-C | §5.2, Fig. 13 |
| vs ASP DP | ASP 7.4× longer to reach 48% accuracy | VGG-16, 4 Cluster-B servers | §5.2 |
| vs model parallelism (with first-stage replication) | 14.9× (VGG-16), 6.5× (AlexNet) | 4 GPUs, Cluster-A | §5.3, Fig. 14a |
| vs FlexFlow | 1.9× faster | AlexNet, Cluster-B | §5.3 |
| GPipe (same partitions) throughput slowdown | 55% / 71% at depth = NOAM; 35% / 42% at max depth that fits | GNMT-16, 16 GPUs, Cluster-A / B | §5.4 |
| Optimizer runtime | < 8 s | all models and deployments evaluated | §3.1, §5.5 |
| Profiling run | 1000 minibatches, 1 GPU | — | §3.1 |
| Best pipeline depth | 4 (NOAM) and 7 | GNMT-8, 4×V100, Cluster-A | §5.5, Fig. 18 |
| Runtime size | ~3000 LOC Python | PyTorch backend | §4 |

Inconsistencies noticed in the paper text:
- §5.2 says VGG-16 reached target 5.28× faster "on a single server", but Table 1 lists that result under 4x4 (A), and the next sentence describes the "4-server configuration".
- §5.2 says that on 4 servers (16 GPUs) of Cluster-A the speedups are 2.92× for GNMT-8 and 2.95× for GNMT-16. Table 1 gives 2.92× to GNMT-16 on 4x4 (A) and 2.95× to GNMT-8 on 3x4 (A), so the attribution and the server count differ.
- §5.2 says VGG-16 on 2 Cluster-B servers reached target 2.98× faster than DP. Table 1 lists 2.98× as the epoch-time speedup and 2.46× as the TTA speedup for that row.
- For GNMT-16 on 1x4 (A), Table 1 lists an epoch-time speedup of 1.46× but a TTA speedup of 2.2×. The text says only "∼1.5×", and the paper does not explain the row. (Own analysis) A TTA speedup above the epoch-time speedup would mean fewer epochs than DP, while §5.2 says PipeDream reaches target in a similar number of epochs.
- The introduction claims PipeDream is "1.7× faster" than GPipe-style pipelining. §5.4 reports percentage "throughput slowdowns" without defining them, so it is not clear which §5.4 figure supports the 1.7× claim.

## Limitations

- **Asynchronous semantics:** the default is not synchronous SGD. Staleness varies by stage, and the evidence is empirical TTA on seven models, not a convergence proof.
- **Chain partitioning:** stages are consecutive layers; the planner assumes stable per-input compute.
- **Memory not optimized:** the partitioner balances compute and communication, not memory. Per-stage footprints differ, and stashing grows with depth (Fig. 18b).
- **fp32 only:** the authors argue mixed precision would raise DP's overhead (Fig. 12) but do not run PipeDream with it.
- **Coarse recovery:** epoch-end checkpoints, and any failure restarts every stage.
- (Own analysis) All evaluated models train with per-GPU batches that fit one device; models whose weights exceed one GPU are not studied. The plan is computed once, with no re-planning for stragglers, shared clusters or elastic resources.
- The official repo's `pipedream_2bw` branch holds the authors' follow-up, "Memory-Efficient Pipeline-Parallel DNN Training" (ICML 2021).

## Relation to other systems

- **GPipe:** synchronous microbatching with flushes and activation recomputation; no partitioner or depth rule. PipeDream drops flushes via 1F1B plus stashing, accepting staleness; compared on identical partitions (§5.4).
- **FlexFlow / OWT:** hybrid intra-batch splits (searched / hand-designed) without inter-batch pipelining. PipeDream moves the same bytes but overlaps them with compute (§5.3).
- **BSP DP (PyTorch DDP, Horovod):** a special case, one replicated stage; chosen when weights are compact and activations large (ResNet-50).
- **ASP / parameter servers (Project Adam, SSP):** also trade staleness for throughput, but without per-stage version discipline; ASP showed much worse statistical efficiency (§5.2).
- **RL device placement (Mirhoseini et al.):** general search; PipeDream exploits pipeline structure for an exact polynomial-time DP (§2.1).
- **LARS large-batch DP:** syncs less often but did not reach target at batch 4096/8192 on VGG-16 (§5.2).

## Takeaways for practice

- A cheap per-layer profile plus a hierarchical bandwidth model sufficed for a fast partitioner whose predicted throughput tracked measured throughput (Fig. 15).
- Replicate small-weight layers and keep large-weight layers unreplicated: 15-1 for VGG-16 beat both DP and straight pipelines (Table 1, Fig. 14a).
- 1F1B keeps every stage busy with roughly NOAM minibatches in flight; deterministic round-robin keeps each minibatch's stashed state on one replica without a coordinator.
- Pipeline depth trades throughput for stash memory (Fig. 18); budget for it explicitly.
- (Own analysis) For schedulers: such jobs want gang allocation that matches the bandwidth hierarchy assumed by the plan; moving workers can invalidate the plan.

## References

- Paper (SOSP 2019): https://doi.org/10.1145/3341301.3359646
- PDF (Microsoft Research): https://www.microsoft.com/en-us/research/wp-content/uploads/2019/08/pipedream.pdf
- MSR publication page: https://www.microsoft.com/en-us/research/publication/pipedream-generalized-pipeline-parallelism-for-dnn-training/
- Code (official, Microsoft Research msr-fiddle; SOSP 2019 work on the `pipedream` branch): https://github.com/msr-fiddle/pipedream
