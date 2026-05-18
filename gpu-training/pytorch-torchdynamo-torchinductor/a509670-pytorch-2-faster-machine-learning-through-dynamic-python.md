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
citations: 1117
abs_url: https://www.semanticscholar.org/paper/a509670659e8b054e2b7d1b6f8a0bc722398fa62
pdf_url: ''
analyzed_at: '2026-05-18T10:00:56+00:00'
model: deepseek-chat
doi: 10.1145/3620665.3640366
---

# PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation

## TL;DR

PyTorch 2 introduces TorchDynamo, a Python-level JIT compiler that dynamically transforms bytecode to extract FX graphs for compilation, and TorchInductor, a default backend that compiles to Triton (GPU) and C++ (CPU), achieving 2.27× inference and 1.41× training speedups on A100 across 180+ models.

## Problem & Motivation

Deep learning frameworks like PyTorch offer eager execution for flexibility, but this prevents global graph-level optimizations that compilers can provide. Prior approaches to graph compilation either required user annotations (e.g., torch.jit.trace) or static graph definitions (e.g., TensorFlow), sacrificing Python dynamism. The challenge is to enable robust graph capture and compilation without breaking Python's dynamic features or requiring significant code changes.

## Key Ideas

- TorchDynamo: A Python-level JIT compiler that intercepts and modifies Python bytecode at runtime to extract sequences of PyTorch operations into an FX graph.
- Dynamic bytecode transformation: TorchDynamo rewrites bytecode to replace PyTorch operations with graph-building calls, enabling graph capture even for dynamic control flow.
- Extensible backend interface: TorchDynamo supports multiple backends; TorchInductor is the default.
- TorchInductor: Translates FX graphs into efficient GPU code via OpenAI's Triton and CPU code via C++ with loop-level optimizations.

## System Design

TorchDynamo operates as a Python-level JIT compiler: it hooks into the Python frame execution, analyzes bytecode, and dynamically transforms it to record PyTorch operations into an FX graph. The graph is then passed to a backend (e.g., TorchInductor) for compilation. TorchInductor lowers the FX graph to intermediate representations (IR) and generates Triton kernels for GPUs or C++ code for CPUs, applying fusion, loop optimizations, and memory planning. The compiled artifacts are cached and reused.

## Evaluation

Evaluated on 180+ real-world models (vision, NLP, speech, etc.) on NVIDIA A100 GPU. TorchDynamo captures graphs with near-zero overhead and higher robustness than prior approaches (e.g., TorchScript tracing). TorchInductor achieves geometric mean speedups of 2.27× for inference and 1.41× for training over eager PyTorch, outperforming six other compilers (including XLA, TensorRT, and TVM).

## Takeaways

- Dynamic bytecode transformation enables robust graph capture in eager-mode frameworks without sacrificing Python flexibility.
- TorchInductor's use of Triton allows leveraging a high-level GPU programming language for efficient kernel generation.
- The system achieves significant speedups across a wide range of models, demonstrating practical impact.
- The extensible backend design allows community contributions and specialization.

## Related Work

Positioned against prior PyTorch compilation efforts (TorchScript, torch.jit.trace/script) which required static graphs or user annotations. Also compared to other deep learning compilers like XLA (JAX/TensorFlow), TensorRT, TVM, and MLIR-based approaches. TorchDynamo's key differentiator is operating at the Python bytecode level rather than requiring a separate graph representation.

## Open Questions

- How does TorchDynamo handle extremely dynamic Python patterns (e.g., data-dependent control flow that changes per iteration)?
- Can TorchInductor's Triton backend match or exceed hand-tuned CUDA kernels for specific operations?
- What is the memory overhead of graph caching and bytecode transformation for very large models?
- How will the system evolve to support new hardware (e.g., AMD GPUs, custom accelerators) beyond NVIDIA and CPU?
