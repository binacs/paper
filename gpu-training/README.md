# GPU Training

Systems for training and serving large models on GPU clusters: parallelism, memory, communication, compilers, cluster-level infrastructure and reliability, inference serving, and RL training systems.

**Contents:** [Training infrastructure at scale](#training-infrastructure-at-scale) · [Reliability & checkpointing](#reliability-checkpointing--fault-tolerance) · [Parallelism strategies](#parallelism-strategies) · [Memory](#memory) · [Communication](#communication) · [Compilers & kernels](#compilers--kernels) · [Scheduling for DL clusters](#scheduling-for-dl-clusters) · [Inference serving](#inference-serving) · [RL training systems](#rl-training-systems) · [Other](#other) · [Auto-analyzed papers](#auto-analyzed-papers)

Entry format: **Paper** (title link — institution · venue year), **Why** (one sentence), and Code / Blog / Analysis links when they exist. Venue years are the conference edition (not the arXiv year). Within a section: newest first.

## Training infrastructure at scale

### * MegaScale

- **Paper:** [MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs](https://arxiv.org/abs/2402.15627) — ByteDance, Peking University · NSDI 2024
- **Why:** Full-stack account of training on >10k GPUs: algorithm–system co-design, communication overlap, and the diagnosis / fault-tolerance tooling that keeps MFU high over weeks.
- **Deep read:** [deep-read note](bytedance-megascale/2402.15627-megascale-scaling-large-language-model-training-to-more.md)

### * Llama 3 infrastructure

- **Paper:** [The Llama 3 Herd of Models](https://arxiv.org/abs/2407.21783) — Meta · arXiv 2024 (infrastructure and reliability sections)
- **Why:** The most detailed public account of a 16K-H100 pretraining run: 4D parallelism, the network, and a categorised list of every job interruption during the run.
- **Deep read:** [deep-read note](meta-llama3-infra/2407.21783-the-llama-3-herd-of-models-infrastructure.md)

### * DeepSeek-V3

- **Paper:** [DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437) — DeepSeek-AI · arXiv 2024
- **Paper:** [Insights into DeepSeek-V3: Scaling Challenges and Reflections on Hardware for AI Architectures](https://arxiv.org/abs/2505.09343) — DeepSeek-AI · ISCA 2025
- **Why:** FP8 mixed-precision training, DualPipe compute/communication overlap and a multi-plane network show how far co-design can push cost per token on constrained hardware; the ISCA paper turns that into a hardware wish-list.
- **Code:** [deepseek-ai/DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3)
- **Deep read:** [deep-read note](deepseek-v3/2505.09343-insights-into-deepseek-v3-scaling-challenges-and-reflections.md)

### Acme (LLM development characterization)

- **Paper:** [Characterization of Large Language Model Development in the Datacenter](https://arxiv.org/abs/2403.07648) — Shanghai AI Lab et al. · NSDI 2024
- **Why:** Six-month trace of an LLM development cluster: workload mix, failure causes, and fault-tolerant pretraining / evaluation-scheduling fixes.
- **Code:** [InternLM/AcmeTrace](https://github.com/InternLM/AcmeTrace)
- **Deep read:** [deep-read note](acme/2403.07648-characterization-of-large-language-model-development-in-the.md)

Also: [MegaScale-MoE: Large-Scale Communication-Efficient Training of Mixture-of-Experts Models in Production](https://arxiv.org/abs/2505.11432) — ByteDance Seed, Peking University · arXiv 2025 — MoE-specific parallelism, overlap and compression; why: MoE all-to-all, not dense compute, is now the scaling bottleneck in production training.

## Reliability, checkpointing & fault tolerance

- [Robust LLM Training Infrastructure at ByteDance (ByteRobust)](https://arxiv.org/abs/2509.16293) — ByteDance Seed, HKU · SOSP 2025 — detects, localises and recovers from faults in large training jobs · [deep read](bytedance-byterobust/2509.16293-robust-llm-training-infrastructure-at-bytedance.md); why: at 10k+ GPUs, effective training time is decided by fault handling, not peak MFU.
- [Understanding Stragglers in Large Model Training Using What-if Analysis](https://arxiv.org/abs/2505.05713) — NYU, ByteDance Seed, ZJU · OSDI 2025 — trace-driven what-if simulation of how often stragglers occur and what causes them; why: first production-scale quantification of a problem most teams only see anecdotally.
- [ByteCheckpoint: A Unified Checkpointing System for Large Foundation Model Development](https://arxiv.org/abs/2407.20143) — HKU, ByteDance · NSDI 2025 — parallelism-agnostic checkpoint format with automatic resharding · [code](https://github.com/ByteDance-Seed/ByteCheckpoint) · [deep read](bytedance-bytecheckpoint/2407.20143-bytecheckpoint-a-unified-checkpointing-system-for-large-foundation.md); why: checkpoints must survive changes of parallel layout between pretraining, evaluation and fine-tuning.
- [GEMINI: Fast Failure Recovery in Distributed Training with In-Memory Checkpoints](https://dl.acm.org/doi/10.1145/3600006.3613145) — Rice, AWS · SOSP 2023 — checkpoints to peer CPU memory with traffic scheduling that hides the transfer; why: makes per-iteration-scale checkpoint frequency practical.
- [Oobleck: Resilient Distributed Training of Large Models Using Pipeline Templates](https://arxiv.org/abs/2309.08125) — UMich, AWS, PKU · SOSP 2023 — precomputed pipeline templates let hybrid-parallel jobs reconfigure after failures without restart · [code](https://github.com/SymbioticLab/Oobleck) · [deep read](oobleck/2309.08125-oobleck-resilient-distributed-training-of-large-models-using.md); why: shows the alternative to checkpoint-restart.

## Parallelism strategies

- [PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel](https://arxiv.org/abs/2304.11277) — Meta · VLDB 2023 — production lessons of PyTorch's ZeRO-3-style sharding; why: the default way most teams now shard large models.
- [Reducing Activation Recomputation in Large Transformer Models](nvidia-megatron-activation-recomputation/2205.05198-reducing-activation-recomputation-in-large-transformer-models.md) — NVIDIA · MLSys 2023 — sequence parallelism plus selective recomputation in Megatron-LM.
- [Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM](https://arxiv.org/abs/2104.04473) — NVIDIA, MSR, Stanford · SC 2021 — composes tensor, pipeline and data parallelism (PTD-P) with an interleaved schedule · [code](https://github.com/NVIDIA/Megatron-LM); why: the reference 3D-parallel recipe that MegaScale and Llama 3 build on.
- [PipeDream: Generalized Pipeline Parallelism for DNN Training](pipedream/3fd7c9b-pipedream-generalized-pipeline-parallelism-for-dnn-training.md) ([paper](https://dl.acm.org/doi/10.1145/3341301.3359646)) — Microsoft, CMU, Stanford · SOSP 2019 — 1F1B pipeline schedule with weight stashing.

## Memory

- [ZeRO-Offload: Democratizing Billion-Scale Model Training](zero-offload/2101.06840-zero-offload-democratizing-billion-scale-model-training.md) — Microsoft, UC Merced · ATC 2021 — offloads optimizer state and update to CPU.

## Communication

- [RDMA over Ethernet for Distributed AI Training at Meta Scale](https://dl.acm.org/doi/10.1145/3651890.3672233) — Meta · SIGCOMM 2024 — design and operation of Meta's RoCEv2 training backend (topology, routing, congestion control); why: a rare production report on running RDMA over Ethernet for GPU training at scale.
- [Alibaba HPN: A Data Center Network for Large Language Model Training](https://dl.acm.org/doi/10.1145/3651890.3672265) — Alibaba Cloud · SIGCOMM 2024 — two-tier, dual-plane Ethernet fabric that avoids ECMP hash polarisation and single-ToR failures; why: shows how LLM traffic patterns change datacenter network design.
- [Scaling Distributed Machine Learning with In-Network Aggregation (SwitchML)](switchml/1903.06701-scaling-distributed-machine-learning-with-in-network-aggregation.md) ([paper](https://www.usenix.org/conference/nsdi21/presentation/sapio)) — KAUST, Microsoft et al. · NSDI 2021 — all-reduce aggregation on programmable switches.

## Compilers & kernels

- [FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision](https://arxiv.org/abs/2407.08608) — Colfax, Meta, NVIDIA, Princeton, Together AI · NeurIPS 2024 — Hopper-specific attention using warp specialisation, GEMM/softmax overlap and FP8 · [code](https://github.com/Dao-AILab/flash-attention); why: kernels must now be written for asynchronous tensor-core hardware to reach peak.
- [FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning](https://arxiv.org/abs/2307.08691) — Princeton, Stanford · ICLR 2024 — better work partitioning across thread blocks and warps; why: the attention kernel behind most training and serving stacks.
- [PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation](pytorch-torchdynamo-torchinductor/a509670-pytorch-2-faster-machine-learning-through-dynamic-python.md) ([paper](https://dl.acm.org/doi/10.1145/3620665.3640366)) — Meta et al. · ASPLOS 2024 — TorchDynamo graph capture + TorchInductor codegen.
- [Ansor: Generating High-Performance Tensor Programs for Deep Learning](ansor/2006.06762-ansor-generating-high-performance-tensor-programs-for-deep.md) — UC Berkeley et al. · OSDI 2020 — search-based tensor program generation in TVM.

## Scheduling for DL clusters

- [Gandiva: Introspective Cluster Scheduling for Deep Learning](microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md) ([paper](https://www.usenix.org/conference/osdi18/presentation/xiao)) — Microsoft · OSDI 2018 — time-slicing, migration and packing exploiting DL job predictability.

See also [orchestration-scheduling → ML-specific](../orchestration-scheduling/README.md#ml-specific).

## Inference serving

### Disaggregated & KV-cache-centric serving

- [Mooncake: Trading More Storage for Less Computation — A KVCache-centric Architecture for Serving LLM Chatbot](https://www.usenix.org/conference/fast25/presentation/qin) — Moonshot AI, Tsinghua · FAST 2025 — Kimi's serving platform built around a distributed KV-cache pool in CPU DRAM / SSD, with KV-aware scheduling and overload rejection · [code](https://github.com/kvcache-ai/Mooncake) · [deep read](moonshot-mooncake/2407.00079-mooncake-a-kvcache-centric-disaggregated-architecture-for-llm.md); why: treats KV cache as a first-class distributed storage tier.
- [MegaScale-Infer: Efficient Mixture-of-Experts Model Serving with Disaggregated Expert Parallelism](https://arxiv.org/abs/2504.02263) — ByteDance Seed, PKU · SIGCOMM 2025 — attention and experts on separate GPU pools with ping-pong micro-batch pipelining · [deep read](bytedance-megascale-infer/2504.02263-megascale-infer-serving-mixture-of-experts-at-scale-with.md); why: disaggregation applied inside the model, not only across prefill/decode.
- [Introducing NVIDIA Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models) — NVIDIA · Blog 2025 — open-source disaggregated serving with KV-aware routing and KV offload · [code](https://github.com/ai-dynamo/dynamo); why: the research ideas above packaged as a vendor-supported framework.
- [Splitwise: Efficient Generative LLM Inference Using Phase Splitting](https://arxiv.org/abs/2311.18677) — Microsoft, UW · ISCA 2024 — prefill and decode on separate machine pools, possibly different hardware · [code](https://github.com/Mutinifni/splitwise-sim) · [deep read](microsoft-splitwise/2311.18677-splitwise-efficient-generative-llm-inference-using-phase-splitting.md); why: makes the cost/power case for heterogeneous prefill vs decode hardware.
- [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving](distserve/2401.09670-distserve-disaggregating-prefill-and-decoding-for-goodput-optimized.md) — Peking University, UCSD · OSDI 2024 — prefill/decode disaggregation sized for per-phase SLOs · [deep read](distserve/2401.09670-distserve-deep-read.md).
- [Inference without Interference: Disaggregate LLM Inference for Mixed Downstream Workloads (TetriInfer)](https://arxiv.org/abs/2401.11181) — Huawei Cloud, ICT CAS · arXiv 2024 — chunked prefill, disaggregation and output-length prediction for decode scheduling; why: targets interference between heterogeneous request types.

### Batching & request scheduling

- [Llumnix: Dynamic Scheduling for Large Language Model Serving](https://www.usenix.org/conference/osdi24/presentation/sun-biao) — Alibaba · OSDI 2024 — live-migrates requests and their KV cache between instances · [code](https://github.com/AlibabaPAI/llumnix) · [deep read](alibaba-llumnix/2406.03243-llumnix-dynamic-scheduling-for-large-language-model-serving.md); why: brings VM-style live migration to LLM load balancing and priority isolation.
- [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve](microsoft-sarathi-serve/2403.02310-taming-throughput-latency-tradeoff-in-llm-inference-with.md) — Microsoft, Georgia Tech · OSDI 2024 — chunked prefill and stall-free batching · [deep read](microsoft-sarathi-serve/2403.02310-sarathi-serve-deep-read.md).
- [DeepSpeed-FastGen: High-throughput Text Generation for LLMs via MII and DeepSpeed-Inference](https://arxiv.org/abs/2401.08671) — Microsoft · arXiv 2024 — Dynamic SplitFuse fills a fixed per-step token budget · [code](https://github.com/microsoft/DeepSpeed-MII); why: independent arrival at the chunked-prefill idea in a production library.
- [SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills](https://arxiv.org/abs/2308.16369) — MSR India, Georgia Tech · arXiv 2023 — the original chunked-prefill paper behind Sarathi-Serve.
- [Orca: A Distributed Serving System for Transformer-Based Generative Models](orca/9d7a756-orca-a-distributed-serving-system-for-transformer-based.md) ([paper](https://www.usenix.org/conference/osdi22/presentation/yu)) — Seoul National University, FriendliAI · OSDI 2022 — iteration-level (continuous) batching.

### Runtimes, memory & cluster platforms

- [Aegaeon: Effective GPU Pooling for Concurrent LLM Serving on the Market](https://doi.org/10.1145/3731569.3764815) — Alibaba, PKU · SOSP 2025 — token-level auto-scaling that multiplexes many models on shared GPUs · [deep read](alibaba-aegaeon/sosp25-aegaeon-effective-gpu-pooling-for-concurrent-llm-serving.md); why: addresses the long tail of rarely used models in a model marketplace.
- [DynamoLLM: Designing LLM Inference Clusters for Performance and Energy Efficiency](https://arxiv.org/abs/2408.00741) — UIUC, Microsoft · HPCA 2025 — reconfigures instance count, parallelism and GPU frequency against SLOs; why: energy is becoming a first-class serving objective.
- [AIBrix: Towards Scalable, Cost-Effective Large Language Model Inference Infrastructure](https://arxiv.org/abs/2504.03648) — ByteDance et al. · arXiv 2025 — Kubernetes-native control plane for vLLM (LoRA management, LLM-aware routing and autoscaling, distributed KV cache) · [code](https://github.com/vllm-project/aibrix); why: the cluster layer above a single-engine server.
- [SGLang: Efficient Execution of Structured Language Model Programs](https://arxiv.org/abs/2312.07104) — Stanford, UC Berkeley et al. · NeurIPS 2024 — RadixAttention prefix reuse and fast constrained decoding · [code](https://github.com/sgl-project/sglang); why: prefix-cache reuse matters most for agent and multi-call workloads.
- [Efficient Memory Management for LLM Serving with PagedAttention (vLLM)](vllm/2309.06180-efficient-memory-management-for-large-language-model-serving.md) — UC Berkeley et al. · SOSP 2023 — paged KV cache.

### Model-level speedups

- [AWQ: Activation-aware Weight Quantization for On-Device LLM Compression and Acceleration](awq-tinychat/2306.00978-awq-activation-aware-weight-quantization-for-on-device.md) — MIT et al. · MLSys 2024 — 4-bit weight-only quantization guided by activation salience.
- [Efficiently Scaling Transformer Inference](misc/2211.05102-efficiently-scaling-transformer-inference.md) — Google · MLSys 2023 — partitioning analysis for large-model inference on TPUs.
- [Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) — Google Research · ICML 2023 — draft-then-verify decoding that exactly preserves the target distribution; why: the basis of most current decode-latency optimisations.

## RL training systems

- [AReaL: A Large-Scale Asynchronous Reinforcement Learning System for Language Reasoning](https://arxiv.org/abs/2505.24298) — Tsinghua IIIS, Ant Research, HKUST · NeurIPS 2025 — fully asynchronous rollout and training with bounded staleness · [code](https://github.com/areal-project/AReaL) · [deep read](areal/2505.24298-areal-a-large-scale-asynchronous-reinforcement-learning-system.md); why: removes the synchronous-generation barrier that dominates RL wall-clock time.
- [StreamRL: Scalable, Heterogeneous, and Elastic RL for LLMs with Disaggregated Stream Generation](https://arxiv.org/abs/2504.15930) — PKU, StepFun · arXiv 2025 — rollout and training on separate, possibly heterogeneous clusters with streamed samples · [deep read](streamrl/2504.15930-streamrl-scalable-heterogeneous-and-elastic-rl-for-llms.md); why: disaggregation applied to RL.
- [HybridFlow: A Flexible and Efficient RLHF Framework (verl)](hybridflow/2409.19256-hybridflow-a-flexible-and-efficient-rlhf-framework.md) — ByteDance, HKU · EuroSys 2025 — hybrid single/multi-controller dataflow for RLHF · [code](https://github.com/volcengine/verl) · [deep read](hybridflow/2409.19256-hybridflow-deep-read.md).
- [Optimizing RLHF Training for Large Language Models with Stage Fusion (RLHFuse)](https://www.usenix.org/conference/nsdi25/presentation/zhong) — PKU, StepFun · NSDI 2025 — fuses generation with inference per sample and overlaps actor/critic pipelines; why: attacks long-tail rollouts and pipeline bubbles directly.
- [ReaL: Efficient RLHF Training of Large Language Models with Parameter Reallocation](https://arxiv.org/abs/2406.14088) — Tsinghua IIIS et al. · MLSys 2025 — redistributes parameters between RLHF stages so each runs with its own parallel layout · [code](https://github.com/openpsi-project/ReaLHF).
- [Kimi k1.5: Scaling Reinforcement Learning with LLMs](https://arxiv.org/abs/2501.12599) — Moonshot AI · arXiv 2025 — §2.6 covers RL infrastructure: partial rollouts, hybrid train/inference deployment and a code sandbox; why: a production RL stack described end to end.
- [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948) — DeepSeek-AI · Nature 2025 — large-scale GRPO with rule-based rewards; why: the workload that made RL-systems efficiency a first-order concern.
- [OpenRLHF: An Easy-to-use, Scalable and High-performance RLHF Framework](https://arxiv.org/abs/2405.11143) — OpenRLHF team et al. · arXiv 2024 — Ray-based placement of actor/critic/reward/reference with vLLM rollouts · [code](https://github.com/OpenRLHF/OpenRLHF).

See also [agent-sandbox](../agent-sandbox/README.md) for the execution sandboxes that RL rollouts and coding agents run in.

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
