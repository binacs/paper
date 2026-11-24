---
title: 'Sinan: ML-Based and QoS-Aware Resource Management for Cloud Microservices'
authors:
- Yanqi Zhang
- Weizhe Hua
- Zhuangzhuang Zhou
- G. Edward Suh
- Christina Delimitrou
affiliations: 'Cornell University'
venue: 'ASPLOS'
year: 2021
doi: 10.1145/3445814.3446693
abs_url: https://doi.org/10.1145/3445814.3446693
pdf_url: https://www.csl.cornell.edu/~delimitrou/papers/2021.asplos.sinan.pdf
code_url: https://github.com/zyqCSL/sinan-local
note_type: deep-read
written_at: '2026-11-25'
---

# Sinan: ML-Based and QoS-Aware Resource Management for Cloud Microservices

> **Why it matters:** Sinan shows that a cheap two-stage learned model (a short-horizon CNN latency predictor plus a longer-horizon boosted-trees violation classifier) can drive per-tier CPU allocation for a multi-tier microservice graph at 1 s granularity, meeting end-to-end tail-latency QoS while using less CPU than tuned autoscaling.

## Problem

Interactive microservice applications are graphs of many small, mostly stateless tiers. The paper argues that managing their resources is harder than for monoliths for four reasons (Sec. 2.3): dependencies among tiers, overall system complexity, a delayed queueing effect (a bad allocation now may only show up as a QoS violation several intervals later, after queues build up), and the boundaries of the allocation space (the manager must learn where the QoS boundary actually is). Prior ML-driven cluster managers were built for monoliths and do not model inter-tier dependencies (Sec. 1).

Sinan's scope is CPU. Memory is provisioned at each tier's maximum profiled usage to avoid OOM errors (Sec. 2.1). Network bandwidth is not managed (Sec. 4.1, 4.2).

## Core design

### Two-stage prediction (Sec. 3)

The authors report that one network predicting latency far into the future lost accuracy quickly as the horizon grew. A multi-task network predicting both latency and violation probability "considerably overpredicts" both (Sec. 3, Fig. 4). The paper attributes the second failure to mixing a bounded probability target with an unbounded latency target. Sinan therefore splits the problem:

- **CNN, short-term latency (Sec. 3.1, Fig. 5).** Three inputs:
  - resource-usage history per tier over T timesteps, as a 3D tensor whose channels are CPU, memory (RSS and cache) and network (rx/tx packets) metrics from Docker cgroups, after feature selection;
  - end-to-end latency history (95th–99th percentiles) over the same T steps;
  - the candidate next-step CPU allocation (tiers × CPU limit).
  Adjacent tiers sit in adjacent rows, so a convolution kernel spans several neighbouring tiers. The output is the 95th–99th percentile end-to-end latency for the next timestep. The loss is a scaled squared loss (Eq. 1–2). Training uses SGD in MXNet.
- **Boosted trees, long-term violation (Sec. 3.2).** An XGBoost classifier takes the CNN's latent representation plus the candidate allocation. It outputs the probability pV that QoS is violated within the next k timesteps if that allocation is held. The evaluation uses the next 5 intervals (5 s) (Sec. 5.2).

### Data collection (Sec. 4.2)

Traces gathered only during normal operation, or by random exploration, were insufficient. Without QoS-violating samples, both models overfit badly (Sec. 4.2, Fig. 9). Sinan treats data collection as a multi-armed bandit, one arm per tier, scored by an information-gain objective (Eq. 3). Exploration targets boundary points (p = 0.5) and covers the latency region [0, QoS + α], with α = 20% of QoS.

### Controller and action space (Sec. 4.1, 4.3, Table 1)

A centralized scheduler, per-server/VM operators that apply CPU limits through the Docker API (cgroups), and a prediction service hosting the models (Fig. 8). Every 1 s the scheduler gathers per-tier CPU, memory and network usage plus user load from the API gateway. Metrics of replicas of one tier are averaged.

Candidate actions (Table 1):

- Scale Down: one tier.
- Scale Down Batch: the k least-utilized tiers.
- Hold: keep the current allocation.
- Scale Up: one tier.
- Scale Up All: all tiers.
- Scale Up Victim: tiers that were scaled down in the previous t cycles.

Only this subset is evaluated, not the full allocation space. The decision rule:

1. Drop actions whose predicted next-step latency exceeds QoS minus the CNN's validation RMSE.
2. Apply two thresholds p_d < p_u to pV. Hold is allowed if pV < p_u, and a scale-down is allowed if pV < p_d.
3. If Hold itself exceeds p_u, only scale-ups with pV < p_u remain. If none remain, all tiers go to maximum.
4. Among the allowed actions, pick the one using the fewest resources.

p_u is set so that validation false negatives are at most 1%. No numeric values for p_d or p_u are given. On a mispredicted violation, all tiers are scaled up at once. If errors pass a trust threshold, the scheduler becomes more conservative about reclaiming (Sec. 4.3).

### Retraining (Sec. 5.4)

When the platform or application changes, the models are fine-tuned incrementally with a learning rate 1/100 of the original (1×10⁻⁵). A change in the number of tiers requires changing the CNN's shape (Sec. 4.2).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Decision interval | 1 s | Both apps | Sec. 4.1 |
| BT prediction horizon | next 5 intervals (5 s) | Both apps | Sec. 5.2 |
| QoS target | p99 200 ms / p99 500 ms | Hotel Reservation / Social Network | Sec. 5.1 |
| Training samples | 31,302 / 58,499 (9:1 train/val split) | Hotel / Social, local cluster | Sec. 5.1 |
| Data collection time | 8.7 h / 16 h | Hotel / Social | Sec. 5.1 (A.5 says 9 h for Hotel) |
| CNN RMSE train/val | 14.2 / 14.7 ms; 25.9 / 26.4 ms | Hotel; Social | Table 2 |
| LSTM RMSE train/val | 17.7 / 18.1 ms; 29.3 / 30.7 ms | Hotel; Social | Table 2 |
| CNN model size | 68 KB / 144 KB | Hotel / Social | Table 2 |
| CNN inference cost | within 1% of the 1 s interval | Single Titan XP GPU, <2% avg util | Sec. 5.2 |
| BT accuracy train/val | 94.4 / 94.1%; 95.5 / 94.6% | Hotel; Social | Table 3 |
| BT accuracy on GCE | 96.1% train / 95.0% val | Social Network on GCE | Sec. 5.5 |
| CPU saved vs other QoS-meeting methods | 25.9% avg, up to 46.0% | Hotel Reservation, 1k–3.7k users | Sec. 1, 5.3 |
| CPU saved | 59.0% avg, up to 68.1% | Social Network, 50–450 users | Sec. 1, 5.3 |
| AutoScaleOpt resources | 53% of Sinan's on average, but violates QoS above 1900 users | Hotel Reservation | Sec. 5.3 |
| PowerChief resources | 2.57× Sinan's, still violates QoS | Hotel Reservation | Sec. 5.3 |
| GCE deployment | 93 containers, 5,900 extra samples for transfer | Social Network on GCE | Sec. 5.1, 5.4 |
| Fine-tune convergence | 5,900 samples (1.6 h), 1,800 (0.5 h), 5,300 (1.5 h) | GCE; more replicas; modified app | Sec. 5.4, Fig. 13 |
| LIME weight of social-graph Redis | 5109.9 with log sync → 451.7 without (drops to 5th) | Social Network | Table 4 |

Baselines (Sec. 5.1, 5.3): AutoScaleOpt, a utilization-threshold autoscaler from a tutorial-style policy; AutoScaleCons, a more conservative, QoS-tuned version; and PowerChief as published. Only Sinan and AutoScaleCons met QoS at all loads for both apps (Sec. 5.3). The 25.9%/59.0% savings sentences do not name the baseline explicitly. Since AutoScaleCons is the only other method that met QoS throughout, they effectively compare against it (Own analysis).

## Explainability (Sec. 5.6)

The authors apply LIME to the CNN on samples taken at QoS violations. They perturb one tier's or one resource's features by constant factors (for example 0.5 and 0.7), label the perturbed samples with the CNN, fit a linear regression, and rank features by summed weights. The top tier for Social Network was the social-graph Redis instance, with cache memory as its top resource. The cause was Redis log persistence: a periodic fork-and-copy to disk that produced latency spikes. Disabling it "eliminated most of the latency spikes" (Fig. 16), and that tier's LIME weight dropped (Table 4). No before/after latency numbers are given.

## Limitations

- CPU only. Memory is statically over-provisioned and network is unmanaged (Sec. 2.1, 4.1).
- The model is tied to a fixed graph: adding or removing tiers changes the CNN input shape and needs retraining (Sec. 4.2). Platform or app changes need fine-tuning, measured at 0.5–1.6 h of new samples (Sec. 5.4).
- Training data has to deliberately cross the QoS boundary. In production that means a controlled exploration phase that causes QoS violations (Own analysis).
- The decision is greedy over a small hand-designed action set at one step, with fallback to Scale Up All. There is no global optimization or placement/bin-packing decision (Own analysis).
- Evaluation covers two DeathStarBench apps (Hotel Reservation, Social Network) on Docker Swarm, plus one GCE deployment. On GCE there is no baseline comparison, only that Sinan always met QoS across four request mixes, with W1 needing the most at 170 vCPUs for 450 users (Sec. 5.5, Fig. 14–15).
- Inconsistencies inside the paper:
  - "approximately 100 container instances" (Sec. 1) vs 93 (Sec. 5.1).
  - Hotel data collection 8.7 h (Sec. 5.1) vs 9 h (A.5).
  - Local cluster four 80-core/256 GB servers (Sec. 5.1) vs two 88-core servers in the artifact appendix.
  - The text describes the tier axis of the CNN input as y-axis in one place and x-axis in another.
  - The Fig. 7 caption says "different k" where the parameter discussed is α.
  - The Table 2 and Table 3 column orders (train vs inference time; false positive vs false negative) are not clearly labeled, so those per-column values are omitted here.
  - The ≤1% false-negative target for p_u (Sec. 4.3) is not obviously reconcilable with the unlabeled validation FP/FN figures in Table 3. They may be measured at different thresholds (Own analysis).

## Relation to other systems

- **PowerChief** (evaluated baseline): estimates per-tier queue length and queueing time from network traces and boosts the bottleneck tier. Sinan instead learns end-to-end latency over the whole graph and beat PowerChief on both QoS and resources (Sec. 5.3).
- **Threshold autoscaling (AutoScaleOpt/Cons):** reacts to per-tier utilization only. The paper shows the aggressive variant breaks QoS at higher load and the conservative one over-provisions (Sec. 5.3). Kubernetes HPA-style policies fall in this class (Own analysis).
- **Seer** (same group, cited in Sec. 6): uses deep learning to anticipate QoS violations in microservices for debugging and mitigation. Sinan turns that kind of prediction into a closed-loop CPU allocator with a separate long-horizon classifier (Own analysis).
- **PARTIES and Quasar** (cited in Sec. 6): QoS-aware managers for colocated or monolithic services. They model per-application interference and do not model the inter-tier dependency graph that Sinan's CNN captures (Own analysis).
- **Autopilot and Resource Central** (cited in Sec. 6): learned resource predictors at fleet scale, mostly for vertical sizing or VM behaviour from history. They do not target per-request end-to-end tail latency across a call graph (Own analysis).

## Takeaways for practice

- Split "what happens next tick" from "will we break SLO in the next few ticks". A regression model for the first and a classifier for the second was more accurate in this paper than one model doing both (Sec. 3, Fig. 4).
- Evaluate a small, structured set of candidate actions with the model and pick the cheapest safe one. Keep a hard fallback (scale everything up) for mispredictions. This keeps the ML in an advisory role (Own analysis).
- Budget for boundary-seeking data collection. Models trained only on healthy traces overfit and miss violations (Sec. 4.2).
- Set the safety threshold from validation false negatives and subtract model RMSE from the SLO. Both are cheap ways to encode prediction error into the policy (Sec. 4.3).

## References

- Paper: https://doi.org/10.1145/3445814.3446693 (PDF read from https://www.csl.cornell.edu/~delimitrou/papers/2021.asplos.sinan.pdf)
- Code (as listed in the paper's Appendix A, not opened for this note): https://github.com/zyqCSL/sinan-local, https://github.com/zyqCSL/sinan-gcp
