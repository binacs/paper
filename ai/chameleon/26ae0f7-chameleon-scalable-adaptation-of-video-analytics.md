---
paper_id: 26ae0f7d0939d594ffb590a288ffa30f168cf603
title: 'Chameleon: scalable adaptation of video analytics'
authors:
- Junchen Jiang
- Ganesh Ananthanarayanan
- P. Bodík
- Siddhartha Sen
- Ion Stoica
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 545
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-10-26T12:23:18+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., input resolution and frame rate) for existing video analytics pipelines, amortizing the cost of configuration search across time and across multiple video feeds by exploiting temporal and spatial correlation in the underlying video characteristics.

## Problem & Motivation

Running deep convolutional neural networks on video at scale is expensive: higher inference accuracy typically demands prohibitive compute. One lever is to trade resource use against accuracy by choosing an NN configuration such as input resolution and frame rate, but the best configuration varies significantly with video dynamics, so a single static choice is suboptimal.

In principle, frequent re-adaptation could cut resource consumption with little accuracy loss, but periodically searching a large configuration space incurs overhead that can overwhelm the adaptation gains. The paper addresses how to adapt configurations continuously without paying the full search cost each time.

## Key Ideas

- Treat NN configuration selection (resolution, frame rate) as a runtime control problem over existing analytics pipelines.
- Exploit temporal correlation: the video characteristics that determine the best configuration (e.g., object velocity and object sizes) persist over time, so search results can be reused across time.
- Exploit spatial correlation: similar characteristics recur across multiple video feeds, so search cost can be amortized across cameras.
- Amortized search lets the controller adapt frequently enough to track dynamics while keeping overhead low.
- Aim to beat a single offline-optimal configuration rather than redesigning the NN itself.

## System Design

Chameleon is a controller layered on top of existing NN-based video analytics pipelines; it does not replace the model but chooses configurations for them. It periodically searches the configuration space, but rather than searching exhaustively per feed per interval, it leverages temporal and spatial correlation in the video characteristics that affect the best configuration, so search effort is shared over time and across multiple video feeds. The abstract does not specify further component-level details.

## Evaluation

Evaluated on video feeds from five traffic cameras. Baselines: a baseline that picks a single optimal configuration offline. Headline results: 20–50% higher accuracy at the same resource budget, or the same accuracy using only 30–50% of the resources (a 2–3X speedup).

## Takeaways

- Configuration choice (resolution, frame rate) is a first-class, dynamic knob for video analytics accuracy/cost trade-offs.
- The main obstacle to adaptation is search overhead, not the idea of adapting.
- Temporal and spatial correlation in video content is the key resource that makes frequent adaptation affordable.
- Gains are large relative to a static offline-optimal configuration: 2–3X resource savings at equal accuracy.
- The approach is complementary to model design since it controls existing pipelines.

## Related Work

The abstract contrasts Chameleon with a baseline that selects a single optimal configuration offline, rather than naming specific prior systems.

## Open Questions

- How robust is the correlation assumption under highly non-stationary scenes (e.g., sudden events, camera motion)?
- How does the controller behave as the number of feeds scales, and what is the search-cost scaling?
- Does the approach generalize beyond traffic-camera workloads and beyond resolution/frame-rate knobs?
- What accuracy guarantees or convergence properties does the adaptive search provide?
