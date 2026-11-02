---
paper_id: 8352e3ba20cb0fd48e2514bc1948e68108943e39
title: 'SOCK: Rapid Task Provisioning with Serverless-Optimized Containers'
authors:
- Edward Oakes
- Leon Yang
- Dennis Zhou
- Kevin Houck
- Tyler Harter
- Andrea C. Arpaci-Dusseau
- Remzi H. Arpaci-Dusseau
venue: USENIX Annual Technical Conference
year: 2018
citations: 498
abs_url: https://www.semanticscholar.org/paper/8352e3ba20cb0fd48e2514bc1948e68108943e39
pdf_url: ''
analyzed_at: '2026-11-02T15:00:21+00:00'
model: deepseek-chat
---

# SOCK: Rapid Task Provisioning with Serverless-Optimized Containers

## TL;DR

SOCK is a serverless-optimized container system that reduces cold-start latency for function provisioning by specializing the container stack for the serverless workload, achieving faster task startup than general-purpose container solutions.

## Problem & Motivation

Serverless platforms must provision function instances quickly, but general-purpose container runtimes carry overhead (image management, isolation setup, general-purpose init) that inflates cold-start latency. Slow provisioning hurts latency-sensitive applications and forces platforms to keep idle capacity warm, raising cost.

The paper targets the tension between strong isolation (needed for multi-tenant serverless) and fast startup, arguing that existing container stacks are not tuned for the short-lived, bursty, single-function nature of serverless tasks.

## Key Ideas

- Specialize the container stack for serverless workloads rather than reusing general-purpose container runtimes.
- Reduce provisioning overhead in the container lifecycle to cut cold-start latency.
- Exploit the characteristics of serverless tasks (short-lived, single-purpose, bursty) to simplify setup.
- Balance fast startup against the isolation guarantees multi-tenant serverless requires.

## System Design

- SOCK provides a serverless-optimized container abstraction layered on container primitives, with a provisioning path tuned for rapid task startup.
- The design streamlines container creation and initialization relative to general-purpose runtimes, targeting the cold-start critical path.
- It maintains isolation between tenants while minimizing per-task setup work.

## Evaluation

The paper evaluates SOCK against general-purpose container-based provisioning, measuring task startup/provisioning latency. Headline numbers are not available from the provided abstract text; the evaluation centers on demonstrating reduced cold-start latency versus baseline container approaches.

## Takeaways

- General-purpose container stacks are a poor fit for serverless cold starts; workload-specific specialization pays off.
- Cold-start latency is a first-order concern for serverless platforms, affecting both user latency and provider cost.
- Fast provisioning and multi-tenant isolation can be jointly pursued rather than traded off naively.

## Related Work

Positioned against general-purpose container runtimes and container-based serverless provisioning approaches that inherit their overhead; the abstract frames SOCK as a specialization of containers for the serverless setting.

## Open Questions

- How does SOCK's isolation compare to stronger sandboxing approaches (e.g., microVMs) under adversarial tenants?
- How well does the design extend to longer-running or stateful functions beyond short-lived tasks?
- What are the concrete latency and throughput numbers versus specific baselines, and how do they scale under bursty load?
