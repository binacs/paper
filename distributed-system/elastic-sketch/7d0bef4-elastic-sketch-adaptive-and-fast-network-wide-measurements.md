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
citations: 699
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: http://qmro.qmul.ac.uk/xmlui/handle/123456789/43547
analyzed_at: '2026-11-02T14:59:50+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive, generic network measurement data structure that adjusts its internal structure to current traffic characteristics, enabling fast and accurate measurement across many tasks and platforms.

## Problem & Motivation

Network measurements become most critical precisely when the network is under stress (congestion, scan attacks, DDoS), but in those situations traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. Conventional sketches are tuned for assumed traffic patterns, so their performance degrades significantly when the actual traffic diverges from those assumptions.

The paper targets a measurement primitive that remains accurate and fast across heterogeneous traffic conditions, and that is generic enough to serve many measurement tasks and run on many hardware/software platforms.

## Key Ideas

- Make the sketch adaptive to current traffic characteristics rather than fixed at design time.
- Design the sketch to be generic across measurement tasks and deployment platforms.
- Support six typical measurement tasks with one structure.
- Provide both theoretical analysis and empirical validation of adaptivity.

## System Design

The abstract does not detail internal components or control/data flow. At a high level, the Elastic sketch is a single measurement structure that adapts its behavior to observed traffic characteristics and is implemented across six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS. It is used to process six typical measurement tasks.

## Evaluation

Evaluated by implementing the Elastic sketch on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS) and running six typical measurement tasks. Compared to state-of-the-art approaches, it reports 44.6–45.2x faster speed and 2.0–273.7x smaller error rate, supported by experimental results and theoretical analysis of adaptivity.

## Takeaways

- Adaptivity to traffic characteristics is a first-class design goal for measurement structures under stress.
- Generality across tasks and platforms is achievable with a single sketch design.
- Large reported gains in both speed and accuracy suggest fixed-structure sketches leave significant performance on the table.
- Cross-platform implementations (P4, FPGA, GPU, CPU, multi-core, OVS) matter for practical deployment.

## Related Work

The abstract compares against unnamed state-of-the-art measurement approaches, reporting speedups of 44.6–45.2x and error reductions of 2.0–273.7x. No specific related systems are named.

## Open Questions

- How does the sketch decide when and how to adapt, and what is the overhead of adaptation?
- How robust is it under adversarial traffic designed to defeat the adaptation mechanism?
- What are the memory/accuracy trade-offs across the six platforms?
- How well does it generalize to measurement tasks beyond the six evaluated?
