---
paper_id: 8352e3ba20cb0fd48e2514bc1948e68108943e39
title: 'SOCK: Rapid Task Provisioning with Serverless-Optimized Containers'
authors:
- Edward Oakes
- Leon Yang
- Dennis Zhou
- Kevin Houck
- Tyler Harter
- Andrea C. Arpaci-Dusseau
- Remzi H. Arpaci-Dusseau
venue: USENIX Annual Technical Conference
year: 2018
citations: 498
pdf_url: ''
analyzed_at: '2026-11-02T15:00:21+00:00'
model: deepseek-chat
abs_url: https://www.usenix.org/conference/atc18/presentation/oakes
edited: '2026-11-24 hand-corrected'
---

# SOCK: Rapid Task Provisioning with Serverless-Optimized Containers

> Hand-corrected 2026-11-24 against the USENIX ATC '18 paper (University of Wisconsin-Madison, Microsoft Gray Systems Lab). The bot's original analysis was generic; this version names the actual mechanisms.

## TL;DR

SOCK makes container start-up fast enough for serverless Python by (1) building **lean containers** that skip kernel operations that scale poorly, (2) **generalised Zygote provisioning** that forks handlers from pre-initialised interpreters with popular packages already imported, and (3) a **three-tier cache** (handler, install, import). Built inside OpenLambda.

## Problem & Motivation

Serverless start-up is dominated by sandbox creation and library imports ("importing many popular libraries adds about 100ms to startup", abstract). General-purpose containers pay for features lambdas do not need, and some of those features hit kernel scalability limits (§2).

## Key Ideas

- **Lean containers (§4.1):** bind mounts instead of union file systems, chroot instead of a mount namespace, no mount/network namespaces (a global lock in network-namespace creation/cleanup is identified in §2.2), and a pool of pre-created cgroups.
- **Generalised Zygotes (§4.2):** multiple pre-initialised interpreter processes, with the packages to pre-import chosen at runtime from usage; a forked handler is moved into a fresh container via fd passing and `setns`.
- **Three-tier caching (§4.3):** a handler cache of paused idle containers (LRU), an install cache of pre-installed packages mapped read-only, and an import cache that manages the Zygotes.

## Evaluation

Abstract: avoiding kernel bottlenecks gives 18x over Docker; generalised Zygotes add 3x; the Zygote-based three-tier cache gives 45x over SOCK without Zygotes; in an image-processing case study OpenLambda+SOCK cuts platform overhead by 2.8x vs AWS Lambda and 5.3x vs OpenWhisk.

## Takeaways

- Fork-from-warm-template is the core trick behind most later fast-start sandboxes (Catalyzer's sfork, snapshot/restore in Firecracker and gVisor-based platforms).
- For agent sandboxes, the import / dependency-install phase can dominate cold start just as in serverless; caching it is as important as the isolation primitive.
- Isolation is weaker than a microVM (shared kernel, no network namespace); compare Firecracker (NSDI 2020) and gVisor.

## Links

- Paper: https://www.usenix.org/conference/atc18/presentation/oakes
- Code: https://github.com/open-lambda/open-lambda
