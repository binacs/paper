---
title: 'Blending Containers and Virtual Machines: A Study of Firecracker and gVisor'
authors:
- Anjali
- Tyler Caraza-Harter
- Michael M. Swift
affiliations: 'University of Wisconsin-Madison'
venue: 'VEE'
year: 2020
paper_id: 800fc573b10b5461dcafd438508a1ddc2e68449e
doi: 10.1145/3381052.3381315
abs_url: https://dl.acm.org/doi/10.1145/3381052.3381315
pdf_url: https://pages.cs.wisc.edu/~swift/papers/vee20-isolation.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Blending Containers and Virtual Machines: A Study of Firecracker and gVisor

> **Why it matters:** It measures, at the level of executed host-kernel lines, how much of the host kernel Docker-style containers, gVisor and Firecracker actually exercise, and shows that "moving the kernel out" (gVisor's Sentry, Firecracker's guest kernel) shrinks the syscall surface but not the host kernel code those systems end up running.

## Problem

Serverless and multi-tenant platforms choose between processes, containers, and "blended" isolation that moves OS functionality out of the host: gVisor (a user-space kernel) and Firecracker (a KVM microVM). The usual security argument for the blended designs is a smaller host-kernel attack surface, usually stated as "fewer host syscalls allowed". The paper asks two questions: (1) how much, and which, host-kernel code each platform really executes, and how often; (2) what each costs in CPU, network, memory and file-access performance relative to native Linux. It uses kernel line coverage as a proxy for exposed attack surface, explicitly as a hint rather than a security proof (§8).

## Core design

This is a measurement study; the "design" is the methodology and the platforms.

**Platforms (§2).**
- *LXC* (run via Docker): host kernel serves every syscall; Docker's default seccomp profile blocks 44 of ~350 syscalls (Table 1). Network via a host bridge; storage via overlayfs on ext4.
- *gVisor* (§2.3): the Sentry, a Go user-space kernel inside a seccomp sandbox, implements most of the syscalls it supports and itself calls only a small allow-list of host syscalls. A per-container Gofer process mediates file-system access so a compromised Sentry cannot open host files directly. Networking uses netstack (a Go TCP/IP stack in the Sentry) or an optional host-networking mode. Syscall interception via ptrace or KVM; all experiments use the KVM platform.
- *Firecracker* (§2.4): a Rust VMM on KVM, one host process per microVM, virtio block and net devices backed by host files and TAP devices, rate limiters, a jailer that sets up cgroups/namespaces and drops privileges, and a seccomp allow-list.

**Coverage methodology (§3.1).**
- Linux v5.4.13 instrumented for gcov/lcov (lcov 1.14) on a CloudLab xl170 (10-core Xeon E5-2640v4, 64 GB, SATA SSD, 10 GbE), Ubuntu 18.04; gVisor release-20200127.0 (KVM mode), Firecracker v0.19.1.
- Each workload runs ten minutes; lcov gives per-line hit counts. A line counts for a platform only if its hit rate exceeds that of a ten-minute idle-host profile, which removes roughly 10k–15k lines per platform; some noise remains (§3.1, §8).
- Results are broken down by subsystem (/virt, /arch/x86/kvm, /net, /mm, /fs, ext4, overlayfs) as Venn diagrams and flame graphs.

**Workloads.** sysbench CPU plus an LLC probe (§4); iperf3 between two machines over 10 GbE, single and ten instances, plus RTT (§5); an mmap microbenchmark that allocates 1 GB in chunks of 4 KB–1 MB, touches one word per page, with and without munmap (§6); sequential reads/writes of varying sizes on a 1 GB file, with cold/warm host and guest caches (§7). Firecracker microVM: 1 vCPU, 8 GB RAM, 4 GB disk; containers capped at 8 GB with `docker run --memory` (§3.1). **No startup/boot time is measured.**

**Key findings.**
- Syscall allow-lists shrink by an order of magnitude, yet executed host-kernel lines rise above native for every platform, and gVisor executes as many lines as LXC (Table 2). Much of the extra code is conditional paths inside functions native Linux also runs, not new functions (§8; no fraction given).
- gVisor and LXC exercise largely the same host code (bridge, net core, mm, ext4, overlayfs) at different frequencies, so gVisor *duplicates* functionality rather than removing it (§5.2, §7.1, §8).
- Firecracker lowers invocation frequency and touches less fs/mm/net code (no overlayfs, no directory operations, TCP in the guest), but adds KVM emulation code (§4.1, §5.2, §7.1).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Host syscalls allowed, LXC | all but 44 of ~350 | Docker default seccomp | Table 1, §3.2 |
| Host syscalls allowed, Firecracker | 36 | seccomp allow-list | Table 1, §3.2 |
| Host syscalls allowed, gVisor | 53 (68 with host networking) | Sentry allow-list | Table 1, §3.2 |
| Host kernel lines executed, native | 63,163 (7.83%) | union over workloads, of 806,318 lines | Table 2, §3.3 |
| … Firecracker | 77,392 (9.59%) | same | Table 2, §3.3 |
| … LXC | 90,595 (11.23%) | same | Table 2, §3.3 |
| … gVisor | 91,161 (11.31%) | same | Table 2, §3.3 |
| CPU workload lines shared by all three | 35,692 | sysbench CPU | Fig. 4a, §4.1 |
| CPU workload footprint | ~78k (gVisor) vs ~49k (Firecracker) LOC | sysbench CPU | Fig. 4a, §4.1 |
| CPU throughput | similar across platforms; −23% per instance at 10 instances | sysbench, 10 s | Fig. 5a, §4.2 |
| Single-stream TCP bandwidth, gVisor | 0.805 Gbps (host and Firecracker highest, LXC slightly lower) | iperf3, 10 GbE, netstack | Fig. 8, §5.3 |
| Aggregate TCP bandwidth, gVisor | 3.294 Gbps | 10 instances | Fig. 8, §5.3 |
| RTT | host 146 µs, LXC 149 µs, gVisor 319 µs, Firecracker 371 µs | two machines, 10 GbE | Table 3, §5.3 |
| `do_mmap()` calls | LXC >1M, gVisor 5,382, Firecracker 3,741 | mmap benchmark | §6.2 |
| `zap_page_range_single()` calls | gVisor 459,984; LXC and Firecracker 0 | mmap benchmark | §6.2 |

Memory and file throughput appear only as plots (Figs. 14–17, 19–20). gVisor is slowest at allocation and first touch for small mmap sizes and catches up as sizes grow (attributed to two levels of page mapping); Firecracker and LXC track native except when unmapping, suspected TLB-shootdown cost (§6.3). Firecracker writes far faster because its guest does not write back to storage; a warm guest cache reads about twice as fast as a warm host cache; gVisor is slightly slower for small writes (§7.2).

## Limitations

- **Coverage is not attack surface.** Executed lines say nothing about exploitability or about which code is reachable by an attacker-controlled input; the paper says so itself (§8). Coverage also depends on the workloads chosen.
- **Microbenchmarks only.** No real applications; the authors note Firecracker's lack of Docker integration made containerised benchmarks hard (§8).
- **No startup or density measurements.** For serverless/sandbox use, cold-start latency and per-instance memory overhead are central, and the study does not measure them.
- **Background filtering is approximate** (§3.1, §8).
- *(Own analysis)* Configurations are not resource-equalised: Firecracker gets 1 vCPU, while the containers are only memory-capped, so multi-instance comparisons (e.g. the 23% CPU drop, Fig. 8 aggregate bandwidth) mix isolation cost with scheduling and CPU allocation.
- *(Own analysis)* Firecracker's write advantage is a durability-semantics artefact (the guest does not write back), not a speed-up a production system can rely on.
- *(Own analysis)* Several causal explanations (netstack being less optimised, Sentry memory management driving `zap_page_range_single`, TLB shootdowns) are hypotheses, not profiled root causes.
- **Dated.** Measurements are of gVisor release-20200127.0 and Firecracker v0.19.1 on Linux 5.4. Both projects have changed considerably since (e.g. gVisor has added new syscall-interception platforms and reworked its file-system path; Firecracker has added features such as snapshotting), so the absolute numbers should be treated as historical context, not current behaviour. No newer numbers are implied here.

## Relation to other systems

This section is the note's own framing from the cited systems' public descriptions; it uses no figures from them.

- **Firecracker (Agache et al., NSDI 2020):** the designers' paper argues for minimal device emulation, a jailer and a tight seccomp policy, and focuses on boot time, density and the VMM's own small code base. This study is complementary and more skeptical: the VMM is small, but the host kernel paths it drives (KVM, TAP, block-backing files) still add executed host code beyond native.
- **gVisor documentation:** gVisor's security model counts the reduced host-syscall set and the Gofer split as the main defence. The paper confirms the syscall counts (Table 1) but shows the host still runs bridge, net-core, mm, ext4 and overlayfs code comparable to LXC, so defence-in-depth comes from the narrow interface plus the Sentry, not from reduced host code volume.
- **Kata Containers:** cited in §9 as another VM-backed container runtime (full guest kernel behind an OCI interface). It is not measured; it sits closer to Firecracker's model (and can use Firecracker as a VMM), so the Firecracker results are the nearest proxy.
- **SOCK (Oakes et al., ATC 2018):** same UW-Madison group; optimises container *startup* for serverless (lean containers, zygote-based package caching) and stays at container-level isolation. This paper studies the stronger-isolation side of the trade-off and leaves startup out, so the two read as a pair.
- **Catalyzer (Du et al., ASPLOS 2020):** builds on gVisor and attacks its startup cost with checkpoint/restore and fork-style sandbox cloning. It addresses exactly the dimension this paper omits, while accepting gVisor's isolation model as given.

## Takeaways for practice

- For coding-agent sandboxes, do not equate "fewer allowed syscalls" with "less host kernel exposed". Measure executed host code (kcov/lcov on a test host) for your own workload mix; gVisor at this release exercised as much host kernel as Docker.
- The real benefit of gVisor/Firecracker is the narrow, policy-checked interface (36–68 host syscalls) and a second kernel in front of the host, not a smaller host footprint. Keep the host's seccomp/cgroup/namespace layers hardened in either case.
- Budget the costs by resource: gVisor (2020) hurts single-stream network throughput and small-mmap-heavy workloads (package installs, many small allocations, compilers) most; Firecracker hurts network latency (two TCP stacks) and munmap-heavy workloads; CPU-bound work is close to native on all three.
- Verify durability semantics of virtio-block backends before trusting fast Firecracker write numbers; startup and density are missing here, so pair this study with SOCK/Catalyzer-style startup work and re-measure on current releases.

## References

- Paper: https://dl.acm.org/doi/10.1145/3381052.3381315
- Author PDF: https://pages.cs.wisc.edu/~swift/papers/vee20-isolation.pdf
- Talk slides (authors' group): https://research.cs.wisc.edu/multifacet/papers/vee20_blending_talk.pdf
