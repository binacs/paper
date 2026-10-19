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
citations: 694
abs_url: https://www.semanticscholar.org/paper/7d0bef4cc924dd3698013f22eeaa0a15f2bc6044
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3230543.3230544
analyzed_at: '2026-10-19T12:09:02+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230544
---

# Elastic sketch: adaptive and fast network-wide measurements

## TL;DR

The Elastic sketch is an adaptive, generic network measurement data structure that adjusts its internal structure to current traffic characteristics, achieving much faster speed and lower error than prior sketches across six platforms and six measurement tasks.

## Problem & Motivation

Network measurements become most critical precisely when the network is under stress (congestion, scan attacks, DDoS), but in those conditions traffic characteristics such as available bandwidth, packet rate, and flow size distribution change drastically. Existing measurement approaches degrade significantly under such shifting traffic, so they fail exactly when accurate measurement matters most.

The paper targets a sketch that remains accurate and fast across heterogeneous traffic conditions, and that is generic enough to serve many measurement tasks and run on many hardware/software platforms.

## Key Ideas

- Make the sketch adaptive to current traffic characteristics rather than using a fixed structure.
- Design the sketch to be generic across measurement tasks and deployment platforms.
- Support six typical measurement tasks with one data structure.
- Implement on six platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS.
- Combine experimental results with theoretical analysis to justify adaptivity.

## System Design

- The Elastic sketch is a sketch-based measurement data structure whose internal organization adapts to observed traffic characteristics.
- It is positioned as a generic measurement primitive reused across six typical measurement tasks rather than a task-specific algorithm.
- Portability is demonstrated by implementations on six platforms spanning programmable switches (P4), hardware (FPGA), accelerators (GPU), general CPUs, multi-core CPUs, and software switching (OVS).
- The abstract does not disclose the specific internal data structures or control flow, so component-level details are not available here.

## Evaluation

- Workloads: six typical network measurement tasks, evaluated under traffic conditions that vary drastically (congestion, scan/DDoS-like stress).
- Platforms: P4, FPGA, GPU, CPU, multi-core CPU, and OVS.
- Baselines: compared against state-of-the-art sketch methods.
- Headline results from the abstract: 44.6–45.2x faster speed and 2.0–273.7x smaller error rate than the state of the art.
- Validation combines experimental results with theoretical analysis of adaptivity.

## Takeaways

- Adaptivity to traffic characteristics is a first-class design goal for measurement structures, since fixed sketches degrade under stress.
- Generality across tasks and platforms is a major practical advantage: one sketch, six tasks, six platforms.
- Large reported gains (tens of times faster, orders of magnitude lower error) suggest structural adaptation pays off versus static sketches.
- Co-designing for programmable hardware (P4/FPGA) and software (CPU/OVS) broadens deployability.

## Related Work

The abstract only positions the Elastic sketch against unnamed 'state-of-the-art' sketch methods, reporting speed and error improvements over them. No specific related systems are named.

## Open Questions

- What specific internal structures enable adaptivity, and how does the sketch decide when and how to reconfigure?
- How does adaptivity behave under rapid traffic regime changes, and what is the reconfiguration overhead?
- Are the reported speed and error gains consistent across all six tasks and all six platforms, or concentrated in some?
- How does the sketch handle adversarial traffic designed to defeat its adaptation logic?
- What are the memory and hardware-resource costs on constrained platforms such as P4 switches and FPGAs?
