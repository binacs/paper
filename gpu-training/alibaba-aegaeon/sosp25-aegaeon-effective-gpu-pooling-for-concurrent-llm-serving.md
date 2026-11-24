---
title: 'Aegaeon: Effective GPU Pooling for Concurrent LLM Serving on the Market'
authors:
- Yuxing Xiang
- Xue Li
- Kun Qian
- Yufan Yang
- Diwen Zhu
- Wenyuan Yu
- Ennan Zhai
- Xuanzhe Liu
affiliations: 'Peking University, Alibaba Group'
venue: 'SOSP'
year: 2025
paper_id: 7b918978febd9142781786aa6733a42f521841a4
doi: 10.1145/3731569.3764815
abs_url: https://dl.acm.org/doi/10.1145/3731569.3764815
pdf_url: https://ennanzhai.github.io/pub/sosp25-aegaeon.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Aegaeon: Effective GPU Pooling for Concurrent LLM Serving on the Market

> **Why it matters:** It shows that a model marketplace's long tail of rarely-used LLMs can be packed onto a shared GPU pool by preempting and auto-scaling models at *token* granularity, provided model-switch cost is driven from tens of seconds to about a second.

(Full author list: Yuxing Xiang, Xue Li, Kun Qian, Yufan Yang, Diwen Zhu, Wenyuan Yu, Ennan Zhai, Xuanzhe Liu, Xin Jin, Jingren Zhou.)

## Problem

A model market (Hugging Face; Alibaba Cloud Model Studio) serves thousands of models with very skewed popularity. In Model Studio's trace, 94.1% of 779 models receive 1.35% of 167.6M requests yet hold 17.7% of a 30K-GPU fleet, each averaging under 0.2 req/s per GPU (§2, Fig. 1a). Hot models, meanwhile, see bursts beyond their reservation (Fig. 1b). Dedicated instances per model therefore waste most GPUs.

Two existing approaches cap out:

- **Multiplexing** (co-locating models on a GPU) is memory-bound to about two or three models per GPU.
- **Request-level auto-scaling** (serverless-style load/evict) suffers head-of-line blocking: a long decode pins the GPU to one model. With Poisson arrivals, E[m] = M·(1−e^(−λT)) models are active (Thm. 3.1, Eq. 1). For 100 models at 3.7 req/s total, that is 46.55 on average, so fewer than three models per GPU (§1, §3.1).

The paper's claim is that GPUs must switch models *between tokens*, not between requests, and that this needs a nearly free switch.

## Core design

### Token-level scheduling with disaggregated prefill/decode (§4)

Prefill-first scheduling hurts TBT and decode-first hurts TTFT (Fig. 6), and a joint ILP is too slow online (§4.1). Aegaeon therefore splits GPUs into prefill and decode instances (following DistServe/Splitwise) and schedules each phase separately. Any instance can preempt and swap its model.

- **Prefill: grouped FCFS (Alg. 1, §4.2).** Each prefill instance queues *groups* of same-model requests, up to MAX_GPSIZE = 8 (grid-searched). An arriving request joins a same-model group with room. Otherwise a new group goes to the instance with the least estimated load (pending run time plus auto-scaling time). Prefill runs at batch size 1. Grouping amortizes switches, and capping by accumulated members keeps order near FCFS without starvation.
- **Decode: weighted round-robin with time quotas (Alg. 2, §4.3).** Each decode instance keeps a rotating work list of single-model batches. A round reorders the list so same-model batches sit next to each other, then runs each batch for its quota q_i. With n_k = d/t_k (target TBT divided by batch k's step time, i.e., how many steps of slack a token deadline gives) and c the total switch overhead in the round: q_i = c / (n_i·(α − Σ_k 1/n_k)) (Eq. 2), and α = max(c/(min_k n_k · Q_MAX) + Σ_k 1/n_k, 0.5) (Eq. 3), with Q_MAX = 4 s. α acts as the reciprocal of the expected SLO attainment, floored at 0.5 so turns have a minimum length. The idea: decode tokens faster than the TBT target while a model holds the GPU, banking slack that covers the time the batch is swapped out.

### Making a model switch cheap (§5)

Per-switch cost is the whole game. An unoptimized vLLM engine start can take up to 26.9 s for a 13B model, and loading LLaMA-13B (TP=2) weights over PCIe 4.0 takes about 4.6 s (§5).

- **Component reuse (§5.1).** Engines are initialized once per instance, and everything except weights and KV is reused across models: the Ray/NCCL executor, profiling results, tokenizers, the scheduler, and a pre-pinned host KV pool. This removes over 80% of scale-up latency (Fig. 8a).
- **Explicit memory management (§5.2, Fig. 9).** VRAM is one self-managed buffer, with about 10% left for tensor libraries. Weights and KV are allocated from it by **bump allocation** (freeing resets the pointer), so there is no allocator GC. Host DRAM holds a shared **Model Cache** of raw checkpoint tensor chunks, and each GPU has a page-locked **Stage Buffer** for copies. The next model can be **prefetched** on a separate CUDA stream behind the running model, then moved forward on-device. KV for different model shapes lives in a **unified KV cache** (GPU and CPU) using **slab allocation**, with one slab class per KV shape.
- **Fine-grained KV cache synchronization (§5.3).** Preempted batches swap KV to host and back on resume, possibly on another instance (prefill → decode). CUDA events with per-transfer tracking overlap swap-in/out with compute, and **move lists** enforce dependencies off the critical path. Combined with §5.1–5.2, scale-up latency drops by up to 97% (Fig. 10).

### Implementation (§6)

About 5,700 lines of Python and CUDA/C++, built on asyncio, Ray and vLLM.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Long-tail skew | 94.1% of 779 models get 1.35% of 167.6M requests, using 17.7% of 30K GPUs | Model Studio trace | §2, Fig. 1a |
| Active models under request-level scaling | 46.55 of 100 active at 3.7 req/s total | Poisson model | §1, §3.1, Eq. 1 |
| Engine init cost (unoptimized) | up to 26.9 s | 13B model | §5 |
| Weight load time | ~4.6 s (2.83 GB/s) | LLaMA-13B, TP=2, PCIe 4.0 | §5 |
| Component reuse saving | >80% of scale-up latency | | §5.1, Fig. 8a |
| Auto-scaling overhead reduction | up to 97% | all §5 optimizations | Abstract, §5.3, Fig. 10 |
| Near-instant scale-ups (prefetch hit) | ~50%; others < 1 s | eval workload | §7.3, Fig. 15 |
| KV sync overhead | < 1 s per request total | | §7.3, Fig. 15 |
| Unified KV cache fragmentation | < 20% | | §7.3, Fig. 16 |
| Goodput vs ServerlessLLM | 2× | RPS 0.1, 16×H800 (6 prefill + 10 decode) | §7.2, Fig. 11 |
| Sustainable arrival rate | 2.5× higher | RPS 0.5 | §7.2, Fig. 11 |
| Models served | up to 70 on 10 decode GPUs (7 models/GPU); MuxServe capped at 32 | | §7.2, Fig. 11 |
| Headline vs baselines | 2–2.5× higher arrival rate, or 1.5–9× more goodput | | Abstract |
| Strict SLO | still ahead at 0.5× and 0.3× SLO; at 0.2× no longer beats MuxServe | | §7.2, Fig. 13 |
| Production GPUs | 1,192 → 213 H20 (82% saving) | 28 models of 1.8–7B (TP=1) + 19 models of 32–72B (TP=4) | §7.5 |
| Production arrival rates | 0.01–1.13 req/s per model, mean 0.037 | | §7.5 |
| Production GPU utilization | 13.3%–33.9% → 48.1% average | 70-hour window | §7.5, Fig. 18 |
| Beta deployment duration | >3 months in Model Studio | | §1 |

## Limitations

- **Latency headroom is consumed.** The design relies on decoding faster than TBT to bank slack for swap-outs. Under tight SLOs the advantage shrinks, and at 0.2× SLO Aegaeon loses to MuxServe (Fig. 13). It is a tail-model system, not a latency-critical one.
- **Hardware assumptions.** Large host DRAM and fast PCIe are assumed. On 24 GB A10s prefetching is disabled (§7.4). The largest model tested is 72B at TP=4. Multi-node models and MoE are not addressed.
- **Evaluation scale.** Controlled runs use 16 H800s, synthetic Poisson arrivals over ShareGPT variants, and mostly 6B–14B models (§7.1). The 82% production figure includes redundant capacity, so it is a deployment comparison, not a controlled one.
- **Static P/D split and tuned knobs.** There is no production P/D ratio or rebalancing policy. MAX_GPSIZE, Q_MAX and a PCIe factor β = 0.625 are set empirically.
- **No cross-model fairness or isolation analysis** beyond FCFS grouping and quotas.
- **Later critique.** Prism (arXiv 2505.04021) characterizes Aegaeon as temporal sharing via P/D disaggregation that needs weight duplication across prefill and decode instances and struggles with diverse, dynamic access patterns, and proposes GPU memory ballooning instead.

## Relation to other systems

- **AlpaServe (OSDI'23):** uses model parallelism for statistical multiplexing of a few co-placed models, with placement planned offline. Aegaeon cites it as temporal multiplexing (§8) and instead swaps models dynamically per token.
- **MuxServe (ICML'24):** uses spatial-temporal multiplexing of co-located LLMs. It is bounded by co-resident memory (32 models versus Aegaeon's 70 in Fig. 11), but it wins at the strictest SLO because it pays no swap cost.
- **ServerlessLLM (OSDI'24):** offers fast multi-tier checkpoint loading, locality-aware placement and live migration at request granularity, so it is exposed to HOL blocking. It is the main baseline, along with "ServerlessLLM+" with oracle SJF (§7.1). Aegaeon targets the non-weight switch costs it leaves on the path.
- **Llumnix (OSDI'24):** migrates requests and KV across replicas of the *same* model for load balancing. It is not discussed in the paper. It is complementary, since Llumnix moves requests while Aegaeon moves models.
- **vLLM / PagedAttention (SOSP'23):** Aegaeon's backend. Aegaeon replaces per-engine memory with a cross-model bump allocator and shape-keyed slab KV caches.
- **DistServe / Splitwise:** the source of the P/D disaggregation Aegaeon builds on.

## Takeaways for practice

- For long-tail catalogs, **pool at token granularity**. Request-level LLM scaling is limited by long decodes (HOL), not just cold start.
- **Profile the whole switch path.** Engine and NCCL init, profiling, pinning and the allocator dominate: 26.9 s versus ~4.6 s of weight load for 13B. Keep engines warm and swap only weights and KV.
- **Own the memory.** A preallocated VRAM arena with bump allocation, plus slab-allocated KV per shape, makes swaps predictable.
- **Turn TBT slack into a scheduling budget.** Quotas from (target TBT / step time) and the known switch cost give an analyzable rule for time-slicing decode.
- **Group by model on prefill** to amortize switches while staying near FCFS.
- Production utilization only reached ~48% with headroom kept, so budget for peaks and failures.

## References

- Paper: https://dl.acm.org/doi/10.1145/3731569.3764815 (author copy: https://ennanzhai.github.io/pub/sosp25-aegaeon.pdf)
- Slides (author): https://echostone1101.github.io/files/aegaeon-slides-final.pdf
- Blog (Alibaba Cloud): https://www.alibabacloud.com/blog/alibaba-cloud-boosts-gpu-utilization-with-ai-infrastructure-breakthrough-at-sosp-2025_602623
