---
paper_id: 26ae0f7d0939d594ffb590a288ffa30f168cf603
title: 'Chameleon: scalable adaptation of video analytics'
authors:
- Jun-Chen Jiang
- Ganesh Ananthanarayanan
- Peter Bodík
- Siddhartha Sen
- Ion Stoica
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 557
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-11-16T14:47:53+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., input resolution and frame rate) for existing video analytics pipelines, exploiting temporal and spatial correlation in video characteristics to amortize the cost of searching a large configuration space. It delivers 20-50% higher accuracy at equal resources, or equal accuracy at 30-50% of the resources, versus a single offline-optimal configuration.

## Problem & Motivation

Running deep convolutional neural networks over video at scale is expensive: higher inference accuracy typically demands prohibitive compute. One lever is to trade resource for accuracy by choosing an NN configuration such as input video resolution and frame rate, but the accuracy impact of a given configuration varies significantly over time and across feeds, so a static choice is suboptimal.

In principle, frequently re-adapting configurations could cut resource use with little accuracy loss. The obstacle is that periodically searching a large configuration space itself costs so much that it cancels the gains from adaptation.

## Key Ideas

- Treat configuration selection (resolution, frame rate, etc.) as a runtime control problem over existing NN-based video analytics pipelines.
- Adapt configurations dynamically rather than picking one optimum offline.
- The key insight: characteristics that determine the best configuration (e.g., object velocity and object sizes) exhibit enough temporal and spatial correlation that search cost can be amortized over time and across multiple video feeds.
- Exploit this correlation to avoid exhaustive per-feed, per-interval search while still tracking changing conditions.

## System Design

Chameleon is a controller layered on top of existing NN-based video analytics pipelines; it does not replace the NN itself but chooses the configuration each pipeline runs with. The controller periodically considers candidate configurations and selects the best one for current conditions, using the temporal and spatial correlation of object characteristics to amortize the cost of exploring the configuration space across time and across multiple video feeds rather than searching independently for each feed and interval.

## Evaluation

Evaluated using video feeds from five traffic cameras. Compared against a baseline that picks a single optimal configuration offline. Headline results: 20-50% higher accuracy with the same resources, or the same accuracy using only 30-50% of the resources (a 2-3X speedup).

## Takeaways

- Configuration choice (resolution, frame rate) is a powerful, low-friction knob for trading accuracy against compute in video analytics.
- The best configuration is not static; it shifts with scene content such as object velocity and size.
- Naive frequent re-search is self-defeating because search overhead can exceed adaptation gains.
- Temporal and spatial correlation across cameras is the key enabler that makes adaptive search affordable.
- Gains are substantial: 2-3X resource reduction at equal accuracy on a real traffic-camera workload.

## Related Work

The primary comparison is a baseline that selects a single optimal configuration offline, which Chameleon outperforms by adapting at runtime.

## Open Questions

- How well does the approach generalize beyond traffic cameras to other video domains with different object dynamics?
- How sensitive are the gains to the accuracy model used to predict configuration quality?
- What happens when temporal/spatial correlation breaks down (e.g., rare events, highly heterogeneous feeds)?
- How does the controller behave at much larger camera counts and under tighter latency constraints?
