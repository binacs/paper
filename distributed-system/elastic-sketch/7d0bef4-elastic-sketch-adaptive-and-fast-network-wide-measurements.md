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
citations: 708
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: http://qmro.qmul.ac.uk/xmlui/handle/123456789/43547
analyzed_at: '2026-11-23T17:23:50+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive, generic data structure for network-wide measurements that adjusts to current traffic characteristics and runs on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS). It reports 44.6–45.2× faster speed and 2.0–273.7× lower error than state-of-the-art sketches.

## Problem & Motivation

Network measurements become most critical exactly when the network is under stress (congestion, scan attacks, DDoS), but in those moments traffic characteristics such as available bandwidth, packet rate, and flow-size distribution change drastically. Conventional sketches are tuned for one regime and degrade sharply when traffic shifts, so their accuracy and speed collapse precisely when operators need them most.

The paper targets a measurement primitive that remains accurate and fast across changing traffic conditions, and that is generic enough to serve many measurement tasks on many hardware/software platforms rather than being specialized to one task or one deployment.

## Key Ideas

- Make the sketch adaptive to current traffic characteristics instead of using a fixed configuration.
- Keep the design generic so it supports multiple measurement tasks (six typical tasks evaluated) and multiple platforms.
- Separate/partition the sketch structure so that heavy and light traffic can be handled differently (elastic behavior under varying flow-size distributions and packet rates).
- Provide theoretical analysis alongside experiments to justify adaptivity and accuracy.
- Emphasize deployability: the same sketch is implemented on P4, FPGA, GPU, CPU, multi-core CPU, and OVS.

## System Design

- The Elastic sketch is a sketch data structure whose internal organization adapts to observed traffic characteristics; the abstract does not specify the exact sub-structures, so details beyond adaptivity should be read from the paper.
- Implementations span six platforms: programmable switches (P4), FPGA, GPU, single-core CPU, multi-core CPU, and OVS, indicating a portable core algorithm with platform-specific realizations.
- It is applied to six typical measurement tasks, implying a common sketch substrate feeding task-specific estimators rather than a separate structure per task.
- Control/data flow: packets update the sketch; the sketch's configuration responds to traffic characteristics; measurement queries are answered from the adapted structure.

## Evaluation

- Validated via both experimental results and theoretical analysis.
- Workloads: six typical network measurement tasks, with traffic conditions including congestion, scan attacks, and DDoS-like stress where characteristics vary drastically.
- Platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS.
- Baselines: compared against state-of-the-art sketches.
- Headline numbers from the abstract: 44.6–45.2× faster speed and 2.0–273.7× smaller error rate.

## Takeaways

- Measurement structures should be designed for the stressed regime, not just steady-state traffic.
- Adaptivity to traffic characteristics can yield order-of-magnitude gains in both speed and accuracy versus fixed sketches.
- Generality across tasks and platforms is a first-class design goal; a single sketch can serve many measurement jobs.
- Wide platform coverage (P4 through OVS) suggests the approach is practical for both hardware and software datapaths.
- Pairing theory with multi-platform experiments is a strong template for sketch papers.

## Related Work

The abstract positions Elastic sketch against unnamed state-of-the-art sketches, claiming 44.6–45.2× speed and 2.0–273.7× error improvements; specific prior systems are not named in the abstract.

## Open Questions

- How does adaptivity behave under rapidly oscillating traffic, and what is the cost of reconfiguration?
- What are the memory/accuracy trade-offs on constrained platforms such as P4 switches versus GPU/CPU?
- How are the six measurement tasks mapped onto one sketch, and does adaptivity help all of them equally?
- Robustness against adversarial traffic that tries to defeat the adaptive policy is not addressed in the abstract.
- Whether the gains hold at line rate in production networks beyond the reported benchmarks.
