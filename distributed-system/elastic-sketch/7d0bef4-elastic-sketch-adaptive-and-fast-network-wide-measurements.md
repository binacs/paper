---
paper_id: 7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
title: 'Elastic sketch: adaptive and fast network-wide measurements'
authors:
- Tong Yang
- Jie Jiang
- Peng Liu
- Qun Huang
- Junzhi Gong
- Yang Zhou
- Rui Miao
- Xiaoming Li
- S. Uhlig
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 690
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3230543.3230544
analyzed_at: '2026-09-21T11:58:38+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive and generic data structure for network-wide measurements that adjusts to changing traffic characteristics, achieving significantly faster speed and lower error rates than state-of-the-art solutions.

## Problem & Motivation

Network measurements become critical during problems like congestion, scan attacks, and DDoS attacks, but in these situations traffic characteristics (available bandwidth, packet rate, flow size distribution) vary drastically, degrading the performance of existing measurement solutions. There is a need for a measurement approach that remains accurate and efficient under such dynamic conditions.

## Key Ideas

['- Adaptivity: The sketch dynamically adjusts its internal structure to match current traffic characteristics.', '- Genericity: It supports multiple measurement tasks and can be deployed on various hardware and software platforms.', '- Efficiency: It achieves high speed and low error compared to prior art.']

## System Design

The abstract does not provide specific details on the internal components or control flow of the Elastic sketch. It is implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS, and is designed to process six typical measurement tasks.

## Evaluation

The paper evaluates the Elastic sketch on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS) across six typical measurement tasks. Compared to state-of-the-art solutions, it achieves 44.6–45.2 times faster speed and 2.0–273.7 times smaller error rate. Both experimental results and theoretical analysis demonstrate its adaptivity to traffic characteristics.

## Takeaways

['- Adaptivity to traffic characteristics is crucial for maintaining measurement accuracy during network anomalies.', '- A single sketch design can be generic across diverse measurement tasks and hardware/software platforms.', '- Significant performance gains (orders of magnitude in speed and error reduction) are possible over existing methods.']

## Related Work

The abstract mentions comparison to state-of-the-art solutions but does not name specific related systems.

## Open Questions

The abstract does not discuss limitations or future work. Potential open questions include the overhead of adaptation, the range of traffic characteristics supported, and how the sketch performs under extreme conditions not covered in the evaluation.
