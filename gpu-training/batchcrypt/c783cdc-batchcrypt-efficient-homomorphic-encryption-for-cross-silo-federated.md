---
paper_id: c783cdc03a32e5094affa7eef710459aac599aaf
title: 'BatchCrypt: Efficient Homomorphic Encryption for Cross-Silo Federated Learning'
authors:
- Chengliang Zhang
- Suyi Li
- Junzhe Xia
- Wei Wang
- Feng Yan
- Yang Liu
venue: USENIX Annual Technical Conference
year: 2020
citations: 932
abs_url: https://www.semanticscholar.org/paper/c783cdc03a32e5094affa7eef710459aac599aaf
pdf_url: ''
analyzed_at: '2026-07-27T09:47:30+00:00'
model: deepseek-chat
---

# BatchCrypt: Efficient Homomorphic Encryption for Cross-Silo Federated Learning

## TL;DR

BatchCrypt enables efficient homomorphic encryption for cross-silo federated learning by encoding a batch of quantized gradients into a long integer, drastically reducing encryption and communication overhead.

## Problem & Motivation

Federated learning (FL) requires aggregating model updates from multiple clients without exposing raw data. Homomorphic encryption (HE) can protect gradient privacy, but existing HE schemes incur high computational and communication costs, making them impractical for cross-silo FL where clients have limited bandwidth and computation resources. The paper addresses the challenge of making HE practical for FL by reducing the number of ciphertexts and the size of encrypted messages.

## Key Ideas

- Quantize gradients to low-bit integers (e.g., 8-bit).
- Batch multiple quantized gradients into a single long integer via bit packing.
- Encrypt the batched integer as one ciphertext using HE, reducing ciphertext count by orders of magnitude.
- Design a new quantization scheme (batch quantization) that aligns with the batch encoding to minimize error.
- Adapt the HE addition and multiplication operations to work on batched ciphertexts.

## System Design

BatchCrypt is a system that sits between the FL server and clients. Clients quantize their gradients, batch them into a single integer, encrypt it with HE, and send the ciphertext to the server. The server aggregates ciphertexts homomorphically (addition) and returns the encrypted aggregate. Clients decrypt and un-batch to get the aggregated gradient. The system uses a modified Paillier or BGV scheme optimized for batched integers.

## Evaluation

Evaluated on three FL tasks (image classification, language modeling, and human activity recognition) with up to 100 clients. Baselines include plaintext FL, naive HE, and secure aggregation (SecAgg). BatchCrypt reduces encryption time by 23–91× and communication by 28–68× compared to naive HE, while maintaining model accuracy within 0.5% of plaintext FL.

## Takeaways

- Batching quantized gradients into a single ciphertext is key to making HE practical for FL.
- Quantization must be carefully designed to avoid accuracy loss when combined with batching.
- BatchCrypt achieves near plaintext accuracy with orders of magnitude less overhead than naive HE.
- The approach is complementary to other privacy techniques like differential privacy.

## Related Work

Compared to prior HE-based FL systems (e.g., using Paillier or BGV directly), BatchCrypt is the first to exploit batching of gradients. It also contrasts with secure multi-party computation (MPC) approaches like SecAgg, which have higher communication costs. The paper positions BatchCrypt as a practical HE solution for cross-silo FL.

## Open Questions

- How does BatchCrypt scale to very large models (e.g., >100M parameters) where batching may still produce many ciphertexts?
- Can the batching technique be combined with other HE optimizations like SIMD packing?
- What is the impact of quantization noise on convergence for more complex models?
- How does BatchCrypt handle client dropouts or stragglers in asynchronous FL?
