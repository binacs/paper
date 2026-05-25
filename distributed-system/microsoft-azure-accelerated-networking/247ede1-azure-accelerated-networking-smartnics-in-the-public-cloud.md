---
paper_id: 247ede1aa594d5fc849a5465553d8b58b1aec6d7
title: 'Azure Accelerated Networking: SmartNICs in the Public Cloud'
authors:
- D. Firestone
- Andrew Putnam
- S. Mundkur
- Derek Chiou
- Alireza Dabagh
- Mike Andrewartha
- Hari Angepat
- V. Bhanu
- Adrian M. Caulfield
- Eric S. Chung
- H. Chandrappa
- Somesh Chaturmohta
- Matt Humphrey
- Jack Lavier
- N. Lam
- Feng Liu
- Kalin Ovtcharov
- J. Padhye
- Gautham Popuri
- S. Raindel
- Tejas Sapre
- Mark Shaw
- Gabriel Silva
- Madhan Sivakumar
- Nisheeth Srivastava
- Anshuman Verma
- Qasim Zuhair
- D. Bansal
- D. Burger
- Kushagra Vaid
- D. Maltz
- A. Greenberg
venue: Symposium on Networked Systems Design and Implementation
year: 2018
citations: 695
abs_url: https://www.semanticscholar.org/paper/247ede1aa594d5fc849a5465553d8b58b1aec6d7
pdf_url: ''
analyzed_at: '2026-05-25T10:02:22+00:00'
model: deepseek-chat
---

# Azure Accelerated Networking: SmartNICs in the Public Cloud

## TL;DR

Azure Accelerated Networking uses FPGA-based SmartNICs to offload host networking, achieving line-rate performance with low latency and minimal CPU overhead in a public cloud.

## Problem & Motivation

Public cloud providers need to virtualize network functions (e.g., virtual switches, ACLs, NAT) for multi-tenant isolation and policy enforcement. Software-based virtual switches consume significant host CPU cores and introduce latency jitter, limiting achievable throughput and scalability. Existing hardware offloads (e.g., SR-IOV) lack flexibility for rapid feature updates.

## Key Ideas

- FPGA-based SmartNIC (Azure SmartNIC) that offloads virtual switching, ACLs, NAT, and encapsulation from host CPUs.
- Reconfigurable logic allows in-field updates without hardware replacement.
- Host-side agent (SoftNIC) handles control path and exception packets; data path runs entirely on FPGA.
- Direct path for tenant VMs via SR-IOV to SmartNIC, bypassing host networking stack.
- Flow-based offload: first packet of a flow goes through software, subsequent packets are offloaded to hardware.

## System Design

- SmartNIC: FPGA with embedded processors (ARM cores) and network interfaces. Implements virtual switch (vSwitch) in hardware.
- Host: Each server has a SmartNIC connected via PCIe. Host runs a lightweight SoftNIC driver for control and exception handling.
- Control plane: Azure Fabric Controller programs SmartNIC rules (ACLs, routes) via host agent.
- Data flow: Tenant VM sends packet via SR-IOV to SmartNIC; SmartNIC performs lookup, encapsulation (VXLAN/GRE), and forwards to physical NIC. Return path reverses.
- Exception path: Packets that miss hardware flow table are sent to host SoftNIC for software processing; resulting flow is then installed in hardware.

## Evaluation

- Workloads: synthetic benchmarks (iperf, netperf) and real Azure production traffic.
- Baselines: software vSwitch (Hyper-V) and SR-IOV without offload.
- Headline results: 95% reduction in host CPU usage for networking; line-rate throughput (40 Gbps) with sub-10 µs latency; no throughput degradation under 1000s of ACL rules.
- Production deployment: deployed across Azure datacenters, handling millions of flows per second.

## Takeaways

- FPGA-based SmartNICs can achieve both performance and programmability, enabling rapid feature deployment in cloud.
- Offloading the entire virtual switch to hardware frees host CPU cores for tenant workloads.
- Hybrid approach (software first packet, hardware fast path) balances flexibility and performance.
- Azure's SmartNIC design influenced subsequent industry adoption of SmartNICs and DPUs.

## Related Work

Compared to software vSwitches (Open vSwitch, Hyper-V) and SR-IOV, Azure's approach provides hardware acceleration with programmability. Related to earlier FPGA-based NICs (e.g., NetFPGA) but tailored for cloud multi-tenancy and scale.

## Open Questions

- How does the design scale to 100 Gbps and beyond?
- Power and cost trade-offs of FPGAs vs. ASICs for cloud networking.
- Security implications of programmable hardware in multi-tenant environments.
- Migration to newer SmartNIC architectures (e.g., AMD Pensando, Intel IPU) and impact on Azure's design.
