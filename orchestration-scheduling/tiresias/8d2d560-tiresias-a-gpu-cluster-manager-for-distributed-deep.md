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
pdf_url: ''
analyzed_at: '2026-11-02T15:00:15+00:00'
model: deepseek-chat
abs_url: https://www.usenix.org/conference/nsdi19/presentation/gu
edited: '2026-11-24 hand-corrected'
---

# Tiresias: A GPU Cluster Manager for Distributed Deep Learning

> Hand-corrected 2026-11-24 against the USENIX NSDI '19 paper. The bot's original analysis described consolidation/packing as the core idea; the core is actually 2D attained-service scheduling.

## TL;DR

Tiresias schedules distributed DL jobs without knowing their durations: priority is based on **two-dimensional attained service** (GPUs × time run so far), discretised into a small multi-level feedback queue, with a Gittins-index variant when a duration distribution is known. Placement consolidation is applied only to jobs whose model structure makes them placement-sensitive.

## Problem & Motivation

DL training jobs in shared GPU clusters are gang-scheduled and their durations are hard to predict, so SRTF-style schedulers that need exact job lengths do not apply. Production schedulers also force strict consolidation, which lengthens queueing even though "some DDL jobs are insensitive to placement" (§2.3).

## Key Ideas

- **2D attained service (2D-LAS):** a job's attained service is `a_J = W_J × t_J` (GPUs used × time running); without prior information, priority is inverse to attained service (§3.2.2).
- **2D Gittins index:** when a job-duration *distribution* (not exact durations) is available from history, priority equals the job's Gittins index (§3.2.2, §2.3).
- **Discretised priorities:** K logical queues in an MLFQ; in practice the paper uses only two queues and one threshold, plus promotion of starving jobs back to the top queue (§3.2.3). Discretisation limits preemption churn.
- **Model-profile-based placement:** a profiler measures the skew of tensor sizes across parameter servers; skew predicts whether consolidation matters, so only skewed models are consolidated (§3.3).

## System Design

- Central scheduler with a profiler; jobs are preempted and resumed via checkpoints when queue order changes.
- Prototype evaluated on the Michigan ConFlux cluster (60 P100 GPUs) plus trace-driven simulation of a Microsoft production trace.

## Evaluation

Abstract: average JCT improves by up to 5.5× over an Apache YARN-based production resource manager, and performance is comparable to schedulers assuming perfect knowledge.

## Takeaways

- Attained-service priority (LAS / MLFQ) is a robust default when job lengths are unknown; adding the GPU dimension matters for gang-scheduled jobs.
- Placement constraints should be per-job and evidence-based, not cluster-wide.
- Related: Gandiva (OSDI 2018), Philly trace analysis (ATC 2019), Pollux (OSDI 2021), Sia (SOSP 2023).

## Links

- Paper: https://www.usenix.org/conference/nsdi19/presentation/gu
- Code: https://github.com/SymbioticLab/Tiresias
