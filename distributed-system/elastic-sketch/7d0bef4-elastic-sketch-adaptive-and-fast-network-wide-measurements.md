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
citations: 696
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3230543.3230544
analyzed_at: '2026-10-26T12:23:11+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is a generic, adaptive data structure for network-wide measurements that adjusts its internal structure to current traffic characteristics, achieving much higher speed and lower error than prior sketches across six platforms and six measurement tasks.

## Problem & Motivation

Network measurements become most critical precisely when the network is under stress (congestion, scan attacks, DDoS), yet in those moments traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. Static sketch designs tuned for one regime degrade sharply when the traffic mix shifts, so existing measurement approaches lose accuracy and throughput exactly when operators need them most.

The paper targets a measurement primitive that remains accurate and fast across heterogeneous traffic conditions, measurement tasks, and deployment platforms, rather than being specialized to a single scenario.

## Key Ideas

- Make the sketch structure adaptive to the current traffic characteristics instead of fixed at design time.
- Keep the design generic so the same sketch serves many measurement tasks rather than one.
- Support deployment across very different platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS).
- Combine theoretical analysis with cross-platform experiments to argue adaptivity and generality.

## System Design

The abstract does not detail internal components or control/data flow. At a high level, the Elastic sketch is a sketch-based measurement data structure whose organization adapts to observed traffic characteristics, and it is implemented on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS) to process six typical measurement tasks. Specific component structure, update/query paths, and adaptation mechanisms are not described in the abstract.

## Evaluation

- Implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS.
- Evaluated on six typical measurement tasks.
- Compared against state-of-the-art sketches.
- Headline results: 44.6–45.2x faster speed and 2.0–273.7x smaller error rate.
- Supported by both experimental results and theoretical analysis of adaptivity to traffic characteristics.

## Takeaways

- Adaptivity to traffic regime is a first-class design goal for sketches, since stress conditions are when measurement matters most.
- Generality across tasks and platforms is a claimed differentiator versus task- or platform-specific sketches.
- Large reported gains in both speed and accuracy suggest the adaptation pays off across regimes rather than trading one for the other.
- Cross-platform implementations (programmable hardware through software switches) indicate the design is portable.

## Related Work

The abstract positions the Elastic sketch against unnamed "state-of-the-art" sketch approaches, claiming 44.6–45.2x faster speed and 2.0–273.7x smaller error rate. No specific prior systems are named in the abstract.

## Open Questions

- The abstract does not describe the adaptation mechanism, so how the sketch detects regime changes and reconfigures is unclear.
- Per-task accuracy and per-platform overhead breakdowns are not given in the abstract.
- Behavior under adversarial or highly non-stationary traffic beyond the tested workloads is not characterized in the abstract.
- Memory footprint and update-cost tradeoffs of adaptation are not stated.
