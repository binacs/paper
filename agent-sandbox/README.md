# Agent Sandbox

Isolation and fast-start execution environments for untrusted code: microVMs and user-space kernels, serverless start-up techniques, and the sandboxes that coding agents and RL rollouts run in. `*` marks featured entries.

**Contents:** [Isolation primitives](#isolation-primitives) · [Fast start: snapshots, forking, caching](#fast-start-snapshots-forking-caching) · [Agent execution platforms](#agent-execution-platforms) · [Benchmarks & agent interfaces](#benchmarks--agent-interfaces)

Entry format follows [CLAUDE.md](../CLAUDE.md). Within a section: newest first.

## Isolation primitives

### * AWS Firecracker

- **Paper:** [Firecracker: Lightweight Virtualization for Serverless Applications](https://www.usenix.org/conference/nsdi20/presentation/agache) — Amazon Web Services · NSDI 2020
- **Why:** A minimal Rust KVM VMM giving VM-level isolation at container-like density and boot time; the isolation primitive behind Lambda and Fargate and many agent sandboxes.
- **Code:** [firecracker-microvm/firecracker](https://github.com/firecracker-microvm/firecracker)
- **Deep read:** [deep-read note](aws-firecracker/nsdi20-firecracker-lightweight-virtualization-for-serverless-applications.md)

### Google gVisor

- **Project:** [gVisor documentation](https://gvisor.dev/docs) — Google · project site
- **Why:** An application kernel in Go that serves container syscalls in user space; the other common answer to "containers are not a security boundary".
- **Code:** [google/gvisor](https://github.com/google/gvisor)

### Containers vs microVMs, measured

- **Paper:** [Blending Containers and Virtual Machines: A Study of Firecracker and gVisor](https://dl.acm.org/doi/10.1145/3381052.3381315) — University of Wisconsin-Madison · VEE 2020
- **Why:** Measures how much host-kernel code Firecracker, gVisor and plain containers exercise, and what each costs in performance; the best single read for choosing between them.

## Fast start: snapshots, forking, caching

- [Memory snapshots: Checkpoint/restore for sub-second startup](https://modal.com/blog/mem-snapshots) — Modal · Blog 2025 — gVisor checkpoint/restore of initialised container memory and file state; why: shows snapshot/restore working in a production multi-tenant platform.
- [Catalyzer: Sub-millisecond Startup for Serverless Computing with Initialization-less Booting](https://dl.acm.org/doi/10.1145/3373376.3378512) — SJTU IPADS, Ant Financial · ASPLOS 2020 — restores from checkpoints and forks from template sandboxes (sfork) on gVisor · [deep read](catalyzer/asplos20-catalyzer-sub-millisecond-startup-for-serverless-computing-with.md); why: start-up cost moves from boot to restore.
- [SOCK: Rapid Task Provisioning with Serverless-Optimized Containers](https://www.usenix.org/conference/atc18/presentation/oakes) — UW-Madison, Microsoft GSL · ATC 2018 — lean containers, generalised Zygote forking and a three-tier package cache · [code](https://github.com/open-lambda/open-lambda) · [analysis](sock/8352e3b-sock-rapid-task-provisioning-with-serverless-optimized-containers.md); why: dependency import, not isolation, often dominates cold start.
- [SAND: Towards High-Performance Serverless Computing](https://www.usenix.org/conference/atc18/presentation/akkus) — Nokia Bell Labs · ATC 2018 — functions of one application as processes in a shared container with a hierarchical message bus; why: trades isolation granularity for chaining latency.

See also [Serverless in the Wild](../distributed-system/misc/2003.03423-serverless-in-the-wild-characterizing-and-optimizing-the.md) (ATC 2020) for cold-start keep-alive policy.

## Agent execution platforms

- [Unleashing autonomous AI agents: Why Kubernetes needs a new standard for agent execution](https://opensource.googleblog.com/2025/11/unleashing-autonomous-ai-agents-why-kubernetes-needs-a-new-standard-for-agent-execution.html) — Google, Kubernetes SIG Apps · Blog 2025 — Agent Sandbox CRDs (Sandbox, SandboxTemplate, SandboxClaim) with gVisor or Kata isolation and warm pools · [code](https://github.com/kubernetes-sigs/agent-sandbox); why: the first upstream Kubernetes API aimed at agent workloads.
- [OpenHands: An Open Platform for AI Software Developers as Generalist Agents](https://arxiv.org/abs/2407.16741) — All Hands AI, CMU, UIUC et al. · ICLR 2025 — agents act through a sandboxed Docker runtime (shell, Jupyter, browser) · [code](https://github.com/All-Hands-AI/OpenHands) · [deep read](openhands/2407.16741-openhands-an-open-platform-for-ai-software-developers.md); why: an open reference for what an agent runtime has to expose.
- RL rollout sandboxes: [Kimi k1.5](https://arxiv.org/abs/2501.12599) §2.6 describes the code sandbox used for RL rewards — see [gpu-training → RL training systems](../gpu-training/README.md#rl-training-systems).

## Benchmarks & agent interfaces

- [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) — Princeton, Stanford · NeurIPS 2024 — purpose-built file viewer, editor and search commands for LM agents · [code](https://github.com/SWE-agent/SWE-agent); why: interface design inside the sandbox changes agent success rates.
- [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770) — Princeton, UChicago · ICLR 2024 — 2,294 real GitHub issues checked by each repo's tests · [code](https://github.com/SWE-bench/SWE-bench); why: the workload that made per-task, reproducible sandboxes a requirement.
