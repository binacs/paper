# paper

A curated reading index for **large-scale cluster scheduling, GPU training / inference systems, agent sandboxes, and the distributed-systems classics underneath them** — papers and official engineering blogs only, organised by topic, with short "why it matters" lines and deep-read notes for the most important ones.

## Topics

| Topic | What's inside | Entries |
|---|---|---|
| [orchestration-scheduling](orchestration-scheduling/README.md) | Cluster managers (Borg, Twine, Gödel, MAST …), two-level / shared-state / distributed schedulers, ML-specific scheduling (Tiresias, Pollux, Sia …), Kubernetes batch (Kueue, Volcano), node-level isolation & QoS | 39 |
| [gpu-training](gpu-training/README.md) | LLM training infrastructure (MegaScale, Llama 3, DeepSeek-V3), reliability & checkpointing, parallelism, communication, kernels, inference serving (disaggregation, KV cache, batching), RL training systems | 53 |
| [distributed-system](distributed-system/README.md) | GFS, MapReduce, Bigtable, Dynamo, Spanner, F1 …, datacenter networking, memory disaggregation, serverless | 18 |
| [agent-sandbox](agent-sandbox/README.md) | MicroVMs and user-space kernels (Firecracker, gVisor), fast-start techniques, agent execution platforms and benchmarks | 11 |
| [ai](ai/README.md) | Ilya Sutskever's "30u30" foundational reading list | 27 |
| [profile](profile/README.md) | Repo owner's academic profiles | — |

Counts are curated papers / posts above each README's `Auto-analyzed papers` section (bot-added papers are also linked from the curated sections).

## Reading paths

**Cluster scheduling**

1. *Start here:* [Borg, Omega, and Kubernetes](orchestration-scheduling/README.md#overviews) → [Omega](orchestration-scheduling/README.md#google-omega) (the scheduler taxonomy)
2. *Classics:* [Borg](orchestration-scheduling/README.md#google-borg) → [Mesos](orchestration-scheduling/README.md#apache-mesos) / [YARN](orchestration-scheduling/README.md#apache-yarn) → [Sparrow](orchestration-scheduling/README.md#uc-berkeley-sparrow) → [DRF](orchestration-scheduling/README.md#fairness)
3. *ML clusters:* [Philly trace](orchestration-scheduling/README.md#ml-specific) → [Tiresias](orchestration-scheduling/README.md#tiresias) → [Pollux](orchestration-scheduling/README.md#pollux) → [Sia](orchestration-scheduling/README.md#sia)
4. *Frontier:* [Twine](orchestration-scheduling/README.md#meta-twine) → [Gödel](orchestration-scheduling/README.md#-bytedance-gödel) → [MAST](orchestration-scheduling/README.md#-meta-mast) → [Kueue](orchestration-scheduling/README.md#kubernetes-batch--ai-scheduling)

**GPU training & inference**

1. *Start here:* [MegaScale](gpu-training/README.md#-megascale) (what a 10k-GPU training stack looks like end to end)
2. *Classics:* [PipeDream](gpu-training/README.md#parallelism-strategies) → [Megatron-LM](gpu-training/README.md#parallelism-strategies) → [ZeRO-Offload](gpu-training/README.md#memory) → [Orca](gpu-training/README.md#batching--request-scheduling) → [vLLM](gpu-training/README.md#runtimes-memory--cluster-platforms)
3. *Frontier, training:* [Llama 3 infra](gpu-training/README.md#-llama-3-infrastructure) → [DeepSeek-V3](gpu-training/README.md#-deepseek-v3) → [reliability & checkpointing](gpu-training/README.md#reliability-checkpointing--fault-tolerance)
4. *Frontier, inference:* [Splitwise / DistServe](gpu-training/README.md#disaggregated--kv-cache-centric-serving) → [Sarathi-Serve](gpu-training/README.md#batching--request-scheduling) → [Mooncake](gpu-training/README.md#disaggregated--kv-cache-centric-serving)
5. *Frontier, RL:* [HybridFlow](gpu-training/README.md#rl-training-systems) → [AReaL](gpu-training/README.md#rl-training-systems)

**Agent sandboxes:** [Firecracker](agent-sandbox/README.md#-aws-firecracker) → [Firecracker vs gVisor study](agent-sandbox/README.md#containers-vs-microvms-measured) → [SOCK / Catalyzer](agent-sandbox/README.md#fast-start-snapshots-forking-caching) → [Kubernetes Agent Sandbox](agent-sandbox/README.md#agent-execution-platforms)

**Distributed-systems foundations:** [GFS](distributed-system/README.md#the-google-file-system) → [MapReduce](distributed-system/README.md#mapreduce) → [Bigtable](distributed-system/README.md#bigtable) → [Dynamo](distributed-system/README.md#dynamo) → [Spanner](distributed-system/README.md#spanner)

## Deep-read notes

Longer notes (problem → core design → key numbers with section references → limitations → relation to other systems → takeaways), written from the papers themselves:

| Area | Note |
|---|---|
| Scheduling | [MAST](orchestration-scheduling/meta-mast/c286274-mast-global-scheduling-of-ml-training-across-geo-distributed.md) (OSDI 2024) · [Gödel](orchestration-scheduling/bytedance-godel/4f005ef-godel-unified-large-scale-resource-management-and-scheduling.md) (SoCC 2023) · [Sia](orchestration-scheduling/sia/71de9b9-sia-heterogeneity-aware-goodput-optimized-ml-cluster-scheduling.md) (SOSP 2023) |
| Training infra | [MegaScale](gpu-training/bytedance-megascale/2402.15627-megascale-scaling-large-language-model-training-to-more.md) (NSDI 2024) · [Llama 3 infra](gpu-training/meta-llama3-infra/2407.21783-the-llama-3-herd-of-models-infrastructure.md) (2024) · [DeepSeek-V3 insights](gpu-training/deepseek-v3/2505.09343-insights-into-deepseek-v3-scaling-challenges-and-reflections.md) (ISCA 2025) · [ByteRobust](gpu-training/bytedance-byterobust/2509.16293-robust-llm-training-infrastructure-at-bytedance.md) (SOSP 2025) |
| Inference | [Splitwise](gpu-training/microsoft-splitwise/2311.18677-splitwise-efficient-generative-llm-inference-using-phase-splitting.md) (ISCA 2024) · [Llumnix](gpu-training/alibaba-llumnix/2406.03243-llumnix-dynamic-scheduling-for-large-language-model-serving.md) (OSDI 2024) · [Mooncake](gpu-training/moonshot-mooncake/2407.00079-mooncake-a-kvcache-centric-disaggregated-architecture-for-llm.md) (FAST 2025) |
| RL systems | [AReaL](gpu-training/areal/2505.24298-areal-a-large-scale-asynchronous-reinforcement-learning-system.md) (NeurIPS 2025) |
| Sandboxes | [Firecracker](agent-sandbox/aws-firecracker/nsdi20-firecracker-lightweight-virtualization-for-serverless-applications.md) (NSDI 2020) |

## How this repo is maintained

- Entry format and conventions: [CLAUDE.md](CLAUDE.md).
- `paper-bot` (weekly GitHub Action) proposes papers from top systems venues as PRs; see [scripts/paper_bot](scripts/paper_bot) and `.github/paper-bot/`.

## Recently updated

- 2026-11 — 12 deep-read notes added (see above).
- 2026-11 — 2023–2026 frontier added (training reliability, disaggregated serving, RL systems, Kubernetes batch); new [agent-sandbox](agent-sandbox/README.md) topic.
- 2026-11 — READMEs reorganised into categories with a unified entry format; venue years corrected to conference editions.
