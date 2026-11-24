---
title: 'Catalyzer: Sub-millisecond Startup for Serverless Computing with Initialization-less Booting'
authors:
- Dong Du
- Tianyi Yu
- Yubin Xia
- Binyu Zang
- Guanglu Yan
- Chenggang Qin
- Qixuan Wu
- Haibo Chen
affiliations: 'Shanghai Jiao Tong University (IPADS), Ant Financial Services Group'
venue: 'ASPLOS'
year: 2020
paper_id: f14446970a5ed7145a6d350e1aff07ca203cece8
doi: 10.1145/3373376.3378512
abs_url: https://dl.acm.org/doi/10.1145/3373376.3378512
pdf_url: https://ipads.se.sjtu.edu.cn/zh/publications/DuASPLOS20.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Catalyzer: Sub-millisecond Startup for Serverless Computing with Initialization-less Booting

> **Why it matters:** It shows that a strongly isolated (gVisor/KVM) sandbox can start in about a millisecond if you stop *initializing* and instead map, lazily restore, or fork already-initialized state, a pattern that now underpins snapshot-based cold starts for functions and agent sandboxes.

## Problem

Serverless platforms want VM-grade isolation and container-grade startup. Containers share the host kernel; full VMs are heavy; gVisor and Firecracker sit in between but still pay large startup costs. The paper breaks gVisor startup into two parts (§2.1–2.2, Fig. 2, Fig. 4):

- **Sandbox initialization**: config parsing, virtualization resource allocation (EPT, KVM memory regions), rootfs mounting via the Gofer I/O process, guest-kernel (Sentry) init. This dominates trivial functions (Python hello).
- **Application initialization**: starting the language runtime (JVM, interpreter), loading classes/libraries. This dominates heavy functions (Java SPECjbb).

Three observations drive the design (§1): most startup time is initialization; a function touches only a small part of the state it built during initialization; and instances of the same function have nearly identical initialized state.

Two existing fixes fall short. **Caching** warm instances (Zygote-style, SOCK, SAND) costs memory when a host carries thousands of functions, the caching policy is hard to tune, and it does not fix tail latency, which cold boots dominate (§2.2). **Plain checkpoint/restore** (gVisor's own restore, "gVisor-restore") removes app initialization, but restore becomes the bottleneck: it eagerly deserializes tens of thousands of kernel objects, copies the whole memory image, and re-opens every file and socket (§2.2, Fig. 6).

## Core design

Catalyzer is built on gVisor (KVM platform). A function's state at a user-annotated **func-entry-point** is saved as a **func-image**. Three boot paths start from progressively "hotter" state (§2.3, Fig. 7, Fig. 10):

- **Cold boot**: create the sandbox from the func-image via restore.
- **Warm boot**: other instances of the function are already running; share their in-memory state.
- **Fork boot**: `sfork` a dedicated *template sandbox* that sits, initialized, at the func-entry-point.

### On-demand restore (§3)

- **Overlay memory (§3.1).** The func-image is mapped into memory instead of copied. Two-layer EPT: a shared, read-only **Base-EPT** per function and a per-sandbox **Private-EPT**, filled by copy-on-write when an EPT violation hits the Base-EPT. Cold boot maps the func-image file; warm boot share-maps an existing Base-EPT.
- **Separated state recovery (§3.2).** gVisor serializes kernel metadata as an object graph that must be deserialized one by one. Catalyzer stores metadata objects contiguously with a relation table so they can be mapped and pointer-fixed rather than deserialized, and reconstructs them in parallel.
- **On-demand I/O reconnection (§3.3).** Files and connections are reopened lazily. An **I/O cache** records the paths and operations seen during a cold boot; warm boots use it as a hint to reconnect what is needed on the critical path, and connect the rest on demand.
- **Virtualization-sandbox Zygote (§3.4).** A generic, function-independent sandbox (KVM resources, base kernel state) is pre-built and then specialized with the function's image, removing sandbox setup from both cold and warm boots.

### sfork: sandbox fork (§4)

A template sandbox is created offline by running the function up to the func-entry-point; a request triggers `sfork`, which clones the template with CoW. Problems a naive fork hits, and the fixes:

- **Multi-threaded runtime (§4.1).** gVisor's Sentry is Go, which is multi-threaded and cannot be forked safely. A **transient single-thread** mode merges all threads into one before sfork and expands them afterwards (732 LoC in the Go runtime, §5).
- **Shared files and fds (§4.2).** A **stateless overlay rootFS** keeps all rootfs writes in memory, so CoW clones them and inherited read-only fds stay valid in the child.
- **PID- and namespace-dependent state.** Table 1 sorts syscalls into denied, handled (e.g., `clone`, `getpid`, `gettid`; `mmap`/`munmap` by sfork; `read`/`newfstat` by the overlay FS; `accept`/`listen` reconnected) and allowed.
- **Shared mappings.** The only host-kernel change is a new **CoW flag for shared memory mappings**, so a child does not inherit a live `MAP_SHARED` region, which would break parent/child isolation.
- **Language-runtime templates (§4.3).** One template per language (e.g., a warmed JVM) gives cold-boot speed to lightweight functions without a per-function template.

### Implementation (§5)

About 2,017 LoC changed in gVisor, 732 LoC in the Go runtime, about 5,000 LoC of Go for init-less booting, a roughly 300-line C kernel module and a 500-line Go manager. To build a func-image, the func-entry-point annotation becomes a syscall; when that syscall is invoked, Catalyzer saves the program state. Extra engineering (§6.7): disabling PML, caching KVM allocations, and a lazy `dup` in the Gofer.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| gVisor sandbox initialization | 22.3 ms | gVisor boot path | §2.2, Fig. 2 |
| gVisor-restore guest-kernel recovery | 135.9 ms | SPECjbb | §2.2 |
| gVisor-restore app memory load | 128.8 ms | SPECjbb, ~200 MB memory | §2.2 |
| Kernel objects recovered by gVisor-restore | >37,838 | SPECjbb | §2.2 |
| gVisor-restore total startup | ~400 ms | Java SPECjbb | §2.2 |
| Boot-path targets | cold 40 ms / warm 12 ms / fork 1 ms | overview figure labels | §2.3, Fig. 7 |
| Fork boot (sfork) | 0.97 ms | C-hello | §6.2 |
| Zygote boot | 5 ms (C), 14 ms (Java) | Catalyzer-Zygote | §6.2 |
| Restore vs. Zygote | ~30 ms extra | Catalyzer-restore | §6.2 |
| Java cold boot | 29.3 ms (template) vs. 659.1 ms (gVisor) vs. 89.4 ms (native) | Java runtime template | Table 2 |
| Overlay memory saving | 261 ms | SPECjbb, vs. gVisor-restore | §6.3 |
| Separated state loading | 6.3x (Django), 7.0x (SPECjbb) faster kernel load | breakdown | §6.3 |
| Lazy I/O reconnection saving | >57 ms | Django and SPECjbb | §6.3 |
| DeathStar startup speedup | 35x–67x | sfork | §6.4 |
| Pillow end-to-end speedup | 4.1x–6.5x (fork), 3.6x–4.3x (cold) | image functions | §6.4 |
| Boot share of e-commerce Java latency | 34%–88% (gVisor) to <5% (Catalyzer) | Ant Financial functions | §6.4 |
| Warm-boot metadata + I/O cache | 165.9 KB (C-Nginx) to 683.0 KB (SPECjbb); I/O cache ≤2.4 KB | per function | §6.5, Table 3 |
| SPECjbb template sandbox memory | >200 MB | fork boot | §6.5 |
| Startup under load | <10 ms | 0–1,000 running instances | §6.6 |
| PML disabled | 5–8 ms saved | KVM memory-region setup | §6.7 |
| kvcalloc overhead | up to 1.6 ms, cut to <50 µs | KVM allocation cache | §6.7 |
| Gofer lazy dup | 10–20 ms saved | | §6.7 |

Microbenchmarks ran on an 8-core i7-7700 with 32 GB; end-to-end and scalability runs used a 96-core, 256 GB server (§6.1).

## Limitations

- **The sub-ms number is fork boot only.** It needs a live template sandbox per function (or per language), which is the memory-for-latency trade the paper criticizes in caching; a SPECjbb template exceeds 200 MB (§6.5). Cold boot from a func-image is tens of ms.
- **Single-host scope.** Func-images are mapped from local files. The paper does not cover remote snapshot storage, cross-host distribution, or page-fault latency when the image is not in page cache, which later snapshot systems and Modal's blog report as the main tail cost.
- **Correctness of resumed state.** Cloned instances share ASLR layout (§6.8; mitigated by periodically regenerating func-images/templates), and potentially RNG seeds and cached credentials or time. Live network connections are reconnected, not preserved.
- **Engineering depth.** Requires gVisor and Go-runtime changes plus a host-kernel flag; tied to KVM-mode gVisor. No GPU state is captured.
- **Lazy restore moves cost into execution.** The paper does not model working-set prefetching; later work (e.g., REAP-style record-and-prefetch) targets that gap.

## Relation to other systems

- **gVisor (checkpoint/restore).** Catalyzer's baseline. gVisor restore eagerly deserializes the object graph and copies memory; Catalyzer maps memory (overlay EPT), maps metadata (separated recovery), and reconnects I/O lazily, turning a ~400 ms restore into tens of ms.
- **SOCK.** Applies the Zygote idea to serverless with container-based, cached, pre-imported Python runtimes (§2). Catalyzer brings the same idea to a virtualization sandbox (§3.4) and adds restore and fork for state SOCK cannot cache. SOCK's isolation is container-level.
- **SAND.** Lets instances of the same application share a sandbox (§2), trading isolation between instances for latency. Catalyzer gives each instance its own sandbox and shares only read-only state via Base-EPT/CoW.
- **Firecracker.** Cited as booting a microVM plus minimized Linux kernel in about 100 ms (§1/§2), without removing app initialization. Firecracker's later snapshot/restore (not discussed in the paper) applies the same "restore initialized state" idea at the microVM level, with mmap-backed lazy memory loading similar to overlay memory. It does not offer an sfork-style in-memory clone primitive.
- **Replayable Execution.** Checkpoint/restore with on-demand paging reaching 54 ms JVM boot (§7), but only for container-based systems (§2).
- **Modal memory snapshots (public blog).** A production descendant of the same idea on gVisor: checkpoint the container just before it accepts requests (after `snap=True` lifecycle hooks), then restore with background page loading that prioritizes pages a process is blocked on, plus page-cache preloading via a FUSE file server. Snapshots are created on demand per worker host and must match CPU features; GPU state is rebuilt after restore. Modal reports restore "about 2.5x faster than a standard container startup" (blog). Unlike Catalyzer, it targets seconds-scale ML imports across a fleet rather than ms-scale fork on one host, and has no fork path.

## Takeaways for practice

- **Remove initialization, not boot.** For heavy runtimes (JVM, Python with torch), app init dwarfs sandbox setup; snapshot after imports/model load at an explicit entry-point hook.
- **Restore must be lazy and mapped.** Eager deserialize-and-copy restore can be as slow as booting. Map images CoW, store kernel/runtime metadata in a mappable layout, and reconnect I/O on demand with a recorded hint list.
- **Tiered boot paths.** A scheduler can choose among fork (template resident, ~1 ms, high memory), warm (share a running instance's base pages), and cold (from image). Which functions get templates is a cache-placement decision driven by invocation rate and template memory footprint.
- **Share read-only base state across tenants of one function.** Base-EPT/CoW makes per-instance memory cost the dirty set, which raises density; but audit what is shared (ASLR, RNG, secrets) and refresh images periodically.
- **Snapshot locality matters.** Catalyzer's numbers assume a local, page-cached image. In a cluster, route requests to hosts that hold the image or prefetch the recorded working set.
- **For agent sandboxes,** sfork-style cloning of a prepared environment at an entry point is the right abstraction; plan for fd/network re-establishment and per-clone identity reset.

## References

- Paper: https://dl.acm.org/doi/10.1145/3373376.3378512 (PDF: https://ipads.se.sjtu.edu.cn/zh/publications/DuASPLOS20.pdf)
- Project page: https://ipads.se.sjtu.edu.cn/_export/xhtml/pub/projects/catalyzer
- Modal memory snapshots blog (comparison): https://modal.com/blog/mem-snapshots
