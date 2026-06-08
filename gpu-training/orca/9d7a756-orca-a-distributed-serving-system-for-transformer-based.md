---
paper_id: 9d7a75601e0e50dd68d40cfb8ef0e891dad797a6
title: 'Orca: A Distributed Serving System for Transformer-Based Generative Models'
authors:
- Gyeong-In Yu
- Joo Seong Jeong
venue: USENIX Symposium on Operating Systems Design and Implementation
year: 2022
citations: 690
abs_url: https://www.semanticscholar.org/paper/9d7a75601e0e50dd68d40cfb8ef0e891dad797a6
pdf_url: ''
analyzed_at: '2026-06-01T11:29:40+00:00'
model: deepseek-chat
---

# Orca: A Distributed Serving System for Transformer-Based Generative Models

## TL;DR

Orca is a distributed serving system for transformer-based generative models that introduces iteration-level scheduling to achieve high throughput and low latency, outperforming prior systems by 2-10x.

## Problem & Motivation

Serving large transformer-based generative models (e.g., GPT-3) in production requires meeting strict latency Service-Level Objectives (SLOs) while maximizing throughput. Existing systems use request-level scheduling, which leads to underutilization of GPU resources because they cannot exploit the batching opportunities across different requests at different generation steps. The key challenge is to efficiently schedule the execution of multiple requests with varying lengths and generation phases.

## Key Ideas

- Iteration-level scheduling: Instead of scheduling entire requests, Orca schedules individual iterations (forward passes) of requests, enabling fine-grained batching.
- Selective batching: Dynamically batches requests that are at the same iteration step, maximizing GPU utilization without violating latency SLOs.
- Distributed execution with a centralized scheduler: A single scheduler assigns iterations to workers, which execute them in parallel.
- Support for both autoregressive and non-autoregressive models.

## System Design

Orca consists of a centralized scheduler and multiple GPU workers. The scheduler maintains a queue of pending requests and their current iteration counts. At each scheduling step, it selects a batch of requests that are at the same iteration and assigns them to workers. Workers execute the forward pass for the batch and return the output tokens. The scheduler then updates the iteration counts and repeats. This design allows overlapping computation across requests and workers.

## Evaluation

Evaluated on GPT-2 and GPT-3 models with up to 175B parameters. Baselines include TensorFlow Serving and FasterTransformer. Headline results: Orca achieves 2-10x higher throughput than baselines while meeting latency SLOs (e.g., 95th percentile latency under 1 second).

## Takeaways

- Iteration-level scheduling is a key technique for serving generative models, enabling efficient batching.
- Selective batching can significantly improve GPU utilization without sacrificing latency.
- Centralized scheduling simplifies coordination and can scale to many workers.
- The approach is model-agnostic and works for both autoregressive and non-autoregressive models.

## Related Work

Orca improves upon prior serving systems like TensorFlow Serving and FasterTransformer by introducing iteration-level scheduling. It is related to systems like NVIDIA Triton Inference Server and Microsoft's DeepSpeed Inference, but focuses on fine-grained scheduling for generative models.

## Open Questions

- How does Orca handle models with very long generation sequences (e.g., 2048+ tokens) where iteration-level scheduling may introduce overhead?
- Can the scheduler become a bottleneck for very large clusters?
- How does Orca compare to newer systems like vLLM or Sarathi-Serve that use similar ideas?
- Extension to multi-model serving or heterogeneous hardware.
