# Mental Model: Search Distribution Adaptation

Evolution Strategies can be viewed as adaptive systems that construct a progressively more appropriate probability distribution for generating candidate solutions. Optimization is an iterative process where search outcomes provide information to modify future search behavior.

## Unified View of Adaptation

Step-size adaptation and covariance adaptation address related but distinct aspects of the search distribution:
- **Step-Size**: Controls overall scale.
- **Covariance**: Controls directional structure.

Both are instances of adapting the search distribution using information obtained during optimization.

## Information Flow

1. **Search**: Generates observations (candidate solutions and fitness values).
2. **Observation**: Provides information about the landscape (e.g., success rates, promising directions).
3. **Adaptation**: Converts this information into changes in strategy parameters (mutation strength, covariance matrix, population size).
4. **Selection**: Determines which outcomes are considered successful.

## Key Components

- **Mutation**: Generates variation.
- **Mutation Strength**: Controls variation scale.
- **Covariance**: Controls directional structure.
- **Population Size**: Influences diversity and information volume per generation.
- **Selection**: Filters information survival.
- **Adaptation**: Updates parameters based on historical success/failure.

## Exploration vs. Exploitation

This balance is continuously adjusted, not separated into phases:
- **Exploration**: Large mutation strengths, diverse populations, broad distributions.
- **Exploitation**: Small mutation strengths, concentrated distributions.

Successful ES algorithms dynamically shift between these modes based on current search state and landscape geometry.

## Noisy Environments

Noise disrupts the relationship between observed fitness and true quality. Responses include:
- Repeated evaluations.
- Larger populations for statistical robustness.
- Mechanisms explicitly accounting for uncertainty.

## Relations

Evolution Strategies -> implements -> Search Distribution Adaptation
Step-Size Adaptation -> controls -> Overall Scale of Search
Covariance Adaptation -> controls -> Directional Structure of Search
Selection -> determines -> Which Outcomes are Successful
Adaptation -> converts -> Information into Parameter Changes
Exploration -> associated with -> Large Mutation Strengths and Diverse Populations
Exploitation -> associated with -> Small Mutation Strengths and Concentrated Distributions
Noisy Environments -> disrupt -> Relationship between Observed Fitness and True Quality

## Provenance

Source: examples/es_long_input.md
