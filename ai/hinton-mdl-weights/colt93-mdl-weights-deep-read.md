---
title: 'Keeping Neural Networks Simple by Minimizing the Description Length of the Weights'
authors:
- Geoffrey E. Hinton
- Drew van Camp
affiliations: 'Department of Computer Science, University of Toronto'
venue: 'COLT'
year: 1993
abs_url: https://www.cs.toronto.edu/~hinton/absps/colt93.pdf
pdf_url: https://www.cs.toronto.edu/~hinton/absps/colt93.pdf
note_type: deep-read
written_at: '2026-11-25'
---

# Keeping Neural Networks Simple by Minimizing the Description Length of the Weights

> **Why it matters:** It turns "regularize the weights" into a concrete coding cost, where each weight is a Gaussian with a learned mean and variance and its cost is a KL divergence to a learned mixture prior, and it trains that objective with exact (not sampled) gradients.

Version used: the PDF on Hinton's own site, whose first page prints no date or venue. Its extracted text loses minus signs, exponents and ligatures, so numbers garbled that way are left out. The full text could only be read in parts, and the section numbers in the headings below are mapped from the paper's heading list, so treat them as approximate.

## Problem

The paper's starting claim (Abstract) is that "Supervised neural networks generalize well if there is much less information in the weights than there is in the output vectors of the training cases." With small training sets, minimizing squared error alone overfits. The question is how to measure the information in the weights, penalize it in a principled way, and optimize that penalty jointly with the data fit.

The framing is the Minimum Description Length principle (Section 2). A sender transmits the training outputs to a receiver who already has the inputs. The cost is the bits for the weights plus the bits for the output misfits, and the best network minimizes that sum.

## Core design

### Coding the data misfits (Section 3)
- Misfits are quantized to a fixed tolerance and coded under a zero-mean Gaussian per output unit, with the RMS misfit as the optimal standard deviation. Minimizing that description length amounts to minimizing squared error.

### Simple weight coding gives weight decay (Section 4)
- Coding weights under a fixed zero-mean Gaussian gives squared error plus a squared-weight term, which is weight decay. Only the ratio of the two variances matters, and it has to be chosen on held-out data.

### Noisy weights and "bits back" (Section 5)
- Each weight has an independent Gaussian posterior Q with its own learned mean and variance. Sender and receiver share a coding prior P.
- Bits-back argument (5.2): the sender picks a precise weight value from Q using random bits and codes it under P. The receiver can rerun the learning procedure, recover Q, and so recover the random bits. Those bits are refunded. The expected net cost of a weight is then the asymmetric divergence (KL) between Q and P, which has a closed form when both are Gaussian.
- The trade-off: a high-variance posterior is cheap to describe, but its noise adds variance to the outputs and so raises the expected misfit cost (5.3).

### Exact expected error for one hidden layer (Sections 5.3, 8)
- With one hidden layer of sigmoid units and linear outputs, a hidden unit's total input is Gaussian with a computable mean and variance.
- A precomputed 2-D lookup table indexed by that mean and variance gives the sigmoid output's mean and variance. A second table gives the derivatives needed for backpropagation.
- With linear outputs, the output mean and variance follow in closed form. The expected squared error is the squared error of the mean output plus the output variance, so training needs no Monte Carlo sampling of weights.

### Learned mixture-of-Gaussians prior (Sections 6, 7)
- Instead of a single fixed Gaussian, the coding prior is a mixture of Gaussians. Its means, variances and mixing proportions are learned along with the weights, so weights are pulled toward nearby cluster centres.
- The KL to a mixture has no closed form. Section 7 codes a component choice with Boltzmann-like probabilities and refunds those bits. A free-energy lemma (7.1) turns the cost into a computable log-sum-exp of per-component Gaussian divergences.

### Optimization (Sections 8, 9)
- All parameters (weight means, log variances, prior parameters, with mixing proportions through a softmax) are optimized together with conjugate gradient. Derivatives were checked numerically against finite differences.
- Penalizing the full weight cost from the start collapses the network into a trivial solution. So the weight cost is multiplied by a coefficient that "starts at .05 and gradually increases to 1" on a printed schedule.
- The optimization was run five times from different random initial means. The run with the lowest overall cost is the one reported.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Input dimension | 128 parameters per molecule | Peptide-effectiveness task, scalar output | Sec. 9 |
| Train / test split | 105 training cases, 420 test cases | Same task | Sec. 9 |
| Network size | 4 hidden units, 521 adaptive weights (incl. biases) | One hidden layer | Sec. 9 |
| Coding prior | Adaptive mixture of 5 Gaussians | Prior over weights | Sec. 9 |
| Lookup table | 300 x 300 with linear interpolation | Sigmoid output moments/derivatives | Sec. 8 |
| CG updates per coefficient value | 100 | Annealed weight-cost schedule starting at .05 | Sec. 9 |
| Initial posterior std of weights | 0.1 | All weights | Sec. 9 |
| Initial posterior means | Drawn from N(0, 0.15 std) | All weights | Sec. 9 |
| Optimization runs | 5 | Different random initial means | Sec. 9 |
| Relative test error, noisy weights + mixture prior | 0.286 | Lowest-overall-cost run | Sec. 9 |
| Relative test error, simple weight decay | 0.317 | 4 nonlinear hidden units, coefficient picked on held-out part of training set | Sec. 9 |
| Relative test error, weight decay tuned on test data | 0.291 | Paper says "this is cheating" | Sec. 9 |
| Relative test error, no penalty | 0.967 | Same network, noise-free weights | Sec. 9 |
| Relative test error, linear regression | 35.6 | No penalty ("gross overfitting") | Sec. 9 |
| Relative test error, penalized linear regression | 0.291 | Penalty chosen on test data | Sec. 9 |
| Relative test error, full-cost-from-start solution | approximately 1.0 | All weights equal and negative | Sec. 9 |

Relative error is test squared error divided by the squared error of guessing the test-set mean (Sec. 9, eq. 27), so 1.0 means no better than the mean.

## Limitations

- **One small task.** All the evidence comes from 105 training cases. The authors say they "have not yet performed a thorough comparison" and that "much more experimental work is required" (Sec. 9).
- **Small margin.** 0.286 against 0.317 for honestly tuned weight decay.
- **MDL's optimum is the trivial solution.** With the full weight cost applied from the start, the optimizer makes all weights equal and negative, with relative error near 1.0. The paper calls this "a serious embarrassment for the Minimum Description Length Principle or for our method of describing the weights" (Sec. 9). The reported result depends on the annealed schedule and on picking the best of five runs.
- **Architecture restriction.** The exact expected error needs one hidden layer and linear outputs.
- **Diagonal posterior.** Weight covariances are ignored, and "it is not clear how much is lost" (Sec. 10).

## Relation to other systems

The paper itself names the following comparison points.

- **Weight decay (Sec. 4, 9).** The special case of a fixed Gaussian prior and noise-free weights, with its coefficient found by a validation sweep. The noisy-weight method learns its prior and gets 0.286 against 0.317.
- **Unregularized backprop (Sec. 9).** The same network with noise-free weights and no penalty gets 0.967.
- **Linear regression, plain and penalized (Sec. 9).** Plain regression overfits (35.6). Penalized regression matches test-tuned weight decay (0.291), which the authors attribute to small weights keeping the hidden units in their linear range.
- **Exact Bayesian averaging (Sec. 10).** Averaging predictions over the true posterior is called intractable. This paper replaces it with one factorized Gaussian posterior, optimized directly.
- **Neal (1993), Monte Carlo (Sec. 10).** Samples the posterior using backprop gradients and avoids "unrealistically simple assumptions" about its shape, at the price of sampling. This paper is deterministic, with a restrictive posterior.
- **MacKay (1992) (Sec. 10).** Fits a full-covariance Gaussian around one local optimum after training. This paper uses a diagonal Gaussian whose variances are learned. The authors argue learning should push the noise toward independence. They were running simulations to test this and report no result.

## Takeaways for practice

Every item here is (Own analysis), aimed at people building GPU training and inference systems.

- **Weight noise is a precision budget.** A large learned variance means a weight tolerates noise, which is the quantity an inference platform needs when deciding how much precision a tensor can lose. The paper gives the objective, not a quantization method.
- **Moment propagation instead of sampling.** Pushing means and variances through the network with lookup tables gives a stochastic objective with no per-step sampling, at the cost of a restricted architecture. Check for that trade before building a sampled estimator on accelerators.
- **A learned mixture prior clusters weights**, much like codebook or weight-sharing compression. A training-time penalty is a place to build compressibility in instead of adding it only after training.
- **Penalty schedules are configuration.** At full strength, the principled objective finds a useless solution. A schedule plus best-of-five restarts made it work, so log regularizer schedules and keep them reproducible.
- **Tune honestly.** The paper calls test-set tuning cheating, and the honest baseline is worse (0.317 against 0.291). Enforce a held-out split for every swept coefficient.
- **Doubled parameter state.** Every weight carries a mean and a variance, which matters for memory, sharding and checkpoints at scale.

## References

- Paper (author's site): https://www.cs.toronto.edu/~hinton/absps/colt93.pdf
