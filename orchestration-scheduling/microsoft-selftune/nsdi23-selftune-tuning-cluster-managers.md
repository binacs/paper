---
title: 'SelfTune: Tuning Cluster Managers'
authors:
- Ajaykrishna Karthikeyan
- Nagarajan Natarajan
- Gagan Somashekar
- Lei Zhao
- Ranjita Bhagwan
- Rodrigo Fonseca
- Tatiana Racheva
- Yogesh Bansal
affiliations: 'Microsoft Research, Microsoft, Stony Brook University'
venue: 'NSDI'
year: 2023
abs_url: https://www.usenix.org/conference/nsdi23/presentation/karthikeyan
pdf_url: https://www.usenix.org/system/files/nsdi23-karthikeyan.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# SelfTune: Tuning Cluster Managers

> **Why it matters:** It shows that a cluster manager's numeric knobs can be tuned continuously in production with a tiny API and a one-weight-per-parameter, model-free gradient method. That makes the cluster manager's own reconciliation loop the tuning loop.

## Problem

Cluster managers such as Kubernetes autoscalers, FaaS app managers, VM allocators and background-task schedulers expose many numeric configuration parameters. Operators usually set them by hand and test them only lightly. They then stay fixed even when workloads, machine types and clusters change. The paper gives two examples (§1). The default Kubernetes VPA settings can drop throughput to "nearly 50%" under short, heavy bursts. Microsoft's WLM team kept hand-made, context-specific variants of one knob, such as per resource and per machine type (§5).

Existing tuners fit this setting poorly (§2):
- Bayesian optimization (CherryPick, Metis, MLOS) assumes one fixed global reward function and needs many samples as dimensions grow.
- Deep RL (Decima, RL database tuners) needs explicitly engineered state features.
- Heuristic or offline search (OpenTuner, BestConfig) does not handle rewards that drift over time.
- Contextual bandits (Decision Service) blow up the action space when there are several numerical parameters.

The goal is online, in-deployment tuning that a developer can bolt onto an existing control loop.

## Core design

### Developer interface (§3, Fig. 1, App. A)
- **Declare parameters:** type, optional initial value, range and step size. Figure 1's example is `UpdateCycle`, a TimeDelta in [1 s, 30 s] that starts at 5 s.
- **Create / Connect:** create a SelfTune instance or attach to an existing one.
- **Predict:** called at the point where the parameter is used, for example once per scheduler-loop iteration. It returns an invocation ID and parameter values.
- **SetReward:** a domain-specific scalar, usually computed from the current-versus-desired state that the manager already tracks. Figure 1 uses `currentLoad - optLoad`. A reward applies to every `Predict` call since the previous `SetReward`.
- **Round:** the interval during which one set of predicted values is live. It ends at `SetReward`, and the developer chooses its length.
- **Scope:** how many independent instances to run, for example one per machine. Scoping splits one hard global problem into many small per-scope problems.

### Components (§3.2)
- **Learning Engine:** runs Bluefin. The framework is algorithm-agnostic and could host contextual bandits instead.
- **Data Collector:** stores `(callId, a, r)` tuples. Bluefin needs only the latest tuple per instance. WLM keeps 30 days for debugging.
- **Reward Tracker:** a background service that computes rewards off the critical path at a set frequency. WLM uses it.

### Bluefin (§4, Algorithm 1)
Bluefin is derivative-free online gradient ascent with **one-point (bandit) feedback**. It adapts results from derivative-free online convex optimization.
1. Keep a real weight vector `w ∈ R^m`, one weight per tuned parameter.
2. Each round, sample a unit vector `u` uniformly from the sphere and deploy `a = g(w + δu)`. `g` rounds to the step size and projects onto the bounds, which is how discrete and bounded knobs get handled.
3. Observe reward `r` and update `w ← w + (η/δ)·r·u`.

There is no surrogate model, no state featurization, and only the rewards at the deployed points are used. Remark 1 gives a **two-point** variant, `w ← w + η·(1/2δ)·[r(g(w+δu)) − r(g(w−δu))]·u`, for settings that can evaluate two points, such as simulators. It gives a better gradient estimate.

On hyperparameters, the theory suggests `δ = O(1)` and `η = O(δ²)`. In WLM, one fixed (δ, η) was chosen from a month of aggregate metrics and used for all clusters. These values are deliberately not decayed to 0, to "prevent stagnation when tuning in deployment" (§4, §5.2).

### WLM deployment (§5)
- WLM schedules background tasks for Substrate, the data engine behind services such as Exchange Online and SharePoint. Background tasks are over 70% of Substrate's tasks.
- WLM controls per-machine background concurrency with AIMD. If all four resources (CPU, disk, memory, network) are under their low thresholds, `MaxConcurrency` goes up by 1. If any resource is over its high threshold, `MaxConcurrency` is halved.
- `RefreshCycle` sets how often that AIMD step runs. It is the **only** parameter SelfTune tunes in this deployment.
- The reward is HUP (Healthy Utilization Percent: the fraction of time a resource is neither over- nor under-utilized) or GR (Grant Ratio: tasks run divided by tasks submitted), aggregated daily. One round is one day, and the scope is one machine.
- The rollout uses "flights", starting with a few hundred servers. Evaluation compares disjoint treatment and control machine sets within the same cluster, with a t-test at p = 0.05. Before/after comparisons were not used because HUP drifts week to week (Fig. 4).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| WLM integration effort | < 50 lines of code | WLM codebase of "tens of thousands of lines" | §5.2 |
| Per-update compute | at most 5 FLOPS | Bluefin update in WLM | §5.2 |
| Data Collector footprint | 30 days of history, a few hundred KB per instance | WLM | §3.2, §5.2 |
| Headline production throughput gain | up to 20% | Abstract | Abstract |
| Cluster throughput gain | 15%–20% "in multiple clusters" | WLM | §1 |
| Background-task throughput gain | up to 17% | 750-machine APAC cluster, half treated, Jan 2022 | §5.3, Fig. 6 |
| Grant Ratio gain, median | 178% | Cluster 1, 144 vs 144 machines, reward GR; HUP change not significant | Table 2 |
| Grant Ratio gain, median | 37% | Cluster 2, 1000 vs 1000 machines, reward GR | Table 2 |
| CPU HUP / GR gain, median | 1% HUP, 18% GR | Cluster 3, 1950 vs 1950 machines, reward CPU HUP | Table 2 |
| Wasted memory reduction | nearly 10%, no worse cold starts | AzureFaaS, per-app tuning vs best global (prewarm, keepalive) | §6.3 |
| Wasted memory vs keepalive=99 | 12.5% less, for 0.5% more cold starts | Time-varying per-app tuning, 14 weeks of traces | §6.4 |
| Parameter drift | up to 300% for over 25% of apps | Converged FaaS params, Aug vs Oct | §6.4, Fig. 10 |
| VPA throughput (%) | Bluefin 86.1±2.2 (12 samples); BO 83.9±3.1 (14); ε-greedy 71.2±4.3 (13); DDPG 73.4±5.4 (50) | DeathStar social network, 4 VPA CPU params, 50-sample budget | Table 3 |
| VPA throughput vs default | "over 75% better" | Bluefin, same setup | §7.1 |
| DeathStar P95 latency | Bluefin 19.5 ms in 8 samples (from 31.1 ms default); BO 19.9 ms / 41; ε-greedy 20.0 ms / 30; DDPG 20.2 ms / 50 | ~85 params across 28 microservices | Table 4, §7 |
| P95 latency seen during tuning | Bluefin 28.3 ms; BO 76541.9 ms; ε-greedy 67640.3 ms; DDPG 148543.1 ms | Same, over 50 rounds | Table 4 |

## Limitations

The paper has no dedicated limitations section. The points below are **my own analysis** unless they are cited.
- **Production scope is narrow.** The live deployment tunes a single scalar (`RefreshCycle`) per machine with daily rounds (§5.2). Multi-parameter, high-dimensional results (DeathStar, ~85 params) come from a 4-server testbed, and the FaaS results come from a trace-driven simulator that assumes zero execution time and uniform memory (§6, §7).
- **Local optimizer.** Bluefin is a gradient-ascent method. The paper claims convergence to "local (or global) optima", so non-convex reward surfaces with plateaus or cliffs can trap it. Fixed, non-decaying δ/η trades convergence for adaptivity, and the paper acknowledges this departs from theory (§5.2).
- **No explicit safety mechanism.** Exploration is bounded only by parameter ranges and by staged flighting. The paper gives no guardrails or rollback criteria for bad explored values. It does note that rewards "vary wildly" in some regions (§7.1).
- **Reward design is left to the developer.** Results depend on choosing a good scalar reward (HUP vs GR). In Clusters 1 and 2 the HUP change was statistically insignificant while GR moved a lot (Table 2). The paper attributes Cluster 1's large gain partly to an "obsolete" control value.
- **Per-scope independence.** Instances share no learning and ignore cross-scope interactions (e.g., many machines changing concurrency at once).
- **Minor internal inconsistencies.** Headline throughput is given as 20%, 15–20% and 17% in different places (Abstract, §1, §5.3). The default `pod-recommendation-min-cpu` appears as 25 millicores in Table 1 but 250 in §7.1.

## Relation to other systems

- **CherryPick / Metis (BO):** these fit a surrogate over a fixed global reward and need evaluations at points that are never deployed. Bluefin is model-free, uses only the deployed point's reward, and tracks a drifting reward. In the paper's DeathStar run it needs 8 samples, against 41 for BO (Table 4).
- **OtterTune / MLOS:** both are BO-based. OtterTune also relies on a workload repository, which the paper argues is impractical to maintain for cluster managers. SelfTune instead embeds in the running system with a small Predict/SetReward API.
- **Decima / RL DB tuners:** deep RL with an explicit state representation and large models. SelfTune needs only a scalar reward and one weight per parameter. DDPG exhausted its 50-sample budget in both of the paper's experiments (Tables 3–4).
- **Azure Decision Service (contextual bandits):** suited to discrete actions. Several numeric knobs explode the action space; the ε-greedy baseline over four VPA parameters was quantized to 24,960 actions (§7).
- **SmartChoices:** also supports numeric parameters, but needs per-parameter rewards. SelfTune uses one reward per round for all parameters.
- **AutoPilot:** the paper calls SelfTune "orthogonal to such cluster management frameworks"; it tunes their knobs, as with Kubernetes VPA in §7.

## Takeaways for practice

- **Reuse the reconciliation loop.** Every cluster manager already computes "current vs desired" state. That difference is a ready-made reward, and the loop iteration is a ready-made round.
- **Scope aggressively.** Per-machine or per-application instances make each learning problem low-dimensional and sample-efficient. They also replace hand-maintained "variant" knobs (per machine type, per resource).
- **Prefer cheap, model-free, one-point methods for online knobs.** One weight per knob and only the latest tuple make it easy to run on every node and to audit.
- **Expect knobs to drift.** Converged values differ across clusters, within clusters and over months (Table 2, Fig. 10). Treat tuning as continuous, and do not decay exploration to zero.
- **Measure with in-cluster treatment/control splits, not before/after.** Week-to-week drift is too large for before/after comparisons (Fig. 4).
- **(My own analysis) For GPU training or inference platforms,** good candidates for this pattern are knobs that sit inside an existing feedback loop and have a clear scalar objective. Examples are autoscaler cooldowns and margins, batching timeouts, admission-control concurrency limits and keepalive/prewarm windows. Add your own guardrails, such as bounded ranges, staged rollout and automatic rollback, because the paper does not provide them.

## References

- Paper: https://www.usenix.org/system/files/nsdi23-karthikeyan.pdf
- Landing page: https://www.usenix.org/conference/nsdi23/presentation/karthikeyan
- Code: https://github.com/microsoft/selftune (named in the paper as reference [14]; not opened for this note)
