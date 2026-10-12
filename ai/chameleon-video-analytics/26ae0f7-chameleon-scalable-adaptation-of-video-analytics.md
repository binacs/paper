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
citations: 540
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-10-12T14:26:55+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects neural network configurations (e.g., resolution, frame rate) for video analytics pipelines, amortizing the search cost by exploiting temporal and spatial correlations in video content. It achieves 20-50% higher accuracy at the same resource cost or 2-3X resource savings at the same accuracy compared to a static offline-optimal configuration.

## Problem & Motivation

Applying deep convolutional neural networks to video data at scale is challenging because improving inference accuracy often requires prohibitive computational resources. While one can balance resource and accuracy by choosing a suitable NN configuration (e.g., input resolution and frame rate), the impact of configuration on accuracy varies significantly over time and across video feeds, making static choices suboptimal.

## Key Ideas

- Dynamically adapt NN configurations for existing video analytics pipelines to balance resource usage and accuracy.
- Frequent adaptation can reduce resource consumption with little accuracy loss, but naive periodic search over a large configuration space incurs overwhelming overhead that negates gains.
- Exploit temporal and spatial correlation in underlying video characteristics (e.g., object velocity and sizes) that affect the best configuration.
- Amortize the search cost over time and across multiple video feeds by leveraging these correlations.

## System Design

Chameleon is a controller that sits on top of existing NN-based video analytics pipelines. It periodically selects configurations (e.g., resolution, frame rate) for each video feed. The controller uses the observed temporal and spatial correlation in video content to predict good configurations without exhaustively searching the full space, thereby amortizing the search overhead across time and multiple feeds.

## Evaluation

Evaluated using video feeds from five traffic cameras. Compared to a baseline that picks a single optimal configuration offline, Chameleon achieves 20-50% higher accuracy with the same resources, or the same accuracy with only 30-50% of the resources (a 2-3X speedup).

## Takeaways

- Dynamic configuration adaptation can significantly improve the accuracy-resource trade-off in video analytics.
- The key enabler is exploiting temporal and spatial correlation to amortize search cost.
- Even a small number of video feeds (e.g., five) can benefit from cross-feed correlation.
- Static offline-optimal configurations are suboptimal under dynamic video content.

## Open Questions

- How well does Chameleon generalize to other video analytics tasks and NN architectures beyond the evaluated traffic camera scenario?
- What is the impact of the number of video feeds on the effectiveness of spatial correlation?
- How does Chameleon handle abrupt changes in video content that break temporal correlation?
- Can the approach be extended to jointly optimize across other resource dimensions (e.g., model selection, hardware heterogeneity)?
