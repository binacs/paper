---
title: 'RDMA over Ethernet for Distributed AI Training at Meta Scale'
authors:
- Adithya Gangidi
- Rui Miao
- Shengbao Zheng
- Sai Jayesh Bondu
- Guilherme Goes
- Hany Morsy
- Rohit Puri
- Mohammad Riftadi
affiliations: 'Meta'
venue: 'SIGCOMM'
year: 2024
paper_id: ec1dca2ac16ce685229cb58c90e07d049d6d5e7a
doi: 10.1145/3651890.3672233
abs_url: https://dl.acm.org/doi/10.1145/3651890.3672233
pdf_url: https://engineering.fb.com/wp-content/uploads/2024/08/sigcomm24-final246.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# RDMA over Ethernet for Distributed AI Training at Meta Scale

> **Why it matters:** An operator's account of running RoCEv2 as the GPU backend fabric for thousands of GPUs per cluster, showing that routing and congestion control had to be co-designed with the collective library rather than taken from storage-era RDMA practice.

## Problem

Meta's ranking/DLRM and LLM jobs need 400 Gbps+ inter-node bandwidth and tens of thousands of GPUs (§2.4). Storage-era RoCE practice (5-tuple ECMP, DCQCN) assumes many flows; collectives produce few, long-lived, line-rate flows with collective-specific incast (Table 1). The paper's four challenges (§2.4): rapid model evolution, low-entropy traffic, varying congestion per collective, and the need to co-tune the collective library with the network.

## Core design

### Backend/frontend split (§3.2, §3.4)
- Each node (ZionEX/A100, then Grand Teton/H100) has 8 NVSwitch-connected GPUs and 8 RDMA NICs mapped 1:1 with GPUDirect (§3.1, Fig. 4).
- The **frontend** (RSW/FSW) carries ingestion, checkpointing and logging. The **backend** is a separate, non-blocking RoCEv2 fabric for training traffic only.
- The split ("an early, major design decision") let the two networks evolve independently and isolated latency-sensitive RoCE (§3.4).

### Topology: AI Zones and ATSW (§3.3, Fig. 6)
- A star topology on non-routable RoCEv1 was replaced by a two-stage Clos, the **AI Zone**.
- **RTSW** (leaf): copper DAC to GPUs, shared shallow buffers. **CTSW** (modular spine): deep buffers statically carved per ingress port, VOQ; single-mode fibre and 400G optics to RTSWs.
- **ATSW** (aggregator): joins CTSWs across a building. Cross-zone capacity is oversubscribed by design and ECMP-balanced. The scheduler seeks a "minimum cut" when splitting a job across zones and recommends topology-aware rank assignment.
- **Rail-optimised design:** the paper does **not** describe one. "Rail" appears only as a "Rail-based Alltoall" tuning option (§6.1). No GPU count per AI Zone is given.

### Routing evolution (§4)
1. **ECMP** performed poorly because of low flow entropy. Table 2 counts about 4 QPs per GPU for AllReduce/AllGather/ReduceScatter and 15 for AlltoAll on 128 GPUs (§4.1.1).
2. **Path pinning** routed by destination "slice" (RTSW downlink index). It broke down with partial-rack allocation and with failures, where ECMP reassignment caused collisions (§4.1.2). The stopgap was doubling RTSW uplinks to 1:2 under-subscription, which the paper calls "an expensive solution" (§4.1.3).
3. **E-ECMP + QP scaling** (§4.2): NCCL spreads each NIC-to-NIC connection over several QPs, and switches also hash the RoCE destination-QP field via ASIC UDF, since UDP ports were often identical across QPs. Round-robin posting of whole messages beat splitting messages, which created small messages and extra ACKs (§4.2.4). Ranking uses 4 QPs, LLMs 16 (§4.2.3).
4. **Centralised TE** (§4.3, Fig. 9): a collector merges static topology with Open/R link state; a TE engine runs CSPF over the traffic matrix and scheduler job placement periodically (e.g. every 30 s); a switch programmer installs RTSW exact-match entries on <source port, destination prefix>, overriding BGP, which stays as fallback.
5. **Flowlet switching** (§4.5): the first-hop RTSW re-hashes a flow to a new ECMP member after an idle gap, in hardware. It needs only 4 QPs for every workload and is still being evaluated for rollout.

Outcome: TE became primary for ranking AI Zones and E-ECMP for DC-scale (ATSW) deployments (§4.4.3).

### Transport and congestion control (§5)
- The backend is lossless RoCEv2: DSCP-based PFC with a single lossless queue, and go-back-N for rare drops. Lost ACK/NACKs trigger millisecond-scale Local ACK Timeouts (§5.1).
- **DCQCN at 200G:** tightening ECN thresholds reduced PFC but cost collective throughput (Fig. 12). Relaxing them gained little and made PFC metrics worse (Fig. 13). Meta settled on relaxed 5 MB ECN marking at the CTSW (§5.2).
- **DCQCN off at 400G:** doubled thresholds degraded performance, and NIC firmware changes introduced bugs, including incorrect CNP counting. Meta has run 400G **without DCQCN** for over a year, monitoring NIC pause duration instead (§5.2.1).
- **Receiver-driven admission in NCCL** (§5.2.2, Fig. 14): the sender GPU fills a channel buffer, and its CPU proxy posts the RDMA write only after a clear-to-send (CTS) from the receiver, which re-issues CTS once its buffer drains. Channel count and buffer size, set experimentally per job size and collective, bound in-flight bytes. CTS packets get a high-priority queue.
- In a 16:1 incast, Perftest showed head-of-line blocking spreading to senders while NCCL Gather caused no PFC back-pressure (Table 3); deep CTSW buffers absorb transient congestion (§5.2.3).

### Collective-library co-design (§6.1)
NCCL assumed sub-10 µs RTT, adaptive routing and a non-blocking fabric; none held. Fixes: larger posted messages, prioritised CTS/ACKs with DSCP remarking, more aggressive CTSW credits, later Tree/LL128 switch points, NIC PCIe/relaxed-ordering settings, topology-aware ranks, dropping zero-byte messages.

### Operations (§6.2–6.4)
- Under-subscription went 1:1 static → 1:2 static → 1:2 TE → 1:1.125 TE, reclaiming CTSW hardware with no measured loss while tolerating two link failures (Fig. 16).
- Jobs see RDMA counters (out-of-sequence, link flaps, Local ACK Timeouts); operators have a PFC watchdog, buffer alarm and pings.
- Incidents: a CTSW image raised port-to-port latency with no congestion metric moving, so latency baselines are now tracked (§6.4.1); a stale SRAM-buffer assumption caused tail drops after a TE migration, visible only with a firmware change, bursty job and H100s together (§6.4.2).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Largest published RoCE cluster design | up to 32,000 GPUs | cited prior Meta design | §1 |
| Llama 3 large variant | 16,000 GPUs on a 24,000-GPU RoCE cluster | production | §2.3 |
| ECMP imbalance (max/mean) | >1.2 on average | sim., 1,000 flows on 16 links | §4.1.1 / Table 2 |
| Path-pinning degradation | up to >30% | partial rack allocation | §4.1.2 |
| E-ECMP + QP scaling gain | up to 40% | AllReduce | §4.2.2 / Fig. 7 |
| E-ECMP 4 QP vs roofline | ~40% longer completion on average | simulation | §4.4.1 |
| Link utilisation, E-ECMP vs TE | 40–90% vs ~80% uniform | 16 uplinks | §4.4.2 / Fig. 10 |
| TE over E-ECMP | 5–10% | AllReduce, AlltoAll, 128 GPUs | §4.4.2 |
| Tight ECN thresholds | ~5% regression | 300/600 KB vs 5 MB, 32-GPU AllReduce, 200G | §5.2 / Fig. 12 |
| Relaxed DCQCN | ~3% gain, PFC 2–3x worse | 128-GPU AlltoAll, 200G | §5.2 / Fig. 13 |
| PFC-only operation | over 1 year | 400G | §5.2.1 |
| No persistent CTSW→RTSW PFC | last 4 years | production AI traffic | §5.3 |
| Unloaded RTT | ~22 µs | VOQ CTSW fabric | §6.1 |
| CTS/ACK rendezvous delay (P90) | 43 µs → 4 µs | QoS priority + DSCP remarking | §6.1 |
| Out-of-box RoCE improvement | >2x in many cases | co-tuning, metric not defined | §6.1 / Fig. 15 |
| Final under-subscription | 1:1.125 | TE, 200G ZionEX AI Zone | §6.2 / Fig. 16 |

## Limitations

Stated by the paper:
- E-ECMP is still probabilistic, and per-workload QP tuning adds long-term operational complexity (§4.2.5).
- TE degrades under multiple link failures, which were "more frequent than expected". It adds software complexity and is not used at DC scale (§4.4.3).
- Running without transport-level congestion control relies on coordination between NCCL and the network, and "may depend on the relative throughput between GPU and network" (§5.3). The authors invite research on this.
- Flowlet switching is not yet deployed (§4.5).

My own analysis (not claims the paper makes):
- Most results are normalised or relative. GPUs per AI Zone, cross-zone oversubscription and absolute bandwidth are not given, so the designs are hard to reproduce.
- There is no topology-level rail-optimised design and no quantitative comparison with InfiniBand, so the paper does not show whether rail alignment would have reduced the ECMP problems.
- The PFC-only stance depends on every backend sender going through NCCL's CTS admission on a single-tenant fabric. Non-NCCL traffic, multi-tenancy, or MoE AlltoAll at higher GPU-to-network bandwidth ratios could break that assumption.

## Relation to other systems

- **Alibaba HPN (SIGCOMM 2024):** its abstract gives the same diagnosis (bursty LLM flows cause ECMP hash polarisation) but answers with topology: a 2-tier dual-plane design of ~15K GPUs per Pod, plus dual-ToR. Meta keeps single-homed AI Zones and fixes balancing with QP-aware hashing and TE.
- **MegaScale (NSDI 2024):** its abstract covers full-stack co-design for >10,000-GPU LLM training (55.2% MFU, 175B model, 12,288 GPUs); network tuning is one item among many. Meta goes deeper on the fabric itself.
- **Llama 3 (arXiv 2024):** its abstract covers only the models (405B dense, 128K context), not infrastructure. This paper's §2.3 names a Llama 3 variant trained on 16K GPUs of a 24K-GPU RoCE cluster, i.e. it documents the network underneath.
- **DeepSeek-V3 insights (ISCA 2025):** its abstract describes 2,048 H800s, a multi-plane topology and hardware-aware model design (MLA, MoE, FP8). The model is shaped to the network, whereas Meta tunes the network and NCCL for existing models.
- **Homa (SIGCOMM 2018):** a receiver-driven transport with in-network priorities and controlled overcommitment for short-message tail latency. Meta's CTS admission is also receiver-driven with prioritised grants, but sits in the collective library above lossless RDMA and targets bulk transfers.

## Takeaways for practice

- Physically isolate the training fabric so routing and transport can change on their own schedule.
- Make the scheduler topology-aware: partial-rack placement cost >30% under path pinning; minimum-cut zone placement and rank assignment are cheap.
- If ECMP stays, hash on fields that carry entropy (destination QP via UDF) and expect per-workload QP tuning; plan for flowlet or TE balancing.
- Receiver-side admission in the collective library can replace DCQCN for single-tenant training; re-validate at each link-speed bump.
- Track loaded/unloaded latency baselines, not just congestion counters.
- Keep headroom (1:1.125, not 1:1) so link failures don't undo balancing gains.

## References

- Paper (ACM DL): https://dl.acm.org/doi/10.1145/3651890.3672233
- Paper (Meta public PDF, the copy read): https://engineering.fb.com/wp-content/uploads/2024/08/sigcomm24-final246.pdf
- Blog: https://engineering.fb.com/2024/08/05/data-center-engineering/roce-network-distributed-ai-training-at-scale/
