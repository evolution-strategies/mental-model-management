# Mental Model: Covariance Matrix Adaptation

Covariance Matrix Adaptation Evolution Strategy (CMA-ES) extends basic ES by adapting the shape of the search distribution, not just its scale. This allows the algorithm to learn variable correlations and align with the local geometry of the objective landscape.

## Limitations of Isotropic Mutation

Standard Gaussian mutation with a single scalar strength produces an isotropic (spherical) search distribution. This treats all directions equally, which is inefficient for functions with:
- Different sensitivities across dimensions.
- Ill-conditioned landscapes (e.g., long narrow valleys).

In such cases, isotropic mutations frequently leave promising regions or overshoot the optimum.

## Covariance Adaptation

CMA-ES uses a covariance matrix to define the mutation distribution's scale and orientation. By adapting this matrix:
1. **Scale**: Controls the overall step size (similar to $\sigma$).
2. **Shape/Orientation**: Aligns the search distribution with promising directions in the search space.

Information from successful search steps is accumulated over time to modify the covariance matrix. This allows the distribution to become elongated and rotated, reflecting the local structure of the objective function.

## Geometry and Optimization

- **Sphere Function**: Symmetric, no variable interactions. Scalar adaptation suffices as distance to optimum decreases uniformly.
- **Ill-Conditioned Functions**: Require covariance adaptation to align mutations with narrow valleys. Learning geometry is as critical as adapting overall strength.

## Relations

CMA-ES -> adapts -> Search Distribution Shape and Scale
Covariance Matrix -> controls -> Directional Structure
Isotropic Mutation -> treats -> All Directions Equally
Ill-Conditioned Functions -> require -> Covariance Adaptation
Sphere Function -> allows -> Scalar Adaptation Sufficiency

## Provenance

Source: examples/es_long_input.md
