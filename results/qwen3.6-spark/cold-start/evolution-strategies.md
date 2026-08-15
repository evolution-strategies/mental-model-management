# Mental Model: Evolution Strategies

Evolution Strategies (ES) are stochastic optimization methods inspired by biological evolution principles. They optimize continuous problems using real-valued parameter vectors without requiring objective function derivatives. This makes them suitable for noisy, non-differentiable, or expensive-to-evaluate functions.

## Core Mechanisms

ES operates through iterative cycles of variation and selection:

1. **Variation**: New candidate solutions (offspring) are generated from existing ones (parents).
2. **Evaluation**: Offspring fitness is assessed via an objective function.
3. **Selection**: Promising individuals are retained for subsequent generations.

### The $(1+1)$-ES Example

The simplest ES variant maintains a single parent $\mathbf{x}$. In each iteration:

$$
\mathbf{x}' = \mathbf{x} + \sigma \mathbf{z}
$$

Where $\mathbf{z}$ is sampled from a multivariate standard normal distribution and $\sigma > 0$ is the mutation strength. If fitness($\mathbf{x}'$) > fitness($\mathbf{x}$), the offspring replaces the parent.

## Mutation Strength Adaptation

A constant mutation strength $\sigma$ is suboptimal because search requirements change during optimization:
- **Large $\sigma$**: Promotes exploration far from the optimum but risks overshooting promising regions.
- **Small $\sigma$**: Supports local refinement near the optimum but may stall progress if too small.

Effective ES algorithms adapt $\sigma$ dynamically using feedback from the optimization process itself.

### Success-Based Adaptation

Algorithms monitor the success rate of recent mutations. The classical **$1/5$ success rule** adjusts $\sigma$ based on whether the observed success rate exceeds a target threshold (typically 1/5). High success rates increase $\sigma$; low rates decrease it.

### Self-Adaptation

Strategy parameters (like $\sigma$) are encoded within the individual's genotype. Mutation modifies both the solution and its strategy parameters. Selection indirectly favors parameter values that produce successful offspring, allowing parameters to evolve alongside the solution.

## Population Dynamics

- **$(\mu, \lambda)$-ES**: $\mu$ parents generate $\lambda$ offspring; next generation selected only from offspring (comma-selection). Encourages continued adaptation.
- **$(\mu+\lambda)$-ES**: Selection considers both parents and offspring (plus-selection). Preserves good parents longer.

## Recombination

Recombination combines information from multiple parents (e.g., averaging or component selection), while mutation introduces stochastic variation. Recombination exploits existing information; mutation explores new variations.

## Knowledge Gaps

- How quickly should strategy parameters react to new observations?
- When is a scalar mutation strength sufficient versus when is covariance adaptation necessary?
- How should population size change dynamically during optimization?
- How should adaptation behave specifically under high-noise conditions?

## Relations

Evolution Strategies -> implements -> Search Distribution Adaptation
Mutation Strength -> controls -> Search Scale
Covariance Matrix -> controls -> Directional Structure
Selection -> determines -> Which Information Survives
Adaptation -> uses -> History of Search Outcomes
CMA-ES -> adapts -> Search Distribution Shape and Scale
Self-Adaptation -> associates -> Strategy Parameters with Individuals
Recombination -> combines -> Information from Multiple Parents
Mutation -> introduces -> Stochastic Modifications
Population Size -> influences -> Diversity and Information Volume
Noisy Environments -> disrupt -> Relationship between Observed Fitness and True Quality

## Provenance

Source: examples/es_long_input.md
