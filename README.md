# paper

A curated reading index for **large-scale cluster scheduling, GPU training / inference systems, and the distributed-systems classics underneath them** — papers and official engineering blogs only, organised by topic, with short "why it matters" lines and deep-read notes for the most important ones.

## Topics

| Topic | What's inside | Entries |
|---|---|---|
| [orchestration-scheduling](orchestration-scheduling/README.md) | Cluster managers (Borg, Twine, Gödel, MAST …), two-level / shared-state / distributed schedulers, ML-specific scheduling, node-level isolation & QoS | 29 |
| [gpu-training](gpu-training/README.md) | LLM training infrastructure, parallelism, memory, communication, compilers, inference serving, RL training systems | 18 |
| [distributed-system](distributed-system/README.md) | GFS, MapReduce, Bigtable, Dynamo, Spanner, F1 …, datacenter networking, serverless | 17 |
| [ai](ai/README.md) | Ilya Sutskever's "30u30" foundational reading list | 27 |
| [profile](profile/README.md) | Repo owner's academic profiles | — |

Counts are curated entries above each README's `Auto-analyzed papers` section (bot-added papers are also linked from the curated sections).

## Reading paths

**Cluster scheduling**

1. *Start here:* [Borg, Omega, and Kubernetes](orchestration-scheduling/README.md#overviews) → [Omega](orchestration-scheduling/README.md#google-omega) (the scheduler taxonomy)
2. *Classics:* [Borg](orchestration-scheduling/README.md#google-borg) → [Mesos](orchestration-scheduling/README.md#apache-mesos) / [YARN](orchestration-scheduling/README.md#apache-yarn) → [Sparrow](orchestration-scheduling/README.md#uc-berkeley-sparrow) → [DRF](orchestration-scheduling/README.md#fairness)
3. *Frontier:* [Twine](orchestration-scheduling/README.md#meta-twine) → [Gödel](orchestration-scheduling/README.md#-bytedance-gödel) → [MAST](orchestration-scheduling/README.md#-meta-mast)

**GPU training & inference**

1. *Start here:* [MegaScale](gpu-training/README.md#-megascale) (what a 10k-GPU training stack looks like end to end)
2. *Classics:* [PipeDream](gpu-training/README.md#parallelism-strategies) → [ZeRO-Offload](gpu-training/README.md#memory) → [Megatron activation recomputation](gpu-training/README.md#parallelism-strategies) → [Orca](gpu-training/README.md#inference-serving) → [vLLM](gpu-training/README.md#inference-serving)
3. *Frontier:* [DistServe](gpu-training/README.md#inference-serving) / [Sarathi-Serve](gpu-training/README.md#inference-serving) → [HybridFlow](gpu-training/README.md#rl-training-systems)

**Distributed-systems foundations:** [GFS](distributed-system/README.md#the-google-file-system) → [MapReduce](distributed-system/README.md#mapreduce) → [Bigtable](distributed-system/README.md#bigtable) → [Dynamo](distributed-system/README.md#dynamo) → [Spanner](distributed-system/README.md#spanner)

## How this repo is maintained

- Entry format and conventions: [CLAUDE.md](CLAUDE.md).
- `paper-bot` (weekly GitHub Action) proposes papers from top systems venues as PRs; see [scripts/paper_bot](scripts/paper_bot) and `.github/paper-bot/`.

## Recently updated

- 2026-11 — READMEs reorganised into categories with a unified entry format; venue years corrected to conference editions.
