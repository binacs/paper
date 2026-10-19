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
citations: 541
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-10-19T12:09:07+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., input resolution and frame rate) for existing video analytics pipelines, amortizing the cost of searching a large configuration space by exploiting temporal and spatial correlation in the video characteristics that determine the best configuration.

## Problem & Motivation

Running deep convolutional neural networks on video at scale is expensive: higher inference accuracy generally demands far more computation. One lever is to tune the NN configuration, such as input video resolution and frame rate, to trade resource use against accuracy. However, the accuracy impact of a given configuration varies significantly over time and across feeds, so a single static configuration is suboptimal.

In principle, frequently re-adapting configurations could cut resource consumption with little accuracy loss. The obstacle is that periodically searching a large configuration space itself costs so much computation that it cancels out the adaptation gains.

## Key Ideas

- Treat configuration selection (resolution, frame rate, etc.) as a runtime control problem over existing NN-based video analytics pipelines.
- Adapt configurations frequently rather than picking one offline optimum.
- The key insight: the underlying video characteristics that determine the best configuration (e.g., object velocity and object sizes) exhibit enough temporal and spatial correlation that search cost can be amortized over time and across multiple video feeds.
- Exploit this correlation to avoid exhaustive per-feed, per-instant search while still tracking dynamics.

## System Design

Chameleon is a controller layered on top of existing NN-based video analytics pipelines; it does not replace the NN itself but chooses the configuration each pipeline runs with. Control flow: the controller observes video characteristics relevant to configuration choice (object velocity and sizes), uses temporal and spatial correlation to amortize the cost of exploring the configuration space, and sets the configuration (e.g., resolution and frame rate) accordingly. Data flow: multiple video feeds (e.g., several traffic cameras) share information so that search effort on one feed or time window informs choices on others, reducing the aggregate search overhead.

## Evaluation

Evaluated on video feeds from five traffic cameras. Baseline: a single optimal configuration chosen offline. Headline results: with the same resource budget, Chameleon achieves 20–50% higher accuracy; alternatively, it reaches the same accuracy using only 30–50% of the resources, i.e., a 2–3X speedup.

## Takeaways

- Configuration tuning (resolution, frame rate) is a practical, model-agnostic lever for the accuracy/cost tradeoff in video analytics.
- The main barrier to adaptive tuning is the search overhead, not the adaptation itself; amortization is the crux.
- Video content statistics that drive optimal configuration are correlated in time and across cameras, making cheap approximate search feasible.
- Gains are substantial: 2–3X resource reduction at equal accuracy in a multi-camera traffic setting.

## Related Work

Compared against a baseline that selects a single optimal configuration offline, i.e., static configuration tuning without runtime adaptation.

## Open Questions

- How well does the correlation assumption hold for non-traffic or highly heterogeneous camera deployments?
- How does the controller behave under abrupt scene changes that break temporal correlation?
- What is the overhead and convergence behavior of the amortized search as the number of feeds scales?
- Does the approach generalize beyond resolution and frame rate to other configuration knobs or NN architectures?
