# JITS manuscript drafting template

Use this as a working outline. Replace brackets with study-specific content and delete prompts before submission.

## Title

`[task or consequence] using [method/framework] in [setting/data/constraint]`

## Abstract

`[Problem and consequence]. Existing [method family] cannot [capability] because [testable limitation]. We develop [named method], consisting of [module A] for [gap 1] and [module B] for [gap 2]. Using [data/scenario, scale, and validation design], we compare against [baselines] with [metrics]. The method achieves [absolute result] and [relative/comparative result] under [condition], while [cost/safety/uncertainty/boundary]. These findings support [specific operational or policy action].`

## Introduction

1. Why the transportation problem matters.
2. Prior work grouped by approach and assumption.
3. Gap 1: `[missing capability]`.
4. Gap 2: `[missing capability]`.
5. Research questions or hypotheses.
6. Contributions:
   - `[artifact or mechanism]`, tested in Section `[x]` with metric `[y]`.
   - `[artifact or mechanism]`, tested in Section `[x]` with metric `[y]`.
   - `[validation or application contribution]`, tested across `[scenarios]`.
7. Paper organization.

## Methods

### Problem, scope, and notation

Define the unit of analysis, inputs/outputs, assumptions, constraints, outcome metrics, and what is out of scope.

### Framework overview

Insert one figure showing data flow, modules, decision points, and outputs.

### Module or algorithm details

For each module: motivation → equation/algorithm → parameters → expected effect → ablation or test that isolates it.

### Data and experimental design

Record source, time and space coverage, sample count, label/ground-truth process, preprocessing, split, hyperparameters, hardware, seeds/repetitions, baselines, metrics, and statistical tests.

## Results

### RQ1: Main comparison

Report absolute values, relative changes, uncertainty, and fair baseline conditions.

### RQ2: Mechanism and ablation

Show what changes when each module, feature, constraint, or loss is removed or replaced.

### RQ3: Robustness and boundary

Vary the operating condition that matters: demand, horizon, site, weather, sensor error, penetration, data split, or model backbone.

### RQ4: Deployment or case evidence

Translate model output into delay, safety, emissions, cost, workload, latency, coverage, or policy consequences. Include a failure or error analysis.

## Discussion

Explain why the observed mechanism is plausible, compare with prior findings, state the practical decision rule, and separate evidence from inference.

## Limitations

For each item use: `[assumption or coverage] → [validity/deployment consequence] → [next measurable study]`.

## Conclusion

Answer each research question, restate the two or three most important quantitative findings, state the bounded application implication, and give only future work that follows from the reported limitation.
