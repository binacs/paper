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

## How this repo is maintained

- Entry format and conventions: [CLAUDE.md](CLAUDE.md).
- `paper-bot` (weekly GitHub Action) proposes papers from top systems venues as PRs; see [scripts/paper_bot](scripts/paper_bot) and `.github/paper-bot/`.

## Recently updated

- 2026-11 — 2023–2026 frontier added (training reliability, disaggregated serving, RL systems, Kubernetes batch); new [agent-sandbox](agent-sandbox/README.md) topic.
- 2026-11 — READMEs reorganised into categories with a unified entry format; venue years corrected to conference editions.
