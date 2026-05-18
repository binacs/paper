---
paper_id: 3fd7c9ba742dd2b435afa75217847e5087e2f2a8
title: 'PipeDream: generalized pipeline parallelism for DNN training'
authors:
- D. Narayanan
- A. Harlap
- Amar Phanishayee
- Vivek Seshadri
- Nikhil R. Devanur
- G. Ganger
- Phillip B. Gibbons
- M. Zaharia
venue: Symposium on Operating Systems Principles
year: 2019
citations: 1158
abs_url: https://www.semanticscholar.org/paper/3fd7c9ba742dd2b435afa75217847e5087e2f2a8
pdf_url: ''
analyzed_at: '2026-05-18T10:00:39+00:00'
model: deepseek-chat
doi: 10.1145/3341301.3359646
---

# PipeDream: generalized pipeline parallelism for DNN training

## TL;DR

PipeDream introduces inter-batch pipelining to DNN training, combining it with intra-batch parallelism to improve throughput. It handles bi-directional training by versioning model parameters and scheduling forward/backward passes to avoid state mismatches and pipeline stalls.

## Problem & Motivation

DNN training is extremely time-consuming, requiring efficient multi-accelerator parallelization. Current intra-batch parallelization (e.g., data parallelism) splits a single iteration over workers but suffers from diminishing returns at higher worker counts due to communication overhead and underutilization. Adding pipelining across batches is challenging because DNN training is bi-directional: a forward pass is followed by a backward pass that depends on state from the forward pass. Naïve pipelining can cause version mismatches (using stale parameters) or require frequent pipeline flushes, reducing efficiency.

## Key Ideas

- Combine inter-batch pipelining with intra-batch parallelism to overlap computation and communication.
- Version model parameters to ensure numerically correct gradient computations when different workers use different parameter versions.
- Schedule forward and backward passes of different minibatches concurrently across workers to minimize pipeline stalls.
- Automatically partition DNN layers among workers to balance work and minimize communication.

## System Design

PipeDream partitions the DNN into stages, each assigned to a worker (e.g., GPU). Workers execute forward and backward passes for different minibatches in a pipelined fashion. Parameter versions are maintained to ensure that the backward pass uses the same parameter state as the corresponding forward pass. The scheduler coordinates the execution of passes to avoid deadlocks and minimize idle time. Communication between stages is overlapped with computation.

## Evaluation

The paper evaluates PipeDream on a range of DNN tasks (e.g., image classification, language modeling) and hardware configurations (up to 16 GPUs). Baselines include data parallelism and other intra-batch methods. PipeDream achieves up to 5.3X speedup over commonly used intra-batch parallelism techniques while maintaining model accuracy.

## Takeaways

- Pipelining across batches can significantly improve throughput beyond what intra-batch parallelism alone can achieve.
- Versioning model parameters is a practical solution to the bi-directional training problem in pipelined DNN training.
- Automatic partitioning of layers is important for load balancing and minimizing communication.
- The combination of pipelining and data parallelism is effective for scaling DNN training.

## Related Work

PipeDream extends prior work on pipeline parallelism (e.g., GPipe) by addressing the challenges of bi-directional training and introducing parameter versioning. It contrasts with pure data parallelism (e.g., using all-reduce) and model parallelism (e.g., splitting layers across devices).

## Open Questions

- How does PipeDream handle dynamic computation graphs or models with non-uniform layer sizes?
- Can the pipelining approach be combined with other parallelism strategies like tensor parallelism?
- What are the trade-offs between pipeline depth and batch size in terms of throughput and memory usage?
- How does PipeDream perform on very large models (e.g., with billions of parameters) where memory constraints are tighter?
