---
title: 'Optimus: An Efficient Dynamic Resource Scheduler for Deep Learning Clusters'
authors:
- Yanghua Peng
- Yixin Bao
- Yangrui Chen
- Chuan Wu
- Chuanxiong Guo
affiliations: 'The University of Hong Kong, Bytedance Inc.'
venue: 'EuroSys'
year: 2018
doi: 10.1145/3190508.3190517
abs_url: https://dl.acm.org/doi/10.1145/3190508.3190517
pdf_url: https://i.cs.hku.hk/~cwu/papers/yhpeng-eurosys18.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Optimus: An Efficient Dynamic Resource Scheduler for Deep Learning Clusters

> **Why it matters:** One of the first DL-cluster schedulers to fit a job's convergence curve and its throughput as a function of parameter-server (PS) and worker counts online, and then use those fitted models to resize running jobs so that average job completion time (JCT) goes down.

## Problem

DL training jobs are long, iterative and resource-hungry. General cluster schedulers such as Borg and YARN-style systems fix a job's resources when it is submitted and ignore how DL workloads behave (§1). A static allocation cannot follow changes in free capacity or differences in job size, and fairness policies such as DRF do not aim at completion time (§2). In PS-based data-parallel training, how many PSs and workers a job gets, and where they are placed, decides its speed. The paper therefore asks how to pick (p, w) per job and where to place tasks, given only models learned while the jobs run.

## Core design

### Online convergence model (§3.1)
- Training loss as a function of step k: `l = 1/(β0·k + β1) + β2`, with β0, β1, β2 ≥ 0 (Eq. 1). The form is motivated by SGD's O(1/k) convergence rate.
- After each step the job records a (k, l) point. Losses are divided by the largest loss seen so far (usually the first), so they lie in [0, 1]. The coefficients are refit with non-negative least squares (SciPy NNLS).
- Outliers are points that fall outside the range set by neighbouring epochs (the minimum of the next 5 and the maximum of the previous 5). They are replaced by the average of their neighbours. For very long jobs the paper suggests sampling points or averaging them per epoch.
- Convergence is decided on training loss. The job owner sets a threshold, and the job counts as converged once the loss decrease between consecutive epochs has stayed below it for several epochs. The remaining steps Q_j come from the fitted curve.
- Prediction error over training progress is shown for nine jobs in Fig. 6. The text gives no summary bound for it.

### Throughput model for PS/worker counts (§3.2)
- Per-step time (Eq. 2) is broken down into forward time (which scales with the per-worker mini-batch), backward time (assumed roughly constant), gradient push and parameter pull (model size S split over p PSs, sent at a share of PS bandwidth B divided among the workers that send to the same PS at once), the PS update time, and an overhead term linear in w and p. The bottleneck is assumed to be at the PS side, and parameters are assumed to be spread evenly over the PSs.
- Asynchronous speed (Eq. 3): `f(p,w) = w · (θ0 + θ1·w/p + θ2·w + θ3·p)^-1`.
- Synchronous speed (Eq. 4), with global batch M fixed and per-worker batch M/w: `f(p,w) = (θ0·M/w + θ1 + θ2·w/p + θ3·w + θ4·p)^-1`.
- The θ coefficients are fitted with NNLS on (p, w, speed) samples. The samples come from short pre-runs on a small data sample, each taking "tens of seconds", and the model is recalibrated as the job runs.

### Marginal-gain allocation (§4.1)
- Objective: minimise the sum over jobs of t_j = Q_j / f_j(p_j, w_j). Constraints: for each resource type r, the jobs' per-worker and per-PS demands summed must stay within cluster capacity C^r, and p_j and w_j must be integers (Eqs. 5–8). The paper calls the problem non-convex and NP-hard in general.
- Heuristic: every active job first gets 1 PS and 1 worker, to avoid starvation. Then, repeatedly, the job with the largest marginal gain gets one more PS or worker. The marginal gain (Eq. 9) is the reduction in t_j from adding one task, divided by that task's dominant-resource share in the DRF sense, taking the better of adding a PS and adding a worker. Gains are recomputed after each addition. The loop stops when resources run out or no gain is positive.
- So the PS:worker ratio is chosen per job; the baselines fix it at 1:1 (§6.1).
- Jobs early in training have their gain multiplied by a priority factor (e.g. 0.95), which damps the effect of their less accurate predictions.
- The scheduler runs once per scheduling interval, 10 minutes in the experiments (§6.1).

### Task placement (§4.2)
- Theorem 1 covers synchronous training on homogeneous servers. The best placement uses the smallest number of servers that can host the job, with the same number of PSs and the same number of workers on each. The proof in the appendix is only an outline.
- Procedure: sort servers by free CPU in descending order and take jobs smallest first. For each job, find the smallest k such that the first k servers fit it, and spread its PSs and workers evenly over them. Then update and re-sort. A job that does not fit is paused until the next interval.

### Implementation (§5)
- Optimus runs as a pod on Kubernetes 1.7 and keeps job state in etcd. Training runs on MXNet, with data and checkpoints on HDFS.
- Scaling is checkpoint-and-restart: the scheduler saves parameters to HDFS and restarts the job with the new (p, w). Data chunks are reassigned round-robin when w changes.
- Stragglers: in async jobs, a worker at half the median speed or slower counts as a straggler. In sync jobs, speed is inferred from the gaps between gradient arrivals at the PSs. A straggler is replaced by a new worker.
- PS load balancing (PAA, §5.3) replaces MXNet's default assignment of parameter blocks to PSs. Blocks are sorted by size. Tiny blocks go to the PS with the fewest update requests, mid-size blocks are placed by best fit, and blocks larger than the average PS share are sliced into pieces.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Testbed | 7 CPU servers + 6 GPU servers (2× GTX 1080Ti each), 1GbE switch | Kubernetes 1.7, HDFS 2.8, MXNet | §6.1 |
| Testbed workload | 9 MXNet jobs | Models in Table 1 (ResNet-50, Seq2Seq, DeepSpeech2, …) | Abstract, Table 1 |
| JCT / makespan vs DRF | DRF's average JCT is 2.39× and its makespan 1.63× those of Optimus | Testbed | §6.2 |
| Same result as stated in the abstract | ~139% (JCT) and ~63% (makespan) improvement over representative schedulers | Testbed | Abstract |
| Time to finish all jobs | 4.1 h (Optimus), 6.7 h (DRF), 5.0 h (Tetris) | Testbed | §6.2 |
| Scaling (checkpoint/restart) overhead | 2.54% of makespan | Testbed | §6.2 |
| Scheduler scalability | 4,000 jobs (~100,000 tasks) scheduled within 5 s on 16,000 nodes | Simulation, one core | §6.2, Fig. 12 |
| Speed-model error | < 10% with 10 sampled (p, w) pairs | ResNet-50, 780 possible pairs | §3.2, Fig. 8 |
| Sample runs | 5 (p, w) pre-runs per job in the evaluation; 5–10 runs "enough" | — | §6.1; §8 |
| Sensitivity to prediction error | ~15% gap vs zero error, with 20% convergence error and 10% speed error; speed error matters more | Simulation | §6.3, Fig. 15 |
| Priority factor 0.95 | JCT −2.66%, makespan −1.88% | Simulation | §6.3 |
| Allocation algorithm alone | JCT −62%, makespan −31% vs the fairness scheduler's allocation | — | §6.4, Fig. 18 |
| Placement alone | ~10% better than Tetris, ~15% better than DRF (JCT and makespan) | — | §6.4, Fig. 19 |
| PAA balance | Parameter-size difference 3.6M → 0.1M; request difference 43 → 1; total requests 247 → 157 | ResNet-50 | Table 3 |
| PAA speedup | Up to 29% over the MXNet default | ResNet-50, ResNext, Inception-BN, VGG | Fig. 21 |

**Inconsistencies in the paper.**
- Table 2 labels the speed-function coefficients θ1–θ5, while Eqs. 3–4 use θ0–θ4. The table also does not say which job the coefficients were fitted on, so its values are left out here.
- The end-of-§6 summary says allocation, placement and PAA contribute "about 62%, 17%, 20%" respectively. The §6.4 text instead gives placement as about 10% against Tetris and 15% against DRF, and the 62% figure in §6.4 is the JCT gain of the allocation algorithm over the fairness scheduler's allocation, a different quantity.

## Limitations

- The design targets production models that converge, with tuned hyperparameters and a fixed learning rate (§2.1, §7). A learning-rate change means refitting from scratch. Models whose loss does not follow Eq. 1 (the paper names A3C) need a fitting function supplied by the job owner.
- It covers PS-based data-parallel training only.
- Scaling by checkpoint and restart may be costly for jobs with hundreds of tasks. The paper suggests capping the number of checkpoints per job (§7).
- Theorem 1 assumes synchronous training on homogeneous servers, and the placement experiments rank servers by CPU capacity. The paper does not clearly model GPUs as a separate dimension in placement.
- No fairness guarantee: the objective is JCT and makespan. The only anti-starvation measures are the 1-PS/1-worker floor and placing small jobs first.
- (Own analysis) The testbed is small (13 servers on 1GbE) and was run on 2018-era hardware. The communication model assumes the PS is the bottleneck, which does not carry over directly to all-reduce or NVLink/RDMA-based training.

## Relation to other systems

- **DRF (as used in Mesos/YARN):** used as a baseline with a fixed 1:1 PS:worker ratio. Optimus reuses DRF's dominant-share idea only to normalise marginal gain, while aiming at JCT instead of fairness (§6.1, §8).
- **Tetris:** packing baseline that favours short or small jobs. In the evaluation it was given Optimus's own speed and convergence estimates, so its gap to Optimus reflects allocation and placement policy, not prediction (§6.1).
- **SLAQ:** similar online loss fitting, but aimed at the quality of approximate or convex ML jobs, not production DL training (§8).
- **Ernest:** predicts performance from sampled runs chosen by experimental design. Optimus needs only 5–10 sample runs and also models convergence (§8).
- **Jockey / Morpheus:** rely on historical traces to meet deadlines. Optimus needs no prior runs of the job (§8).
- **Proteus:** uses transient VMs with a simpler performance model and targets cost (§8).
- (Own analysis) Later DL schedulers such as Tiresias, Gandiva and Pollux are often compared with Optimus. Tiresias avoids needing a convergence prediction, Gandiva adds time-slicing and migration, and Pollux jointly adapts batch size and resources. This comparison is not from the paper.

## Takeaways for practice

- Fit simple parametric models online, and refit them often. A three-parameter loss curve and a few-term throughput model, fitted with NNLS on a handful of short pre-runs, were enough to drive scheduling.
- Rank jobs by marginal gain per unit of dominant resource. This greedy rule is cheap (4,000 jobs within 5 s in simulation) and handles several resource types in one rule.
- Choose the PS:worker ratio per job instead of fixing it. In the paper's ablation, the allocation algorithm accounts for the largest gain.
- Pack each job onto as few servers as possible and spread its tasks evenly across them, to bound the slowest transfer per step.
- Check framework-level load balance. Uneven parameter sharding across PSs alone cost up to 29% speed in MXNet.
- Dampen decisions for young jobs, whose predictions are least accurate. Speed error hurt more than convergence error in the paper's sensitivity study.
- (Own analysis) Restart-based elasticity is acceptable at 10-minute intervals (2.54% overhead here). Finer-grained or larger-scale resizing needs cheaper reconfiguration than checkpoint/restart.

## References

- Paper: https://dl.acm.org/doi/10.1145/3190508.3190517
- PDF (author's HKU page): https://i.cs.hku.hk/~cwu/papers/yhpeng-eurosys18.pdf
