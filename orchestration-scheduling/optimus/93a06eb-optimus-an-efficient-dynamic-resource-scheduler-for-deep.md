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
citations: 504
abs_url: https://www.semanticscholar.org/paper/93a06eb066fe58ed7d036e46e4cee53483e16bb8
pdf_url: http://dl.acm.org/ft_gateway.cfm?id=3190517&type=pdf
analyzed_at: '2026-06-29T10:54:02+00:00'
model: deepseek-chat
doi: 10.1145/3190508.3190517
---

# Optimus: an efficient dynamic resource scheduler for deep learning clusters

## TL;DR

Optimus is a dynamic resource scheduler for deep learning clusters that uses online resource-performance models to estimate job completion times and optimally allocate resources, reducing average job completion time by up to 46% compared to static schedulers.

## Problem & Motivation

Deep learning training jobs are resource-intensive and have variable resource requirements over time. Existing cluster schedulers typically allocate fixed resources to jobs, leading to inefficiency because they cannot adapt to changing demands. This results in longer job completion times and lower cluster utilization, especially in shared clusters where multiple jobs compete for resources.

## Key Ideas

- Online resource-performance model that predicts job completion time as a function of allocated resources (CPU, GPU, memory, network).
- Dynamic resource adjustment: scheduler periodically reallocates resources among running jobs based on model predictions to minimize average job completion time.
- Efficient optimization algorithm that solves the resource allocation problem in real-time, considering job priorities and fairness.

## System Design

Optimus consists of a central scheduler that monitors resource usage and job progress. It maintains a resource-performance model for each job, which is updated online using runtime metrics. The scheduler periodically runs an optimization algorithm to compute a new resource allocation that minimizes the average job completion time. Resources are then dynamically adjusted by preempting or adding containers. The system integrates with existing cluster managers like YARN and Kubernetes.

## Evaluation

Evaluated using trace-driven simulations and a prototype on a 16-node GPU cluster. Workloads include TensorFlow training jobs with varying resource demands. Baselines include static allocation (e.g., fair scheduling) and other dynamic schedulers. Headline result: reduces average job completion time by up to 46% compared to static allocation.

## Takeaways

- Dynamic resource scheduling based on online performance models can significantly improve cluster efficiency for deep learning workloads.
- The resource-performance model must be lightweight and adaptive to capture changing job behavior.
- Preemption and resource reallocation must be handled carefully to avoid overhead and ensure fairness.

## Related Work

Optimus is positioned as a dynamic scheduler for deep learning clusters, contrasting with static schedulers like YARN and Mesos. It extends prior work on performance modeling and resource scheduling for general big data analytics (e.g., Autopilot, Quasar) by focusing on the unique characteristics of deep learning jobs.

## Open Questions

- How to handle jobs with complex resource dependencies (e.g., multi-GPU training with communication patterns)?
- Scalability to very large clusters with thousands of jobs.
- Integration with newer deep learning frameworks and hardware accelerators beyond GPUs.
