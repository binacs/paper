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
- Xiao-Ming Li
- S. Uhlig
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 707
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: http://qmro.qmul.ac.uk/xmlui/handle/123456789/43547
analyzed_at: '2026-11-16T14:47:40+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is a generic, traffic-adaptive sketch for network-wide measurement that dynamically reallocates memory between heavy and light flow structures based on observed traffic, achieving large speed and accuracy gains over prior sketches across six platforms and six measurement tasks.

## Problem & Motivation

Network measurement becomes most critical precisely when the network is under stress (congestion, scan attacks, DDoS), but in those moments traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. Static sketches are tuned for assumed traffic patterns, so their accuracy and throughput degrade sharply when the real distribution shifts.

The paper targets a measurement primitive that stays accurate and fast across heterogeneous traffic conditions, and that is generic enough to serve many measurement tasks and run on many hardware/software platforms rather than being specialized to one.

## Key Ideas

- Make the sketch adaptive to current traffic characteristics rather than fixed at design time.
- Separate handling of heavy flows (large, persistent) from light flows (small, numerous) so each gets appropriate memory and update treatment.
- Dynamically adjust the internal structure/memory allocation as traffic characteristics change.
- Keep the design generic so it supports multiple measurement tasks and multiple platforms.
- Provide theoretical analysis alongside experiments to justify adaptivity.

## System Design

- The Elastic sketch is organized around distinct structures for heavy and light flows, with the balance between them adjusted according to observed traffic.
- Updates are applied per packet, with the sketch adapting its configuration as traffic characteristics evolve.
- It is implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS, indicating a portable core design rather than a single-target implementation.
- The same sketch supports six typical measurement tasks, so task-specific logic sits on top of a shared adaptive data structure.

## Evaluation

- Implemented on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS) and evaluated on six typical measurement tasks.
- Compared against state-of-the-art sketches.
- Headline results from the abstract: 44.6–45.2x faster speed and 2.0–273.7x smaller error rate.
- Validation combines experimental results with theoretical analysis of adaptivity to traffic characteristics.

## Takeaways

- Traffic adaptivity matters most exactly when measurement matters most: during congestion and attacks.
- Splitting heavy and light flow handling and rebalancing resources is a strong lever for sketch accuracy.
- Generality across tasks and platforms is a first-class design goal, not an afterthought.
- Reported gains are large in both speed and error, suggesting static sketches leave substantial headroom.

## Related Work

The abstract positions Elastic sketch against unnamed state-of-the-art sketches, claiming 44.6–45.2x faster speed and 2.0–273.7x smaller error rate; specific prior systems are not named in the abstract.

## Open Questions

- How quickly and stably does the adaptation converge under rapidly shifting traffic, and what overhead does reconfiguration add?
- How are the heavy/light structures sized and tuned, and how sensitive are results to those parameters?
- Do the reported speedups hold uniformly across all six platforms and tasks, or are some combinations weaker?
- How does it behave under adversarial traffic designed to defeat the adaptation heuristic?
