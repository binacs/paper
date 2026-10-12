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
citations: 694
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3230543.3230544
analyzed_at: '2026-10-12T14:26:50+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive and generic data structure for network-wide measurements that dynamically adjusts to changing traffic characteristics, achieving significantly faster speed and lower error rates than state-of-the-art sketches.

## Problem & Motivation

Network measurements become critical during problems like congestion, scan attacks, or DDoS attacks, but in such scenarios traffic characteristics (available bandwidth, packet rate, flow size distribution) vary drastically, degrading the performance of existing measurement solutions. Traditional sketches are not adaptive to these changes and often fail to provide accurate and fast measurements under extreme conditions.

## Key Ideas

- Adaptivity: The sketch dynamically adjusts its internal structure and parameters based on current traffic characteristics to maintain high accuracy and speed.
- Generality: It is designed to be generic across different measurement tasks and deployment platforms.
- Elasticity: The sketch can expand or contract its resources (e.g., memory, counters) in response to traffic variations, ensuring optimal performance.
- Unified framework: Supports multiple measurement tasks (e.g., heavy hitter detection, flow size distribution) without task-specific tuning.

## System Design

The Elastic sketch is implemented on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS. It processes six typical measurement tasks. The design likely includes components for dynamic memory allocation, counter management, and adaptation logic that monitors traffic and reconfigures the sketch. Data flows through the sketch, which updates counters and adjusts its structure in real-time based on observed traffic patterns.

## Evaluation

The paper validates the Elastic sketch through experimental results and theoretical analysis. It compares against state-of-the-art solutions and reports that the Elastic sketch achieves 44.6 to 45.2 times faster speed and 2.0 to 273.7 times smaller error rate. Evaluations cover six measurement tasks across six platforms, demonstrating adaptivity and generality.

## Takeaways

- Adaptivity to traffic characteristics is crucial for maintaining measurement performance during network anomalies.
- A single generic sketch can be deployed across diverse platforms and tasks, simplifying network measurement infrastructure.
- Significant speed and accuracy improvements over existing sketches are achievable through elastic resource management.
- Theoretical analysis and extensive experiments validate the approach.

## Related Work

The abstract compares the Elastic sketch to state-of-the-art solutions, indicating that existing sketches are not adaptive and suffer from degraded performance under varying traffic. The Elastic sketch outperforms these by being adaptive and generic.

## Open Questions

- How does the Elastic sketch handle extremely high-speed networks beyond the tested platforms?
- What are the memory overheads and trade-offs in dynamic adaptation?
- Can the adaptation logic be extended to other network measurement tasks not covered in the paper?
- How does it perform under adversarial traffic patterns designed to defeat adaptivity?
