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
citations: 553
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-11-09T15:12:45+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configuration (resolution, frame rate) per video analytics pipeline to trade off resource cost and accuracy, amortizing the cost of searching the configuration space by exploiting temporal and spatial correlation across video feeds.

## Problem & Motivation

Running deep convolutional neural networks on video at scale is expensive: higher inference accuracy typically demands prohibitive compute. One lever is choosing a suitable NN configuration (e.g., input resolution and frame rate), but the accuracy impact of a given configuration varies significantly over time and across scenes, so a single static choice is suboptimal.

In principle, frequent re-adaptation of configurations could cut resource use with little accuracy loss, but periodically searching a large configuration space itself costs so much resource that it can negate the adaptation gains.

## Key Ideas

- Treat NN configuration selection (resolution, frame rate) as a runtime control problem over existing video analytics pipelines.
- Adapt configurations frequently to track changing scene conditions rather than fixing one offline-optimal configuration.
- Amortize search cost by exploiting temporal correlation (best configurations persist over time) and spatial correlation (similar across multiple video feeds).
- Use these correlations to avoid exhaustive per-feed, per-interval searching, keeping adaptation overhead low relative to the savings.

## System Design

Chameleon is a controller layered on top of existing NN-based video analytics pipelines. It periodically selects configurations for each pipeline, using observed characteristics that affect which configuration is best (e.g., object velocity and object sizes) and leveraging temporal and spatial correlation to share/amortize search effort across time and across multiple video feeds rather than searching the full space independently for each feed and interval.

## Evaluation

Evaluated on video feeds from five traffic cameras. Compared against a baseline that picks a single optimal configuration offline, Chameleon achieves 20-50% higher accuracy at the same resource budget, or matches baseline accuracy using only 30-50% of the resources (a 2-3X speedup).

## Takeaways

- Configuration choice (resolution/frame rate) is a first-class knob for NN video analytics cost/accuracy trade-offs.
- Adaptation gains are real but only if the cost of searching configurations is controlled.
- Temporal and spatial correlation in scene characteristics is the key enabler that makes frequent adaptation affordable.
- Reported gains: 20-50% accuracy improvement at equal resources, or 2-3X resource reduction at equal accuracy.

## Related Work

Positioned against a baseline that selects a single optimal configuration offline; Chameleon argues this static approach misses dynamic scene changes and that naive periodic re-searching is too costly.

## Open Questions

- How well do the correlation assumptions hold for non-traffic, highly heterogeneous camera deployments?
- What is the sensitivity of gains to the search/adaptation interval and to the number of correlated feeds available?
- Does the approach generalize beyond resolution and frame rate to other NN configuration knobs?
