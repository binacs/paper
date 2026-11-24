# Scheduling System

Cluster managers and schedulers, from Borg-era shared clusters to ML-specific and geo-distributed schedulers, plus the node-level isolation / QoS work they depend on. `*` marks featured entries.

**Contents:** [Monolithic / centralised](#monolithic--centralised) · [Two-level](#two-level) · [Shared-state / optimistic](#shared-state--optimistic) · [Distributed](#distributed) · [ML-specific](#ml-specific) · [Overviews](#overviews) · [Node & cluster](#node--cluster) · [Blogs](#blogs) · [Auto-analyzed papers](#auto-analyzed-papers)

Entry format: `### <System>` then **Paper** (title link — institution · venue year), **Why** (one sentence), and Code / Blog / Analysis links when they exist.

## Monolithic / centralised

One logical scheduler (possibly sharded or replicated) owns placement for the whole cell.

### Google Borg

- **Paper:** [Large-scale cluster management at Google with Borg](https://dl.acm.org/doi/abs/10.1145/2741948.2741964) — Google · EuroSys 2015
- **Paper:** [Borg: the Next Generation](https://dl.acm.org/doi/pdf/10.1145/3342195.3387517) — Google, Harvard · EuroSys 2020
- **Why:** The reference design for shared production clusters (cells, priorities, quotas, Borgmaster); the 2020 paper revisits it with the 2019 trace.

### Meta Twine

- **Paper:** [Twine: A Unified Cluster Management System for Shared Infrastructure](https://www.usenix.org/conference/osdi20/presentation/tang) — Meta · OSDI 2020
- **Blog:** [Efficient, reliable cluster management at scale with Twine](https://engineering.fb.com/2019/06/06/data-center-engineering/twine/) · [Meta Research page](https://research.facebook.com/publications/twine-a-unified-cluster-management-system-for-shared-infrastructure/)
- **Why:** One control plane per region instead of per cluster, with entitlements and host profiles; the substrate MAST builds on.

### Microsoft Protean

- **Paper:** [Protean: VM Allocation Service at Scale](https://www.usenix.org/system/files/osdi20-hadary.pdf) — Microsoft · OSDI 2020
- **Why:** Rule-based VM placement for Azure at very high allocation rates; a good contrast to container schedulers.

### Netflix Titus

- **Paper:** [Titus: Introducing Containers to the Netflix Cloud](https://dl.acm.org/doi/pdf/10.1145/3155112.3158370) — Netflix · ACM Queue 2017
- **Why:** Container management layered on top of EC2 VMs, with a Mesos-based scheduler; an experience report on bringing containers to a VM-native cloud.

## Two-level

A resource manager offers or grants resources; per-framework schedulers decide placement.

### Apache Mesos

- **Paper:** [Mesos: A Platform for Fine-Grained Resource Sharing in the Data Center](https://www.usenix.org/event/nsdi11/tech/full_papers/Hindman.pdf) — UC Berkeley · NSDI 2011
- **Why:** Introduced resource offers so multiple frameworks (Hadoop, MPI, Spark) share one cluster.

### Apache YARN

- **Paper:** [Apache Hadoop YARN: Yet Another Resource Negotiator](https://dl.acm.org/doi/abs/10.1145/2523616.2523633) — Yahoo!, Hortonworks, Microsoft et al. · SoCC 2013
- **Why:** Split Hadoop's JobTracker into a ResourceManager plus per-application masters; the request-based two-level model.

## Shared-state / optimistic

Several schedulers work on a shared view of the cluster and resolve conflicts optimistically.

### * ByteDance Gödel

- **Paper:** [Gödel: Unified Large-Scale Resource Management and Scheduling at ByteDance](https://dl.acm.org/doi/abs/10.1145/3620678.3624663) — ByteDance · SoCC 2023
- **Paper:** [From Bottleneck to Breakthrough: Optimizing Scheduling for Hyperscale Containerized Clusters](https://dl.acm.org/doi/10.1145/3772052.3772240) — ByteDance · SoCC 2025
- **Why:** A Kubernetes-based unified scheduler for online and offline workloads at very large cluster sizes, using partitioned optimistic concurrency; the follow-up pushes scheduling throughput further.

### Google Omega

- **Paper:** [Omega: flexible, scalable schedulers for large compute clusters](https://dl.acm.org/doi/abs/10.1145/2465351.2465386) — Google, UC Berkeley, Cambridge · EuroSys 2013
- **Why:** Defined the monolithic / two-level / shared-state taxonomy used on this page and argued for shared state with optimistic concurrency.

### Microsoft Apollo

- **Paper:** [Apollo: Scalable and Coordinated Scheduling for Cloud-Scale Computing](https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-boutin_0.pdf) — Microsoft · OSDI 2014
- **Why:** Distributed schedulers sharing a global cluster view, with estimated completion times used for placement.

## Distributed

### UC Berkeley Sparrow

- **Paper:** [Sparrow: Distributed, Low Latency Scheduling](https://people.eecs.berkeley.edu/~matei/papers/2013/sosp_sparrow.pdf) — UC Berkeley · SOSP 2013
- **Code:** [radlab/sparrow](https://github.com/radlab/sparrow)
- **Why:** Stateless schedulers using batch sampling and late binding for sub-second tasks.

## ML-specific

### * Meta MAST

- **Paper:** [MAST: Global Scheduling of ML Training across Geo-Distributed Datacenters at Hyperscale](https://www.usenix.org/system/files/osdi24-choudhury.pdf) — Meta · OSDI 2024
- **Why:** Global scheduling of training jobs and their data across regions; the scheduler behind Meta's LLM training fleet.

### Optimus

- **Paper:** [Optimus: an efficient dynamic resource scheduler for deep learning clusters](https://dl.acm.org/doi/10.1145/3190508.3190517) — HKU, ByteDance · EuroSys 2018
- **Why:** Fits online models of training convergence and speed to allocate parameter-server / worker resources dynamically.
- **Analysis:** [optimus/93a06eb-…](optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md)

See also (filed under other topics): [Gandiva](../gpu-training/microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md) (OSDI 2018), [Decima](../distributed-system/decima/1810.01963-learning-scheduling-algorithms-for-data-processing-clusters.md) (SIGCOMM 2019).

## Overviews

### Borg, Omega, and Kubernetes

- **Paper:** [Borg, Omega, and Kubernetes](https://queue.acm.org/detail.cfm?id=2898444) — Google · ACM Queue / CACM 2016 ([CACM HTML](https://dl.acm.org/doi/fullHtml/10.1145/2890784))
- **Why:** Lessons from three generations of Google container management, by their designers.

# Node & Cluster

## Isolation

- [CPI²: CPU performance isolation for shared compute clusters](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/40737.pdf) — Google · EuroSys 2013 — detects and throttles antagonists using CPI outliers.
- [IOCost: Block IO Control for Containers in Datacenters](http://www.cs.cmu.edu/~dskarlat/publications/iocost_asplos22.pdf) — Meta, CMU · ASPLOS 2022 — cost-model-based IO isolation in the Linux cgroup controller.
- [Heracles: Improving Resource Efficiency at Scale](https://dl.acm.org/doi/pdf/10.1145/2749469.2749475) — Stanford, Google · ISCA 2015 — co-locates best-effort work with latency-critical services via a feedback controller over cores, LLC, memory bandwidth and network.

## QoS

- [Reconciling High Server Utilization and Sub-millisecond Quality-of-Service](https://mast.stanford.edu/pubs/reconciling_high_server_utilization_and_sub_millisecond_quality_of_service/paper.pdf) — Stanford · EuroSys 2014 — shows tail-latency interference sources for memcached-style services under co-location.
- [PARTIES: QoS-Aware Resource Partitioning for Multiple Interactive Services](https://dl.acm.org/doi/pdf/10.1145/3297858.3304005) — Cornell · ASPLOS 2019 — partitions resources among several latency-critical services on one server.
- [Sinan: ML-Based and QoS-Aware Resource Management for Cloud Microservices](https://dl.acm.org/doi/pdf/10.1145/3445814.3446693) — Cornell · ASPLOS 2021 — learned models predict QoS violations across microservice graphs.
- [Quasar: Resource-Efficient and QoS-Aware Cluster Management](https://mast.stanford.edu/pubs/quasar_resource_efficient_and_qos_aware_cluster_management/paper.pdf) — Stanford · ASPLOS 2014 — classifies workloads with collaborative filtering instead of user reservations.
- [Thunderbolt: Throughput-Optimized, Quality-of-Service-Aware Power Capping at Scale](https://www.usenix.org/system/files/osdi20-li_shaohong.pdf) — Google · OSDI 2020 — power capping that throttles batch work first.

## Fairness

- [Dominant Resource Fairness: Fair Allocation of Multiple Resource Types](https://www.usenix.org/legacy/event/nsdi11/tech/full_papers/Ghodsi.pdf) — UC Berkeley · NSDI 2011 — max-min fairness on each user's dominant resource; the basis of many multi-resource schedulers.

## Workload & autoscaling

- [Autopilot: workload autoscaling at Google](https://dl.acm.org/doi/pdf/10.1145/3342195.3387524) — Google · EuroSys 2020 — automatic vertical and horizontal scaling of Borg jobs.
- [Towards Energy Proportionality for Large-Scale Latency-Critical Workloads](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/42523.pdf) — Google, Stanford · ISCA 2014 — energy-proportional operation for latency-critical search.

## Building cluster managers

- [Building Scalable and Flexible Cluster Managers Using Declarative Programming](https://www.usenix.org/system/files/osdi20-suresh.pdf) — VMware Research et al. · OSDI 2020 — DCM expresses scheduling policy as SQL constraints solved by a solver.
- [SelfTune: Tuning Cluster Managers](https://www.usenix.org/system/files/nsdi23-karthikeyan.pdf) — Microsoft · NSDI 2023 — online tuning of cluster-manager configuration parameters.

## * Blogs

- [65,000 nodes and counting: Google Kubernetes Engine is ready for trillion-parameter AI models](https://cloud.google.com/blog/products/containers-kubernetes/gke-65k-nodes-and-counting) — Google Cloud · 2024 — how GKE raised cluster scale limits for AI training.

---

## Auto-analyzed papers

_Entries below this line are managed by `paper-bot`. Manual edits are fine; just keep them above the marker._


## Optimus: an efficient dynamic resource scheduler for deep learning clusters (European Conference on Computer Systems 2018)

Paper link: [Optimus: an efficient dynamic resource scheduler for deep learning clusters](https://www.semanticscholar.org/paper/93a06eb066fe58ed7d036e46e4cee53483e16bb8)

Analysis: [optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md](optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md)

<!-- paper-bot:end -->
