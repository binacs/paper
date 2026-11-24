# Distributed System

Classic and modern distributed-systems papers: storage, data processing, databases, datacenter networking and cloud infrastructure.

**Contents:** [Storage](#storage) · [Data processing](#data-processing) · [Databases & transactions](#databases--transactions) · [Datacenter networking](#datacenter-networking) · [Memory disaggregation](#memory-disaggregation) · [Cloud & serverless](#cloud--serverless) · [Blockchain](#blockchain) · [Auto-analyzed papers](#auto-analyzed-papers)

Entry format: **Paper** (title link — institution · venue year), **Why** (one sentence), and Code / Blog / Analysis links when they exist. Within a section: classics first, then by year.

## Storage

### The Google File System

- **Paper:** [The Google File System](https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/gfs-sosp2003.pdf) — Google · SOSP 2003
- **Why:** Single-master, chunk-replicated file system designed around large sequential appends and component failure as the norm.

### Bigtable

- **Paper:** [Bigtable: A Distributed Storage System for Structured Data](https://static.googleusercontent.com/media/research.google.com/zh-CN//archive/bigtable-osdi06.pdf) — Google · OSDI 2006
- **Why:** Sparse, sorted, multi-dimensional map on GFS + Chubby; the template for HBase and many wide-column stores.

### Dynamo

- **Paper:** [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) — Amazon · SOSP 2007
- **Why:** Always-writable store using consistent hashing, sloppy quorums, vector clocks and anti-entropy; the root of Cassandra/Riak-style designs.

### Megastore

- **Paper:** [Megastore: Providing Scalable, Highly Available Storage for Interactive Services](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36971.pdf) — Google · CIDR 2011
- **Why:** Paxos-replicated entity groups on Bigtable, giving ACID within a group across datacenters; Spanner's predecessor.

## Data processing

### MapReduce

- **Paper:** [MapReduce: Simplified Data Processing on Large Clusters](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/16cb30b4b92fd4989b8619a61752a2387c6dd474.pdf) — Google · OSDI 2004
- **Why:** The programming model and fault-tolerant runtime that made commodity-cluster batch processing mainstream.

### Percolator

- **Paper:** [Large-scale Incremental Processing Using Distributed Transactions and Notifications](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/36726.pdf) — Google · OSDI 2010
- **Why:** Snapshot-isolation transactions and observers on Bigtable for incremental index updates; its 2PC scheme is reused by TiKV and others.

### F1 Query

- **Paper:** [F1 Query: Declarative Querying at Scale](https://storage.googleapis.com/gweb-research2023-media/pubtools/pdf/fa380016eccb33ac5e92c84f7b5eec136e73d3f1.pdf) — Google · VLDB 2018
- **Why:** One federated SQL engine covering OLTP-style point queries, interactive analytics and batch ETL over many storage systems.

See also: [Decima](decima/1810.01963-learning-scheduling-algorithms-for-data-processing-clusters.md) (RL-learned scheduling for Spark jobs, SIGCOMM 2019).

## Databases & transactions

### Spanner

- **Paper:** [Spanner: Google's Globally-Distributed Database](https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf) — Google · OSDI 2012
- **Paper:** [Spanner: Becoming a SQL System](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/46103.pdf) — Google · SIGMOD 2017
- **Why:** Externally consistent transactions across the globe via TrueTime-bounded commit wait; the 2017 paper covers its evolution into a full SQL system.
- **Deep read:** [deep-read note](google-spanner/osdi12-spanner-googles-globally-distributed-database.md)

### F1

- **Paper:** [F1: A Distributed SQL Database That Scales](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41344.pdf) — Google · VLDB 2013
- **Paper:** [Online, Asynchronous Schema Change in F1](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/41376.pdf) — Google · VLDB 2013
- **Why:** The AdWords database on Spanner; the schema-change paper's intermediate-state protocol is widely copied by online DDL tools.

## Datacenter networking

- [Homa](homa/1803.09615-homa-a-receiver-driven-low-latency-transport-protocol.md) — Stanford · SIGCOMM 2018 — receiver-driven transport using network priorities for low tail latency.
- [Azure Accelerated Networking](microsoft-azure-accelerated-networking/247ede1-azure-accelerated-networking-smartnics-in-the-public-cloud.md) ([paper](https://www.usenix.org/conference/nsdi18/presentation/firestone)) — Microsoft · NSDI 2018 — FPGA SmartNICs offloading the host SDN stack.

## Memory disaggregation

- [Pond: CXL-Based Memory Pooling Systems for Cloud Platforms](https://arxiv.org/abs/2203.00241) — Microsoft Azure, CMU, Virginia Tech · ASPLOS 2023 (Distinguished Paper) — small CXL memory pools with ML-predicted per-VM pool allocation · [analysis](microsoft-pond/2203.00241-pond-cxl-based-memory-pooling-systems-for-cloud.md) · [deep read](microsoft-pond/2203.00241-pond-deep-read.md); why: the reference design for CXL memory pooling in a public cloud.

## Cloud & serverless

See also [agent-sandbox](../agent-sandbox/README.md) for microVMs, sandboxes and fast-start techniques.

- [Serverless in the Wild](misc/2003.03423-serverless-in-the-wild-characterizing-and-optimizing-the.md) — Microsoft · ATC 2020 — Azure Functions trace characterisation and a hybrid keep-alive policy against cold starts.
- [The Design and Operation of CloudLab](cloudlab/05e41e1-the-design-and-operation-of-cloudlab.md) ([paper](https://www.usenix.org/conference/atc19/presentation/duplyakin)) — Utah, Wisconsin, Clemson et al. · ATC 2019 — the bare-metal research testbed.

## Blockchain

- [Hyperledger Fabric](hyperledger-fabric/1801.10228-hyperledger-fabric-a-distributed-operating-system-for-permissioned.md) — IBM · EuroSys 2018 — execute-order-validate architecture for permissioned chains.
- [Monoxide](monoxide/ea639e0-monoxide-scale-out-blockchains-with-asynchronous-consensus-zones.md) ([paper](https://www.usenix.org/conference/nsdi19/presentation/wang-jiaping)) — Tsinghua · NSDI 2019 — sharded blockchain with asynchronous consensus zones.

---

## Auto-analyzed papers

_Entries below this line are managed by `paper-bot`. Manual edits are fine; just keep them above the marker._


## Hyperledger fabric: a distributed operating system for permissioned blockchains (European Conference on Computer Systems 2018)

Paper link: [Hyperledger fabric: a distributed operating system for permissioned blockchains](https://arxiv.org/abs/1801.10228)

Analysis: [hyperledger-fabric/1801.10228-hyperledger-fabric-a-distributed-operating-system-for-permissioned.md](hyperledger-fabric/1801.10228-hyperledger-fabric-a-distributed-operating-system-for-permissioned.md)


## Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider (USENIX Annual Technical Conference 2020)

Paper link: [Serverless in the Wild: Characterizing and Optimizing the Serverless Workload at a Large Cloud Provider](https://arxiv.org/abs/2003.03423)

Analysis: [misc/2003.03423-serverless-in-the-wild-characterizing-and-optimizing-the.md](misc/2003.03423-serverless-in-the-wild-characterizing-and-optimizing-the.md)


## Learning scheduling algorithms for data processing clusters (Conference on Applications, Technologies, Architectures, and Protocols for Computer Communication 2018)

Paper link: [Learning scheduling algorithms for data processing clusters](https://arxiv.org/abs/1810.01963)

Analysis: [decima/1810.01963-learning-scheduling-algorithms-for-data-processing-clusters.md](decima/1810.01963-learning-scheduling-algorithms-for-data-processing-clusters.md)


## Azure Accelerated Networking: SmartNICs in the Public Cloud (Symposium on Networked Systems Design and Implementation 2018)

Paper link: [Azure Accelerated Networking: SmartNICs in the Public Cloud](https://www.semanticscholar.org/paper/247ede1aa594d5fc849a5465553d8b58b1aec6d7)

Analysis: [microsoft-azure-accelerated-networking/247ede1-azure-accelerated-networking-smartnics-in-the-public-cloud.md](microsoft-azure-accelerated-networking/247ede1-azure-accelerated-networking-smartnics-in-the-public-cloud.md)


## The Design and Operation of CloudLab (USENIX Annual Technical Conference 2019)

Paper link: [The Design and Operation of CloudLab](https://www.semanticscholar.org/paper/05e41e129cb49cafc36810c7b062f707ada13fce)

Analysis: [cloudlab/05e41e1-the-design-and-operation-of-cloudlab.md](cloudlab/05e41e1-the-design-and-operation-of-cloudlab.md)


## Monoxide: Scale out Blockchains with Asynchronous Consensus Zones (Symposium on Networked Systems Design and Implementation 2019)

Paper link: [Monoxide: Scale out Blockchains with Asynchronous Consensus Zones](https://www.semanticscholar.org/paper/ea639e0bb4e4ef7ec5cbc7c0915033de4c89fd65)

Analysis: [monoxide/ea639e0-monoxide-scale-out-blockchains-with-asynchronous-consensus-zones.md](monoxide/ea639e0-monoxide-scale-out-blockchains-with-asynchronous-consensus-zones.md)


## Homa: a receiver-driven low-latency transport protocol using network priorities (Conference on Applications, Technologies, Architectures, and Protocols for Computer Communication 2018)

Paper link: [Homa: a receiver-driven low-latency transport protocol using network priorities](https://arxiv.org/abs/1803.09615)

Analysis: [homa/1803.09615-homa-a-receiver-driven-low-latency-transport-protocol.md](homa/1803.09615-homa-a-receiver-driven-low-latency-transport-protocol.md)

<!-- paper-bot:end -->
