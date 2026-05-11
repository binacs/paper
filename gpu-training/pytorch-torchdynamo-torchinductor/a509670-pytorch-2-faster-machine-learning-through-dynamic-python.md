---
paper_id: a509670659e8b054e2b7d1b6f8a0bc722398fa62
title: 'PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation
  and Graph Compilation'
authors:
- Jason Ansel
- Edward Yang
- Horace He
- N. Gimelshein
- Animesh Jain
- Michael Voznesensky
- Bin Bao
- Peter Bell
- D. Berard
- Evgeni Burovski
- Geeta Chauhan
- Anjali Chourdia
- W. Constable
- Alban Desmaison
- Zachary DeVito
- Elias Ellison
- W. Feng
- Jiong Gong
- Michael Gschwind
- B. Hirsh
- Sherlock Huang
- Kshiteej Kalambarkar
- Laurent Kirsch
- Michael Lazos
- M. Lezcano
- Yanbo Liang
- Jason Liang
- Yinghai Lu
- C. Luk
- Bertrand A. Maher
- Yunjie Pan
- Christian Puhrsch
- Matthias Reso
- Mark-Albert Saroufim
- Marcos Yukio Siraichi
- Helen Suk
- Shunting Zhang
- Michael Suo
- P. Tillet
- Xu Zhao
- Eikan Wang
- Keren Zhou
- Richard Zou
- Xiaodong Wang
- Ajit Mathews
- W. Wen
- Gregory Chanan
- Peng Wu
- Soumith Chintala
venue: International Conference on Architectural Support for Programming Languages
  and Operating Systems
year: 2024
citations: 1101
abs_url: https://www.semanticscholar.org/paper/a509670659e8b054e2b7d1b6f8a0bc722398fa62
pdf_url: ''
analyzed_at: '2026-05-11T09:38:12+00:00'
model: deepseek-chat
doi: 10.1145/3620665.3640366
---

# PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation

## TL;DR

PyTorch 2 introduces TorchDynamo, a Python bytecode JIT compiler that robustly captures computation graphs from arbitrary PyTorch programs, and TorchInductor, a backend that compiles these graphs into efficient Triton/C++ code, achieving 2.27× inference and 1.41× training speedups on A100 GPUs across 180+ models.

## Problem & Motivation

Existing deep learning frameworks face a tension between eager-mode flexibility (Pythonic, dynamic) and graph-mode performance (static, optimized). Prior graph capture approaches (e.g., tracing, scripting) often fail on real-world models due to Python control flow or dynamic shapes, limiting the applicability of compiler optimizations. PyTorch users want both the ease of eager execution and the speed of compiled graphs.

## Key Ideas

- TorchDynamo: Dynamically modifies Python bytecode at runtime to extract FX graphs from PyTorch operations, handling arbitrary Python control flow and dynamic shapes without user intervention.
- TorchInductor: Default backend that lowers FX graphs to Triton (GPU) or C++ (CPU), leveraging loop-level optimizations and fusion.
- Extensible backend interface: TorchDynamo can use multiple backends (e.g., NVFuser, XLA) beyond TorchInductor.
- Minimal overhead: Graph capture adds negligible runtime cost, enabling always-on compilation.

## System Design

TorchDynamo intercepts Python frame execution via bytecode rewriting, identifying sequences of PyTorch ops and extracting them into FX graphs. These graphs are then passed to a chosen backend (default TorchInductor) for compilation. TorchInductor uses a lowering pass to generate Triton kernels for GPU or C++ code for CPU, applying fusion and memory optimizations. The compiled graph is cached and reused for subsequent calls with the same input shapes.

## Evaluation

Evaluated on 180+ real-world models (vision, NLP, speech, etc.) on NVIDIA A100 GPU. Baselines include eager PyTorch, TorchScript, and six other compilers (e.g., XLA, NVFuser). Headline results: 2.27× geometric mean inference speedup, 1.41× training speedup over eager mode. TorchDynamo captures graphs for 99% of models, outperforming prior approaches in robustness.

## Takeaways

- Dynamic bytecode transformation is a practical and robust method for graph capture in eager-mode frameworks.
- TorchInductor's use of Triton enables competitive GPU performance with minimal engineering effort.
- The extensible backend design allows the community to contribute new compilers.
- Significant speedups are achievable without sacrificing Python flexibility.

## Related Work

Positioned against prior graph capture methods in PyTorch (TorchScript tracing/scripting) and other frameworks (TensorFlow AutoGraph, JAX). Also compared to compiler backends like XLA, NVFuser, and TVM. TorchDynamo's key advantage is its ability to handle arbitrary Python code without user annotations.

## Open Questions

- How does TorchDynamo handle very dynamic models (e.g., with frequent shape changes) where recompilation overhead may dominate?
- Can TorchInductor's Triton code match hand-tuned kernels for specific operations?
- Extending support to more hardware (e.g., AMD GPUs, custom accelerators) via new backends.
- Reducing compilation time for large models to improve developer iteration speed.
