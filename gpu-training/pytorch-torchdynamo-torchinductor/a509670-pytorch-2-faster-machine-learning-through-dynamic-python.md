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
analyzed_at: '2026-05-11T03:53:43+00:00'
model: deepseek-chat
doi: 10.1145/3620665.3640366
---

# PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation

## TL;DR

PyTorch 2 introduces TorchDynamo, a Python-level JIT compiler that dynamically transforms bytecode to extract FX graphs for compilation, and TorchInductor, a default backend that compiles to Triton (GPU) and C++ (CPU), achieving 2.27× inference and 1.41× training speedups on A100 across 180+ models.

## Problem & Motivation

Existing deep learning frameworks like PyTorch offer eager execution for flexibility but suffer from performance overhead due to Python interpreter and lack of graph-level optimizations. Prior graph compilation approaches (e.g., TorchScript, JIT tracing) are brittle, often failing on dynamic control flow or requiring significant user effort to convert models. The challenge is to combine the flexibility of eager mode with the performance of graph compilation without sacrificing usability.

## Key Ideas

- TorchDynamo: A Python-level JIT compiler that dynamically modifies Python bytecode before execution to capture PyTorch operations into an FX graph, handling arbitrary Python control flow.
- TorchInductor: A default compiler backend that lowers FX graphs to efficient kernels using OpenAI's Triton for GPUs and C++ for CPUs.
- Extensible backend interface: TorchDynamo supports multiple backends (e.g., NVFuser, XLA) beyond TorchInductor.
- Minimal overhead: TorchDynamo adds negligible overhead for graphs it cannot capture, falling back to eager execution.

## System Design

TorchDynamo intercepts Python execution by patching frame evaluation; it analyzes bytecode to identify PyTorch operations, extracts them into an FX graph, and compiles the graph via a chosen backend. TorchInductor takes the FX graph, applies optimizations (e.g., fusion, loop reordering), and generates Triton kernels (GPU) or C++ code (CPU). The compiled graph is cached and reused. If compilation fails, execution falls back to eager mode.

## Evaluation

Evaluated on 180+ real-world models (vision, NLP, speech, etc.) on NVIDIA A100 GPU. TorchDynamo captures graphs with >99% success rate. TorchInductor achieves geometric mean speedup of 2.27× for inference and 1.41× for training over eager PyTorch, outperforming six other compilers (including TensorFlow XLA, TorchScript, and TVM).

## Takeaways

- Dynamic bytecode transformation enables robust graph capture for arbitrary Python code, solving a key limitation of prior static approaches.
- TorchInductor's use of Triton allows leveraging a high-level kernel language for GPU optimization.
- The extensible backend design makes TorchDynamo a versatile platform for compiler research.
- Significant speedups are achievable without model changes, lowering the barrier for users.

## Related Work

Positioned against prior PyTorch compilation efforts (TorchScript, JIT tracing) which are less robust. Also compared to TensorFlow's XLA and TVM, which require static graphs or separate compilation pipelines. TorchDynamo's dynamic approach is novel in combining Python-level JIT with graph extraction.

## Open Questions

- How does TorchDynamo handle very dynamic models (e.g., with frequent graph changes)?
- Can TorchInductor's Triton backend match hand-tuned kernels for specific operations?
- Extending support to more hardware (e.g., AMD GPUs, custom accelerators) via Triton.
- Reducing compilation time for large models to improve user experience.
