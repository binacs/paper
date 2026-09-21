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
citations: 533
abs_url: https://www.semanticscholar.org/paper/26ae0f7d0939d594ffb590a288ffa30f168cf603
pdf_url: ''
analyzed_at: '2026-09-21T11:58:42+00:00'
model: deepseek-chat
doi: 10.1145/3230543.3230574
---

# Chameleon: scalable adaptation of video analytics

## TL;DR

Chameleon is a controller that dynamically selects NN configurations (e.g., resolution, frame rate) for video analytics pipelines, exploiting temporal and spatial correlation to amortize search cost and improve the accuracy-resource tradeoff.

## Problem & Motivation

Applying deep convolutional neural networks to video data at scale is challenging because higher inference accuracy demands significantly more computational resources. While selecting an appropriate NN configuration can balance resource usage and accuracy, the optimal configuration varies dynamically due to changing video content, making static offline selection suboptimal. Frequent adaptation could reduce resource consumption with minimal accuracy loss, but periodically searching a large configuration space incurs overwhelming overhead that negates the benefits.

## Key Ideas

['- Dynamically adapt NN configurations (e.g., resolution, frame rate) for existing video analytics pipelines.', '- Exploit temporal and spatial correlation in underlying video characteristics (e.g., object velocity and sizes) to amortize configuration search cost over time and across multiple video feeds.', '- Use a controller that periodically searches for the best configuration but leverages correlations to reduce the frequency and scope of searches.', '- Balance resource consumption and accuracy by adapting configurations frequently with low overhead.']

## System Design

Chameleon is a controller that sits on top of existing NN-based video analytics pipelines. It dynamically picks configurations for each video feed. The controller periodically searches a space of configurations, but uses the insight that characteristics affecting the best configuration have temporal and spatial correlation. This allows the search cost to be amortized over time and across multiple video feeds, enabling frequent adaptation without overwhelming resource overhead.

## Evaluation

Evaluated using video feeds from five traffic cameras. Compared to a baseline that picks a single optimal configuration offline, Chameleon achieves 20-50% higher accuracy with the same resources, or achieves the same accuracy with only 30-50% of the resources (a 2-3X speedup).

## Takeaways

['- Dynamic configuration adaptation can significantly improve the accuracy-resource tradeoff for video analytics.', '- Temporal and spatial correlations in video content enable amortizing the cost of configuration search.', '- Frequent adaptation is feasible when search overhead is mitigated through correlation exploitation.', '- The approach works with existing NN-based pipelines without requiring model changes.']
