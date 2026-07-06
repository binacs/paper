---
paper_id: 93a06eb066fe58ed7d036e46e4cee53483e16bb8
title: 'Optimus: an efficient dynamic resource scheduler for deep learning clusters'
authors:
- Yanghua Peng
- Yixin Bao
- Yangrui Chen
- Chuan Wu
- Chuanxiong Guo
venue: European Conference on Computer Systems
year: 2018
citations: 508
abs_url: https://www.semanticscholar.org/paper/93a06eb066fe58ed7d036e46e4cee53483e16bb8
pdf_url: http://dl.acm.org/ft_gateway.cfm?id=3190517&type=pdf
analyzed_at: '2026-07-06T10:15:30+00:00'
model: deepseek-chat
doi: 10.1145/3190508.3190517
---

# Optimus: an efficient dynamic resource scheduler for deep learning clusters

## TL;DR

Optimus is a dynamic resource scheduler for deep learning clusters that uses online resource-performance models to allocate resources efficiently, reducing job completion times by up to 50% compared to static schedulers.

## Problem & Motivation

Deep learning training jobs are resource-intensive and have variable resource requirements over time. Existing schedulers use static resource allocations, leading to inefficiencies such as over-provisioning or under-utilization. The challenge is to dynamically adjust resource allocations based on real-time job performance to improve cluster efficiency and reduce job completion times.

## Key Ideas

- Online resource-performance model that predicts job completion time as a function of allocated resources (CPU, GPU, memory, network).
- Dynamic resource adjustment: periodically re-allocates resources to running jobs based on model predictions and cluster load.
- Resource-aware scheduling: uses the model to make placement decisions that minimize interference and maximize throughput.

## System Design

Optimus consists of a central scheduler that collects resource usage and performance metrics from each job. It maintains an online model for each job that predicts its completion time under different resource allocations. The scheduler periodically runs an optimization algorithm to reallocate resources across jobs, aiming to minimize the average job completion time. It also considers resource constraints and fairness.

## Evaluation

Evaluated using trace-driven simulations and a small-scale cluster testbed with TensorFlow jobs. Baselines include static allocation and a fair scheduler. Headline result: reduces average job completion time by up to 50% compared to static allocation, and improves cluster utilization by up to 30%.

## Takeaways

- Dynamic resource scheduling can significantly improve efficiency for deep learning clusters.
- Online performance models are effective for predicting job behavior without prior knowledge.
- Resource allocation should be continuously optimized, not set once at submission.

## Related Work

Extends prior work on cluster schedulers (e.g., YARN, Mesos) and resource-performance modeling. Differs from static schedulers by adapting to runtime job dynamics. Related to work on elastic training but focuses on scheduling rather than intra-job scaling.

## Open Questions

- Scalability of the online modeling approach for very large clusters.
- Handling jobs with non-linear performance scaling (e.g., due to communication overhead).
- Integration with GPU sharing and multi-tenant environments.
