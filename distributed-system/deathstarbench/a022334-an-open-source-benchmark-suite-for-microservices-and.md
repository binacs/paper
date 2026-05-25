---
paper_id: a022334521d88eb0181e76f01b53ce42e7dcc302
title: An Open-Source Benchmark Suite for Microservices and Their Hardware-Software
  Implications for Cloud & Edge Systems
authors:
- Yu Gan
- Yanqi Zhang
- Dailun Cheng
- A. Shetty
- Priyal Rathi
- Nayan Katarki
- Ariana Bruno
- Justin Hu
- Brian Ritchken
- Brendon Jackson
- Kelvin Hu
- Meghna Pancholi
- Yuan He
- B. Clancy
- C. Colen
- Fukang Wen
- Catherine Leung
- Siyuan Wang
- Leon Zaruvinsky
- Mateo Espinosa Zarlenga
- Rick Lin
- Zhongling Liu
- Jake Padilla
- Christina Delimitrou
venue: International Conference on Architectural Support for Programming Languages
  and Operating Systems
year: 2019
citations: 791
abs_url: https://www.semanticscholar.org/paper/a022334521d88eb0181e76f01b53ce42e7dcc302
pdf_url: https://dl.acm.org/doi/pdf/10.1145/3297858.3304013
analyzed_at: '2026-05-25T10:01:49+00:00'
model: deepseek-chat
doi: 10.1145/3297858.3304013
---

# An Open-Source Benchmark Suite for Microservices and Their Hardware-Software Implications for Cloud & Edge Systems

## TL;DR

DeathStarBench is an open-source benchmark suite of representative microservice applications (social network, media, e-commerce, banking, IoT) that reveals how microservices shift assumptions across the cloud stack, increasing pressure on performance predictability and causing tail-at-scale effects.

## Problem & Motivation

Cloud services are moving from monolithic applications to graphs of hundreds or thousands of loosely-coupled microservices. This shift fundamentally changes assumptions in cloud system design (e.g., networking, OS, cluster management) and introduces new challenges for QoS and utilization. Existing benchmarks do not capture the complexity and scale of real-world microservice architectures, making it hard to study their implications.

## Key Ideas

- Design and implement DeathStarBench, a modular and extensible open-source benchmark suite with five representative microservice applications: social network, media service, e-commerce, banking, and IoT (UAV swarm coordination).
- Use the suite to study architectural characteristics of microservices, their networking and OS implications, cluster management challenges, and trade-offs in application design and programming frameworks.
- Explore tail-at-scale effects in real deployments with hundreds of users, highlighting increased pressure on performance predictability.

## System Design

DeathStarBench consists of five distinct microservice applications, each built as a graph of loosely-coupled services. The suite is designed to be modular (services can be added/removed) and extensible. The paper does not detail internal component architecture beyond the application types; it focuses on using the suite to study system-level implications.

## Evaluation

The paper validates claims by deploying DeathStarBench in real environments with hundreds of users. It studies architectural characteristics, networking/OS implications, cluster management challenges, and application design trade-offs. Headline findings include increased tail-at-scale effects and pressure on performance predictability.

## Takeaways

- Microservices fundamentally change assumptions across the cloud stack, from hardware to cluster management.
- Tail latency becomes more pronounced and harder to predict in microservice architectures.
- DeathStarBench provides a realistic, open-source platform for future microservices research.
- The suite covers diverse domains (social, media, e-commerce, banking, IoT) to ensure representativeness.

## Related Work

DeathStarBench is positioned as a novel open-source benchmark suite for microservices, filling a gap left by existing benchmarks that focus on monolithic applications or simpler distributed systems. It is designed to be representative of large end-to-end services.

## Open Questions

The paper does not provide detailed performance numbers or comparisons with other benchmarks. Future work could include deeper analysis of specific microservice interactions, resource provisioning strategies, and hardware-software co-design for microservices.
