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
citations: 535
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-10-05T13:35:34+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., resolution, frame rate) for video analytics pipelines, exploiting temporal and spatial correlation to amortize the cost of searching a large configuration space. It achieves 20–50% higher accuracy at the same resource budget, or the same accuracy with 30–50% of the resources, compared to a single offline-optimal configuration.

## Problem & Motivation

Applying deep convolutional neural networks to video at scale is costly: improving inference accuracy typically demands prohibitive computational resources. A promising lever is to trade off resource usage and accuracy by choosing an appropriate NN configuration, such as input resolution and frame rate. However, the impact of a given configuration on analytics accuracy varies significantly over time and across video feeds, so a single static configuration is suboptimal.

Adapting configurations frequently could reduce resource consumption with little accuracy loss, but periodically searching a large configuration space incurs overwhelming resource overhead that can negate the gains of adaptation. The core problem is therefore how to adapt configurations dynamically without paying an unsustainable search cost.

## Key Ideas

- Treat configuration selection (resolution, frame rate, etc.) as a dynamic control problem for existing NN-based video analytics pipelines.
- Exploit temporal correlation: the characteristics that determine the best configuration (e.g., object velocity and sizes) persist over time, so search results can be reused across nearby time windows.
- Exploit spatial correlation: similar characteristics recur across multiple video feeds, so search cost can be amortized across cameras.
- Amortize the cost of exploring a large configuration space over time and across feeds, making frequent adaptation affordable.
- Keep the pipeline unchanged; Chameleon acts as an external controller that picks configurations for existing NN-based analytics.

## System Design

- Chameleon is a controller that sits alongside existing NN-based video analytics pipelines and dynamically selects the best configuration for each feed.
- It periodically searches the configuration space, but uses temporal and spatial correlation to avoid exhaustive per-feed, per-time search.
- Search results are shared/reused across time windows and across multiple video feeds, amortizing exploration overhead.
- The controller observes underlying characteristics (e.g., object velocity and sizes) that affect which configuration is best, and maps them to configuration choices.
- Control flow: monitor feed characteristics → reuse or refine configuration knowledge from correlated times/feeds → apply selected configuration to the analytics pipeline.

## Evaluation

- Workload: video feeds from five traffic cameras.
- Baseline: a single optimal configuration chosen offline.
- Headline results: 20–50% higher accuracy with the same amount of resources, or the same accuracy using only 30–50% of the resources (a 2–3× speedup).

## Takeaways

- Static, offline-optimal configurations leave substantial accuracy or resource gains on the table because the best configuration is dynamic.
- Frequent adaptation is only practical if the search cost is amortized; temporal and spatial correlation make this possible.
- The same accuracy can be achieved with roughly one-third to one-half of the resources, or accuracy can be raised 20–50% at fixed cost.
- The approach is pipeline-agnostic: it controls existing NN-based video analytics without modifying the models.

## Related Work

The abstract contrasts Chameleon with a baseline that selects a single optimal configuration offline. It positions the work against static configuration selection rather than naming specific competing systems.

## Open Questions

- How well do the temporal and spatial correlation assumptions hold for non-traffic workloads or highly heterogeneous camera deployments?
- What is the sensitivity of the gains to the number of feeds, search frequency, and configuration space size?
- Can the controller generalize to other configuration knobs (e.g., model architecture, batching) beyond resolution and frame rate?
- How does Chameleon handle concept drift or abrupt scene changes that break correlation?
