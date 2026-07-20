---
paper_id: 26ae0f7d0939d594ffb590a288ffa30f168cf603
title: 'Chameleon: scalable adaptation of video analytics'
authors:
- Junchen Jiang
- Ganesh Ananthanarayanan
- P. Bodík
- S. Sen
- Ion Stoica
venue: Conference on Applications, Technologies, Architectures, and Protocols for
  Computer Communication
year: 2018
citations: 520
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-07-20T08:54:15+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects the best NN configuration (e.g., resolution, frame rate) for video analytics pipelines, exploiting temporal and spatial correlations to amortize search costs and achieve 2-3x resource savings or 20-50% accuracy gains.

## Problem & Motivation

Applying deep neural networks to video at scale is challenging because improving inference accuracy often requires prohibitive computational resources. While selecting a suitable NN configuration (e.g., resolution, frame rate) can balance resource and accuracy, the impact of configuration on accuracy is highly dynamic. Adapting configurations frequently could reduce resource consumption with little accuracy loss, but periodically searching a large configuration space incurs overwhelming overhead that negates the gains.

## Key Ideas

- Exploit temporal and spatial correlations in video characteristics (e.g., object velocity, size) to amortize the cost of searching for the best configuration over time and across multiple video feeds.
- Dynamically pick the best NN configuration for each video feed at each time, without exhaustive per-frame search.
- Use a controller that leverages correlations to reduce the frequency and scope of configuration searches.

## System Design

Chameleon is a controller that sits on top of existing NN-based video analytics pipelines. It monitors video feeds and periodically selects the best configuration (e.g., input resolution, frame rate) for each feed. The key design is to reuse search results across time (temporal correlation) and across multiple cameras (spatial correlation) to minimize the overhead of configuration exploration.

## Evaluation

Evaluated using video feeds from five traffic cameras. Compared to a baseline that picks a single optimal configuration offline, Chameleon achieves 20-50% higher accuracy with the same resources, or the same accuracy with only 30-50% of the resources (2-3x speedup).

## Takeaways

- Frequent adaptation of NN configuration can significantly improve resource-accuracy trade-offs, but search overhead must be managed.
- Temporal and spatial correlations in video content can be exploited to amortize search costs.
- Chameleon demonstrates practical gains on real traffic camera feeds.

## Related Work

Positioned against systems that use a fixed NN configuration or offline optimization. Related to work on video analytics pipelines and resource-accuracy trade-offs, but Chameleon focuses on online adaptation with low overhead.

## Open Questions

How well does Chameleon generalize to other video domains (e.g., surveillance, sports)? What about scenarios with very low temporal/spatial correlation? Can the approach be extended to adapt other parameters like model architecture or compression?
