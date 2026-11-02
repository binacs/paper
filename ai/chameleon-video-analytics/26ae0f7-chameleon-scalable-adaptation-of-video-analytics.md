---
paper_id: 26ae0f7d0939d594ffb590a288ffa30f168cf603
title: 'Chameleon: scalable adaptation of video analytics'
authors:
- Junchen Jiang
- Ganesh Ananthanarayanan
- Peter Bodík
- Siddhartha Sen
- Ion Stoica
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 550
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-11-02T14:59:56+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., input resolution and frame rate) for existing video analytics pipelines, amortizing the cost of configuration search across time and multiple video feeds by exploiting temporal and spatial correlation in scene characteristics.

## Problem & Motivation

Applying deep CNNs to video at scale is expensive: improving inference accuracy typically demands prohibitive compute. One can trade resource for accuracy by choosing an NN configuration such as input resolution and frame rate, but the best configuration shifts significantly as video content changes.

Frequent re-adaptation could cut resource use with little accuracy loss, yet periodically searching a large configuration space costs so much that it negates the adaptation gains. The paper targets this tension between adaptation benefit and search overhead.

## Key Ideas

- Treat configuration selection (resolution, frame rate, etc.) as a dynamic control problem over existing NN video analytics pipelines.
- Exploit temporal correlation: the scene characteristics that determine the best configuration persist over time, so search results can be reused across nearby frames.
- Exploit spatial correlation: similar characteristics across multiple video feeds let search cost be amortized across cameras.
- Amortize the configuration search rather than paying it independently per feed per interval.

## System Design

- A controller sits in front of existing NN-based video analytics pipelines and picks configurations for them.
- It periodically searches the configuration space but shares/amortizes that search over time and across multiple video feeds using observed temporal and spatial correlation.
- Configuration choices are driven by underlying scene characteristics such as object velocity and object sizes.

## Evaluation

- Workload: video feeds from five traffic cameras.
- Baseline: a single optimal configuration chosen offline.
- Headline results: with the same resources, Chameleon achieves 20–50% higher accuracy; or achieves the same accuracy using only 30–50% of the resources (a 2–3X speedup).

## Takeaways

- Configuration adaptation is a practical lever for balancing accuracy and compute in video analytics without changing the NN itself.
- The main obstacle to frequent adaptation is search overhead, not the adaptation idea itself.
- Scene characteristics exhibit enough temporal and spatial correlation that search can be shared across frames and cameras.
- Gains are substantial: 2–3X resource reduction at equal accuracy on multi-camera traffic workloads.

## Open Questions

- How well does the correlation assumption hold for highly non-stationary scenes or feeds with little spatial overlap?
- How does the approach generalize beyond traffic cameras and beyond resolution/frame-rate knobs?
- What is the sensitivity to the search interval and to the number of feeds sharing amortized search?
