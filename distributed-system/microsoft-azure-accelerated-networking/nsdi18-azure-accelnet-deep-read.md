---
title: 'Azure Accelerated Networking: SmartNICs in the Public Cloud'
authors:
- Daniel Firestone
- Andrew Putnam
- Sambhrama Mundkur
- Derek Chiou
- Alireza Dabagh
- Mike Andrewartha
- Hari Angepat
- Vivek Bhanu
affiliations: 'Microsoft'
venue: 'NSDI'
year: 2018
abs_url: https://www.usenix.org/conference/nsdi18/presentation/firestone
pdf_url: https://www.usenix.org/system/files/conference/nsdi18/nsdi18-firestone.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Azure Accelerated Networking: SmartNICs in the Public Cloud

> **Why it matters:** A fleet-scale production account of moving a public cloud's host SDN datapath from CPUs to FPGA SmartNICs while keeping software programmability and serviceability.

## Problem

Azure implements its SDN (virtual networks, load balancing, stateful NAT, ACLs, metering, QoS) in the hypervisor vSwitch, VFP. That software path costs host cores, adds latency and limits single-connection throughput. SR-IOV is fast but bypasses the vSwitch, and with it all SDN policy. The goal is SR-IOV-class performance with host SDN intact.

Section 3 lists eight goals, among them: burn no host cores, keep VFP programmability, support new primitives and roll them out fleet-wide, high single-connection performance, a path to 100GbE+, and retained serviceability. On cost, the paper says a physical core sells for $0.10-0.11/hr, about $900/yr and $4500 over a server's lifetime (§3).

## Core design

### Offload model: VFP stays in charge, GFT caches its decisions

- **Generic Flow Tables (GFT, §2.4).** An exact-match table keyed on VFP *unified flows* (UF): a unique source/destination L2/L3/L4 tuple, possibly across several encapsulation layers. The action is a *header transposition* (HT) saying which header fields to add, remove or change.
- **JIT compilation.** Policy from several controllers is not offloaded rule by rule. VFP's just-in-time flow action compiler emits one stateful exact-match rule per UF, with a composite action covering all policies for that flow; that becomes the GFT entry (§2.4).
- **Exception path (§5.1).** A flow missing from the table is sent to software as an *exception packet*, mostly on a flow's first packet. The FPGA tags it with a marker in the 802.1Q VLAN ID and sends it to a dedicated hypervisor vPort. VFP creates the flow, populates the GFT entry, and either delivers the packet locally or re-injects it to the SmartNIC through the same vPort.
- **Why this works (§3).** "We typically observe at least 7-10 packets including handshakes" per flow, so software handling only the first still offloads most traffic.
- **Hiding the split (§5.1).** A GFT Lightweight Filter driver presents NIC plus FPGA to VFP as one SR-IOV+GFT NIC. Flow creation/deletion, policy and health monitoring stay in the hypervisor, and controllers never see the offload, which made deployment "much less disruptive" (§8.3).

### Flow state, aging and policy updates

- TCP SYN/RST/FIN packets are forwarded and also copied to VFP, which tracks connection state and removes stale rules (§5.1).
- GFT keeps per-flow counters, TCP seq/ACK, state and last-seen time, and periodically DMAs them to VFP, which verifies flows and ages out idle ones (§5.3).
- **Generation IDs (§5.3).** Each flow records the policy generation it was created under; new controller policy increments the SmartNIC's generation ID, and flows are refreshed lazily by treating their next packet as an exception.

### FPGA pipeline (§5.2)

- Two deeply pipelined units, each with four stages: store-and-forward buffer, parser (up to 3 groups of L2/L3/L4 headers), flow lookup/match, flow action.
- Lookup indexes by a Toeplitz hash of the flow key. Simpler hashes and 2-way set-associative caches were tried; the costlier but less collision-prone Toeplitz hash with a direct-mapped L1 won.
- Caches: on-chip direct-mapped L1 of 2,048 flows, and an 8-way set-associative L2 in FPGA-attached DRAM with O(1M) flows, limited only by DRAM capacity.
- Actions are microcode-driven: only entirely new actions need a new bitstream. Per-flow QoS can be added as pipeline stages; its design is out of scope.

### Hardware: why FPGA (§4)

- **ASIC (§4.1.1).** Spec to silicon took "on the order of 1-2 years", so a design must cover SDN requirements "7 years into the future": too rigid for changing policy.
- **Multicore SoC NICs (§4.1.2).** Often "10 µs or more" to get packets into a core; 40GbE needed "nearly 4x the cores" of 10GbE; single-flow performance "does not improve much".
- **Host cores (§4.1.3).** Too expensive (see §3).
- **FPGA (§4.2).** Generic FPGA logic needs 10-20x ASIC area, but the authors estimate about 2-3x overall for this design. The market has two competing vendors, and porting is feasible if planned for. The team averaged fewer than 5 FPGA developers.
- **Board (§4.3).** The FPGA is a "bump-in-the-wire" between NIC and ToR, with 2 PCIe Gen3 x8 links to the CPUs. Gen1 cables a separate NIC through the FPGA and runs at 40Gbps (§6); Gen2 puts an SR-IOV NIC and an Intel Arria 10 on one board at 50GbE. GFT uses about 1/3 of Gen1's Stratix V D5 logic (§5.2). The same hardware also served other accelerators such as Bing ranking and BrainWave (§8).

### Servicing and failure handling (§7)

- **Requirement.** TCP flows and vNICs survive FPGA reconfiguration and FPGA, PF and GFT driver updates.
- **Mechanism.** "Turning off hardware acceleration and switching back to synthetic vNICs". VFP already keeps TCP connections alive across servicing and live migration, so the software path is the safety net.
- **Transparent bonding.** The guest stack never binds to the VF: NetVSC enslaves it and TCP/IP binds only to the synthetic NIC. On VF revocation, transmit moves to the synthetic path automatically; receive is accepted on both. DPDK uses a failsafe PMD bonding VF and synthetic PMDs, so apps see only a temporary slowdown. This was upstreamed to Linux and dpdk.org and is native in Windows Server 2012+.
- **RDMA** is the gap: queue pairs are closed so apps fall back to TCP; transparency for QP-dependent apps is "an open question for the future".
- **Diagnostics (§7.2).** Over 500 metrics per host; programmable capture at every SmartNIC interface; a metadata bus recording how each packet was parsed, matched and acted on; hardware timestamps; automatic state dumps on error.
- **Failures (§8.3).** Rates "remain low", like other passive parts; DRAM fails most. No rates given, and no automatic fallback for an unhealthy FPGA is described beyond software "health monitoring" (§5.1).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Fleet | >1M hosts; all new Azure servers since late 2015 | Production | Abstract |
| One-way TCP latency, no AccelNet | avg 50µs, P99 ~100µs, P99.9 ~300µs | Windows Server 2016 VMs, Gen1 40G, 1M 4-byte pings | §6, Fig. 5 |
| One-way TCP latency, AccelNet | avg 17µs, P99 25µs, P99.9 80µs | Same | §6, Fig. 5 |
| Single-connection throughput | 31Gbps, 0% host CPU (vs ~5Gbps without) | VM to VM | §6 |
| Linux VM latency | 10µs average | Cross-cloud comparison, Nov 2017, Skylake instances | §6, Fig. 6 |
| Azure SQL DB read time | ~1ms → ~300µs average | Production workload | §6 |
| FPGA latency overhead | <1µs | vs. SR-IOV NIC alone | §8 |
| Host CPU for exceptions | <1% core utilization | Production | §8 |
| Gen1 board power | 17-19W | Operational servers, depends on load | §6 |
| GFT logic footprint | ~1/3 of Stratix V D5 | Gen1 | §5.2 |
| Flow cache | L1 2,048 flows (direct-mapped); L2 O(1M) (8-way, DRAM) | GFT pipeline | §5.2 |

Inconsistencies noted in the paper:
- Abstract: "<15µs" VM-VM TCP latency and 32Gbps; §6 measures a 17µs average (Windows) and 31Gbps single-connection. The 10µs (Linux, Fig. 6) and 32Gbps (gateway) figures come from other setups.
- The gateway latency is printed as "<5s" (§6), likely a unit typo; omitted.
- 100Gb+ scaling is claimed (goal 7, §8) but nothing above 40G is measured.
- §2.4/§5.1 put flow insertion in software; §8.2 says it later moved into hardware, undescribed.

## Limitations

- No flow-setup rate or first-packet latency is reported; the design leans on the 7-10 packets-per-flow observation, and short-flow-heavy workloads are not evaluated.
- QoS design is out of scope; RDMA servicing transparency is unsolved; unplanned FPGA failure is not described.
- The authors doubt it suits "anyone beyond a large-scale cloud vendor" yet (§8.1): effort is "certainly higher than software", and high-level FPGA languages were not efficient enough.
- Evaluation is Gen1 at 40G: one microbenchmark plus production anecdotes.

## Relation to other systems

- **VFP (ref. [6]).** Not replaced: AccelNet caches VFP's per-flow decisions in hardware; controllers and policy semantics are unchanged.
- **Catapult (refs. [7, 8]).** The FPGA program and bump-in-the-wire board AccelNet builds on.
- **Cavium LiquidIO II, Netronome Agilio CX.** Embedded-core SmartNICs; performance "not great", and no path to 100G without many cores (§9).
- **ASIC match-action NIC offload (ref. [30]).** "Not very flexible", little room for new actions (§9).
- **SilkRoad.** Stateful L4 load balancing in switch ASICs; AccelNet's policy state is "at least 2 orders of magnitude" beyond switch SRAM, while a NIC can use GBs of DRAM (§9).
- **P4.** Could express parts of GFT but lacks scheduling, QoS, background state updates and programmable transport (§9).

(Own analysis) The slow-path-populates-a-flow-cache pattern resembles OVS's kernel flow caching; AccelNet's contribution is doing it in an FPGA at fleet scale with a servicing story.

## Takeaways for practice

- Keep the policy engine in software and offload only compiled per-flow decisions, so upper layers never see the hardware change.
- Use generation IDs with lazy revalidation instead of bulk invalidation when policy churns.
- Design serviceability first: "the hardest of anything here to get right", it "cannot be bolted on later" (§8.3). Keep a working software fallback and bind the guest to the stable interface, not the accelerated one.
- Stateful transports break fallback: RDMA had no transparent answer. (Own analysis) GPU fabrics with long-lived RDMA QPs face the same servicing problem.
- Build line-rate per-packet diagnostics into hardware; they were the "most constant source of iteration" (§8.2).
- Taking I/O off shared host cores lowered variance and reduced Meltdown/Spectre mitigation impact (§8.3). (Own analysis) A case for dedicated datapath hardware on multi-tenant inference and sandbox hosts.

## References

- Paper: https://www.usenix.org/conference/nsdi18/presentation/firestone
- PDF: https://www.usenix.org/system/files/conference/nsdi18/nsdi18-firestone.pdf
