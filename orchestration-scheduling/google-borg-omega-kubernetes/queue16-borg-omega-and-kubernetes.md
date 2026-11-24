---
title: 'Borg, Omega, and Kubernetes'
authors:
- Brendan Burns
- Brian Grant
- David Oppenheimer
- Eric Brewer
- John Wilkes
affiliations: 'Google'
venue: 'ACM Queue'
year: 2016
abs_url: https://queue.acm.org/detail.cfm?id=2898444
pdf_url: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Borg, Omega, and Kubernetes

> **Why it matters:** A first-hand account, from the people who built them, of the design lessons from more than a decade of Google cluster management. It explains why Kubernetes looks the way it does: pods, labels, an IP per pod, reconciliation controllers and an API server in front of the store.

## Problem

Google ran Linux containers at scale for more than ten years across three systems. Borg came first. It unified long-running services and batch jobs, which "had previously been handled by two separate systems: Babysitter and the Global Work Queue." Omega was a re-architecture aimed at better software engineering of the Borg ecosystem. Kubernetes is the open-source system, conceived as outside developers took up Linux containers and Google grew its public cloud.

This is an experience piece, not an evaluation: which abstractions worked, which were mistakes, and what is still open. Its main goal for Kubernetes is to make complex distributed systems easy to deploy and manage while keeping the utilization benefits of containers.

## Core design

### Containers and their limits
- Borg co-locates latency-sensitive services with batch work. Services reserve more than they usually use, and batch reclaims the slack. This "enabled Google to drive utilization significantly higher than industry norms."
- Isolation is imperfect. The kernel does not manage resources such as L3 caches and memory bandwidth, so containers cannot stop interference there. Against malicious tenants, containers "need to be supported by an additional security layer (such as virtual machines)."
- Images: the ideal is a hermetic image whose only external dependency is the Linux system-call interface. Borg falls short because tasks share a machine-installed base image, and upgrades to it have caused trouble.

### Application-oriented infrastructure
- Containerization shifts the data center's "primary key" from the machine to the application. Developers are shielded from machine details, operators can upgrade hardware and OS with little impact, and telemetry is keyed by application.
- Health checks: Borg uses a `/healthz` endpoint. Kubernetes uses a user-specified HTTP endpoint or an exec command. An unhealthy instance is killed and restarted, which the authors call a key building block for reliable distributed systems.
- Two-level container: Borg's *alloc* and Kubernetes' *pod*. Kubernetes always runs an app inside a top-level pod, even with only one container. Helpers such as a log rotator run beside the main container with their own resources. Logging cannot starve the app, and offloading continues "even if the main application gets wedged."

### Consistent API and decoupled controllers
- Borg's ecosystem (Borg Name Service, Chubby-based master election, load balancing, autoscaling, rollout, workflow and monitoring tools) grew organically, each with an idiosyncratic API, which made deployment harder.
- Kubernetes fixes this with a uniform object shape: ObjectMetadata (name, UID, version, labels), Spec (desired state) and Status (read-only observed state). Generic tools then work on every type.
- Small controllers compose. The ReplicationController keeps N pods. The autoscaler "simply adjusts the desired number of pods" without knowing how pods are created. ReplicationController, DaemonSet and Job are three forms of replicated pod, all built on the common pod object.

### Reconciliation and choreography
- All three systems use control loops that compare desired with observed state and act to converge them. Decisions come from observation, not from a state diagram, so a restarted controller "simply picks up where it left off."
- The authors call Kubernetes "control through choreography": autonomous entities whose collaboration produces the desired emergent behaviour. They contrast this with centralized orchestration, which is easier to build at first but "tends to become brittle and rigid over time."

### Control-plane state: three points in the design space
- **Borg:** a monolithic Borgmaster "knows the semantics of every API operation," holds the job, task and machine state machines, and runs the Paxos-based replicated store.
- **Omega:** a centralized, Paxos-based, transaction-oriented store accessed directly by peer components, such as several schedulers, with optimistic concurrency control for conflicts. All semantics live in the clients. "Many of Omega's innovations (including multiple schedulers) have since been folded into Borg."
- **Kubernetes:** a shared persistent store watched by components, like Omega, but every access goes through "a centralized API server that hides the details of the store implementation and provides services for object validation, defaulting, and versioning."

### Things to avoid (lessons from Borg)
- **Managed host ports.** Borg gives each container a unique host port, which forces DNS replacements and rewrites of tools that expect plain IPs. Kubernetes allocates an IP per pod, so apps can use well-known ports such as 80.
- **Indexed jobs.** A Borg job is "a compact vector of one or more identical tasks, indexed sequentially from zero." Restarts must reuse index slots and exits leave holes. Kubernetes uses mutable, overlapping key-value labels; "label selectors are the grouping mechanism."
- **Hard ownership.** Borg tasks belong to their job for life. In Kubernetes, controllers find pods by label selector, which allows "orphan" and "adopt" operations, such as pulling a misbehaving pod out of a service for debugging while a replacement starts. The cost is that overlapping selectors must be avoided through configuration.
- **Raw state exposure.** Omega's passive store makes every client enforce semantics. The API server is the middle path between Borg's monolith and Omega's raw store.

## Key numbers

The article states very few quantitative figures and no performance measurements.

| What | Value | Setting | Source |
|---|---|---|---|
| Google experience managing Linux containers at scale | more than ten years | Borg, Omega, Kubernetes | Opening section |
| Predecessor systems unified by Borg | 2 (Babysitter, Global Work Queue) | services vs batch | Opening section |
| Basic fields in every Kubernetes object | 3 (ObjectMetadata, Spec, Status) | Kubernetes API | "Orchestration is the beginning, not the end" |
| Forms of replicated pod | 3 (ReplicationController, DaemonSet, Job) | Kubernetes controllers | "Orchestration is the beginning, not the end" |
| Example well-known port enabled by IP-per-pod | 80 (HTTP) | Kubernetes networking | "Don't make the container system manage port numbers" |

Utilization is described only qualitatively ("significantly higher than industry norms", Containers section). No figure is given.

## Limitations

- No quantitative evidence. Claims about utilization, reliability or productivity are not measured in this article; the Borg (EuroSys 2015) and Omega (EuroSys 2013) papers it cites hold the numbers.
- Isolation is incomplete. Interference through unmanaged resources (L3 cache, memory bandwidth) is acknowledged but not solved, and multi-tenant security is pushed to VMs.
- Open problems, stated by the authors:
  - **Configuration.** Configuration absorbs whatever the platform lacks (defaults, validation, template libraries), and domain-specific configuration languages "(eventually)" become Turing complete. The authors suggest keeping data in JSON or YAML and doing computation in a real programming language, and they accept that programmatic configuration is inevitable.
  - **Dependency management.** Systems rarely capture an application's dependencies, transitive ones included. Hand-kept records go stale and automatic tracing misses intent. One idea is to require apps to list their dependencies and block undeclared access. This is unsolved.
- Label-selector ownership trades safety for flexibility: overlapping selectors can conflict, and only configuration discipline prevents it.
- (Own analysis) The article says little about scheduling policy itself: gang scheduling, queueing and quota, fairness, accelerator topology, or federation across clusters. It is about control-plane structure and APIs, not placement algorithms.

## Relation to other systems

- **Borg (Verma et al., EuroSys 2015)** — cited by the article; the quantitative companion. This article explains which Borg choices (host ports, indexed jobs, hard ownership, monolithic master) Kubernetes deliberately reversed.
- **Omega (Schwarzkopf et al., EuroSys 2013)** — cited; introduced the shared-state, optimistic-concurrency scheduler design. The article's lesson is that a raw shared store needs an API server for semantics, and that Omega's multi-scheduler idea flowed back into Borg.
- **Twine (Meta)** — (Own analysis) Also a unified fleet-wide container manager, but with more emphasis on app-aware lifecycle hooks during maintenance and one control plane over many machines, where the article centres on pods and per-cluster controllers.
- **Gödel (ByteDance)** — (Own analysis) A public Kubernetes-based unified scheduler for online and offline work. It applies the Borg-style co-location goal and Omega-style optimistic, multi-scheduler concurrency inside the Kubernetes API model this article describes, aimed at scale beyond the default scheduler.
- **MAST (Meta)** — (Own analysis) A global scheduler for ML training. It works at a level above the single-cluster reconciliation and pod abstractions discussed here: placement across regions and data locality, which the article does not cover.
- **Volcano / Kueue** — (Own analysis) Kubernetes-native batch extensions (gang scheduling, queues, quotas). They are good examples of the article's "consistent API plus small controllers" lesson: they add new object types and controllers, not a separate API, filling the batch-scheduling gap the article leaves open.

## Takeaways for practice

- Make the application, not the machine, the unit of identity, telemetry and scheduling. Give every instance a health check and a way to report status.
- Use a two-level container (pod or alloc) so sidecars get their own resource limits and keep working when the main process wedges.
- Keep one object shape (metadata, spec, status) across all resource types so generic tooling works everywhere.
- Build controllers as small, level-triggered reconcilers over observed state. Prefer composition (an autoscaler that only writes `replicas`) to one orchestrator with a big state machine.
- Put an API server between clients and the state store for validation, defaulting and versioning. Do not let clients mutate raw shared state, even with optimistic concurrency.
- Group with labels and selectors, not array indices. Plan for orphan and adopt workflows, and guard against overlapping selectors.
- Do not rely on containers alone for performance isolation (cache, memory bandwidth) or hostile multi-tenancy. Add interference-aware placement and VM or sandbox layers. (Own analysis) This bears directly on GPU and agent-sandbox platforms.

## References

- Paper: https://queue.acm.org/detail.cfm?id=2898444
- Google-hosted PDF: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44843.pdf
- Google Research page: https://research.google/pubs/borg-omega-and-kubernetes/
