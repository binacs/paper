---
title: 'Firecracker: Lightweight Virtualization for Serverless Applications'
authors:
- Alexandru Agache
- Marc Brooker
- Andreea Florescu
- Alexandra Iordache
- Anthony Liguori
- Rolf Neugebauer
- Phil Piwonka
- Diana-Maria Popa
affiliations: 'Amazon Web Services'
venue: 'NSDI'
year: 2020
abs_url: https://www.usenix.org/conference/nsdi20/presentation/agache
pdf_url: https://files.usenix.org/s3fs-public/cdn/nsdi20-paper-agache.pdf
code_url: https://github.com/firecracker-microvm/firecracker
note_type: deep-read
written_at: '2026-11-25'
---

# Firecracker: Lightweight Virtualization for Serverless Applications

> **Why it matters:** It showed that a deliberately minimal KVM-based VMM can give VM-grade multi-tenant isolation at container-like density and start latency, and it became the reference design for microVM sandboxes in serverless and, later, untrusted-code execution.

## Problem

AWS Lambda originally isolated functions with Linux containers inside per-customer EC2 VMs. That gives strong isolation between customers but poor packing: Lambda functions can be as small as 128 MB, so a server would need up to 8000 functions to fill its RAM (§2). AWS wanted to run functions from many customers on the same bare-metal host, which needs an isolation boundary safe against untrusted arbitrary Linux binaries.

The paper sets six criteria (§2): **Isolation**, **Overhead and density** (initial target about 10% RAM and CPU), **Performance** (near-native, unaffected by neighbors), **Compatibility** (unmodified Linux binaries), **Fast switching**, and **Soft allocation** (oversubscription: pay for what is used, not what is entitled).

Why containers were not enough (§2.1.1): all tenants share one host kernel, and the main security boundary is seccomp-bpf over the syscall interface. Restricting syscalls trades compatibility for security: a trivial program needs 15 syscalls, while a typical Ubuntu install needs 224 syscalls and 52 ioctls (citing Tsai et al.). Rich kernel interfaces such as /proc have repeatedly leaked information (CVE-2018-17972, CVE-2017-18344). Language-level isolation (V8 isolates, JVM) was rejected because Lambda must run arbitrary binaries (§2.1.2). Classic virtualization fixes isolation but brings density/start-up costs and a large VMM: QEMU has more than 1.4 M lines of code and may need up to 270 syscalls (§2.1.3).

## Core design

**Minimal VMM on KVM (§1.1, §3).** Firecracker keeps KVM in the host kernel but replaces QEMU with a single-purpose VMM in Rust, about 50k lines (96% fewer than QEMU). It started as a fork of Google's crosvm; work focused on removing code (USB, GPU, 9p filesystem), ending with fewer than half of crosvm's lines, then adding about 20k and changing about 30k lines. It omits BIOS, booting arbitrary kernels, legacy device emulation, PCI and VM migration (§1.1). The VMM loads the guest kernel directly, with no bootloader (§5.1). One Firecracker process runs per microVM, and Firecracker reuses Linux for CPU scheduling, memory management, block I/O and TUN/TAP networking (§3).

**Device model (§3.1).** virtio network and virtio block devices (MMIO transport, no PCI), a serial console, and partial i8042 (PS/2 keyboard controller) support. Storage is exposed only as block devices, never as a shared host filesystem, as a security choice: filesystems are large and complex, so passing block I/O keeps the host kernel surface small. The virtio-block implementation is about 1400 lines of Rust.

**API (§3.2).** A REST API on a Unix socket configures kernel, devices, machine config/CPUID, rate limiters, logging/metrics and a metadata service; the minimum is a kernel plus one root block device.

**Rate limiters (§3.3).** Per-device, per-microVM token buckets in the device emulation path limit both operations per second (disk IOPS, network packets/s) and bandwidth, with separate network RX and TX limits. Buckets allow short bursts and a one-time initial burst to speed boot. Limits sit inside the VMM because the host must bound the VMM and host-kernel CPU work a guest can cause, and "we do not trust the guest to implement its own limits." The authors say these limiters are much less flexible than cgroups, and use cgroups for everything else. A key purpose is reserving bandwidth for the control plane and stopping noisy neighbors.

**Defense in depth (§3.4, §3.4.1).** Host hardening against side channels: SMT disabled; KPTI, IBPB, IBRS and L1TF cache-flush mitigations checked; Speculative Store Bypass mitigation on; swap and same-page merging (KSM) off; no file sharing between tenants (Flush+Reload and Prime+Probe); RowHammer-resistant hardware recommended. Power and thermal side channels are out of scope. The **jailer** wraps each VMM in a chroot holding only the binary, /dev/net/tun, cgroup control files and that VM's resources; it uses pid and network namespaces, drops privileges, and applies a seccomp-bpf profile allowing 24 syscalls (each with argument filtering) and 30 ioctls (22 of them required by KVM). A guest that escapes into the VMM is still contained.

**Lambda deployment (§4.1).** Frontend (authenticate, load function metadata) → Worker Manager (stateful sticky router that sends a function's events to as few workers as possible and runs concurrency control) → Placement (decides where slots go, asks workers to create them, leases them with a time-based lease). Each worker host runs "hundreds or thousands" of microVMs. A **slot** is one microVM holding one customer sandbox (minimal Linux kernel plus userland and a shim) and handles one invocation at a time, reused across serial invocations. A per-host **MicroManager** manages the Firecracker processes, provides slot management and locking to Placement and an invoke API to the Frontend, and talks to the in-guest shim over TCP/IP. It keeps a small pool of pre-booted microVMs sized by Little's law (pool = creation rate × creation latency): at 125 ms boot, one pooled VM per 8 creations/s (§4.1.2). Fargate also runs on Firecracker, but the paper gives no detail about how.

**Soft allocation economics (§4.2).** Memory is about 40% of server capital cost, so an idle slot should cost about 40% of a busy one, which requires CPU oversubscription. With N uncorrelated workloads, the ratio of the X-th percentile (for example 99.99%) of demand to mean demand falls roughly as √N. Workloads from the same customer or application count as correlated, so multi-tenancy across customers is what makes packing efficient.

**Migration (§4.3).** From 2018, Lambda moved to Firecracker on bare metal with no availability or latency regression. Slots live at most 12 hours, so changing the recycling logic moved traffic; internal workloads went first, with per-stack metric comparison. Surprises: SMT-off changed timing and exposed client-library bugs; missing DNS caching in the microVM caused one rollback.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| VMM size | ~50k lines of Rust, 96% fewer than QEMU (>1.4M) | Code size | §2.1.3 |
| Jailer seccomp allowlist | 24 syscalls (with arg filters), 30 ioctls (22 for KVM) | Production profile | §3.4.1 |
| Boot to application code | <125 ms | Headline claim | §1, §4.1.2 |
| microVM creation rate | up to 150 per second per host | Headline claim, not measured in §5 | §1 |
| Boot, 99th percentile | 146 ms (FC-pre) vs 158 ms (Cloud Hypervisor); ~153 ms at 100 concurrent | 50 concurrent boots, 1 vCPU/256 MB, m5d.metal | §5.1, Fig. 6 |
| Boot vs QEMU | pre-configured FC and Cloud HV about 2x faster than QEMU | Serial boots, 500 samples | §5.1, Fig. 5 |
| VMM memory overhead | ~3 MB (FC), ~13 MB (Cloud HV), ~131 MB (QEMU) | pmap non-shared segments minus guest size, VM sizes up to 8 GB | §5.2, Fig. 7 |
| Block I/O ceiling | ~13,000 IOPS (52 MB/s at 4 kB) vs >340,000 IOPS bare metal | fio, libaio, QD32, local NVMe, no rate limit | §5.3, Fig. 8 |
| 4 kB read latency | 49 µs slower than native (p99) | QD1 | §5.3, Fig. 9 |
| Network throughput (1 flow) | 15.61 RX / 14.15 TX Gb/s (FC) vs 23.76 / 20.43 (QEMU), 44.14 loopback | iperf3, 1500 MTU tap | §5.3, Table 1 |
| Oversubscription | tested >20x; production up to 10x | Lambda | §5.4 |
| Pre-boot pool sizing | 1 pooled microVM per 8 creations/s | 125 ms boot, Little's law | §4.1.2 |

## Limitations

- **I/O is the weak spot.** virtio-block is serial with no flush-to-disk, capping IOPS far below the device; network is about two-thirds of QEMU/Cloud HV (§5.3). The authors call it "adequate" for Lambda and Fargate.
- **Deliberately narrow features**: no PCI, no device passthrough or accelerators (GPUs), no live migration, no BIOS or arbitrary kernels (§1.1). GPU and accelerator host-bypass at high density is listed as future work (§6).
- **Boot numbers depend on a minimal guest kernel** (Linux 4.14 with no modules, 4.0 MB compressed; §5); a stock distribution kernel would be slower. The 125 ms and 150/s claims in §1 are not reproduced in §5 (§5.4 says "as little as 150 ms").
- **Density gains rule out KSM-style memory deduplication** for side-channel reasons; recovering density without weakening isolation is open (§6).
- **Trusts the host kernel**: KVM and the Linux subsystems Firecracker reuses (about 120k lines for KVM alone, §2.1.3) stay in the TCB.
- **No snapshot/restore in the paper**; fast start relies on a pre-booted pool. Snapshotting was added to the project later (see project docs).

## Relation to other systems

- **QEMU/KVM**: same hypervisor, but QEMU is a general emulator (>1.4M LOC, BIOS, PCI, legacy devices). Firecracker trades generality for about 131 MB → 3 MB VMM overhead and a smaller attack surface.
- **crosvm (ChromeOS)**: Firecracker's starting point; also Rust and KVM. Firecracker cut its device set (USB, GPU, 9p) to fewer than half its lines.
- **Cloud Hypervisor (Intel)**: a sibling Rust VMM with a richer device model; slightly faster boot and network but ~13 MB overhead (§5).
- **Linux containers + seccomp/namespaces**: shared host kernel, isolation bought by shrinking the syscall surface (§2.1.1). Firecracker uses these only as a second layer (jailer).
- **V8 isolates / JVM**: cheaper, but cannot run arbitrary binaries (§2.1.2).
- **Kata Containers**: OCI/CRI lightweight VMs that can use Firecracker as one of several hypervisors (per the Kata site); packaging for Kubernetes, not a VMM.

## Takeaways for practice

- **Choose the boundary by threat model.** For untrusted multi-tenant code, including AI-agent code execution, the paper rejects shared-kernel containers; a hardware-virtualization boundary plus a jailed VMM is the pattern.
- **Today's options, as their official docs describe them** (kept short):
  - *gVisor* puts a user-space application kernel (the Sentry) between the app and the host; its `runsc` is an OCI runtime, systrap is its default platform with KVM as an option, and it supports checkpoint/restore into a new container.
  - *Kata Containers* gives OCI/CRI-compatible lightweight VMs and supports QEMU, Cloud Hypervisor and Firecracker.
  - *Kubernetes agent-sandbox* (SIG Apps) adds a `Sandbox` CRD for a single stateful pod with stable identity, plus `SandboxTemplate`, `SandboxClaim` and `SandboxWarmPool`; it hands isolation to RuntimeClass runtimes such as gVisor or Kata.
- **Warm pools are a queueing problem.** Lambda sizes its pool by Little's law (rate × latency); the same math sizes a `SandboxWarmPool`.
- **Snapshot/restore has a correctness tax.** Firecracker's own snapshot docs warn that restoring one snapshot many times can repeat identifiers, PRNG state and tokens across clones, that the guest clock must be updated, that network connections may not survive, and that snapshot files must be secured by the user. Re-seed entropy and re-establish connections before handing a restored sandbox to an agent.
- **Rate-limit inside the VMM** so one sandbox's I/O cannot starve neighbors or the control plane.
- **Oversubscription works only with decorrelated tenants.** The √N argument (§4.2) means bin-packing across many customers beats per-customer pools. Count one customer's or one agent fleet's sandboxes as correlated load.
- **Plan for weak I/O and no GPUs**: fine for CPU-bound tool use, not for heavy disk or accelerator work.
- **Roll out by recycling.** Short slot lifetimes (≤12 h) made the isolation-layer swap a routing change; expect timing bugs, not functional breakage.

## References

- Paper: https://www.usenix.org/conference/nsdi20/presentation/agache
- PDF: https://files.usenix.org/s3fs-public/cdn/nsdi20-paper-agache.pdf
- Code: https://github.com/firecracker-microvm/firecracker (project site https://firecracker-microvm.github.io/; evaluation data https://github.com/firecracker-microvm/nsdi2020-data)
- Firecracker snapshot docs: https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md
- gVisor docs: https://gvisor.dev/docs/ , https://gvisor.dev/docs/architecture_guide/platforms/ , https://gvisor.dev/docs/user_guide/checkpoint_restore/
- Kata Containers: https://katacontainers.io/
- Kubernetes agent-sandbox: https://github.com/kubernetes-sigs/agent-sandbox
