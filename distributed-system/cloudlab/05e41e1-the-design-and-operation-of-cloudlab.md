---
paper_id: 05e41e129cb49cafc36810c7b062f707ada13fce
title: The Design and Operation of CloudLab
authors:
- Dmitry Duplyakin
- R. Ricci
- Aleksander Maricq
- Gary Wong
- Jonathon Duerig
- E. Eide
- L. Stoller
- Mike Hibler
- David Johnson
- Kirk Webb
- Aditya Akella
- Kuang-Ching Wang
- G. Ricart
- L. Landweber
- C. Elliott
- M. Zink
- E. Cecchet
- Snigdhaswin Kar
- Prabodh Mishra
venue: USENIX Annual Technical Conference
year: 2019
citations: 642
abs_url: https://www.semanticscholar.org/paper/05e41e129cb49cafc36810c7b062f707ada13fce
pdf_url: ''
analyzed_at: '2026-06-01T11:30:06+00:00'
model: deepseek-chat
---

# The Design and Operation of CloudLab

## TL;DR

CloudLab is a large-scale, distributed scientific infrastructure that provides users with bare-metal access to thousands of cores across multiple datacenters, enabling repeatable and customizable experiments in cloud, networking, and systems research.

## Problem & Motivation

Researchers in cloud computing, networking, and distributed systems need realistic, large-scale testbeds to validate their ideas, but existing platforms often impose virtualization overhead, limit hardware access, or are not geographically distributed. CloudLab addresses the need for a flexible, reproducible, and isolated environment where users can control the full software stack and hardware resources.

## Key Ideas

- Bare-metal provisioning: Users get direct access to physical servers without virtualization overhead.
- Federated architecture: Multiple independent clusters (at Utah, Wisconsin, Clemson) are coordinated via a common control framework.
- Profile-based experiment management: Users define experiments via profiles (e.g., hardware topology, OS image, network configuration) that can be shared and reused.
- Isolation and reproducibility: Each experiment runs in an isolated slice of resources, and profiles ensure experiments can be repeated exactly.
- Support for diverse hardware: Includes different CPU architectures, GPUs, FPGAs, and programmable networking hardware.

## System Design

CloudLab consists of multiple clusters, each with its own hardware and local control infrastructure. A central portal (www.cloudlab.us) provides a unified interface for user management, experiment creation, and monitoring. The control framework uses a set of services: a database for resource tracking, a node manager for bare-metal provisioning (via PXE boot and disk imaging), and a network manager for configuring VLANs and software-defined networking. Users define experiments using a profile system (based on the GENI control framework) that specifies the desired topology, OS images, and software. The system then allocates resources across clusters and boots nodes into the specified configuration. Experiments are isolated via VLANs and firewall rules.

## Evaluation

The paper evaluates CloudLab through its operational experience over several years, reporting usage statistics: over 1,000 users, 100+ projects, and 10,000+ experiments run. It demonstrates the system's ability to provision large-scale experiments (e.g., 1,000+ nodes) and highlights the reproducibility of experiments via profiles. No specific baseline comparison is provided; the evaluation focuses on feasibility and user adoption.

## Takeaways

- Bare-metal provisioning is critical for systems research that requires low-level hardware access.
- A federated model allows scaling resources while maintaining a unified user experience.
- Profile-based experiment management enables reproducibility and sharing of complex setups.
- Operational experience shows that a diverse user community can effectively use such a testbed for a wide range of experiments.

## Related Work

CloudLab builds on the GENI (Global Environment for Network Innovations) project, adopting its control framework and profile system. It differentiates from Emulab (its predecessor) by supporting larger scale, multiple geographically distributed clusters, and a wider variety of hardware. Compared to commercial clouds (e.g., AWS, Azure), CloudLab offers bare-metal access and more flexible network configurations, but with less emphasis on production-grade reliability and SLAs.

## Open Questions

- How to manage resource contention and fairness among users with diverse experiment sizes?
- Can the federated model be extended to include more sites with heterogeneous hardware?
- How to evolve the platform to support emerging hardware (e.g., SmartNICs, persistent memory) while maintaining backward compatibility?
- What are the long-term sustainability and funding models for such academic testbeds?
