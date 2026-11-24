---
title: 'Optimizing RLHF Training for Large Language Models with Stage Fusion'
authors:
- Yinmin Zhong
- Zili Zhang
- Bingyang Wu
- Shengyu Liu
- Yukun Chen
- Changyi Wan
- Hanpeng Hu
- Lei Xia
affiliations: 'Peking University, StepFun'
venue: 'NSDI'
year: 2025
arxiv_id: '2409.13221'
abs_url: https://www.usenix.org/conference/nsdi25/presentation/zhong
pdf_url: https://www.usenix.org/system/files/nsdi25-zhong.pdf
code_url: https://github.com/FlexFusion/FlexFusion
note_type: deep-read
written_at: '2026-11-25'
---

# Optimizing RLHF Training for Large Language Models with Stage Fusion

> **Why it matters:** RLHFuse shows the waste in RLHF training sits *inside* the stages — long-tail generation, pipeline bubbles — and that both are recoverable by scheduling at subtask granularity.

## Problem

A PPO-style RLHF iteration runs six tasks over four models (Actor, Critic, Reference, Reward) in three stages — **generation** (Actor rollout), **inference** (Ref/Critic/Reward forwards), **training** (Actor and Critic backward + optimizer) — with data and weight dependencies forming a barrier between stages (§1, §2.1). Prior frameworks make each *task* the scheduling atom: a placement and 3D-parallel strategy per task, tasks run serially. Two structural holes follow (§2.2):

1. **Data skew in generation.** Output lengths are long-tailed: on LMSYS-Chat-1M the 99.9th-percentile length exceeds 10× the median, and under 1% of samples consume more than half the generation stage's time (Fig. 2). Thousands of GPUs idle while a handful of sequences decode, and it worsens as max output length grows.
2. **Pipeline bubbles in training.** Large actors need pipeline-parallel degrees in the tens. The 1F1B bubble fraction is `(N−1)/(N−1+M)` for `N` stages and `M` micro-batches, `(N−1)/(N−1+KM)` interleaved; as `N` approaches `M` it tends to ~50% (Fig. 3). RLHF has *two* pipelined training tasks, so the loss is paid twice.

The thesis: decompose tasks into subtasks — *samples* for generation/inference, *micro-batches* for training — and fuse across barriers.

## Core design

### Inter-stage fusion: generation ⇄ inference at sample granularity (§4)

Generation→inference dependencies are per-sample: once a sample finishes decoding, Ref/Critic/Reward forwards on it can start. Training cannot be fused this way, since each mini-batch must see the same data distribution, so that barrier stays (§4.1). The plan (§4.2):

- **Migration trigger.** When still-decoding samples fall below threshold `R_t`, the rest are migrated. `R_t` is picked by sweeping 5%–95% of the global batch in a simulator for minimum predicted time, and re-tuned at runtime as the length distribution drifts.
- **Destination count.** Consolidate onto `m` instances with `m ≥ R_t / BS_max` (decode batch below the GPU-saturation point, so per-token latency is unchanged) and `m ≥ R_t·M / C` (`M` = KV size of the longest sample, `C` = per-instance KV capacity); the `m` instances holding the most unfinished samples win.
- **Mechanism.** KV caches move over RDMA rather than being recomputed by prefill; freed instances switch at once to inference on finished samples. One round normally suffices, as tail decoding outlasts the inference stage.

### Intra-stage fusion: one bidirectional pipeline for Actor + Critic (§5)

Chimera fills bubbles by replicating a model and running the replicas in opposite pipeline directions. RLHF already has two trainable models, so replication is unnecessary — but Actor and Critic differ in size and parallel strategy, so Chimera's symmetric schedule does not apply (§5.1). Heterogeneity is normalized first: if `tp1 = s·tp2`, every `s` consecutive stages of the second model merge into one, giving `pp2/s` stages (needs `pp2` divisible by `s`). The task becomes fusing `K1` pipeline groups of A with `K2` of B, coprime, `K1·N1 = K2·N2 = N` (Fig. 6). A schedule is an `N × 2(M1+M2)` matrix of subtasks with profiled latencies, subject to data dependency, deadlock freedom and per-stage peak activation memory ≤ `C`; objective is minimum latency, tie-broken by lower memory.

A greedy bidirectional extension (always run the larger model's ready subtask) is rejected: no global view, cannot delay a micro-batch to fill a later bubble, ignores memory (§5.2). Instead:

- **Alg. 1** — simulated annealing seeded by the greedy schedule; initial temperature = greedy execution time; worse neighbours accepted with probability `e^((e_cur−e_nb)/T)`; `T ← αT` until `T < ε`.
- **Alg. 2** — neighbour = random stage, swap two *adjacent* subtasks, resample until valid.
- **Alg. 3** — energy = max finish time over stages, memoized recursion over dependencies, `O(N·(M1+M2))`.
- **Second pass** — re-anneal from the latency-optimal schedule with peak activation memory as energy, accepting only latency-neutral moves.

The search parallelizes over random seeds and generalizes past two models.

### Implementation (§6)

~7K lines of Python/C++/CUDA on Megatron-LM, extended so tasks run asynchronously on multiple device meshes with per-task parallelism. Generation uses an in-house engine (continuous batching, prefix sharing, chunked prefill), not vLLM. Per-task strategies come from a pruned brute-force search over a profiling-based simulator (following ReaLHF), extended to workflow level to pick `R_t`; schedules lower to per-device NCCL sequences. Also: cross-node-minimizing weight redistribution, Ref/RW weights swapped in from CPU overlapped with compute, GAE as one matmul, length-aware mini-batch balancing.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Throughput vs DeepSpeed-Chat | 2.5×–3.7× | LLaMA 13B–65B Actor/Critic pairs, HH-RLHF | §7.1, Fig. 7 |
| vs ReaLHF | 1.4×–2.4× | same | §7.1, Fig. 7 |
| vs RLHFuse-Base (fusion off) | 1.2×–1.4× | isolates both fusion techniques | §7.1 |
| Generation+inference speedup | 1.2×–1.6× | grows with max output length | §7.2, Fig. 8 |
| Training stage speedup | 1.2×–1.3× | intra-stage fusion only | §7.2, Fig. 8 |
| Non-compute overhead (switching, resharding, transfer) | <3% of iteration; migration negligible | — | §7.2 |
| Best migration threshold `R_t` | ≈20% of global batch | 33B/65B, 65B/33B, max len 1024 | §7.3, Fig. 9 |
| Generation tail | <1% of samples → >50% of generation time | LMSYS-Chat-1M | §2.2, Fig. 2 |
| Fused schedule vs serial 1F1B | 1.38× (33B/13B, PP 8/4, GBS 8; greedy 1.29×, 1F1B+ 1.10×); 1.50× (65B/33B, PP 16/16, GBS 16) | = lower bound | Table 3 |
| Peak activation memory | greedy up to 2.88× of 1F1B; annealed 1.0×–1.47× | Table 3 configs | Table 3 |
| Deep dive | fused 65B(PP16)+33B(PP8) costs the same as 65B alone | micro-batches = PP | §7.4, Fig. 10 |
| Testbed | 256 Hopper GPUs (32×8), NVLink, 8×200 Gbps RoCEv2 | batch 512, mini-batch 64, max output 512/1024/2048 | §7 |

## Limitations

From the paper:

- **Inference→training is not fused** (§4.1): iterations get cheaper, the synchronous on-policy barrier stays.
- **`R_t` is workload-dependent**, from simulation, re-tuned as the length distribution drifts; drift is argued to be gradual (§7.3).
- **Structural constraints:** `pp2` divisible by `s`, coprime `K1`, `K2` (§5.2) — not every parallel-strategy pair is fusible as-is. Annealing gives no optimality guarantee; one Table 3 config falls short of the lower bound.
- **Benchmark scope:** one cluster, 256 GPUs, LLaMA 13B–65B, HH-RLHF. DSChat's mini-batch had to be raised to 256 to run; the authors note this favours DSChat.
- **RDMA assumption:** migration needs a high-bandwidth fabric; prefill recomputation is named as the alternative but not evaluated.

*My own analysis, not claims in the paper:*

- *The evaluation omits HybridFlow/verl and OpenRLHF, the most widely deployed open frameworks; baselines are DSChat, ReaLHF and RLHFuse-Base only.*
- *The public repo ships only intra-stage fusion; the migration path, generation engine and simulator are not open-sourced, so end-to-end reproduction is hard.*
- *Migration concentrates tail samples on few instances, so their KV capacity becomes the new limit at the 32K–128K output lengths typical of 2025 reasoning RL — far beyond the 2048 tested.*
- *Intra-stage fusion presumes PPO with a trained critic; critic-free algorithms (GRPO and relatives) have one training task, so the bidirectional pipeline loses its second model.*

## Relation to other systems

- **HybridFlow / verl** (EuroSys 2025, arXiv 2409.19256): hybrid single-/multi-controller model with hierarchical APIs for RLHF dataflows plus a 3D-HybridEngine resharding the actor between training and generation; 1.53×–20.57× over baselines. Programmability and placement at *task* level; RLHFuse keeps task-level strategy search (ReaLHF's) and adds the subtask fusion HybridFlow lacks.
- **OpenRLHF** (arXiv 2405.11143): Ray + vLLM + DeepSpeed + HF Transformers, pitched on accessibility and simpler code, 1.22×–1.68× speedups. It spreads the four models over Ray actors but still runs stages serially — the task-granular execution RLHFuse targets.
- **DeepSpeed-Chat** (arXiv 2308.01320): the reference InstructGPT-style pipeline, co-locating all models and switching between ZeRO-3 training and TP generation; its abstract claims accessibility and affordability, with no speedup figures. RLHFuse's weakest baseline.
- **StreamRL** (arXiv 2504.15930): same two inefficiencies, opposite architecture — fully *disaggregated* generation and training on dedicated, possibly heterogeneous cross-datacenter resources, with streaming generation and an output-length ranker routing long samples; up to 2.66× throughput, 1.33× cost-effectiveness. RLHFuse instead migrates KV caches inside one co-located pool.
- **AReaL** (NeurIPS 2025, arXiv 2505.24298): removes the batch barrier — rollout workers generate continuously while trainers update as data arrives, with staleness-bounded load balancing and a staleness-tolerant PPO variant; up to 2.77× over synchronous systems at equal GPU count. The counter-position: AReaL relaxes RL semantics to kill the bubble, RLHFuse kills it by scheduling.

## Takeaways for practice

- **Pick the scheduling atom below the task.** The 1.2×–1.4× over the same system with fusion off comes purely from treating samples and micro-batches as schedulable units, reusable in any multi-stage workflow with per-item dependencies.
- **Long-tail skew is a migration problem, not a batching problem.** Consolidating stragglers is cheap when KV state moves over RDMA, and the destination count falls out of two capacity inequalities (saturation batch size, KV memory).
- **Two heterogeneous pipelines can fill each other's bubbles,** but search the joint schedule rather than greedily interleaving: greedy cost up to 2.88× peak activation memory for less speedup.
- **Budget for planning infrastructure.** Threshold and schedule come from a simulator plus a 768-core two-pass annealing search (latency, then memory); this scheduler is as much offline planner as runtime. Check its assumptions before adopting: PPO with a critic, synchronous iterations, RDMA, outputs ≤2K tokens.

## References

- Paper (NSDI '25): https://www.usenix.org/conference/nsdi25/presentation/zhong
- PDF: https://www.usenix.org/system/files/nsdi25-zhong.pdf
- arXiv preprint (earlier title "RLHFuse"): https://arxiv.org/abs/2409.13221
- Code (intra-stage fusion only): https://github.com/FlexFusion/FlexFusion
