---
title: 'SAND: Towards High-Performance Serverless Computing'
authors:
- Istemi Ekin Akkus
- Ruichuan Chen
- Ivica Rimac
- Manuel Stein
- Klaus Satzke
- Andre Beck
- Paarijaat Aditya
- Volker Hilt
affiliations: 'Nokia Bell Labs'
venue: 'USENIX ATC'
year: 2018
abs_url: https://www.usenix.org/conference/atc18/presentation/akkus
pdf_url: https://files.usenix.org/s3fs-public/cdn/atc18-akkus.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# SAND: Towards High-Performance Serverless Computing

> **Why it matters:** SAND argues that isolation should follow the trust boundary (the application, not the function) and that function-to-function messages should stay on the host, two ideas that recur in later serverless and agent-sandbox runtimes.

## Problem

Serverless platforms of the time (AWS Lambda / Step Functions, IBM Cloud Functions, Apache OpenWhisk) ran each function in its own container and treated every function call the same way, whether it came from outside or from another function of the same application. The paper names two costs (§1, §2):

- **Startup vs. idle waste.** A per-function container either starts cold (cold-call delays "of up to a few seconds" on AWS Lambda, §2.2) or stays warm and holds memory while idle.
- **Chaining overhead.** Internal calls take the same path through a central controller as external ones. In a four-function image pipeline, total runtime on AWS Step Functions and IBM Cloud Functions is "significantly more than the actual time required for function executions" (Fig. 1).

## Core design

### Two-level isolation (application-level sandboxing, §3.1, §4)

- **Container per application per host ("sandbox").** "Each application runs in its own container." Different applications are assumed to need strong isolation from each other.
- **Process per function.** The functions ("grains") of one application run in the same container as separate OS processes. The authors argue that "stronger mechanisms (e.g., containers) are needed only for the isolation among applications."
- **Grain worker and grain instance.** For each grain a sandbox hosts, a dedicated *grain worker* process loads the grain's code and libraries and subscribes to its local queue. On each event it "forks itself to create a grain instance that handles the event message"; the OS reclaims resources on exit. Each request thus gets a fresh copy-on-write process with the interpreter and libraries already initialized.
- **Placement.** Grains per sandbox can differ by host, set by the developer "or automatically by SAND via strategies or heuristics" (§4); no heuristic is described.
- **Runtime constraint.** Only runtimes with native fork work. The grain worker is implemented in Python, and "SAND currently does not support language runtimes without native forking (e.g., Java and NodeJS)" (§9).

(Own analysis) Inside one sandbox, functions are separated only by process boundaries: separate address spaces, but shared filesystem, network namespace, user, kernel, local data and bus. That is no security boundary against a compromised function of the same application. The paper states no intra-application threat model (§3.1 only says such functions "may not need such a strong isolation").

### Hierarchical message bus (§3.2, §4.1)

- **Local bus.** Each host runs a local FIFO queue per grain. If the next grain runs on the same host, the event goes there and the receiving grain worker forks an instance; the call never leaves the host.
- **Global bus (Kafka).** Each grain has a global queue, partitioned for parallelism, carrying cross-host messages and backing up local buses. The Java *host agent* subscribes to the global queues of its host's grains and bridges the two levels.
- **Local-first, asynchronous backup.** The stricter "global-then-local" order "can add additional latency," so the event goes local first and a backup is published globally, asynchronously, "with a condition flag" that the host agent updates to "processing" or "finished". The authors liken this to write-ahead logging.
- **Failure recovery.** Hosts sync consumption progress per partition. After a timeout another host takes over a failed host's partitions, skips finished messages, reprocesses processing ones, and takes no new messages until that backlog is done (§4). SAND "does not guarantee the recovery of functions that make externally-visible side effects."

(Own analysis) This is roughly at-least-once delivery, with idempotency left to the developer. The asynchronous backup leaves a window where a local event has no global copy; the paper does not characterize it.

### Data layers and control plane (§4, §5)

- A local in-memory key-value store per host and a global store (Apache Cassandra) form a two-level data layer that mirrors the bus.
- A frontend server (Java, embeds Jetty, behind nginx) handles deployment and external calls. Multiple frontends can run behind a load balancer.
- Implementation sizes (§5): host agent 7,273 lines of Java, Python grain worker 732 lines, frontend server 461 lines of Java, and an emulator of 764 lines of Python for local testing. The local bus and local data layer interfaces are generated with Apache Thrift.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Event delivery, local vs. global bus (Python client) | 2.90× faster via local bus | Kafka 0.10.1.0, 3 hosts, 3 replicas | §6.2, Fig. 5b |
| Event delivery, local vs. global bus (Java client, used by host agent) | 5.42× speedup | same | §6.2, Fig. 5b |
| Function interaction latency vs. OpenWhisk / Greengrass, warm containers | 8.32× / 3.64× lower in SAND | local installations of both baselines | §6.3, Fig. 5c |
| Same, cold containers | 562× / 358× | same | §6.3, Fig. 5c |
| Memory per extra concurrent call | OpenWhisk ~14.61 MB, Greengrass ~13.96 MB, SAND 1.1 MB (on top of 16.35 MB for the grain worker) | up to 50 concurrent calls to one Python function | §6.4 |
| Idle memory cost reduction | from 3.32× up to two orders of magnitude | workloads A–E, 2,000 calls each, mean 100 calls/min, mean duration 600 ms | §6.5, Fig. 6a, Table 1 |
| SAND call latency in idle-cost experiment | 15.87–16.29 ms | same | §6.5, Fig. 6b |
| OpenWhisk calls hitting cold start (1 s timeout) | 18.15%–33.35% | same | §6.5 |
| Image pipeline overhead | 22.0× lower than OpenWhisk | even after removing time for OpenWhisk features SAND lacks | §6.6, Fig. 7 |
| Image pipeline end-to-end | 43% speedup vs. OpenWhisk | four-function pipeline | Abstract, §1 |

Testbed (§6): Xeon E5520, 16 cores at 2.27 GHz, 48 GB RAM. The startup microbenchmark used a Xeon E5-2609 (4 cores, 32 GB, CentOS 7.4, kernel 4.9.63) with Docker CE-17.11/runc 1.0.0 and Xen 4.8.1/MirageOS 2.9.1.

Startup latency (§6.1, Fig. 5a) is qualitative in the text: fork (C, Python) is fastest, Docker adds significant overhead over plain exec, and `docker exec` into a warm container beats `docker run`. Figure values are not reproduced.

**Inconsistencies / reading cautions noticed in the paper:**
- §3.1 claims "up to three orders of magnitude speedup (§6.1)" for fork over per-call container launch, but the §6.1 text states no numbers. The claim can only be checked against Figure 5a.
- The headline 43% (abstract, §1) is an end-to-end speedup. The 22.0× in §6.6 is a reduction in *overhead* (runtime minus function compute). They measure different things and are easy to conflate.
- §8 says "SAND does not use any sharing nor cache management schemes", yet §3.1 motivates process sandboxing partly by sharing initialized libraries across forked instances. (Own analysis) It holds only in the sense of no cross-grain cache.
- Greengrass is an edge/IoT runtime, chosen because it "can run local installations for a fair comparison" (§6).

## Limitations

- **Weak intra-application isolation.** Grains in a sandbox "compete for the same resources and interfere with each other's performance". SAND relies on the OS for fairness (§9). There is no per-function security boundary.
- **Fork-only runtimes.** Java and Node.js are unsupported (§9). (Own analysis) Fork hazards (threads, sockets, duplicated RNG state) are not discussed.
- **Locality vs. load balance.** The locality-optimized policy "might lead to sub-optimal load balancing" (§9); placement is future work (§10).
- **Recovery semantics.** Side-effecting functions are not guaranteed to recover correctly. The async backup window is not characterized.
- **Small-scale evaluation.** No multi-tenant, multi-host evaluation at scale.
- **Alternatives discussed, not built.** §9: VMs isolate more strongly, unikernels need recompilation per function change, lightweight contexts "may provide the best of both worlds."

## Relation to other systems

All comparisons below are (Own analysis) unless they cite the paper.

- **Firecracker (NSDI 2020).** Makes VM-strength isolation cheap enough per function, the opposite trade-off to SAND's weaker boundary. A SAND-style design maps to one microVM per application with forked processes inside; snapshot/restore plays the role fork plays in the grain worker. (Own analysis)
- **gVisor.** A user-space kernel (runsc) shrinking the host-kernel attack surface behind a container interface. It could replace runc under SAND's per-application sandbox, hardening the *inter*-application boundary but adding nothing between grains. (Own analysis)
- **SOCK / Pipsqueak.** Per §8 these "create a cache of pre-warmed Python interpreters" shared across functions; SAND instead uses a per-grain forked worker, in effect a per-grain zygote. (Own analysis for the comparison)
- **OpenWhisk / Lambda / Step Functions.** The baselines: container per function and a central controller on every call. SAND's wins come from the local bus and from fork instead of container start.
- **Unikernels (MirageOS) and in-process isolation.** §6.1 finds MirageOS starts similar to containers. (Own analysis) WebAssembly runtimes such as Faasm (ATC 2020) pursue the "lighter than processes" direction §9 points to.

## Takeaways for practice

- **Isolate at the trust boundary.** For agent sandboxes: one strong sandbox (microVM or gVisor) per tenant or session, cheap process separation for tools inside, stated plainly as not a security boundary. (Own analysis)
- **Fork from a pre-initialized worker** is a simple warm-start primitive; snapshot/restore generalizes it. (Own analysis)
- **Keep chained calls local.** A host-local queue before a durable global log gave the largest latency wins (§6.2, §6.3), with asynchronous durability if steps are re-executable.
- **Make recovery semantics explicit.** Re-execution is at-least-once; side-effecting tool calls need idempotency keys or a commit protocol. (Own analysis)
- **Locality-first placement fights load balancing**; co-location needs a spill path when a host saturates.

## References

- Paper: https://www.usenix.org/conference/atc18/presentation/akkus
- PDF: https://files.usenix.org/s3fs-public/cdn/atc18-akkus.pdf
- Code / blog: no official code repository is listed on the paper's page.
