---
paper_id: 382b54869bb92039a7f7c56de67d70fb2421f604
title: 'HPCC: high precision congestion control'
authors:
- Yuliang Li
- Rui Miao
- H. Liu
- Yan Zhuang
- Fei Feng
- Lingbo Tang
- Zheng Cao
- Ming Zhang
- F. Kelly
- Mohammad Alizadeh
- Minlan Yu
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2019
citations: 757
abs_url: https://www.semanticscholar.org/paper/382b54869bb92039a7f7c56de67d70fb2421f604
pdf_url: ''
analyzed_at: '2026-05-25T10:02:06+00:00'
model: deepseek-chat
doi: 10.1145/3341302.3342085
---

# HPCC: high precision congestion control

## TL;DR

HPCC leverages in-network telemetry (INT) to obtain precise link load information, enabling high-speed congestion control that simultaneously achieves ultra-low latency, high bandwidth utilization, and network stability.

## Problem & Motivation

Existing high-speed congestion control schemes (e.g., DCQCN, TIMELY) have inherent limitations in achieving ultra-low latency, high bandwidth, and network stability simultaneously in large-scale RDMA networks. They suffer from delayed or imprecise congestion signals, leading to either underutilization or excessive queuing.

## Key Ideas

- Use in-network telemetry (INT) to get precise, per-packet link load information.
- Design a precise traffic control algorithm that quickly converges to utilize free bandwidth while avoiding congestion.
- Address challenges: delayed INT information during congestion and overreaction to INT information.
- Maintain near-zero in-network queues for ultra-low latency.
- Ensure fairness and ease of deployment in hardware.

## System Design

HPCC is implemented with commodity programmable NICs and switches. The control loop: senders embed INT requests in packets; switches insert current link load into packets; receivers echo INT information back to senders; senders adjust sending rates based on precise load feedback.

## Evaluation

Evaluated in a testbed with commodity programmable NICs and switches. Compared to DCQCN and TIMELY, HPCC shortens flow completion times by up to 95% and causes little congestion even under large-scale incasts.

## Takeaways

- Precise link load information from INT enables near-optimal congestion control.
- Addressing delayed and overreactive feedback is critical for fast convergence.
- HPCC achieves ultra-low latency by maintaining near-zero queues.
- Hardware deployability is feasible with commodity programmable devices.

## Related Work

HPCC is positioned against existing high-speed CC schemes like DCQCN and TIMELY, which rely on ECN or delay-based signals and suffer from imprecision. HPCC improves upon them by using INT for direct load measurement.

## Open Questions

Scalability of INT in very large networks; potential overhead of INT processing; applicability to non-RDMA transports; interaction with multi-path or load-balanced networks.
