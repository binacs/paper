# GPU Training

Systems for training and serving large models on GPU clusters: parallelism, memory, communication, compilers, cluster-level infrastructure and reliability, inference serving, and RL training systems.

**Contents:** [Training infrastructure at scale](#training-infrastructure-at-scale) · [Parallelism strategies](#parallelism-strategies) · [Memory](#memory) · [Communication](#communication) · [Compilers & kernels](#compilers--kernels) · [Scheduling for DL clusters](#scheduling-for-dl-clusters) · [Inference serving](#inference-serving) · [RL training systems](#rl-training-systems) · [Other](#other) · [Auto-analyzed papers](#auto-analyzed-papers)

Entry format: **Paper** (title link — institution · venue year), **Why** (one sentence), and Code / Blog / Analysis links when they exist. Venue years are the conference edition (not the arXiv year). Within a section: newest first.

## Training infrastructure at scale

### * MegaScale

- **Paper:** [MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs](https://arxiv.org/abs/2402.15627) — ByteDance, Peking University · NSDI 2024
- **Why:** Full-stack account of training on >10k GPUs: algorithm–system co-design, communication overlap, and the diagnosis / fault-tolerance tooling that keeps MFU high over weeks.

### Acme (LLM development characterization)

- **Paper:** [Characterization of Large Language Model Development in the Datacenter](https://arxiv.org/abs/2403.07648) — Shanghai AI Lab et al. · NSDI 2024
- **Why:** Six-month trace of an LLM development cluster: workload mix, failure causes, and fault-tolerant pretraining / evaluation-scheduling fixes.

## Parallelism strategies

- [Reducing Activation Recomputation in Large Transformer Models](nvidia-megatron-activation-recomputation/2205.05198-reducing-activation-recomputation-in-large-transformer-models.md) — NVIDIA · MLSys 2023 — sequence parallelism plus selective recomputation in Megatron-LM.
- [PipeDream: Generalized Pipeline Parallelism for DNN Training](pipedream/3fd7c9b-pipedream-generalized-pipeline-parallelism-for-dnn-training.md) — Microsoft, CMU, Stanford · SOSP 2019 — 1F1B pipeline schedule with weight stashing.

## Memory

- [ZeRO-Offload: Democratizing Billion-Scale Model Training](zero-offload/2101.06840-zero-offload-democratizing-billion-scale-model-training.md) — Microsoft, UC Merced · ATC 2021 — offloads optimizer state and update to CPU.

## Communication

- [Scaling Distributed Machine Learning with In-Network Aggregation (SwitchML)](switchml/1903.06701-scaling-distributed-machine-learning-with-in-network-aggregation.md) — KAUST, Microsoft et al. · NSDI 2021 — all-reduce aggregation on programmable switches.

## Compilers & kernels

- [PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation](pytorch-torchdynamo-torchinductor/a509670-pytorch-2-faster-machine-learning-through-dynamic-python.md) — Meta et al. · ASPLOS 2024 — TorchDynamo graph capture + TorchInductor codegen.
- [Ansor: Generating High-Performance Tensor Programs for Deep Learning](ansor/2006.06762-ansor-generating-high-performance-tensor-programs-for-deep.md) — UC Berkeley et al. · OSDI 2020 — search-based tensor program generation in TVM.

## Scheduling for DL clusters

- [Gandiva: Introspective Cluster Scheduling for Deep Learning](microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md) — Microsoft · OSDI 2018 — time-slicing, migration and packing exploiting DL job predictability.

See also [orchestration-scheduling → ML-specific](../orchestration-scheduling/README.md#ml-specific).

## Inference serving

- [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving](distserve/2401.09670-distserve-disaggregating-prefill-and-decoding-for-goodput-optimized.md) — Peking University, UCSD · OSDI 2024 — prefill/decode disaggregation sized for per-phase SLOs.
- [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve](microsoft-sarathi-serve/2403.02310-taming-throughput-latency-tradeoff-in-llm-inference-with.md) — Microsoft, Georgia Tech · OSDI 2024 — chunked prefill and stall-free batching.
- [Efficient Memory Management for LLM Serving with PagedAttention (vLLM)](vllm/2309.06180-efficient-memory-management-for-large-language-model-serving.md) — UC Berkeley et al. · SOSP 2023 — paged KV cache.
- [Efficiently Scaling Transformer Inference](misc/2211.05102-efficiently-scaling-transformer-inference.md) — Google · MLSys 2023 — partitioning analysis for large-model inference on TPUs.
- [Orca: A Distributed Serving System for Transformer-Based Generative Models](orca/9d7a756-orca-a-distributed-serving-system-for-transformer-based.md) — Seoul National University, FriendliAI · OSDI 2022 — iteration-level (continuous) batching.
- [AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration](awq-tinychat/2306.00978-awq-activation-aware-weight-quantization-for-on-device.md) — MIT et al. · MLSys 2024 — 4-bit weight-only quantization guided by activation salience.

## RL training systems

- [HybridFlow: A Flexible and Efficient RLHF Framework (verl)](hybridflow/2409.19256-hybridflow-a-flexible-and-efficient-rlhf-framework.md) — ByteDance, HKU · EuroSys 2025 — hybrid single/multi-controller dataflow for RLHF.

## Other

- [A System for Massively Parallel Hyperparameter Tuning (ASHA)](determined-asha/1810.05934-a-system-for-massively-parallel-hyperparameter-tuning.md) — CMU, Determined AI et al. · MLSys 2020.
- [Federated Optimization in Heterogeneous Networks (FedProx)](fedprox/1812.06127-federated-optimization-in-heterogeneous-networks.md) — CMU et al. · MLSys 2020.

---

## Auto-analyzed papers

_Entries below this line are managed by `paper-bot`. Manual edits are fine; just keep them above the marker._


## Federated Optimization in Heterogeneous Networks (Conference on Machine Learning and Systems 2018)

Paper link: [Federated Optimization in Heterogeneous Networks](https://arxiv.org/abs/1812.06127)

Analysis: [fedprox/1812.06127-federated-optimization-in-heterogeneous-networks.md](fedprox/1812.06127-federated-optimization-in-heterogeneous-networks.md)


## Efficient Memory Management for Large Language Model Serving with PagedAttention (Symposium on Operating Systems Principles 2023)

Paper link: [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)

Analysis: [vllm/2309.06180-efficient-memory-management-for-large-language-model-serving.md](vllm/2309.06180-efficient-memory-management-for-large-language-model-serving.md)


## HybridFlow: A Flexible and Efficient RLHF Framework (European Conference on Computer Systems 2024)

Paper link: [HybridFlow: A Flexible and Efficient RLHF Framework](https://arxiv.org/abs/2409.19256)

Analysis: [hybridflow/2409.19256-hybridflow-a-flexible-and-efficient-rlhf-framework.md](hybridflow/2409.19256-hybridflow-a-flexible-and-efficient-rlhf-framework.md)


## AWQ: Activation-aware Weight Quantization for On-Device LLM Compression and Acceleration (Conference on Machine Learning and Systems 2023)

Paper link: [AWQ: Activation-aware Weight Quantization for On-Device LLM Compression and Acceleration](https://arxiv.org/abs/2306.00978)

Analysis: [awq-tinychat/2306.00978-awq-activation-aware-weight-quantization-for-on-device.md](awq-tinychat/2306.00978-awq-activation-aware-weight-quantization-for-on-device.md)


## PipeDream: generalized pipeline parallelism for DNN training (Symposium on Operating Systems Principles 2019)

Paper link: [PipeDream: generalized pipeline parallelism for DNN training](https://www.semanticscholar.org/paper/3fd7c9ba742dd2b435afa75217847e5087e2f2a8)

Analysis: [pipedream/3fd7c9b-pipedream-generalized-pipeline-parallelism-for-dnn-training.md](pipedream/3fd7c9b-pipedream-generalized-pipeline-parallelism-for-dnn-training.md)


## PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation (International Conference on Architectural Support for Programming Languages and Operating Systems 2024)

Paper link: [PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation](https://www.semanticscholar.org/paper/a509670659e8b054e2b7d1b6f8a0bc722398fa62)

Analysis: [pytorch-torchdynamo-torchinductor/a509670-pytorch-2-faster-machine-learning-through-dynamic-python.md](pytorch-torchdynamo-torchinductor/a509670-pytorch-2-faster-machine-learning-through-dynamic-python.md)


## Orca: A Distributed Serving System for Transformer-Based Generative Models (USENIX Symposium on Operating Systems Design and Implementation 2022)

Paper link: [Orca: A Distributed Serving System for Transformer-Based Generative Models](https://www.semanticscholar.org/paper/9d7a75601e0e50dd68d40cfb8ef0e891dad797a6)

Analysis: [orca/9d7a756-orca-a-distributed-serving-system-for-transformer-based.md](orca/9d7a756-orca-a-distributed-serving-system-for-transformer-based.md)


## DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving (USENIX Symposium on Operating Systems Design and Implementation 2024)

Paper link: [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving](https://arxiv.org/abs/2401.09670)

Analysis: [distserve/2401.09670-distserve-disaggregating-prefill-and-decoding-for-goodput-optimized.md](distserve/2401.09670-distserve-disaggregating-prefill-and-decoding-for-goodput-optimized.md)


## Efficiently Scaling Transformer Inference (Conference on Machine Learning and Systems 2022)

Paper link: [Efficiently Scaling Transformer Inference](https://arxiv.org/abs/2211.05102)

Analysis: [misc/2211.05102-efficiently-scaling-transformer-inference.md](misc/2211.05102-efficiently-scaling-transformer-inference.md)


## ZeRO-Offload: Democratizing Billion-Scale Model Training (USENIX Annual Technical Conference 2021)

Paper link: [ZeRO-Offload: Democratizing Billion-Scale Model Training](https://arxiv.org/abs/2101.06840)

Analysis: [zero-offload/2101.06840-zero-offload-democratizing-billion-scale-model-training.md](zero-offload/2101.06840-zero-offload-democratizing-billion-scale-model-training.md)


## Gandiva: Introspective Cluster Scheduling for Deep Learning (USENIX Symposium on Operating Systems Design and Implementation 2018)

Paper link: [Gandiva: Introspective Cluster Scheduling for Deep Learning](https://www.semanticscholar.org/paper/0606676f16d581fa453f6b7b8a14fc7c4af8d025)

Analysis: [microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md](microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md)


## Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve (USENIX Symposium on Operating Systems Design and Implementation 2024)

Paper link: [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve](https://arxiv.org/abs/2403.02310)

Analysis: [microsoft-sarathi-serve/2403.02310-taming-throughput-latency-tradeoff-in-llm-inference-with.md](microsoft-sarathi-serve/2403.02310-taming-throughput-latency-tradeoff-in-llm-inference-with.md)


## Ansor : Generating High-Performance Tensor Programs for Deep Learning (USENIX Symposium on Operating Systems Design and Implementation 2020)

Paper link: [Ansor : Generating High-Performance Tensor Programs for Deep Learning](https://arxiv.org/abs/2006.06762)

Analysis: [ansor/2006.06762-ansor-generating-high-performance-tensor-programs-for-deep.md](ansor/2006.06762-ansor-generating-high-performance-tensor-programs-for-deep.md)


## Scaling Distributed Machine Learning with In-Network Aggregation (Symposium on Networked Systems Design and Implementation 2019)

Paper link: [Scaling Distributed Machine Learning with In-Network Aggregation](https://arxiv.org/abs/1903.06701)

Analysis: [switchml/1903.06701-scaling-distributed-machine-learning-with-in-network-aggregation.md](switchml/1903.06701-scaling-distributed-machine-learning-with-in-network-aggregation.md)


## A System for Massively Parallel Hyperparameter Tuning (Conference on Machine Learning and Systems 2018)

Paper link: [A System for Massively Parallel Hyperparameter Tuning](https://arxiv.org/abs/1810.05934)

Analysis: [determined-asha/1810.05934-a-system-for-massively-parallel-hyperparameter-tuning.md](determined-asha/1810.05934-a-system-for-massively-parallel-hyperparameter-tuning.md)


## Reducing Activation Recomputation in Large Transformer Models (Conference on Machine Learning and Systems 2022)

Paper link: [Reducing Activation Recomputation in Large Transformer Models](https://arxiv.org/abs/2205.05198)

Analysis: [nvidia-megatron-activation-recomputation/2205.05198-reducing-activation-recomputation-in-large-transformer-models.md](nvidia-megatron-activation-recomputation/2205.05198-reducing-activation-recomputation-in-large-transformer-models.md)

<!-- paper-bot:end -->
