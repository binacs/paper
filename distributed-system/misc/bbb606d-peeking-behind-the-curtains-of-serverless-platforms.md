---
paper_id: bbb606d78d379262c85c4615cb5d9c191cd2e3bf
title: Peeking Behind the Curtains of Serverless Platforms
authors:
- Liang Wang
- Mengyuan Li
- Yinqian Zhang
- Thomas Ristenpart
- M. Swift
venue: USENIX Annual Technical Conference
year: 2018
citations: 654
abs_url: https://www.semanticscholar.org/paper/bbb606d78d379262c85c4615cb5d9c191cd2e3bf
pdf_url: ''
analyzed_at: '2026-06-01T11:29:47+00:00'
model: deepseek-chat
---

# Peeking Behind the Curtains of Serverless Platforms

## TL;DR

This paper performs a systematic measurement study of three major serverless platforms (AWS Lambda, Azure Functions, Google Cloud Functions) to characterize their performance, resource management, and security properties, revealing opaque behaviors and potential side-channel vulnerabilities.

## Problem & Motivation

Serverless computing abstracts infrastructure management, but platforms are opaque black boxes. Developers lack visibility into resource allocation, cold-start latency, and multi-tenancy isolation. This opacity hinders performance optimization and raises security concerns, as co-located functions may leak sensitive information via side channels. The paper aims to empirically uncover these hidden behaviors.

## Key Ideas

- Conducted extensive measurements on AWS Lambda, Azure Functions, and Google Cloud Functions using custom microbenchmarks.
- Inferred platform internals such as container reuse policies, CPU throttling, and network bandwidth allocation.
- Identified side-channel vulnerabilities in CPU caches and memory bus, enabling cross-function information leakage.
- Developed techniques to detect co-location of functions and measure resource contention.

## Evaluation

The paper validates claims through controlled experiments on three commercial platforms. It measures cold-start latency, CPU performance, network throughput, and memory bandwidth. Headline findings include: cold starts can take hundreds of milliseconds to seconds; CPU resources are throttled after bursts; and co-located functions can leak data via cache timing channels with high accuracy.

## Takeaways

- Serverless platforms exhibit significant performance variability due to opaque resource management.
- Container reuse policies vary widely, affecting cold-start frequency.
- Multi-tenancy introduces security risks: side-channel attacks are feasible across functions.
- Developers should design for performance unpredictability and consider security implications of co-location.

## Related Work

This work is among the first to empirically characterize serverless platforms. It contrasts with prior studies on cloud VM performance (e.g., EC2) and extends side-channel research (e.g., Prime+Probe) to the serverless context. It is related to later work on serverless benchmarking and security.

## Open Questions

- How do newer serverless platforms (e.g., Cloudflare Workers, Alibaba) compare?
- Can platform providers mitigate side channels without sacrificing performance?
- How can developers model and predict performance given opaque scheduling?
- What are the implications for function composition and workflow orchestration?
