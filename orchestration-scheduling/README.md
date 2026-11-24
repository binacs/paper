# Scheduling System

Cluster managers and schedulers, from Borg-era shared clusters to ML-specific and geo-distributed schedulers, plus the node-level isolation / QoS work they depend on. `*` marks featured entries.

**Contents:** [Monolithic / centralised](#monolithic--centralised) · [Two-level](#two-level) · [Shared-state / optimistic](#shared-state--optimistic) · [Distributed](#distributed) · [ML-specific](#ml-specific) · [Kubernetes batch & AI](#kubernetes-batch--ai-scheduling) · [Overviews](#overviews) · [Node & cluster](#node--cluster) · [Blogs](#blogs) · [Auto-analyzed papers](#auto-analyzed-papers)

Entry format: `### <System>` then **Paper** (title link — institution · venue year), **Why** (one sentence), and Code / Blog / Analysis links when they exist.

## Monolithic / centralised

One logical scheduler (possibly sharded or replicated) owns placement for the whole cell.

### Google Borg

- **Paper:** [Large-scale cluster management at Google with Borg](https://dl.acm.org/doi/abs/10.1145/2741948.2741964) — Google · EuroSys 2015
- **Paper:** [Borg: the Next Generation](https://dl.acm.org/doi/pdf/10.1145/3342195.3387517) — Google, Harvard · EuroSys 2020
- **Why:** The reference design for shared production clusters (cells, priorities, quotas, Borgmaster); the 2020 paper revisits it with the 2019 trace.
- **Deep read:** [deep-read note](google-borg/3a04371-large-scale-cluster-management-at-google-with-borg.md) (EuroSys 2015 paper)

### Meta Twine

- **Paper:** [Twine: A Unified Cluster Management System for Shared Infrastructure](https://www.usenix.org/conference/osdi20/presentation/tang) — Meta · OSDI 2020
- **Blog:** [Efficient, reliable cluster management at scale with Twine](https://engineering.fb.com/2019/06/06/data-center-engineering/twine/) · [Meta Research page](https://research.facebook.com/publications/twine-a-unified-cluster-management-system-for-shared-infrastructure/)
- **Why:** One control plane per region instead of per cluster, with entitlements and host profiles; the substrate MAST builds on.
- **Deep read:** [deep-read note](meta-twine/osdi20-twine-a-unified-cluster-management-system-for-shared.md)

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
- **Code:** [kubewharf/godel-scheduler](https://github.com/kubewharf/godel-scheduler)
- **Deep read:** [deep-read note](bytedance-godel/4f005ef-godel-unified-large-scale-resource-management-and-scheduling.md)

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
- **Deep read:** [deep-read note](meta-mast/c286274-mast-global-scheduling-of-ml-training-across-geo-distributed.md)

### Sia

- **Paper:** [Sia: Heterogeneity-aware, Goodput-optimized ML-cluster Scheduling](https://dl.acm.org/doi/10.1145/3600006.3613175) — CMU, Cornell, Petuum · SOSP 2023
- **Why:** Picks GPU type, count and batch size per job on heterogeneous clusters from online-learned throughput models; the state of the art for goodput-driven DL scheduling.
- **Code:** [siasosp23/artifacts](https://github.com/siasosp23/artifacts)
- **Deep read:** [deep-read note](sia/71de9b9-sia-heterogeneity-aware-goodput-optimized-ml-cluster-scheduling.md)

### Pollux

- **Paper:** [Pollux: Co-adaptive Cluster Scheduling for Goodput-Optimized Deep Learning](https://arxiv.org/abs/2008.12260) — CMU, Petuum · OSDI 2021
- **Why:** Introduced goodput (throughput × statistical efficiency) as the scheduling objective and co-adapts batch size with GPU allocation.
- **Code:** [petuum/adaptdl](https://github.com/petuum/adaptdl)
- **Deep read:** [deep-read note](pollux/2008.12260-pollux-co-adaptive-cluster-scheduling-for-goodput-optimized-deep.md)

### Tiresias

- **Paper:** [Tiresias: A GPU Cluster Manager for Distributed Deep Learning](https://www.usenix.org/conference/nsdi19/presentation/gu) — UMich, Microsoft, Alibaba, ByteDance · NSDI 2019
- **Why:** Schedules DL jobs without knowing their durations, using two-dimensional attained service (GPUs × time) in a discretised MLFQ, and consolidates only placement-sensitive jobs.
- **Code:** [SymbioticLab/Tiresias](https://github.com/SymbioticLab/Tiresias) · **Analysis:** [tiresias/8d2d560-…](tiresias/8d2d560-tiresias-a-gpu-cluster-manager-for-distributed-deep.md)
- **Deep read:** [deep-read note](tiresias/nsdi19-tiresias-a-gpu-cluster-manager-for-distributed-deep.md)

### Optimus

- **Paper:** [Optimus: an efficient dynamic resource scheduler for deep learning clusters](https://dl.acm.org/doi/10.1145/3190508.3190517) — HKU, ByteDance · EuroSys 2018
- **Why:** Fits online models of training convergence and speed to allocate parameter-server / worker resources dynamically.
- **Analysis:** [optimus/93a06eb-…](optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md)

Workload studies and production schedulers:

- [Lucid: A Non-intrusive, Scalable and Interpretable Scheduler for Deep Learning Training Jobs](https://dl.acm.org/doi/10.1145/3575693.3575705) — NTU, Shanghai AI Lab, SenseTime · ASPLOS 2023 — interpretable runtime and interference models for packing jobs · [code](https://github.com/S-Lab-System-Group/Lucid); why: scheduling that operators can explain and debug.
- [MLaaS in the Wild: Workload Analysis and Scheduling in Large-Scale Heterogeneous GPU Clusters](https://www.usenix.org/conference/nsdi22/presentation/weng) — Alibaba, HKUST · NSDI 2022 — two-month trace of Alibaba PAI's ~6,000-GPU cluster · [trace](https://github.com/alibaba/clusterdata) · [deep read](alibaba-pai/nsdi22-mlaas-in-the-wild-workload-analysis-and-scheduling-in.md); why: one of the few public traces of a heterogeneous production GPU fleet.
- [Singularity: Planet-Scale, Preemptive and Elastic Scheduling of AI Workloads](https://arxiv.org/abs/2202.07848) — Microsoft · arXiv 2022 — transparent preemption, migration and resizing of DL jobs via device-proxy checkpointing · [deep read](microsoft-singularity/2202.07848-singularity-planet-scale-preemptive-and-elastic-scheduling-of.md); why: MAST's closest public counterpart at Microsoft.
- [Analysis of Large-Scale Multi-Tenant GPU Clusters for DNN Training Workloads](https://arxiv.org/abs/1901.05758) — Microsoft Research et al. · ATC 2019 — Philly trace: gang scheduling, locality and failures as the causes of low utilisation · [analysis](microsoft-philly/1901.05758-analysis-of-large-scale-multi-tenant-gpu-clusters.md) · [deep read](microsoft-philly/1901.05758-philly-deep-read.md); why: the workload study most DL schedulers cite.

See also (filed under other topics): [Gandiva](../gpu-training/microsoft-gandiva/0606676-gandiva-introspective-cluster-scheduling-for-deep-learning.md) (OSDI 2018), [Decima](../distributed-system/decima/1810.01963-learning-scheduling-algorithms-for-data-processing-clusters.md) (SIGCOMM 2019).

## Kubernetes batch & AI scheduling

- [Introducing Kueue](https://kubernetes.io/blog/2022/10/04/introducing-kueue/) — Kubernetes SIG Scheduling · Blog 2022 — job queueing that admits batch jobs as whole units under quotas and fair sharing, leaving placement to kube-scheduler · [code](https://github.com/kubernetes-sigs/kueue); why: the upstream answer to gang admission and quota for AI jobs on Kubernetes.
- [Volcano: Cloud Native Batch System](https://volcano.sh/) — Huawei Cloud, CNCF · project site — batch scheduler adding gang scheduling, queues and fair share to Kubernetes · [code](https://github.com/volcano-sh/volcano) · [CNCF incubation post](https://www.cncf.io/blog/2022/04/07/cloud-native-batch-system-volcano-moves-to-the-cncf-incubator/); why: the most widely deployed alternative scheduler for AI/HPC on Kubernetes.

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

- [How Google Does It: Building the largest known Kubernetes cluster, with 130,000 nodes](https://cloud.google.com/blog/products/containers-kubernetes/how-we-built-a-130000-node-gke-cluster/) — Google Cloud · 2025 — experimental 130K-node GKE cluster with a Spanner-backed store and Kueue gang admission (65K is the supported limit).
- [65,000 nodes and counting: Google Kubernetes Engine is ready for trillion-parameter AI models](https://cloud.google.com/blog/products/containers-kubernetes/gke-65k-nodes-and-counting) — Google Cloud · 2024 — how GKE raised cluster scale limits for AI training.

---

## Auto-analyzed papers

_Entries below this line are managed by `paper-bot`. Manual edits are fine; just keep them above the marker._


## Optimus: an efficient dynamic resource scheduler for deep learning clusters (European Conference on Computer Systems 2018)

Paper link: [Optimus: an efficient dynamic resource scheduler for deep learning clusters](https://www.semanticscholar.org/paper/93a06eb066fe58ed7d036e46e4cee53483e16bb8)

Analysis: [optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md](optimus/93a06eb-optimus-an-efficient-dynamic-resource-scheduler-for-deep.md)

<!-- paper-bot:end -->
