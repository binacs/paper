---
title: 'SOCK: Rapid Task Provisioning with Serverless-Optimized Containers'
authors:
- Edward Oakes
- Leon Yang
- Dennis Zhou
- Kevin Houck
- Tyler Harter
- Andrea C. Arpaci-Dusseau
- Remzi H. Arpaci-Dusseau
affiliations: 'University of Wisconsin-Madison, Microsoft Gray Systems Lab'
venue: 'USENIX ATC'
year: 2018
abs_url: https://www.usenix.org/conference/atc18/presentation/oakes
pdf_url: https://www.usenix.org/system/files/conference/atc18/atc18-oakes.pdf
code_url: https://github.com/open-lambda/open-lambda
note_type: deep-read
written_at: '2026-11-25'
---

# SOCK: Rapid Task Provisioning with Serverless-Optimized Containers

> **Why it matters:** It measures which Linux isolation primitives make container start-up slow at high churn. It then shows that a lean container (bind mounts + chroot, no network or mount namespace, pooled cgroups) plus forking from pre-imported "Zygote" interpreters cuts Python cold start to tens of milliseconds. Fast-start agent sandboxes can reuse the same recipe.

## Problem

Serverless handlers are short-lived, so start-up cost dominates. That cost has two sources:

- **Container engines.** Docker-style engines build each instance from union file systems and a full set of namespaces, and these were not designed for hundreds of creates per second.
- **Python itself.** Python start-up is slow, and popular packages take about 100 ms to import and seconds to install (§1).

Platforms hide this by keeping idle instances for minutes or hours, which wastes memory. SOCK is built inside OpenLambda.

## Core design

### Lean-container analysis (§2)

All measurements use an 8-core m510 running Linux 4.13.

- **Bind mounts vs union FS.** At scale, bind-mounting is about 2x faster than AUFS (Fig. 1). The paper does not evaluate overlayfs.
- **Mount namespaces.** A clone copies the host's mount table. About 1500 clones/s are possible with few host mounts, and the rate "approaches zero" as host mounts grow (Fig. 2). `chroot` costs under 1 µs.
- **Namespace cleanup.** Mount and IPC namespace cleanup waits on RCU grace periods and takes tens of ms. It holds no lock, so it adds latency without limiting throughput (Fig. 3).
- **Network namespaces (the main bottleneck).** Creation walks all existing namespaces under a global lock.
  - Unmodified: about 200 containers/s.
  - With IPv6 disabled and costly broadcast code removed: over 400 c/s.
  - Without network namespaces: about 900 c/s (Fig. 4).
- **Cgroups.** Reusing a cgroup is at least 2x faster than creating one, with the best rate at 16 threads (Fig. 5).
- **Implications (§2.4).**
  - Use bind mounts and `chroot` instead of union file systems and mount namespaces.
  - Drop network namespaces, which matter little when traffic already arrives through NAT.
  - Pool cgroups.
  - User and cgroup namespaces were not evaluated.

### Python package study (§3)

The study covers 876K GitHub projects and 101K PyPI packages. Imports are highly skewed (Fig. 6), and installs are costly but mostly compatible: 97% of installable packages can share one local install (§3). That compatibility is what makes a shared read-only install tree possible.

### SOCK containers (§4.1)

- **Root file system.** Four bind-mounted host directories:
  - a read-only shared base;
  - read-only `packages`;
  - read-only handler code;
  - a writable scratch directory.
- **Setup.** `chroot` sets the root. An init process calls `unshare` without mount or network namespaces. The paper does not list the namespaces it keeps.
- **Requests.** They arrive over a Unix domain socket in the scratch directory, so no network namespace is needed. cgroups come from a pool.

### Generalized Zygotes (§4.2)

Each container runs an init process and a Python helper that can pre-import modules and then load a handler. Provisioning takes four steps:

1. The manager passes a Zygote file descriptors for the target container's namespaces and root.
2. The Zygote forks a child, which runs `fchdir`/`chroot` and `setns`.
3. `setns` only partly applies to the caller, so the child forks a grandchild that sits fully inside the new container.
4. The manager moves the grandchild into the container's cgroup.

The handler inherits imported modules through copy-on-write. Zygotes are themselves sandboxed.

### Three-tier cache (§4.3)

- **Handler cache.** Paused idle containers, evicted LRU.
- **Install cache.** A large static set of pre-installed packages, mapped read-only into every container.
- **Import cache.** A tree of Zygotes with different package sets, sharing copy-on-write memory "unbroken by any call to exec".
  - **Lookup.** SOCK picks the entry with the most matching packages and never one with extra packages. On a miss, it extends the closest entry.
  - **Eviction.** Each entry's benefit is the size of its unique packages and its cost is recent uses. The entry with the highest benefit/cost ratio is evicted.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Bind mount vs AUFS | ~2x faster | at scale, m510, Linux 4.13 | §2.1, Fig. 1 |
| Mount-namespace clone rate | ~1500/s, approaching 0 with many host mounts | few vs many host mounts | §2.1, Fig. 2 |
| `chroot` latency | < 1 µs | microbenchmark | §2.1 |
| Container churn, network namespaces | ~200 c/s unmodified; >400 c/s optimized; ~900 c/s without netns | create/destroy throughput | §2.2, Fig. 4 |
| Mount/IPC namespace cleanup | tens of ms | RCU-bound | §2.2, Fig. 3 |
| cgroup reuse vs create | ≥2x faster | best at 16 threads | §2.3, Fig. 5 |
| Import skew | 36% of imports to 0.02% of packages | 876K GitHub projects | §1, §3, Fig. 6 |
| Popular-package cost | 1.6 s download, 2.3 s install, 107 ms import (means) | PyPI packages | §3, Fig. 7 |
| Co-installable packages | 97% of installable packages | single local install | §3 |
| SOCK (no Zygotes) vs Docker | 76 req/s (18x), 130 ms mean latency (19x lower) | 10 concurrent, no-op handler | §5, Fig. 14 |
| Zygote provisioning | additional ~3x throughput | at scale | §5, Fig. 15 |
| Cold start with Zygote / unpause | 32 ms / 3 ms | no-op, concurrency 10 | §5, Fig. 16 |
| Pre-imported package latency | ≥1 s → ~20 ms (≥45x) | import + install caches | §5, Fig. 17 |
| Handler cache hit rate | 18% → 56% when import cache added | 200 requests | §5, Fig. 19 |
| Scalability, median latency | 39 ms (100 handlers); 345 ms (500); 502 ms (10K) | 100K synthetic packages | §5, Fig. 20 |
| Image-resize platform latency | 365 ms cold (2.8x < AWS Lambda, 5.3x < OpenWhisk); 120 ms cold+ | Pillow + boto3 handler, 50 runs | §5, Fig. 21 |

§5 setup: two m510 nodes (package mirror + worker); 5 GB handler cache, 25 GB import cache.

## Limitations

- **Isolation traded for speed.** SOCK relies on chroot, cgroups and the namespaces it keeps. The paper does not discuss seccomp or kernel attack surface. *(Own analysis: a shared kernel without syscall filtering is not enough for untrusted, agent-written code on multi-tenant hosts, and `chroot` is escapable by privileged processes.)*
- **Fork without exec undermines ASLR.** The paper acknowledges this, citing prior work. Code running in a Zygote affects every child forked from it.
- **Runtime scope.** The paper says it is not obvious how SOCK applies to statically linked programs such as most Go binaries. JIT runtimes are future work.
- **Narrow evaluation.**
  - One 8-core host and one kernel version.
  - User and cgroup namespaces not measured.
  - AUFS is the only union FS compared. *(Own analysis: overlayfs and newer kernels change these costs, so re-measure before reusing the numbers.)*
- **Heuristic caching.** The eviction and matching rules are not compared with alternatives.
- **Networking assumption.** All I/O goes through a Unix socket behind NAT. *(Own analysis: agent sandboxes that need per-sandbox egress policy must reintroduce some network isolation and its cost.)*

## Relation to other systems

- **Firecracker (NSDI 2020).** The abstract rejects the choice between heavy VMs and weaker containers and describes a minimal VMM running Lambda and Fargate. SOCK stays on the container side and tunes Linux primitives. In a microVM its namespace findings matter less, but guest boot and init cost then dominate.
- **Catalyzer (ASPLOS 2020).** The abstract describes checkpoint restore with on-demand state recovery and an `sfork` that reuses a running sandbox's state, with sub-millisecond best-case start for virtualization-based sandboxes. It shares SOCK's idea of skipping init on the critical path, but applies it to whole sandboxes. SOCK forks only the interpreter process.
- **SAND (ATC 2018).** The abstract describes application-level sandboxing and a hierarchical message bus, with a 43% speedup over OpenWhisk on image processing. SAND avoids creating containers by grouping an application's functions. SOCK keeps one container per handler and makes each creation cheap.
- **Firecracker/gVisor study (VEE 2020).** The abstract finds that Firecracker and gVisor execute substantially more host-kernel code than native Linux, and that gVisor and Docker run much the same code at different frequencies. Fast start and a small kernel footprint are separate goals. Tyler Caraza-Harter co-authored both papers.
- **Serverless in the Wild (ATC 2020).** The abstract reports that most Azure functions are invoked rarely, with invocation rates spanning about 8 orders of magnitude. It proposes a policy that cuts cold starts with fewer resources. SOCK lowers the cost of each cold start, and this work reduces how often they happen.

## Takeaways for practice

- **Check the primitives first.** Network-namespace creation and mount-namespace cloning can cap sandbox churn. Pre-create or pool network namespaces, and keep the host mount table small.
- **Pool what can be reused.** That includes cgroups, namespaces and scratch directories.
- **Mount shared trees read-only.** Read-only bind mounts plus one writable scratch dir can replace per-sandbox layered images. Benchmark overlayfs on your own kernel.
- **Share installed dependencies.** One shared, read-only dependency tree removes per-session `pip install` seconds.
- **Fork from warm interpreters.** Fork agent tool runtimes from interpreters with common tooling already imported (~20 ms in the paper). Never run tenant code inside a shared Zygote.
- **Layer isolation on top.** Put SOCK-style tricks inside a stronger boundary (microVM or gVisor), or pair them with snapshot/restore.
- **Pair fast start with retention policy.** Unpausing a sandbox (3 ms) is still about 10x cheaper than a Zygote cold start (32 ms).

## References

- Paper: https://www.usenix.org/conference/atc18/presentation/oakes
- PDF: https://www.usenix.org/system/files/conference/atc18/atc18-oakes.pdf
- Code: https://github.com/open-lambda/open-lambda
- Related (abstracts): https://www.usenix.org/conference/nsdi20/presentation/agache · https://asplos.hosting2.acm.org/wp/wp-content/uploads/2020/abstracts/paper_5_0.html · https://www.usenix.org/conference/atc18/presentation/akkus · https://conf.researchr.org/details/vee-2020/vee-2020-papers/1/Blending-Containers-and-Virtual-Machines-A-Study-of-Firecracker-and-gVisor · https://arxiv.org/abs/2003.03423
