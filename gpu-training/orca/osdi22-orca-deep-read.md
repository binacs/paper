---
title: 'Orca: A Distributed Serving System for Transformer-Based Generative Models'
authors:
- Gyeong-In Yu
- Joo Seong Jeong
- Geon-Woo Kim
- Soojeong Kim
- Byung-Gon Chun
affiliations: 'Seoul National University, FriendliAI'
venue: 'OSDI'
year: 2022
abs_url: https://www.usenix.org/conference/osdi22/presentation/yu
pdf_url: https://www.usenix.org/system/files/osdi22-yu.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Orca: A Distributed Serving System for Transformer-Based Generative Models

> **Why it matters:** Orca introduced iteration-level scheduling (now usually called "continuous batching") and selective batching, which every production LLM server since then (vLLM, TGI, TensorRT-LLM, SGLang) builds on.

## Problem

Autoregressive models such as GPT-3 produce one token per forward pass. Inference has an *initiation* phase, which processes all prompt tokens, and then many *increment* iterations. Each increment iteration feeds back the previous output token and reuses the attention keys and values cached from earlier tokens (§2, Fig. 1).

Serving stacks of the time, such as Triton grouping requests in front of the FasterTransformer engine, schedule at **request level**. The scheduler pulls a batch from a queue and hands it to the engine, and the batch stays fixed until every request in it finishes (§1–2, Fig. 2). That causes two problems (§3, C1, Fig. 3):

- **Early-finished requests** keep occupying batch slots. They still receive computation in later iterations, and they cannot be returned to the client until the longest request in the batch finishes.
- **Late-joining requests** wait in the queue for the whole current batch to finish, even when the GPU has spare capacity.

The natural fix is to schedule at iteration granularity, but that creates a second problem (C2). The requests in one iteration then differ in phase (initiation or increment), in input length, and in current token index. Their attention inputs, `[L_i, H]` queries against request-specific key and value histories, cannot be stacked into a single `[B, L, H]` tensor.

## Core design

### Iteration-level scheduling (S1)
- The scheduler invokes the engine for **one iteration** on a selected batch, receives the output tokens, and then decides again (§3, Fig. 4). A finished request (EOS or `max_tokens` reached) is returned immediately, and a new arrival can join at the next iteration.
- A request pool holds all live requests. The endpoint, request pool, scheduler and engine are separate components (Fig. 4).

### Selective batching (S2)
- **Batched ops:** the non-attention operations (Linear/QKV projection, output projection, FFN, LayerNorm, Add, GeLU). They are applied to a **flattened** `[ΣL_i, H]` token matrix with no explicit batch dimension, so requests of different lengths and phases share one GEMM (§3, Fig. 5). For example, 7 tokens across several requests form a `[7, H]` tensor.
- **Attention is split per request:** a *Split* op slices the flattened tensor per request, attention runs separately for each request against that request's own keys and values, and a *Merge* op concatenates the outputs back into `[ΣL_i, H]` (Fig. 5).
- **Why splitting attention is cheap:** batching pays off by amortising weight reads from GPU memory. Attention has **no model parameters**, so batching it saves little (§1, §3). The microbenchmark in §6.1 supports this: the engine is on par with, or slightly slower than, FasterTransformer at equal batch, and the authors attribute the gap to unbatched attention.
- **Attention K/V manager:** it keeps each request's keys and values across iterations until the scheduler explicitly frees them. Attention kernels locate the history by request ID and token index (§3, §4.1).

### Distributed architecture (§4.1, Figs. 6–7)
- **Intra-layer parallelism** (Megatron-style tensor parallelism, splitting matmuls across GPUs) is combined with **inter-layer parallelism** (pipeline stages over groups of layers). In Fig. 6, a 4-layer model is split into 2 inter-layer partitions × 3 intra-layer partitions on 6 GPUs.
- **Processes:** there is one worker process per inter-layer partition, possibly on different machines. Inside it, one CPU thread drives each GPU of the intra-layer group.
- **Control plane / data plane split:** the engine master sends the iteration's tokens plus a small control message to Worker 1 over **gRPC**. The message carries request IDs, the current token index for increment-phase requests, and the input token count for initiation-phase requests. Each worker's controller forwards the message to the next stage **without waiting for its own GPU kernels to finish**. Intermediate activations move GPU-to-GPU over **NCCL**. The last stage synchronises and returns output tokens to the master. This separation keeps CPU-GPU synchronisation off the critical path, and §6.1 credits it for the 175B microbenchmark gain.
- **Implementation:** about 13K lines of C++ on CUDA, with gRPC and NCCL. Fused kernels cover LayerNorm, Attention and GeLU (§5).

### Scheduling algorithm (§4.2, Algorithm 1)
- **Selection:** the pool is sorted by arrival time and up to `max_bs` requests are taken. This gives **iteration-level FCFS**: an earlier request has always run at least as many iterations as a later one, although a later short request may still finish first.
- **KV-slot reservation:** the operator sets `n_slots`, the K/V memory region measured in token slots, as the largest value that fits in GPU memory. When a request is first scheduled, the scheduler reserves `req.max_tokens` slots and skips the request if `n_rsrv + max_tokens > n_slots`. It releases those slots when the request finishes. Because a request can never exceed `max_tokens`, an admitted request is guaranteed to have K/V space, so the scheduler never deadlocks or evicts mid-generation.
- **Pipelining without microbatches:** the scheduler keeps up to `n_workers` independent batches in flight, one per pipeline stage, and blocks only when `n_scheduled == n_workers` (Fig. 8a). FasterTransformer instead has to split one request-level batch into microbatches. That forces a choice between batching efficiency (bigger microbatches) and fewer pipeline bubbles (more microbatches). Orca avoids the trade-off because each stage can work on a different batch (§4.2, Fig. 8b).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| End-to-end throughput gain over FasterTransformer at equal latency | 36.9× | GPT-3 175B | Abstract, §1 |
| Throughput at 190 ms median normalized latency | Orca 6.81 req/s vs FT 0.185 req/s | 175B, 16 A100 (2 pipeline × 8 tensor) | §6.2, Fig. 10 |
| Engine speed-up over FT (no pipelining) | up to 47% faster | 175B microbenchmark, same batch | §6.1, Fig. 9 |
| Engine vs FT on single-stage models | similar or slightly slower | 13B, 101B | §6.1, Fig. 9 |
| FT out-of-memory point (pre-allocates K/V for max sequence length) | batch ≥ 8 (13B), batch ≥ 16 (101B) | microbenchmark | §6.1 |
| Model configurations (layers / hidden / GPUs) | 13B: 40/5120/1; 101B: 80/10240/8; 175B: 96/12288/16; 341B: 120/15360/32 | max sequence length 2048, fp16 | Table 1 |
| Parallelism (inter × intra) | 1×1, 1×8, 2×8, 4×8 | 13B, 101B, 175B, 341B | Table 1 |
| Testbed | Azure ND96asr A100 v4: 8× A100-40GB per VM over NVLink, 8× 200 Gb/s HDR InfiniBand (1.6 Tb/s) per VM, up to 4 VMs | all experiments | §6 |
| Workload | Poisson arrivals, input length U[32, 512], max generated tokens U[1, 128], no EOS emitted | synthetic trace | §6.2 |
| Best FT configs (max_bs, microbatch) | (1, 1) or (8, 8) | end-to-end | §6.2 |

## Limitations

These points are this note's own reading of the design, not claims the paper makes.

- **Worst-case KV reservation.** Every admitted request reserves `max_tokens` slots up front, so memory sized for the maximum is held even by requests that stop early. That caps concurrency well below what the memory could hold. vLLM's PagedAttention targets this waste directly with on-demand block allocation, at the price of needing preemption or swapping when memory runs out.
- **Batch size counted in requests only.** There is no per-iteration token budget, so an initiation-phase request with a long prompt that joins a batch inflates that iteration's latency for every co-scheduled decoding request. The paper does not analyse this interference. Sarathi-Serve (chunked prefill) and DistServe (disaggregation) are built around it.
- **FCFS with no SLO awareness.** Requests have no priorities, the scheduler cannot preempt, and the paper does not discuss starvation or fairness across tenants.
- **Optimistic evaluation.** The workload is synthetic, outputs are short (≤128 tokens) and no request emits EOS early. The baseline is FT behind a scheduler the authors wrote, not production Triton.
- **Tight coupling.** The scheduler and engine are co-designed. A general interface that lets other engines support iteration-level scheduling is left to future work (§7).
- **Per-request attention launches** were acceptable at the batch sizes tested. Later systems use fused variable-length or paged attention kernels instead.

## Relation to other systems

- **FasterTransformer / Triton (baselines):** these are fast fused-kernel engines with tensor and pipeline parallelism, but they batch at request level. FT pre-allocates K/V memory for the full sequence length and pipelines only through microbatches of one batch. Orca keeps comparable kernels and changes the scheduling granularity and the pipelining model.
- **BatchMaker (EuroSys'18):** cellular batching for RNNs at the granularity of a cell. It cannot batch Transformer steps that attend to different K/V histories, and it has no model or pipeline parallelism (§7). Orca's selective batching is the Transformer-specific answer.
- **vLLM / PagedAttention (SOSP'23):** keeps iteration-level scheduling but replaces Orca's contiguous, worst-case K/V reservation with paged blocks allocated on demand. Its abstract reports 2–4× throughput at the same latency over FasterTransformer and Orca, with larger gains for longer sequences and larger models.
- **Sarathi-Serve (OSDI'24):** keeps iteration-level batching but splits prefills into chunks of roughly equal size and uses "stall-free" admission, so new prompts do not stall ongoing decodes. Its abstract also notes that uniform iterations reduce pipeline bubbles. It reports up to 2.6× (Mistral-7B, 1 A100), 3.7× (Yi-34B, 2 A100) and 5.6× (Falcon-180B with pipeline parallelism) serving capacity over vLLM under tail-latency SLOs.
- **DistServe (OSDI'24):** rejects colocating the two phases altogether. It places prefill and decode on separate GPUs with per-phase parallelism and optimises goodput under TTFT/TPOT SLOs, reporting 7.4× more requests or 12.6× tighter SLOs (abstract).

## Takeaways for practice

- **Schedule at the finest unit the engine can re-plan.** For autoregressive models that unit is one decoding step. Request-level batching wastes compute on finished requests and adds queueing delay.
- **Batch what touches weights; split what does not.** Flattening tokens across requests for GEMMs and handling attention per request (or in a variable-length kernel) is the core trick. It generalises to any operator whose cost is dominated by parameter reads.
- **Admission control is memory control.** Orca's `n_slots`/`max_tokens` reservation is a simple, deadlock-free admission policy. Its cost is worst-case over-reservation. Decide explicitly between conservative reservation (no preemption) and on-demand paging (needs preemption, swapping or recompute).
- **Budget by tokens as well as requests.** Orca's `max_bs` caps requests only. Production schedulers also need a per-iteration token budget to bound decode latency when long prompts arrive.
- **Keep control off the GPU critical path.** A CPU-side control plane (gRPC) that runs ahead of the GPU data plane (NCCL) made the 175B engine faster. With iteration-level scheduling, each pipeline stage can also hold a different batch instead of microbatches.

## References

- Paper: https://www.usenix.org/conference/osdi22/presentation/yu
- PDF: https://www.usenix.org/system/files/osdi22-yu.pdf
- Later work (abstracts only): vLLM https://arxiv.org/abs/2309.06180 ; Sarathi-Serve https://arxiv.org/abs/2403.02310 ; DistServe https://arxiv.org/abs/2401.09670
