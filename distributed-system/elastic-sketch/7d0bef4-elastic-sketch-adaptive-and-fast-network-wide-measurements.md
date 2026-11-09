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
citations: 704
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: http://qmro.qmul.ac.uk/xmlui/handle/123456789/43547
analyzed_at: '2026-11-09T15:12:38+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive, generic data structure for network-wide measurements that adjusts its internal structure to current traffic characteristics, achieving large speed and accuracy gains over prior sketches across six platforms and six measurement tasks.

## Problem & Motivation

Network measurements become most critical precisely when the network is under stress (congestion, scan attacks, DDoS), but in those situations traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. Static sketch designs tuned for one regime degrade badly when the traffic mix shifts, so existing measurement approaches lose accuracy and speed exactly when operators need them most.

The paper targets a measurement primitive that remains accurate and fast across heterogeneous traffic conditions, and that is generic enough to serve many measurement tasks and run on many hardware/software platforms.

## Key Ideas

- Make the sketch structure adaptive to the current traffic characteristics rather than fixed at design time.
- Keep the design generic so the same sketch supports multiple measurement tasks (e.g., heavy-hitter and flow-size-distribution style queries).
- Port the sketch across very different platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS) to show platform genericity.
- Combine theoretical analysis with experiments to argue adaptivity and accuracy.

## System Design

The abstract does not disclose internal components or control/data flow in detail. At a high level, the Elastic sketch is a sketch data structure that adapts its organization to observed traffic characteristics, is deployed as a measurement primitive on six platforms (P4, FPGA, GPU, CPU, multi-core CPU, OVS), and is queried for six typical measurement tasks. Specific bucket layouts, adaptation triggers, and update/query procedures are not described in the abstract.

## Evaluation

- Implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS.
- Evaluated on six typical measurement tasks.
- Compared against state-of-the-art sketches.
- Headline results: 44.6–45.2x faster speed and 2.0–273.7x smaller error rate.
- Supported by both experimental results and theoretical analysis of adaptivity.

## Takeaways

- Adaptivity to traffic regime is a first-class design goal for sketches; static tuning is a liability under attack or congestion.
- Genericity across tasks and platforms is achievable with a single sketch design, reducing per-deployment engineering.
- Reported gains are large in both speed (tens of x) and accuracy (up to hundreds of x lower error), suggesting the adaptive approach pays off broadly.

## Related Work

The abstract only positions the Elastic sketch against unnamed 'state-of-the-art' sketch methods, claiming 44.6–45.2x speed and 2.0–273.7x lower error. No specific prior systems are named.

## Open Questions

- What exactly is the adaptive mechanism, and what signals trigger restructuring?
- How does adaptation overhead behave under extremely rapid traffic shifts?
- Are the reported gains uniform across all six tasks and six platforms, or concentrated in some?
- How does the sketch handle adversarial traffic designed to defeat its adaptation heuristic?
- What are memory-cost tradeoffs versus the baselines at equal accuracy?
