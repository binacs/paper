---
title: 'A Tutorial Introduction to the Minimum Description Length Principle'
authors:
- Peter Grünwald
affiliations: 'Centrum voor Wiskunde en Informatica (CWI), Amsterdam'
venue: 'arXiv'
year: 2004
arxiv_id: 'math/0406077'
abs_url: https://arxiv.org/abs/math/0406077
pdf_url: https://arxiv.org/pdf/math/0406077v1
note_type: deep-read
written_at: '2026-11-25'
---

# A Tutorial Introduction to the Minimum Description Length Principle

> **Why it matters:** It recasts model selection as data compression, so that "fit vs. complexity" becomes a single, additive quantity in bits, with no need to assume a true data-generating distribution.

Version used: arXiv math/0406077v1 (4 Jun 2004), the only version listed. Coverage: Chapter 1 (§1.1–§1.8) and Chapter 2 from §2.1 through §2.5.2 (up to the start of Example 2.12, the Bayesian universal model). §2.5.3 (NML) and §2.6–§2.11 were not readable through the fetch tool and are not summarized here.

## Problem

Given data and a list of candidate models of growing richness (polynomials of degree k, Markov chains of order k), pick the one that best captures the regularity in the data. Plain maximum likelihood fails: the richest model always fits best, e.g. an (n−1)-degree polynomial through n points, or a Markov chain of order n−1 that gives the observed sequence probability 1 (§1.3, §2.3). The tutorial argues that the right yardstick is compression: any regularity can be used to compress the data, so learning is finding the description that compresses most (§1.2, §1.5). Two obstacles block a direct use of this idea. Ideal MDL, based on Kolmogorov complexity, is uncomputable and depends on the choice of description language up to a constant (§1.2.1). Practical MDL therefore restricts itself to description methods drawn from the candidate models (§1.2.2).

## Core design

**Codes and probabilities (§2.2).**
- Only prefix codes are used: no codeword is a prefix of another. The author argues that this restriction loses nothing for codelengths (§2.2.1).
- Boxed correspondence (§2.2.2): for any probability mass function P there is a prefix code with L(z) = ⌈−log P(z)⌉. Conversely, every prefix code defines a (possibly defective) distribution. After dropping integer rounding, codelength functions and probability distributions are treated as the same object.
- Information inequality (§2.2.3): if the data come from P, the code built from P minimizes expected codelength. By the law of large numbers, this also governs actual codelengths for large samples.

**Crude two-part MDL (§1.3, §2.4).**
- Select the point hypothesis H minimizing L(H) + L(D|H). The selected model is the smallest model that contains H.
- L(D|H) = −log P(D|H). Section 2.4.1 justifies this as the only sensible choice: it equals the negative log-likelihood, it minimizes expected codelength when H is true, and other choices can make MDL inconsistent.
- The code for hypotheses must not depend on n. Otherwise MDL collapses to maximum likelihood and overfits. With any fixed code, two-part MDL is consistent for a wide range of models, Markov chains included: beyond some sample size it selects the true P* (§2.4.2).
- Worked code for Markov chains (Example 2.8): encode the order with the integer code of Example 2.4, then each parameter as a count in {0,…,n} using log(n+1) bits. Reserving codewords only for parameters on a coarser grid shortens this to eq. (2.9): −log P(D|k, θ̂) + (k/2) log n + c_k. The author calls this "optimal" in a sense developed in §2.6.
- The "bad news" (§2.4.2): nothing in crude MDL says how to design L(H). This motivates universal codes.

**Universal codes and models (§2.5, read through §2.5.2).**
- Goal: one code, agreed in advance, that encodes every sequence nearly as well as the hindsight-best code in a candidate set. Matching it exactly is impossible, since the implied probabilities would sum to more than 1 (Example 2.9, nine Bernoulli codes with θ = 0.1,…,0.9).
- Two-part codes are the simplest universal codes. For a finite set of M codes, first send the index of the best code with a uniform code, then the data; the overhead is log M (Example 2.10, eq. 2.11). For a countable set, first send the index k with the integer code, and the overhead for the k-th code is at most 2 log k + 1 (Example 2.11).
- Every universal code maps back to a universal model, a single (possibly defective) distribution. The author warns that the term is "twice misleading": the model is universal only relative to the candidate set, and in information theory "model" names one distribution, not a family. Example 2.12 begins with the Bayesian mixture over a prior W; the text read here stops at that point.

**Refined MDL, as previewed in Chapter 1 (§1.4).**
- A whole model is given one universal one-part code. Its codelength is the stochastic complexity, which the paper writes as "L(D | Ĥ) + COMP(H)". Ĥ is the maximum-likelihood member of the model, and COMP(H), the parametric complexity, measures the model's ability to fit random data.
- §1.4 lists four interpretations: counting/differential-geometric, two-part code, Bayesian (Bayes factors with a non-informative prior such as Jeffreys' prior), and prequential (the best sequential predictor of unseen data).
- Example 1.4: Stevens' model y = ax^b + Z and Fechner's model y = a ln(x + b) + Z both have two parameters, yet Stevens' model is more flexible. Refined MDL assigns it the larger complexity term, so it prefers Fechner's model when both fit about equally well.

**Philosophy (§1.5–§1.6).** A model is a language for describing data; "noise" is relative to that model, and consistency is only a sanity check. Preferring simple models is a small-sample strategy, not a claim that the world is simple: an overly simple model's best fit tends to predict about as well as it fits, while an overly complex model's best fit can predict very badly (Example 1.6).

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Length of each example sequence | 10000 bits | Three binary sequences: regular, random, biased | §1.2 |
| First sequence | 2500-fold repetition of 0001 | Deterministic regularity example | §1.2 |
| Stevens' model fits better | 67% of trials | Many samples of size 4 generated from Fechner's model (Myung, Balasubramanian, Pitt 2000) | §1.4, Example 1.4 |
| Compress fair-coin data by more than 20 bits | probability smaller than one in a million | Counting argument | §2.2.2, Example 2.2 |
| Two-part MDL penalty | (k/2) log n + c_k | Markov chains, coarse parameter grid | §2.4.2, eq. (2.9) |
| Index cost, nine Bernoulli codes | log 9 bits | Uniform code over the candidates | §2.5.1, Example 2.10 |
| Two-part universal code overhead, M codes | log M | Finite candidate set | §2.5.1, eq. (2.11) |
| Two-part overhead, k-th of countably many codes | at most 2 log k + 1 | Integer code for the index | §2.5.1, Example 2.11 |
| First MDL paper | Rissanen 1978 | History | §1.7 |
| Precise prescription of MDL | 1996 | History | §1.4 |
| First summary of refined MDL | Barron, Rissanen and Yu 1998 | History | §1.7 |

## Limitations

- Crude MDL gives no principle for choosing the hypothesis code L(H). The paper states this itself (§2.4.2), and it is the reason refined MDL exists.
- Practical MDL is only as good as the chosen family of description methods; ideal MDL, which avoids that choice, is uncomputable (§1.2.1).
- No universal code can match the hindsight-best code on every sequence (Example 2.9). There is always some overhead, such as log M or 2 log k + 1.
- Consistency guarantees in §2.4.2 hold beyond some unspecified sample size and require that the true distribution have a finite codelength under the fixed code.
- Example 2.8 (the Markov-chain code) has a notational mismatch. The text says the parameters take k′ log(n+1) bits with k′ = 2^k, but the displayed L(P) uses k log(n+1).
- The paper's own list of problems for MDL (§2.10) was not readable and is not covered.

## Relation to other systems

The paper compares MDL only with other inference approaches, not with software systems.
- **Maximum likelihood (§2.3, §2.4.2):** MDL adds a codelength term for the hypothesis or model. Without it, or with a hypothesis code that varies with n, MDL reduces to ML and overfits.
- **Kolmogorov complexity / ideal MDL (§1.2.1):** this is the conceptual origin. Practical MDL trades its generality for computability by restricting description methods.
- **Bayesian inference (§1.4):** refined MDL often coincides with Bayes factor selection under Jeffreys' prior. The paper's framing (§1.5) differs: it does not read the prior as a degree of belief in a true model.
- **Prequential approaches (§1.4):** refined MDL can be read as choosing the best sequential predictor of unseen data.
- **Wallace's Minimum Message Length (§1.7):** the paper calls it closely related, starting with Wallace and Boulton (1968).
- **Akaike's AIC (§1.7):** named as an influence on Rissanen's first MDL paper.

## Takeaways for practice

All points below are (Own analysis), aimed at engineers building GPU training and inference systems.

- When choosing among model variants, compression methods or configurations, account for the cost of the choice itself. The log M overhead for picking one of M candidates (eq. 2.11) is a clean reminder that a wider search buys better fit at the price of more selection cost.
- Treat −log P(data) as the goodness-of-fit metric in nats or bits. It is additive, it relates directly to codelength, and it is the one choice the tutorial defends for L(D|H) (§2.4.1).
- Keep the description scheme fixed before seeing the data. If the scheme is tuned to the sample size or to the data, MDL degenerates to maximum likelihood (§2.4.2). The same discipline applies to fixing evaluation protocols before hyperparameter sweeps.
- The fit-vs-complexity asymmetry in Example 1.6 favors erring toward simpler models when evaluation data are small. An underfit model's in-sample error predicts its out-of-sample error better than an overfit model's does.

## References

- Paper: https://arxiv.org/abs/math/0406077 (PDF: https://arxiv.org/pdf/math/0406077v1)
