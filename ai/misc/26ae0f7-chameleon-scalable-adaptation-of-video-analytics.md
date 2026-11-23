---
paper_id: 26ae0f7d0939d594ffb590a288ffa30f168cf603
title: 'Chameleon: scalable adaptation of video analytics'
authors:
- Jun-Chen Jiang
- Ganesh Ananthanarayanan
- Peter Bodík
- Siddhartha Sen
- I. Stoica
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 560
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-11-23T17:23:55+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., input resolution and frame rate) for existing video analytics pipelines, amortizing the cost of configuration search across time and across multiple video feeds by exploiting temporal and spatial correlation in scene characteristics.

## Problem & Motivation

Running deep convolutional neural networks on video at scale is expensive: higher inference accuracy typically demands prohibitive compute. One can trade resource use against accuracy by choosing an NN configuration such as input resolution and frame rate, but the best configuration shifts significantly over time as scene dynamics change.

A naive approach of periodically re-searching a large configuration space to adapt would itself consume so many resources that it negates the adaptation gains, so the challenge is to adapt frequently without paying an overwhelming search overhead.

## Key Ideas

- Treat configuration selection (resolution, frame rate) as a control problem over existing NN-based video analytics pipelines.
- Adapt configurations dynamically rather than fixing a single offline-optimal configuration.
- Exploit the insight that characteristics affecting the best configuration (e.g., object velocity and object sizes) exhibit temporal and spatial correlation.
- Use that correlation to amortize the configuration search cost over time and across multiple video feeds, making frequent adaptation affordable.

## System Design

Chameleon is a controller layered on top of existing NN-based video analytics pipelines; it does not change the NN models themselves but picks configurations for them. Control flow: the controller observes scene characteristics that influence accuracy, searches the configuration space, and applies the chosen configuration to the pipeline. The search is not repeated from scratch each time: results are reused over time (temporal correlation) and shared across multiple video feeds (spatial correlation), which is what keeps the search overhead low relative to the adaptation benefit.

## Evaluation

Evaluated on video feeds from five traffic cameras. Compared against a baseline that picks a single optimal configuration offline, Chameleon achieves 20-50% higher accuracy at the same resource budget, or matches baseline accuracy using only 30-50% of the resources (a 2-3X speedup).

## Takeaways

- Configuration choice (resolution, frame rate) is a first-class lever for the accuracy/resource tradeoff in video analytics, but only if it tracks scene dynamics.
- The cost of adaptation, not the idea of adaptation, is the real obstacle; amortizing search is the crux.
- Temporal and spatial correlation in scene properties (object velocity, object size) makes cheap, frequent reconfiguration feasible.
- Gains are substantial: 2-3X resource savings at equal accuracy, or large accuracy gains at equal cost.

## Related Work

The primary comparison point is an offline baseline that selects a single optimal configuration once and keeps it fixed; Chameleon is positioned as a dynamic alternative that beats this static optimum under the same resource budget.

## Open Questions

- How well does the correlation assumption hold for scenes without strong structure, e.g., non-traffic or highly irregular feeds?
- How does the controller behave when many feeds are heterogeneous rather than similar cameras?
- What is the sensitivity to the configuration search space and to the accuracy model used to rank configurations?
- Does the approach extend beyond resolution and frame rate to other knobs (model choice, batching)?
