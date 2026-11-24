---
title: 'Alibaba HPN: A Data Center Network for Large Language Model Training'
authors:
- Kun Qian
- Yongqing Xi
- Jiamin Cao
- Jiaqi Gao
- Yichi Xu
- Yu Guan
- Binzhang Fu
- Xuemei Shi
affiliations: 'Alibaba Cloud'
venue: 'SIGCOMM'
year: 2024
paper_id: 15d37231657883a1e7022e1e84b5188a94800eca
doi: 10.1145/3651890.3672265
abs_url: https://dl.acm.org/doi/10.1145/3651890.3672265
pdf_url: https://ennanzhai.github.io/pub/sigcomm24-hpn.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Alibaba HPN: A Data Center Network for Large Language Model Training

> **Why it matters:** A production account of redesigning a GPU backend fabric around what LLM training traffic actually looks like: few elephant flows, synchronous bursts and a high cost per ToR failure. It replaces a 3-tier Clos with a 2-tier, dual-plane, dual-ToR Pod of about 15K GPUs.

## Problem

Classic cloud DCNs assume many small, high-entropy flows at low utilisation, so ECMP balances load statistically and losing a single ToR is tolerable. The paper argues that LLM training breaks all three assumptions (§1, §2.2):

- **Low entropy, high utilisation.** Cloud hosts carry hundreds of thousands of connections and stay below 20% NIC utilisation. A training GPU uses only a few dozen to a few hundred connections (Fig. 1, Fig. 3).
- **Bursty and periodic.** Gradient AllReduce in the backward phase drives a 2×200G NIC to its full 400 Gbps for seconds to tens of seconds, once per iteration (Fig. 2).
- **Hash polarisation.** ECMP hashes the same five-tuple at the ToR, Aggregation and Core stages. With few flows, the imbalance compounds across stages, and cross-Pod traffic suffers most (§2.2).
- **Fragility of synchronous jobs.** Monthly failure rates are about 0.057% for NIC–ToR links and about 0.051% for ToRs, so a single job still crashes 1–2 times a month. Each crash rolls the job back to a checkpoint taken 2–4 hours earlier (§2.3, Figs. 4–5).

The design goals (§2.4) are 15K GPUs per Pod (100K at data-centre level), as few hops and hash stages as possible, and no single-ToR point of failure.

## Core design

**Host and fabric layout (§3).** Each host has 8 GPUs and 9 NICs of 2×200G. NIC0 serves the frontend. NIC1–8 serve the backend, one per GPU rail, so each GPU gets 400G and each host 3.2 Tbps. The frontend and backend are physically separate networks.

**Non-stacked dual-ToR (§4).** The two ports of every backend NIC go to two different ToRs. Stacked dual-ToR (vPC, M-LAG and similar) needs an inter-ToR sync link. The paper attributes over 40% of critical failures in Alibaba's traditional DCs over three years to stacked dual-ToR issues, and says about 70% of ToR upgrades violate ISSU's small-diff assumption (§4.1). HPN removes the inter-ToR link (§4.2):
- Both ToRs run independently but look like one LACP partner to the host. They share a pre-configured virtual-router MAC, and each ToR offsets its LACP port IDs by a constant above 256 so the two ToRs' IDs never collide.
- The host duplicates every ARP message to both ports. Each ToR turns learned ARP entries into /32 host routes advertised in BGP, and both ToRs also advertise the subnet route at equal cost.
- When a link or ToR fails, the ARP entry and its /32 route are withdrawn. BGP then steers traffic to the surviving ToR, which still holds the longest-prefix route.
- L2 broadcast is disabled and the ToRs run ARP proxy, so intra-segment traffic is routed at L3. This avoids black holes during the 5-minute MAC aging window.
- The authors rejected host-side BGP because it would slow convergence and complicate upgrades across O(10K) hosts.

**Tier 1: the 51.2 Tbps single-chip ToR and 1K-GPU segment (§5).**
- **Why single-chip.** In Alibaba's fleet, multi-chip chassis switches have 3.77× more critical hardware failures than single-chip boxes, traced to their internal chip fabric (§5.1). Single-chip switches also outnumber them 32.6× in operation.
- **Port plan.** Each ToR has 128 active 200G downlinks, 8 backup 200G downlinks and 60 400G uplinks, about 1.067:1 oversubscription. The backup ports attach standby hosts for fast replacement (§5.1).
- **Cooling.** The 51.2T chip draws 45% more power than its 25.6T predecessor. Neither heat pipes nor the original vapour-chamber design could run it at full power. An optimised vapour chamber improved cooling efficiency by 15% (§5.1, Figs. 9–10).
- **Segment size.** Rail-optimised dual-ToR with 16 ToRs gives 1,024 active GPUs (+64 backup) per segment (Fig. 7). Table 2 traces the scaling: 64 GPUs under plain Clos, 128 with dual-ToR, 1K with rail optimisation. The size was chosen because about 96.3% of production jobs use fewer than 1K GPUs (Fig. 6), so most jobs never leave Tier 1.

**Tier 2: the dual-plane Pod (§6).**
- **Two planes.** The ToRs of each dual-ToR set split into two groups, each wired to a separate plane of 60 Aggregation switches. Traffic leaving NIC port 0 stays in its plane end to end (§3, Fig. 12).
- **Why polarisation disappears.** Once a flow picks a ToR uplink, its path through the Pod is fully determined. The aggregation layer never re-hashes the same five-tuple, which removes polarisation inside the Pod (§6.1). Load-balancing choice drops to O(60) uplinks, against O(2048–4096) for SuperPod, Jupiter or a k=48 fat tree (Table 1).
- **Host-side path selection.** RePaC returns the source ports that map to disjoint paths, and the collective library opens one RDMA connection per source port. Each new message goes to the connection with the fewest unfinished WQE bytes (§6.1, Algs. 1–2).
- **Pod scale.** 15 segments make 15,360 GPUs per Pod (Table 1). Splitting into planes does not reduce bisection bandwidth (§3).

**Tier 3 (§7).** Pods connect through Core switches at 15:1 Aggregation–Core oversubscription, a deliberate trade for larger Pods. The argument is that only PP Send/Recv traffic, the smallest class, needs to cross Pods (Table 3). The Core layer uses per-port hashing to avoid polarisation.

**Frontend (§8).** A separate 2×200G NIC per host, also non-stacked dual-ToR, at 1:1 at Aggregation and Core. It carries management, dataset and image loading, checkpoints, storage (96–128 CPFS/OSS hosts) and inference traffic. Keeping storage there prevents it from disturbing training traffic (§10).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| GPUs per Pod | 15,360 | 15 segments × 1,024 | Table 1, §3 |
| GPUs per segment | 1,024 active + 64 backup | 16 × 51.2T ToRs, rail-optimised | Fig. 7 |
| Jobs < 1K GPUs | ~96.3% | production jobs | §1, Fig. 6 |
| Tier-1 oversubscription | ~1.067:1 | 128×200G down / 60×400G up | §5.1 |
| Agg–Core oversubscription | 15:1 | cross-Pod | §3, §7 |
| Multi-chip vs single-chip critical HW failures | 3.77× | fleet statistics | §5.1 |
| Stacked dual-ToR share of critical failures | >40% | traditional DCs, 3 years | §4.1 |
| NIC–ToR link failures | ~0.057% per month | production | §2.3, Fig. 5 |
| ToR critical failures | ~0.051% | production | §2.3 |
| ToR downstream queue length | −91.8% | dual-plane vs Clos | §6.1, Fig. 14 |
| Host-side path selection | up to +34.7% | 4 concurrent AllReduce, 512 GPUs | §6.1 |
| End-to-end training throughput | +14.9% | proprietary LLM, 2,300+ GPUs, vs DCN+ | §9.1, Fig. 15a |
| Cross-segment traffic at Agg | −37% avg | same job (3 vs 19 segments) | §9.1, Fig. 15b |
| LLaMa-7B / 13B / GPT-3 175B | +7.9% / +14.4% / +6.3% | 448 GPUs | §9, Fig. 16 |
| AllReduce / Multi-AllReduce | up to +59.3% / +158.2% | 448 GPUs, NCCL 2.18.3 | §9, Fig. 17 |
| Degradation on link failure | 6.25% (single-ToR halts) | 256 GPUs, LLaMa-7B | §9.3, Fig. 18a |
| Multi-mode vs single-mode optics cost | −70% | all fibre <100 m in one 18 MW building | §10 |

## Limitations

- **The baseline mixes several changes.** DCN+ is Alibaba's own 3-tier Clos with 128-GPU segments (§9, App. C). HPN differs from it in segment size, tier count and plane split at once, and the paper attributes part of the AllReduce gain to NVLS. Per-feature attribution therefore rests mainly on the ablations in §6.1 and App. A. *(Own analysis.)*
- **Cross-Pod jobs are second-class.** The 15:1 Core ratio assumes only PP traffic crosses Pods. Jobs that put DP or EP traffic across Pods, or schedulers that fragment placement, would lose that guarantee. *(Own analysis, extending §7.)*
- **Load balancing still lives on the host.** Path selection depends on RePaC and a modified collective library, so hosts or tenants that cannot run that stack fall back to plain ECMP. *(Own analysis.)*
- **The design is tied to one site's constraints.** Pod size is fixed by an 18 MW building (§10). Wiring complexity caused early mistakes and needed INT-based verification (§10). The paper says nothing about congestion control or PFC behaviour at scale. *(Own observation of scope.)*
- **A unit mismatch in the traffic data.** §2.2 states connection counts per GPU, but the Fig. 3 caption says "per host".

## Relation to other systems

- **Meta RoCE (SIGCOMM 2024).** Per its abstract, Meta also isolates a dedicated backend RoCE network and iterates on routing for low-entropy, bursty traffic. Meta's congestion fix moved admission control into the collective library after DCQCN proved hard to tune. HPN instead removes polarisation by topology (dual-plane) and host-chosen source ports, and adds dual-ToR for availability. HPN §10 also rejects Meta's rail-only idea because MoE all-to-all traffic and multi-tenancy need cross-rail paths.
- **MegaScale (NSDI 2024).** Its abstract describes full-stack co-design (model, overlap, operators, data pipeline, network tuning) and stability tooling, reaching 55.2% MFU on 12,288 GPUs. MegaScale treats the network as one layer to tune and diagnose. HPN redesigns the fabric itself. The two are complementary.
- **Llama 3 (arXiv 2024).** Its abstract covers the model family (405B dense, 128K context) and does not describe the training network. Meta's RoCE paper is the closer infrastructure comparison.
- **DeepSeek-V3 insights (ISCA 2025).** Its abstract credits a multi-plane network topology with cutting cluster networking overhead on 2,048 H800s, and calls for converging scale-up and scale-out networks. That is the same plane-splitting idea as HPN, applied at smaller scale and in co-design with MoE.
- **Jupiter Rising (SIGCOMM 2015) / classic fat tree.** Jupiter's abstract describes multi-stage Clos fabrics of merchant silicon with centralised control, scaled to building-wide bisection. HPN keeps merchant silicon but rejects deep Clos tiers for training. Its Table 1 argues that 3-tier fabrics leave O(2K–4K) hash choices per flow, against O(60) in HPN.

## Takeaways for practice

- Size the high-bandwidth domain from the job-size distribution. If ~96% of jobs fit in 1K GPUs, a 1K-GPU single-tier segment avoids most ECMP problems outright.
- Topology can remove hash stages. Dual planes plus host-chosen source ports beat tuning switch hashes for low-entropy flows.
- Treat ToR availability as a training-throughput issue. Dual-ToR without an inter-ToR link turns a job crash into a ~6% slowdown.
- Schedulers should be topology-aware: pack jobs within a segment, keep cross-Pod placement to PP stages, and keep backup hosts on the same ToR for fast swaps.
- Keep storage, checkpoint and inference traffic on a separate frontend so it cannot perturb collectives.

## References

- Paper: https://dl.acm.org/doi/10.1145/3651890.3672265
- PDF (author page): https://ennanzhai.github.io/pub/sigcomm24-hpn.pdf
