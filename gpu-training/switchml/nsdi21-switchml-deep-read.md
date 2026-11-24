---
title: 'Scaling Distributed Machine Learning with In-Network Aggregation'
authors:
- Amedeo Sapio
- Marco Canini
- Chen-Yu Ho
- Jacob Nelson
- Panos Kalnis
- Changhoon Kim
- Arvind Krishnamurthy
- Masoud Moshref
affiliations: 'KAUST, Microsoft, Barefoot Networks, University of Washington'
venue: 'NSDI'
year: 2021
arxiv_id: '1903.06701'
abs_url: https://www.usenix.org/conference/nsdi21/presentation/sapio
pdf_url: https://www.usenix.org/system/files/nsdi21-sapio.pdf
code_url: https://github.com/p4lang/p4app-switchML
note_type: deep-read
written_at: '2026-11-25'
---

# Scaling Distributed Machine Learning with In-Network Aggregation

> **Why it matters:** SwitchML shows that a commodity programmable Ethernet switch (Tofino) can do the all-reduce sum of data-parallel training in the data plane, halving per-worker traffic versus ring all-reduce, provided the end hosts own reliability, pacing and number format.

Source note: all numbers below are from the NSDI 2021 proceedings PDF (USENIX). The arXiv record (1903.06701) has v1 (Feb 2019) and v2 (Sep 2020); earlier arXiv text differs and was not used for numbers. Front matter lists the first eight of ten authors (also Dan Ports, Peter Richtárik).

## Problem

Data-parallel SGD needs a sum of model updates across all workers every iteration, and updates can be hundreds of MB to GB (§2.1). The paper argues compute has outpaced networking: it cites a 62× compute improvement over seven years (§1), and its profile of eight DNNs on 8 P100 workers (Table 1, §2.2) finds that at 10 Gbps all but three workloads spend more than 50% of batch time in communication, and at 100 Gbps communication is still at least 17% for half of them. Incumbents are parameter servers and ring all-reduce (RAR).

The obstacle to doing the reduction in a switch is the hardware: a small per-packet compute budget, little on-chip memory (far smaller than a model), integer-only ALUs while ML uses floating point, and lossy Ethernet (§1).

## Core design

**Streaming aggregation in a slot pool (§4.3, Algorithm 1).** The switch never holds the whole model. It keeps a pool of `s` integer aggregator slots; each slot sums a vector of `k` integers (k = 64 or 256 in the prototype). A packet carries a slot index, an offset into the tensor and `k` values. The switch adds the payload into the slot and increments a per-slot counter; when the count reaches `n` (worker count) it writes the sum into the packet, multicasts it to all workers and resets the slot; otherwise it drops the packet. Hosts divide by `n`; arrival order is irrelevant.

**Self-clocked worker protocol (§4.4, Algorithm 2).** Each worker starts by sending `s` packets, one per slot. When the result for slot `i` arrives, the worker copies it into the output and sends the next chunk (offset advanced by `k·s`) to the same slot. The slot/offset mapping is deterministic, so workers need no coordination, and a result packet doubles as a flow-control acknowledgement: a slot is never reused before every worker has contributed. To reach line rate the pool must cover the bandwidth-delay product of the links; the sizing is tuned in Appendix C (Figure 9).

**Host-driven loss recovery (§4.5, Algorithms 3–4).** Workers detect loss with a timeout and retransmit. The switch keeps two copies of every slot, selected by a one-bit version, and workers alternate between them; the inactive copy is a "shadow" that still holds the last result. A bitmap of which workers have contributed to each slot filters duplicate retransmissions. If a retransmission hits a slot that has already completed, the switch unicasts the stored result to that worker, which covers lost result packets. The invariant that no worker is more than one chunk ahead of any other is what makes a single shadow copy sufficient. Cost: 2× slot memory plus the bitmap. Failures of workers, links or the switch itself are explicitly out of scope and left to the ML framework (footnote 6, §4.2).

**Quantized integer arithmetic (§4.6).** The switch adds 32-bit fixed-point integers. Workers convert gradients with a block-floating-point-like scheme: each block gets a scaling factor derived from the largest-magnitude value across workers and the worker count, so the aggregated block cannot overflow 32 bits. The global exponent is computed in the switch without an extra round trip: alongside block `j` each worker sends the local maximum for block `j+1`, and the switch returns the global maximum with the aggregated block `j`.

**Implementation (§5).** About 3,700 lines of P4 on the switch and about 3,100 lines of C++ on workers. One Tofino pipeline handles 64-element packets; 256-element (1024-byte) packets use all four pipelines via recirculation, with ports put into loopback, leaving 16 × 100 Gbps for workers. Worker transports: a DPDK stack that shards slots and tensor chunks across up to 8 cores, and an RDMA variant that implements a subset of RoCE v2 in Unreliable Connected mode with Write-with-Immediate, multi-packet messages and whole-message retransmission on timeout, which does not need lossless Ethernet. Integration is into PyTorch DistributedDataParallel and TensorFlow via Horovod. As the extracted text reads, the RDMA variant was not yet integrated with the ML frameworks.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| End-to-end training speedup (headline) | up to 5.5× | real-world benchmark models | Abstract |
| Microbenchmark speedup vs NCCL | up to 2.9× (RDMA), 9.1× (TCP) | tensor aggregation | §1 |
| End-to-end speedup, 16 workers | 1.13–2.27× vs NCCL-RDMA; 2.05–5.55× vs NCCL-TCP | four network-bound models, 100 Gbps, incl. data loading | §6.2, Fig. 5 |
| Batch speedup vs NCCL-RDMA | at most 2.1× | 8 workers, 100 Gbps | §6.2, Fig. 4 |
| Goodput vs line rate by payload size | 63% (32 el.), 77% (64 el.), 93% (256 el.) | header overhead | §5 |
| Extra latency per recirculation pass | 520 ns | 256-element config | §5 |
| Worker bandwidth with loopback config | 16 × 100 Gbps | 256-element packets | §5 |
| Workers per pipeline | 16–64 | depends on network speed | §6.3 |
| Switch memory use | less than 10% of resources | testbed | §6.3 |
| Loss where SwitchML beats Gloo/NCCL | 0.1% and higher | uniform per-link loss, 1 ms timeout | §6.3, Figs. 6–7 |
| Communication share of batch time | >50% for all but three workloads (10 Gbps); ≥17% for half (100 Gbps) | 8 DNNs, 8 P100 workers | §2.2, Table 1 |
| Projected scale with hierarchy | 240 workers (2 tiers), 3,600 (3 tiers) | projection, not measured | §7 |

Testbed (§6): 8 single-P100 machines (16 for scaling runs), a Wedge100BF-65X Tofino switch, 10 and 100 Gbps links. UGATIT, SSD and ResNet are not network-bound at 100 Gbps (§6.2).

Inconsistencies and caveats inside the paper:
- §1 says a switch can serve "up to 64 nodes at 100 Gbps or 256 at 25 Gbps", but the 256-element configuration evaluated leaves 16 × 100 Gbps for workers (§5), and §6.3 gives 16–64 workers per pipeline. (Own analysis) The 64-node figure is not the configuration that was measured.
- §1 claims up to 2.9× over NCCL-RDMA, above the "fundamental 2×" advantage of in-network aggregation over RAR that §6.2 invokes. §6.2 attributes the excess to NCCL's RAR not reaching its theoretical efficiency; §6.1 itself does not state the 2.9× figure in the text I read.
- The 5.5× headline is against NCCL over TCP; against NCCL-RDMA the end-to-end maximum is 2.27× (Fig. 5).
- The repo README describes integration as an NCCL plugin and a TNA/BFRuntime controller, which differs from the paper's PyTorch DDP / Horovod integration; the code has evolved since publication.

## Limitations

- **Single rack, single job, dedicated bandwidth.** The prototype targets one top-of-rack switch and assumes dedicated bandwidth for training (§1, footnote 6). Multi-rack is discussed only as a hierarchical design with projected sizes (§7). Multi-tenancy needs per-job pools plus admission control, left to follow-up work such as ATP (§7).
- **No congestion control.** Self-clocking is "rudimentary flow control", argued to suffice in dedicated ML networks (§7).
- **Failures delegated.** Worker, link and switch failures are left to the framework (footnote 6).
- **Dense, synchronous all-reduce only.** The slot pool assumes every worker contributes every chunk; stragglers stall a slot, and at 1% loss some slots are hit unevenly with no work-stealing to rebalance (§6.3). (Own analysis) sparse or compressed updates do not map onto fixed-offset slots.
- **Host-side cost.** Float-to-fixed conversion is negligible at 10 Gbps but becomes significant at 100 Gbps (§6.3); the lossy format is validated empirically (Fig. 2, Appendix E).
- **Hardware specificity.** Requires a programmable switch (Tofino) in the path. (Own analysis) The design ideas (host-owned reliability, slot pools, fixed-point aggregation) are less tied to one chip than the P4 artifact is.

## Relation to other systems

- **Ring all-reduce (NCCL, Gloo, Horovod):** host-only, bandwidth-optimal among host schemes, but each worker sends and receives roughly twice what in-network aggregation needs (§3). SwitchML replaces the collective, not the framework.
- **Parameter servers / Parameter Hub:** aggregate on servers (PHub is cited in §8 as rack-scale PS aggregation); §6.1 shows dedicated PS with twice the machines still does not match SwitchML's DPDK path, and co-located PS is about half of dedicated.
- **Mellanox SHARP:** fixed-function aggregation on InfiniBand. SwitchML runs on standard Ethernet with its own loss recovery and on programmable hardware that can still do other work (§8).
- **DAIET:** the closest prior work, described as an initial but incomplete proposal (§8). (Own analysis) SwitchML adds loss recovery, quantization and a full implementation.
- **iSwitch:** FPGA aggregation for RL at 4×10 Gbps storing whole gradient vectors; SwitchML claims 40× higher throughput (§8).
- **ATP (NSDI 2021):** follow-up cited in §7 and §8 as addressing the multi-job setting that SwitchML leaves open.

## Takeaways for practice

- The useful abstraction is a **bounded streaming window over a reduction**: a fixed pool of slots sized to the bandwidth-delay product, deterministic chunk-to-slot mapping, and responses as credits.
- **Push reliability to the endpoints** and keep the in-network state minimal (shadow copy + bitmap). This avoids needing lossless fabrics (PFC) for the RDMA path.
- In-network aggregation helps only when jobs are **network-bound**; check the communication share per model first (Table 1 style profiling). In the paper DeepLight and LSTM gain most and BERT/NCF less (§6.2); (Own analysis) many-small-tensor models likely need tensor fusion before a transport change matters.
- A scheduler that places jobs on such hardware must treat **switch aggregator memory as a schedulable, per-job resource** with admission control, and must keep a job's workers under the aggregating switch (rack locality).
- Compare against NCCL-RDMA; TCP-baseline headlines overstate the gain.

## References

- Paper (NSDI 2021): https://www.usenix.org/conference/nsdi21/presentation/sapio
- PDF: https://www.usenix.org/system/files/nsdi21-sapio.pdf
- arXiv: https://arxiv.org/abs/1903.06701
- Code: https://github.com/p4lang/p4app-switchML
