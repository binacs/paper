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
analyzed_at: '2026-05-11T03:53:28+00:00'
model: deepseek-chat
doi: 10.1145/3341301.3359646
---

# PipeDream: generalized pipeline parallelism for DNN training

## TL;DR

PipeDream introduces inter-batch pipelining to DNN training, combining it with intra-batch parallelism to improve throughput. It handles bi-directional computation by versioning model parameters and scheduling forward/backward passes to avoid state mismatches and pipeline stalls.

## Problem & Motivation

DNN training is time-consuming and requires efficient multi-accelerator parallelization. Existing intra-batch parallelism (e.g., data parallelism) splits a single iteration over workers but suffers from diminishing returns at higher worker counts due to communication overhead and underutilization. There is a need for better overlap of computation and communication to scale training.

## Key Ideas

- Inter-batch pipelining: overlap forward and backward passes of different minibatches across workers.
- Versioned model parameters: maintain multiple versions to ensure correct gradient computations despite concurrent passes.
- Scheduler: coordinate forward and backward passes to minimize pipeline stalls.
- Automatic partitioning: balance work and minimize communication by partitioning DNN layers among workers.

## System Design

PipeDream partitions a DNN into stages, each assigned to a worker. Workers execute forward and backward passes on different minibatches in a pipelined fashion. Parameter versions are stored to match the state used in forward and backward passes. A scheduler orchestrates the order of passes to avoid stalls. Communication between stages is overlapped with computation.

## Evaluation

Experiments with various DNN tasks, models, and hardware configurations show PipeDream trains models up to 5.3× faster than commonly used intra-batch parallelism techniques. Baselines include data parallelism and other parallelization methods.

## Takeaways

- Pipelining across minibatches can significantly improve throughput beyond intra-batch parallelism.
- Versioning model parameters is a practical solution to the bi-directional dependency in DNN training.
- Automatic partitioning is crucial for load balancing and minimizing communication.
- The approach is general and works across different DNN architectures.

## Related Work

PipeDream extends intra-batch parallelism (e.g., data parallelism) with inter-batch pipelining. It addresses limitations of naive pipelining in bi-directional DNN training, distinguishing it from traditional pipeline parallelism used in other domains.

## Open Questions

- Scalability to very large numbers of workers and extremely deep models.
- Impact of pipeline bubbles on efficiency for different model architectures.
- Integration with other parallelism strategies (e.g., model parallelism, tensor parallelism).
- Handling dynamic computation graphs or non-deterministic operations.
