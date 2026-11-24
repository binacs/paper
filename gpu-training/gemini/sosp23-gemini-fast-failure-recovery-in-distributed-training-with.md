---
title: 'GEMINI: Fast Failure Recovery in Distributed Training with In-Memory Checkpoints'
authors:
- Zhuang Wang
- Zhen Jia
- Shuai Zheng
- Zhen Zhang
- Xinwei Fu
- T. S. Eugene Ng
- Yida Wang
affiliations: 'Rice University, Amazon Web Services'
venue: 'SOSP'
year: 2023
paper_id: a2eba36b34833621fa70bcc63ba239846bfd529a
doi: 10.1145/3600006.3613145
abs_url: https://dl.acm.org/doi/10.1145/3600006.3613145
pdf_url: https://cdn.amazon.science/29/31/6523473f48e4af52252bac56ef51/gemini-fast-failure-recovery-in-distributed-training-with-in-memory-checkpoints.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# GEMINI: Fast Failure Recovery in Distributed Training with In-Memory Checkpoints

> **Why it matters:** It showed that large-model training can checkpoint every iteration, at no measurable cost to iteration time, by writing replicas into peer hosts' CPU memory and sending that traffic in the network's idle gaps. Remote storage stays in the system as a rare fallback.

## Problem

Large training jobs fail often. The paper cites OPT-175B on 992 A100s, which saw about 110 failures over two months (§2.1). On a failure the job rolls back to the last checkpoint. Eq. (1) gives the average wasted time as `T_wasted = t_ckpt + 1/(2f) + t_rtvl`, where f is the checkpoint frequency. Eq. (2) adds the constraint `1/f ≥ max(t_ckpt, T_iter)`, so a new checkpoint can't start before the last one finishes, and checkpoints come at most once per iteration.

With remote persistent storage, `t_ckpt` is set by storage bandwidth, which is low and shared. BLOOM checkpointed about every three hours. Writing MT-NLG to remote storage at 20 Gbps takes 42 minutes, which gives an average of 105 minutes wasted per failure (§2.2). The checkpoint is too large for the storage pipe, so checkpoints are rare and every failure throws away hours of work.

Host CPU memory is a far better target. It is large: a p4d.24xlarge has 1152 GB of CPU memory against 8×40 GB of GPU memory (Table 1). Its aggregate bandwidth across the cluster's NICs is also much higher than remote storage. Two challenges remain (§2.3):

1. **Availability:** CPU memory is lost when its machine fails. Replicas must be placed so that the likely failure patterns leave at least one copy of every shard.
2. **Interference:** checkpoint traffic shares the network with training collectives (ZeRO-3 all-gather and reduce-scatter) and can slow iterations down.

## Core design

### Architecture (§3, Fig. 2)
- Each machine runs a **worker agent**. A **root agent** reads health status from a distributed KV store (etcd). Workers write heartbeats and status, a stale entry marks a failure, and the root itself is re-elected by leader election (§3.2, §6.2).
- Storage is a hierarchy: local CPU memory, remote (peer) CPU memory, and remote persistent storage. Persistent storage is still written at a low rate; the evaluation uses every 3 h (§7.1). It serves as the fallback and for other uses of checkpoints.
- Scope: static, synchronous training with fixed resources. Elastic and asynchronous training are out of scope (§1). The prototype is built on DeepSpeed ZeRO-3.

### Checkpoint placement (§4, Alg. 1, Fig. 3)
- The problem: place m replicas of each machine's checkpoint shard across N machines so that the probability of recovering from CPU memory after k simultaneous failures is as high as possible.
- **Group placement:** split machines into disjoint groups of size m. Every member of a group stores the checkpoints of all other members. A group loses data only if all m of its members fail.
- **Ring placement:** each machine sends replicas to the next m−1 machines on a ring. Any m consecutive failures lose data, and many more failure sets are consecutive than are a whole group, so ring placement is worse.
- **Mixed (Alg. 1):** use groups of size m. When m does not divide N, the leftover machines form a ring.
- **Theorem 1 (proof in App. A):** when m divides N, group placement is optimal. Otherwise mixed is near-optimal, with a gap of at most (2m−3)/C(N,m), and it also minimizes checkpoint communication time.
- **Corollary 1 (App. B, Eq. 3):** for m | N, Pr = 1 if k < m. For m ≤ k ≤ N, Pr ≥ max{0, 1 − N·C(N−m, k−m) / (m·C(N,k))}.

### Interleaving checkpoint traffic with training (§5)
- **Idle-span scheduling (§5.1, Fig. 4):** ZeRO-3 iterations leave gaps in network use, for example during compute that has no collective in flight. Gemini profiles these idle spans online during the first 20 iterations. Their normalized standard deviation is under 10%, so the profile is stable (§5.4). Checkpoint chunks are then packed into the spans.
- **GPU-to-GPU path through a small buffer (§5.2, Fig. 5):** the checkpoint goes GPU→network→remote GPU, then GPU→CPU on the receiver, using a reserved GPU buffer. The prototype reserves 128 MB, split into four 32 MB sub-buffers (§7.1, §7.4). With sub-buffers, one chunk can be on the wire while the previous one is being copied to host memory.
- **Partitioning (Alg. 2, §5.3):** chunks are at most R/p in size (R is the reserved buffer, p the number of sub-buffers). Each span's capacity comes from a cost model `f(s) = α + s/B` with a safety factor μ. Each remote replica is partitioned separately. Traffic that does not fit goes into the last span, and Gemini then lowers the checkpoint frequency.
- **Consistency:** two CPU-memory buffers per checkpoint, one holding the last complete checkpoint and one being filled (§7.1). The paper gives no further protocol detail.

### Failure recovery (§6, Fig. 6)
- **Software failure:** restart in place and load the checkpoint from local CPU memory.
- **Hardware failure:** the root agent asks the cloud operator (AWS Auto Scaling Groups) for replacement machines. Replacements take over the failed ranks and pull their shards from surviving peers in the same placement group (Case 1). If a whole group is gone, they load from remote persistent storage (Case 2). Optional pre-allocated standby machines skip the wait for a new instance; a new standby is then requested in the background.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Remote-storage checkpoint, MT-NLG | 42 min; 105 min average wasted time | 20 Gbps remote storage | §2.2 |
| Recovery from CPU memory, 2 simultaneous failures | 93.3% | N=16, m=2 | §4, Fig. 9 |
| Recovery from CPU memory, 3 simultaneous failures | 80.0% (ring 25.0% lower) | N=16, m=2 | §7.2, Fig. 9 |
| Gemini checkpoint time | < 3 s, every iteration (iteration ≈ 62 s) | GPT-2 100B, 16× p4d.24xlarge | §7.2 |
| Checkpoint-time reduction vs remote storage | 65× at 100 Gbps; > 250× at 400 Gbps | 16 instances | §7.2, Fig. 11 |
| Checkpoint frequency gain | 8× vs HighFreq; > 170× vs Strawman (3 h) | 16× p4d | §7.2, Fig. 12 |
| Average wasted time | > 13× lower than HighFreq | recoverable from CPU memory | §7.2, Fig. 10 |
| Iteration-time overhead | none measurable | GPT-2 up to 100B | §7.2, Figs. 7–8 |
| Ablation: blocking checkpoint traffic | +10.1% iteration time | GPT-2 40B, 16× p3dn.24xlarge | §7.4, Fig. 16 |
| Ablation: interleaving without pipelining | +3.5% iteration time; naive interleaving runs out of GPU memory | same | §7.4, Fig. 16 |
| Recovery breakdown | detection 15 s, checkpoint serialization 162 s, restart warmup 253 s, retrieval < 3 s | GPT-2 100B, one instance replaced | §7.3, Fig. 14 |
| Instance replacement wait | 4–7 min | AWS ASG, p4d | §7.3 |
| Total failure overhead | ≈ 7 min (software), ≈ 12 min (hardware) | GPT-2 100B | §7.3 |
| Effective training time at scale (simulated) | ≈ 91% at 1000 instances, 54% higher than HighFreq | 1.5% daily instance failure rate | §7.3, Fig. 15b |
| Reserved GPU buffer | 128 MB (4 × 32 MB) | prototype | §7.1, §7.4 |

## Limitations

- **Narrow parallelism coverage:** only DeepSpeed ZeRO-3 is implemented and evaluated. Pipeline and tensor parallelism are future work (§9). Their communication patterns, such as pipeline bubbles and constant TP all-reduces, leave different idle spans.
- **Static synchronous jobs only:** after a failure the job waits for a replacement machine or uses a standby. There is no elastic downsizing (§1).
- **Correlated failures:** placement assumes independent machine failures. A rack, switch or power-domain failure that takes out a whole group forces a fallback to remote storage. Groups are not built around failure domains.
- **Where the time goes now:** retrieval drops below 3 s, but detection, serialization, instance replacement and warmup still add 7–12 minutes per failure (Fig. 14). Per-iteration checkpoints fix the "lost work" term, not the restart term.
- **Memory cost:** each host keeps m replicas in two buffers (complete and in progress). The paper gives no CPU-memory budget formula and does not discuss jobs that already use host memory, such as CPU offload.
- **Scale evidence:** real runs use 16 instances. The 1000-instance results are simulated (Fig. 15).
- The idle-span profile assumes iterations look alike. Dynamic shapes or MoE routing could break the under-10% variance assumption.

## Relation to other systems

- **CheckFreq (FAST'21):** profiles per-iteration cost to choose a frequency and overlaps snapshot with persist in two phases, but still persists to storage. Gemini removes the storage bottleneck by targeting peer CPU memory, and Gemini cites CheckFreq (§8). CheckFreq's snapshot/persist split is roughly what Gemini's local-copy plus remote-replica path generalizes.
- **Check-N-Run, DeepFreeze (cited in §8):** cut checkpoint size or overhead for storage-bound checkpointing. These techniques work alongside Gemini rather than competing with it.
- **Bamboo / Varuna (cited in §8):** spot-instance resilience. Bamboo uses redundant computation, which Gemini does not need. Varuna leaves checkpoint frequency and storage to the user, whereas Gemini handles them transparently.
- **Oobleck (SOSP'23, abstract only; not cited by Gemini):** avoids restart from a checkpoint altogether. It keeps several pipeline templates and replicas, so after a failure it rebuilds pipelines and copies state from surviving replicas. Both systems recover from in-memory replicas of other workers. Oobleck pays with redundant model replicas plus reconfiguration and keeps running, while Gemini pays with CPU-memory copies and restarts on a fixed set of machines.
- **ByteCheckpoint (NSDI'25, abstract only):** a production checkpointing system for persistent storage. It offers a parallelism-agnostic representation with load-time resharding, multiple frameworks and backends, and I/O optimizations, cutting checkpoint stalls by 54.20× on average. Its focus is storage-side checkpoints and resharding, which is the tier Gemini keeps as a fallback. The two fit together naturally: in-memory checkpoints for fast restart, and resharding persistent checkpoints for parallelism changes and later training stages.
- **MegaScale (NSDI'24, abstract only):** at 10k+ GPUs, the abstract stresses stability, deep observability, root-cause diagnosis, fault tolerance and straggler mitigation. That covers the detection and diagnosis part of the overhead that Gemini's Fig. 14 leaves untouched.

## Takeaways for practice

- Treat host DRAM across the cluster as the primary checkpoint tier and remote storage as a durable tier with low frequency. With checkpoint time under 3 s, per-iteration checkpoints are feasible, and lost work shrinks to about half an iteration.
- Use group placement, not ring placement, for replicas. Put groups across failure domains (rack, ToR, PDU), which the paper does not do but which its independence assumption implies.
- Never let checkpoint traffic block training. Profile the collective schedule's idle spans, chunk transfers to fit them, and stage them through a small pipelined GPU buffer. Blocking costs about 10% (Fig. 16).
- After per-iteration checkpointing, failure cost is mostly detection, replacement and warmup. Hot standbys, faster health checks and faster process or NCCL restart are the next things to fix. A scheduler that keeps warm spare nodes per job pays off directly here.
- Check that the placement and idle-span assumptions still hold when you move from ZeRO-3 to 3D parallelism or MoE before relying on the reported numbers.

## References

- Paper: https://dl.acm.org/doi/10.1145/3600006.3613145
- PDF (Amazon Science): https://cdn.amazon.science/29/31/6523473f48e4af52252bac56ef51/gemini-fast-failure-recovery-in-distributed-training-with-in-memory-checkpoints.pdf
- Blog: https://amazon.science/blog/more-efficient-recovery-from-failures-during-large-ml-model-training
- Slides (first author): https://zhuangwang93.github.io/docs/Gemini_SOSP23_slides.pdf
