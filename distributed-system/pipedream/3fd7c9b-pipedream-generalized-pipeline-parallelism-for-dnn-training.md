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
citations: 1144
abs_url: https://www.semanticscholar.org/paper/3fd7c9ba742dd2b435afa75217847e5087e2f2a8
pdf_url: ''
analyzed_at: '2026-05-11T09:37:52+00:00'
model: deepseek-chat
doi: 10.1145/3341301.3359646
---

# PipeDream: generalized pipeline parallelism for DNN training

## TL;DR

PipeDream introduces inter-batch pipelining to DNN training, combining it with intra-batch parallelism to improve throughput. It handles bi-directional computation by versioning model parameters and scheduling forward/backward passes to avoid state mismatches and pipeline stalls.

## Problem & Motivation

DNN training is time-consuming and requires efficient multi-accelerator parallelization. Existing intra-batch parallelism (data/model parallelism) suffers from diminishing returns at higher worker counts due to communication overhead and underutilization. Adding pipelining across batches is challenging because DNN training is bi-directional: a forward pass is followed by a backward pass that depends on intermediate state from the forward pass. Naïve pipelining can cause version mismatches (using stale parameters) or require frequent pipeline flushes, reducing efficiency.

## Key Ideas

- Combine inter-batch pipelining with intra-batch parallelism to overlap computation and communication.
- Version model parameters to ensure numerically correct gradient computations when multiple minibatches are in flight.
- Schedule forward and backward passes of different minibatches concurrently on different workers to minimize pipeline stalls.
- Automatically partition DNN layers among workers to balance work and minimize communication.

## System Design

PipeDream partitions the DNN into stages, each assigned to a worker (e.g., GPU). Workers process minibatches in a pipeline: a worker performs a forward pass on one minibatch, then sends activations to the next worker; later, it performs a backward pass using gradients from the subsequent worker. To handle bi-directional dependencies, PipeDream maintains multiple versions of model parameters (one per in-flight minibatch) so that the backward pass uses the same parameter version as the corresponding forward pass. The scheduler orchestrates forward and backward passes across workers to keep the pipeline full while avoiding deadlocks and version conflicts. The partitioner uses a profiling-based algorithm to split layers across workers to balance computation and minimize communication volume.

## Evaluation

Evaluated on a range of DNN tasks (e.g., image classification, language modeling) and models (e.g., AlexNet, VGG, ResNet, Transformer) with multiple hardware configurations (up to 16 GPUs). Baselines include data parallelism and model parallelism. PipeDream achieves up to 5.3× speedup over commonly used intra-batch parallelism techniques.

## Takeaways

- Pipelining across batches can significantly improve throughput beyond what intra-batch parallelism alone achieves.
- Versioning parameters is a simple yet effective solution to the state mismatch problem in bi-directional training pipelines.
- Automatic partitioning is crucial for balancing work and minimizing communication in heterogeneous models.
- The combination of pipelining and intra-batch parallelism is complementary and can be applied to many DNN architectures.

## Related Work

PipeDream extends prior work on pipeline parallelism (e.g., GPipe) by handling the bi-directional nature of DNN training and supporting automatic partitioning. It contrasts with pure data parallelism (e.g., TensorFlow's all-reduce) and model parallelism (e.g., mesh networks) by adding inter-batch pipelining.

## Open Questions

- How does PipeDream scale to very deep pipelines (many workers) and large models with memory constraints?
- Can the versioning overhead be reduced for models with very large parameter counts?
- How does PipeDream compare to newer pipeline parallelism approaches (e.g., 1F1B scheduling, interleaved schedules) that have emerged since?
- What are the implications for training with dynamic computation graphs or non-deterministic operations?
