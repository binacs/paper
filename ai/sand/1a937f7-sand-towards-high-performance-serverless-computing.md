---
paper_id: 1a937f78c2d968d134981b5c82adba6495e470e5
title: 'SAND: Towards High-Performance Serverless Computing'
authors:
- I. E. Akkus
- Ruichuan Chen
- I. Rimac
- Manuel Stein
- Klaus Satzke
- Andre Beck
- Paarijaat Aditya
- Volker Hilt
venue: USENIX Annual Technical Conference
year: 2018
citations: 525
abs_url: https://www.semanticscholar.org/paper/1a937f78c2d968d134981b5c82adba6495e470e5
pdf_url: ''
analyzed_at: '2026-11-02T15:00:08+00:00'
model: deepseek-chat
---

# SAND: Towards High-Performance Serverless Computing

## TL;DR

SAND is a serverless platform that organizes functions into application-level containers shared by multiple functions, using a hierarchical message bus and two-tier scheduling to cut cold-start latency and improve resource efficiency over per-function containers.

## Problem & Motivation

Serverless platforms typically isolate each function in its own container, which forces frequent cold starts, adds per-function resource overhead, and makes it hard to share state or resources across functions of the same application. This hurts latency-sensitive workloads and wastes capacity, especially when functions are short-lived or invoked at high rates.

## Key Ideas

- Group functions belonging to the same application into shared containers rather than one container per function.
- Use a hierarchical message bus to decouple function invocation from container lifecycle and enable fast inter-function communication.
- Apply two-tier scheduling: a global scheduler places application containers, while local schedulers dispatch individual function calls within a container.
- Exploit application-level isolation and resource sharing to reduce cold starts and improve packing.

## System Design

- Application containers host multiple functions of the same app and are scheduled by a cluster-level scheduler.
- A hierarchical message bus routes invocation requests and responses between the platform front end and function containers.
- Local schedulers inside containers manage concurrent function execution and resource allocation.
- Control flow: client request -> front end -> message bus -> local scheduler -> function execution -> response via bus.

## Evaluation

The paper evaluates SAND against per-function container baselines on serverless workloads, reporting reduced cold-start latency and improved throughput/resource efficiency; headline numbers are not specified in the provided abstract.

## Takeaways

- Sharing containers across an application's functions is a practical way to amortize cold-start and resource costs in serverless computing.
- Decoupling invocation from container lifecycle via a message bus enables fast, flexible function dispatch.
- Two-tier scheduling balances global placement with low-latency local dispatch.

## Related Work

Positioned against conventional serverless platforms that use one container per function (e.g., per-function isolation models), arguing that application-level grouping and hierarchical messaging outperform that baseline.

## Open Questions

- How well does application-level container sharing preserve isolation and security across tenants?
- What are the limits of the two-tier scheduler under skewed or bursty workloads?
- How does SAND handle heterogeneous function resource requirements and autoscaling?
