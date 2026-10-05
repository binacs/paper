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
citations: 693
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3230543.3230544
analyzed_at: '2026-10-05T13:35:28+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive and generic data structure for network-wide measurements that adjusts to changing traffic characteristics, achieving much faster speed and lower error than prior sketches across six platforms and six tasks.

## Problem & Motivation

Network measurements become critical during congestion, scan attacks, or DDoS attacks, but in those situations traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. These shifts significantly degrade the performance of existing measurement solutions, which are not designed to adapt to such dynamic conditions.

## Key Ideas

- Make the sketch adaptive to current traffic characteristics so performance remains stable under drastic changes.
- Design the sketch to be generic across different measurement tasks and deployment platforms.
- Support both heavy-hitter and heavy-changer detection in a unified structure.
- Enable fast packet processing and low error simultaneously through adaptivity.

## System Design

The Elastic sketch is implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS. It processes six typical measurement tasks. The design is adaptive to traffic characteristics and generic to measurement tasks and platforms, though the abstract does not detail internal components or control flow.

## Evaluation

The paper validates the Elastic sketch through experimental results and theoretical analysis on six platforms and six measurement tasks. Compared to state-of-the-art methods, it achieves 44.6–45.2 times faster speed and 2.0–273.7 times smaller error rate.

## Takeaways

- Adaptivity to traffic characteristics is key to maintaining measurement accuracy and speed during network problems.
- A single sketch design can be generic across diverse platforms and tasks.
- Large gains in speed and accuracy are possible over prior art when the sketch adapts to current traffic.
- Theoretical analysis complements experimental results to support the claims.

## Related Work

The abstract compares the Elastic sketch to state-of-the-art measurement solutions, reporting speedups of 44.6–45.2x and error reductions of 2.0–273.7x, but does not name specific related systems.

## Open Questions

- How does the sketch adapt internally to traffic changes, and what are the adaptation mechanisms?
- What are the specific six measurement tasks and six platforms, and how does performance vary across them?
- What are the theoretical guarantees and their limitations?
- How does the sketch handle adversarial traffic or extreme conditions beyond those tested?
- What is the overhead of adaptation, and how quickly does it respond to sudden traffic shifts?
