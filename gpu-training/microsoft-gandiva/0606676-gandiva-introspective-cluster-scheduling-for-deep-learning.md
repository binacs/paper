---
paper_id: 0606676f16d581fa453f6b7b8a14fc7c4af8d025
title: 'Gandiva: Introspective Cluster Scheduling for Deep Learning'
authors:
- Wencong Xiao
- Romil Bhardwaj
- R. Ramjee
- Muthian Sivathanu
- Nipun Kwatra
- Zhenhua Han
- Pratyush Patel
- Xuan Peng
- Hanyu Zhao
- Quanlu Zhang
- Fan Yang
- Lidong Zhou
venue: USENIX Symposium on Operating Systems Design and Implementation
year: 2018
citations: 580
abs_url: https://www.semanticscholar.org/paper/0606676f16d581fa453f6b7b8a14fc7c4af8d025
pdf_url: ''
analyzed_at: '2026-06-08T10:50:20+00:00'
model: deepseek-chat
---

# Gandiva: Introspective Cluster Scheduling for Deep Learning

## TL;DR

Gandiva is a cluster scheduler for deep learning that uses introspective techniques to dynamically adjust GPU allocations and job placements, improving utilization and reducing job completion times.

## Problem & Motivation

Deep learning training jobs in shared clusters have varying resource needs over time due to phases like data loading, forward/backward passes, and synchronization. Static allocation leads to low GPU utilization and long queue times. Existing schedulers lack the ability to adapt to these dynamic requirements.

## Key Ideas

- Introspective scheduling: monitors job progress and resource usage in real-time to detect bottlenecks.
- Dynamic GPU allocation: adjusts the number of GPUs assigned to a job based on its current phase.
- Locality-aware placement: co-locates jobs to minimize data transfer and improve network utilization.
- Preemption and migration: can preempt or migrate jobs to consolidate resources and improve overall throughput.

## System Design

Gandiva consists of a central scheduler that collects per-job metrics (e.g., GPU utilization, data loading time) via a lightweight monitoring agent. The scheduler uses a decision engine to determine when to add or remove GPUs from a job, and a placement module to assign GPUs to nodes considering locality. Jobs are submitted with a priority and expected duration; the scheduler can preempt lower-priority jobs to free resources.

## Evaluation

Evaluated using traces from Microsoft's production DL clusters. Compared against YARN and a static allocation baseline. Gandiva reduces average job completion time by 25% and improves cluster utilization by 20%.

## Takeaways

- Introspection enables fine-grained resource allocation that matches the dynamic nature of DL training.
- Dynamic GPU allocation can significantly improve cluster efficiency without sacrificing fairness.
- Preemption and migration are effective for handling bursty workloads.

## Related Work

Extends prior work on cluster scheduling (e.g., YARN, Mesos) and DL-specific schedulers (e.g., SLA-aware schedulers). Differs by focusing on introspective monitoring and dynamic GPU allocation rather than static resource reservations.

## Open Questions

How to handle jobs with highly irregular or unpredictable resource patterns? Can the introspective approach scale to extremely large clusters? What are the implications for fairness when preempting jobs?
