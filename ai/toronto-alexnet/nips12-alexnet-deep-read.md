---
title: 'ImageNet Classification with Deep Convolutional Neural Networks'
authors:
- Alex Krizhevsky
- Ilya Sutskever
- Geoffrey E. Hinton
affiliations: 'University of Toronto'
venue: 'NeurIPS'
year: 2012
abs_url: https://proceedings.neurips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html
pdf_url: https://proceedings.neurips.cc/paper_files/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf
code_url: http://code.google.com/p/cuda-convnet/
note_type: deep-read
written_at: '2026-11-25'
---

# ImageNet Classification with Deep Convolutional Neural Networks

> **Why it matters:** A 60M-parameter CNN, hand-split across two 3 GB GTX 580 GPUs and fed by a CPU-side augmentation pipeline, cut ILSVRC-2012 top-5 test error to 15.3% against 26.2% for the runner-up, and the paper says plainly that GPU memory and training time capped its size.

## Problem

The goal is to classify about 1.2M ImageNet (ILSVRC) training images into 1000 classes with a CNN large enough to use that much labelled data. Two constraints shape the design. First, hardware: "the network's size is limited mainly by the amount of memory available on current GPUs and by the amount of training time that we are willing to tolerate" (§1), and "a single GTX 580 GPU has only 3GB of memory" (§3.2). Second, overfitting: each example imposes only 10 bits of constraint, which is not enough to learn 60M parameters without considerable overfitting (§4). The answer is systems work (a hand-written GPU convolution and a two-GPU model split) plus regularization (augmentation and dropout).

## Core design

### Network (§3.5, Fig. 2)
- Five conv layers and three fully-connected layers, ending in a 1000-way softmax. Input is 224×224×3.
- Conv1: 96 kernels of 11×11×3, stride 4. Conv2: 256 of 5×5×48. Conv3: 384 of 3×3×256. Conv4: 384 of 3×3×192. Conv5: 256 of 3×3×192. FC6/FC7: 4096 neurons each.
- ReLU after every conv and FC layer. Local response normalization (LRN) after conv1 and conv2. Overlapping max-pooling after both LRN layers and after conv5.
- (Own analysis) The kernel depths of 48 and 192 reflect the split: those layers see only their own GPU's half of the previous maps.

### Two-GPU model parallelism (§3.2)
- The model is split, not the data: "half of the kernels (or neurons) on each GPU". In the Fig. 2 caption, one GPU runs the top layer-parts and the other runs the bottom ones.
- The GPUs exchange data only at certain layers. Conv3 takes input from all conv2 maps on both GPUs. Conv2, conv4 and conv5 read only maps on their own GPU (§3.5). The fully-connected layers are connected to all neurons in the previous layer (§3.5).
- The GPUs "are able to read from and write to one another's memory directly, without going through host machine memory" (§3.2).
- The connectivity pattern is "a problem for cross-validation". In the paper's words, it lets the authors "precisely tune the amount of communication until it is an acceptable fraction" of computation (§3.2).
- The one-GPU baseline has half as many kernels in each conv layer, but footnote 2 says it keeps the full kernel count in the last conv layer and in the FC layers. The authors note that this biases the comparison toward the one-GPU net.

### Speed-oriented choices
- **ReLU (§3.1):** Networks with ReLUs "train several times faster" than networks with tanh units.
- **GPU convolution code (§1):** They wrote "a highly-optimized GPU implementation of 2D convolution" and released it as cuda-convnet (footnote 1).

### Normalization and pooling
- **LRN (§3.3):** Each activity is normalized across n adjacent kernel maps at the same position, with k = 2, n = 5, α = 10⁻⁴, β = 0.75.
- **Overlapping pooling (§3.4):** The stride is s = 2 and the window is z = 3. The authors observe that models with overlapping pooling are slightly harder to overfit.

### Data pipeline and augmentation (§2, §4.1)
- Preprocessing: the shorter side is rescaled to 256 and the central 256×256 patch is cropped. The per-pixel training-set mean is subtracted, and the network trains on raw RGB values (§2).
- Augmentation 1: random 224×224 crops plus horizontal reflections, which grow the training set "by a factor of 2048". At test time the model averages softmax outputs over ten patches: four corners, the centre, and their reflections.
- Augmentation 2: PCA-based RGB intensity jitter. Multiples of the RGB principal components are added to each image, with magnitudes proportional to the eigenvalues times a Gaussian draw (mean 0, standard deviation 0.1).
- Systems point: the transformed images are generated "in Python code on the CPU while the GPU is training on the previous batch of images". They are never stored on disk, and the authors call the schemes "computationally free" (§4.1).

### Dropout (§4.2)
- In the first two FC layers, each hidden neuron's output is set to zero with probability 0.5. At test time, outputs are multiplied by 0.5. Dropout "roughly doubles the number of iterations required to converge".

### Optimization (§5)
- SGD with batch size 128, momentum 0.9 and weight decay 0.0005. Weight decay "is not merely a regularizer: it reduces the model's training error".
- Weights start from a zero-mean Gaussian with standard deviation 0.01. Biases are 1 in conv2, conv4, conv5 and the FC hidden layers, and 0 elsewhere.
- Learning rate: it starts at 0.01 and is divided by 10 by hand when validation error stops improving, three times before termination.
- About 90 passes through the 1.2M images, taking five to six days on two GTX 580 3 GB GPUs.

## Key numbers

| What | Value | Setting | Source |
|---|---|---|---|
| Parameters / neurons | 60M / 650,000 | Full network | Abstract |
| GPU memory | 3 GB per GTX 580 | Hardware limit cited for the split | §3.2 |
| Training time | 5–6 days | Two GTX 580 3 GB GPUs | §1, §5 |
| Passes over data | ~90 | 1.2M training images | §5 |
| Two-GPU vs one-GPU net | −1.7% top-1, −1.2% top-5 | Half-kernel one-GPU baseline | §3.2 |
| Two-GPU vs one-GPU training time | "slightly less" | Same comparison | §3.2 |
| ReLU vs tanh | 6× faster to 25% training error | Four-layer CNN, CIFAR-10 | Fig. 1, §3.1 |
| LRN gain | −1.4% top-1, −1.2% top-5 | ImageNet | §3.3 |
| LRN on CIFAR-10 | 13% → 11% test error | Four-layer CNN | §3.3 |
| Overlapping pooling gain | −0.4% top-1, −0.3% top-5 | s=2, z=3 vs s=z=2 | §3.4 |
| PCA colour augmentation | top-1 reduced by over 1% | ImageNet | §4.1 |
| Crop/flip augmentation | training set ×2048 | 224 crops from 256 images | §4.1 |
| Dropout cost | ~2× iterations to converge | FC1–FC2, p=0.5 | §4.2 |
| ILSVRC-2010 test | 37.5% top-1, 17.0% top-5 | Single CNN | Table 1 |
| Prior best, ILSVRC-2010 | 45.7% top-1, 25.7% top-5 | SIFT+FVs, test | Table 1 |
| ILSVRC-2012, 1 CNN | 40.7% top-1, 18.2% top-5 | Validation | Table 2 |
| ILSVRC-2012, 7 CNNs* | 36.7% top-1 / 15.4% top-5 (val); 15.3% top-5 (test) | 2 pretrained on Fall 2011 + 5 CNNs | Table 2 |
| ILSVRC-2012 runner-up | 26.2% top-5 | SIFT+FVs, test | Table 2 |
| Depth ablation | ~2% top-1 loss | Removing any middle conv layer | §7 |

## Limitations

- The two-GPU split is built into the architecture. The connectivity pattern was picked by cross-validation, so changing the GPU count changes the model (§3.2).
- The paper gives no throughput, per-iteration time, GPU utilization or communication volume. Its only timing evidence is the end-to-end five to six days and "slightly less time" than the one-GPU net (§1, §3.2).
- The one-GPU comparison does not hold the architecture fixed (footnote 2). (Own analysis) The 1.7% top-1 gain mixes the effects of model capacity and of the split.
- The learning-rate schedule was adjusted by hand from validation error (§5). (Own analysis) The recipe is hard to reproduce without a person watching the run.
- (Own analysis) The design is single-node, model-parallel only. Data parallelism, multi-machine scaling and fault tolerance are not discussed.
- The authors say GPU memory and the time they would tolerate capped the network's size, and that their experiments suggest results "can be improved simply by waiting for faster GPUs and bigger datasets" (§1). (Own analysis) The design is therefore tied to the hardware of its time.

## Relation to other systems

- **Cireşan et al. multi-column CNNs** (cited, §3.2): the paper says its columns, unlike theirs, are not independent. (Own analysis) The two GPU "columns" exchange activations at conv3 and in the FC layers, so they form one coupled model.
- **SIFT + Fisher Vectors / sparse coding** (cited, Tables 1–2): these hand-built feature pipelines were the previous state of the art and the ILSVRC-2012 runner-up. (Own analysis) The paper replaces them with features learned end-to-end on GPUs.
- **Dropout (Hinton et al.)** (cited, §4.2): the paper uses it in a large network and reports its cost of about twice as many iterations.
- **Jarrett et al. local contrast normalization** (cited, §3.3): the paper's LRN does not subtract the mean activity, so the authors call it "brightness normalization".
- **cuda-convnet** (footnote 1): this is the authors' own released GPU convolution code.

## Takeaways for practice

- **Memory decides the parallelism strategy.** The 3 GB limit forced model parallelism here (§3.2). (Own analysis) Size per-device memory first; it decides model vs data parallelism.
- **Design cross-device communication as a tunable knob.** The authors restricted which layers exchange data and tuned the pattern until communication was "an acceptable fraction" of computation (§3.2). (Own analysis) Cut points should come from profiling communication against compute.
- **Use direct device-to-device memory access.** The GPUs read and write each other's memory without staging in host memory (§3.2). (Own analysis) Check that peer-to-peer access or an equivalent fast link is really in use before assuming communication is cheap.
- **Overlap input processing with GPU compute.** Augmentation runs on the CPU, in Python, while the GPU trains on the previous batch, and nothing is written to disk (§4.1). (Own analysis) Keep the input pipeline on a separate resource, prefetch at least one batch, and treat augmentation throughput as a capacity question: a slow host pipeline will idle expensive GPUs.
- **Count regularization in the compute budget.** Dropout roughly doubles the iterations to converge (§4.2), and test-time predictions average ten patches (§4.1). (Own analysis) Both multiply compute and belong in capacity estimates.
- **Keep partitioning out of the model.** The best ILSVRC-2012 entry ensembled seven CNNs, two pretrained on a 15M-image, 22K-category set (§6, Table 2). (Own analysis) Such results hide a large compute bill, and code that hard-wires a device count, as this model does, ages quickly with each hardware generation.

## References

- Paper: https://proceedings.neurips.cc/paper_files/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf
- Abstract page: https://proceedings.neurips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html
- Code (as cited in the paper, footnote 1): http://code.google.com/p/cuda-convnet/
