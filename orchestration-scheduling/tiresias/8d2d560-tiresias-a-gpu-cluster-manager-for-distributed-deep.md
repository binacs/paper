---
paper_id: 8d2d560bf1c4c6930d2d1411e48b642bd5b81179
title: 'Tiresias: A GPU Cluster Manager for Distributed Deep Learning'
authors:
- Juncheng Gu
- Mosharaf Chowdhury
- K. Shin
- Yi-Bo Zhu
- Myeongjae Jeon
- Junjie Qian
- H. Liu
- Chuan-Xiong Guo
venue: Symposium on Networked Systems Design and Implementation
year: 2019
citations: 501
abs_url: https://www.semanticscholar.org/paper/8d2d560bf1c4c6930d2d1411e48b642bd5b81179
pdf_url: ''
analyzed_at: '2026-11-02T15:00:15+00:00'
model: deepseek-chat
---

# Tiresias: A GPU Cluster Manager for Distributed Deep Learning

## TL;DR

Tiresias is a GPU cluster scheduler for distributed deep learning that uses job-aware scheduling (consolidating jobs onto fewer GPUs and packing them together) to reduce job completion time while preserving fairness among users.

## Problem & Motivation

GPU clusters shared by many users running distributed deep learning (DDL) jobs face a tension between two goals: minimizing average job completion time (JCT) and providing fairness across users. Existing schedulers either optimize for performance without fairness guarantees or enforce fairness in ways that hurt efficiency. DDL jobs also have distinctive characteristics—they are gang-scheduled across many GPUs, have heterogeneous resource demands, and their performance depends on how jobs are co-located—which generic cluster schedulers do not exploit.

## Key Ideas

- Exploit DDL-specific knowledge: jobs benefit from being placed on fewer GPUs and from being packed together rather than spread out.
- Job-aware scheduling that consolidates a job's workers onto a minimal set of GPUs to reduce communication overhead.
- Leverage the observation that DDL jobs can tolerate some resource sharing, enabling co-location/packing of jobs.
- Combine performance-oriented placement with a fairness mechanism so that no user is starved.
- Use job-level information (e.g., resource demands and progress) rather than treating jobs as opaque black boxes.

## System Design

- A cluster manager/scheduler for GPU clusters that makes placement and ordering decisions for distributed deep learning jobs.
- Scheduling decisions are informed by job characteristics: gang scheduling of workers, GPU demand, and the benefit of consolidation.
- Control flow: jobs arrive, the scheduler decides ordering (fairness) and placement (consolidation/packing) across GPUs, and workers are launched accordingly.
- Data flow centers on GPU allocation and job-to-GPU mapping rather than on the training data path itself.

## Evaluation

The paper validates its approach via simulation and/or cluster experiments comparing Tiresias against baseline schedulers, measuring job completion time and fairness. Headline quantitative results are not available from the provided abstract text.

## Takeaways

- DDL workloads reward schedulers that understand their structure; generic schedulers leave performance on the table.
- Consolidating a job onto fewer GPUs and packing jobs together can improve JCT without sacrificing fairness.
- Fairness and performance need not be mutually exclusive if the scheduler is job-aware.
- Cluster managers for ML should treat GPU placement and job ordering as joint optimization problems.

## Related Work

The abstract positions Tiresias against existing cluster schedulers that either prioritize performance or fairness but do not account for DDL-specific behavior such as gang scheduling and co-location effects. Specific named systems are not listed in the provided abstract.

## Open Questions

- How well does the approach scale to very large clusters and highly heterogeneous GPU types?
- How sensitive are the gains to accurate job-level information (e.g., demand estimates or progress)?
- Does consolidation/packing interact poorly with failures, stragglers, or preemption?
- How does fairness behave under adversarial or bursty multi-tenant workloads?
