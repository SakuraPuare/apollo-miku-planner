---
name: jits-writing
description: Write, revise, or review transportation and intelligent-transportation manuscripts for Journal of Intelligent Transportation Systems (JITS) using evidence-based patterns extracted from 39 recent JITS papers. Use for paper framing, title/abstract, introduction, methods, experiments, discussion, and submission-readiness checks; it does not guarantee acceptance or replace the journal's current author instructions.
metadata:
  short-description: JITS transportation paper writing guide
---

# JITS 论文写作 skill

Use this skill when a manuscript targets the *Journal of Intelligent Transportation Systems* or a closely related intelligent-transportation venue. The guidance below describes recurring, auditable patterns in the supplied 39-paper sample (JITS volume 30, issues 3–5, 2026). Treat them as design heuristics, not as a promise of acceptance. Before submission, check the current Taylor & Francis author instructions, article type, ethics requirements, word limits, reference style, and data/code policy.

## JITS submission hard limits (Taylor & Francis, 2026 instructions)

These are publisher-enforced ceilings, not stylistic guidance. Verify them against the current author instructions on the day of submission; when they change, update this section.

| Article type    | Body word count               | Abstract         | Keywords |
|-----------------|-------------------------------|------------------|----------|
| Research Article| ≤ 7000 words, inclusive of abstract, tables, references, figure/table captions | Unstructured, ≤ 250 words | 3–5 |
| Data Note       | ≤ 3000 words                  | Structured (Introduction / Methods / Results / Discussion), ≤ 250 words | 3–6 |
| Method          | 2500–4000 words               | Structured (Introduction / Methods / Results / Discussion), ≤ 200 words | 3–6 |

Other publisher-enforced items to comply with before hitting *Submit*:

- English only; American spelling; double quotation marks; long quotations indented without quote marks.
- References in Taylor & Francis APA style.
- Every submission must include: data availability statement, code availability where applicable, funding statement (or "no funding"), disclosure of interest statement (or "no competing interests"), author contributions (CRediT), and a generative-AI-use statement (or a statement that AI was not used).
- Figures at 1200 dpi line art, 600 dpi grayscale, 300 dpi colour; supplied separately from the text.
- SI units, non-italicised; editable equations if submitting in Word.
- LaTeX submissions must upload both the compiled PDF (named and anonymous where applicable) and a zipped LaTeX source bundle.
- Colour figures in print incur charges; monochrome-safe design is prudent.

## Length discipline heuristic

Before drafting, budget every word:

- Reserve about 200 words for the abstract and use the remainder for the body. Overshooting the abstract by 30–60 words is common when the six-step evidence chain is applied without pruning; treat "compact" in that chain as a hard rule, not a suggestion.
- After each major revision round, count words with the same tool used at submission (e.g., `texcount` for LaTeX; the T&F Portal word counter is authoritative). Do not rely on rendered page counts.
- If a Chinese review/twin manuscript is being maintained alongside the English submission, target ≤ 350 CJK characters for the abstract when the English abstract is at 234–250 words; a 1.4–1.6 character-per-word ratio is a workable expansion budget. Keep punctuation full-width in prose and half-width inside math, `\cite`, `\label`, `\ref`, and paths.

## Start with a fit statement

Write one sentence that connects the transportation consequence, the research object, and the paper's contribution:

> In [specific transportation setting], [measurable operational/safety/environmental problem] remains unresolved because [testable limitation in prior work]; this paper develops [named method/system] and evaluates it under [data/scenarios] using [decision-relevant metrics].

If the sentence cannot name a setting, a measurable consequence, and a falsifiable gap, narrow the paper before drafting prose.

## Title

Prefer:

`[transportation task or consequence] + [method/framework/system] + [scene, constraint, or data source]`

Examples from the sample include a control method *considering dedicated lanes*, a stress framework *based on urban street view and explainable machine learning*, and statewide geometry extraction *using GIS and deep learning from road maps*. Use a named method or system only when the paper explains what it does. Avoid titles that say only “a study,” “an analysis,” or a model acronym without the task and setting.

## Abstract: a compact evidence chain

Keep one coherent paragraph, normally in this order:

1. State the real transportation, safety, environmental, policy, or service problem.
2. Identify the specific gap or failed assumption in existing work.
3. Name the method and its modules, with each module tied to one gap.
4. Give the data, study area, participants, simulation, or validation design and its scale.
5. Report two to four decision-relevant numbers: an absolute metric, a comparison or relative change, and where useful a cost, latency, uncertainty, or safety measure.
6. Translate the result into an operational, design, regulatory, or deployment implication, then state the main boundary when it materially limits interpretation.

Do not use “significantly improves” without a number, comparison, or statistical test. Distinguish an internal benchmark from an external or field validation. If the method has a negative or failed component in a realistic setting, report it briefly and explain the design choice that follows.

## Introduction: funnel, gap, contribution map

Use a four-part funnel:

1. Establish why the transportation problem matters to safety, reliability, emissions, equity, cost, or policy.
2. Organize prior work by method, data source, or operating regime. A comparison table is useful when studies differ in assumptions or metrics.
3. State two to four concrete gaps. Phrase each as a missing capability or testable assumption, such as “macro control lacks vehicle-level execution,” “periodic and hierarchical flow constraints are omitted,” or “abstract certification scenarios are not linked to field criticality.” Avoid “few studies have…” without saying what cannot currently be done.
4. List two to four numbered contributions. Each contribution must produce an identifiable artifact (model component, algorithm, dataset/processing pipeline, theorem, experiment, or policy result) and map to a later subsection and result. End with a short paper roadmap.

Use the recurring transition: existing work is useful under its stated assumptions; the present setting violates one of those assumptions; the proposed design addresses that violation and is tested in a defined regime.

## Methods: make the paper auditable

Present the method from overview to detail:

1. Scope, research questions or hypotheses, notation, data boundary, assumptions, and outcome definitions.
2. A framework or process figure showing inputs, modules, outputs, and decision points.
3. Module-level equations, algorithms, pseudocode, or proofs. Explain the mechanism each module is intended to change; do not list architecture components without a causal role.
4. Training, calibration, optimization, or controller settings: data source and time span, sampling and aggregation, preprocessing, train/validation/test split, hardware, hyperparameters, thresholds, random seeds or repetitions, and computational budget.
5. Baselines and metrics chosen before presenting results. Include both model metrics and transportation metrics when the method affects operations.

For control and optimization papers, define objectives, constraints, feasibility, stability or convexity claims, and the decision interval. For empirical human or stakeholder studies, state recruitment, exclusions, missing data, instrumentation, counterbalancing, hypotheses, and the reason for each statistical test. For machine-learning papers, state class balance, leakage controls, external validation, and whether a comparison uses the same data, hardware, and preprocessing.

## Validation: use an evidence ladder

Build a matrix before writing the Results section:

| Question | Minimum evidence | Stronger evidence in the sample |
|---|---|---|
| Does the method beat a credible alternative? | One strong, fairly implemented baseline | Classical + recent + domain/analytical baselines |
| Which design choice matters? | Component ablation | Ablation plus sensitivity to thresholds, horizons, graph structure, or loss weights |
| Does it generalize? | Multiple operating conditions | Multiple sites, dates, datasets, demand levels, directions, or model backbones |
| Is the effect reliable? | Repeated runs or uncertainty | Confidence intervals, distribution-aware tests, effect sizes, and failure cases |
| Can it be used? | Runtime or resource report | Field/official-record check, cost, latency, safety, emissions, or operator benefit |

For simulation, disclose warm-up, duration, demand or service levels, scenario generation, random seeds, and repetitions. For field data, disclose collection period, spatial coverage, labels or ground truth, missingness, and measurement error. Report absolute values and relative changes together; retain subgroup results when a rare class, transfer station, emergency vehicle, or high-risk user is the actual decision target.

## Results and discussion

Organize results by research question or hypothesis rather than by the order in which code ran:

1. Main comparison against baselines.
2. Component contribution and parameter or scenario sensitivity.
3. Robustness, transfer, subgroup, or time-horizon behavior.
4. Error, failure, side-effect, complexity, or cost analysis.
5. A representative case or visualization that explains the mechanism.

After every major claim, answer “under which condition, by how much, compared with what, and why?” Use tables for exact values, figures for trends or mechanisms, and concise text for interpretation. Report non-significant findings and adverse effects when they affect safety or usability. A realistic paper may conclude that one method is globally optimal, another is faster, and a third is safer; explain the decision rule instead of forcing a single winner.

In Discussion, connect the mechanism to prior findings, then translate it into an actionable implication for agencies, operators, designers, insurers, or regulators. Separate what the data establish from what is inferred for deployment. Do not turn a single city, simulation, or benchmark into a universal claim.

## Limitations and conclusion

Write limitations as specific threats with a consequence and a next experiment:

`[boundary or assumption] → [how it may bias validity or deployment] → [concrete data, scenario, or method needed next]`

Common boundaries in the sample include one city or intersection, simulation-only evidence, ideal communication or no delay, incomplete weather/incident variables, convenience or self-reported samples, noisy or private labels, fixed geometry classes, and high model complexity. The conclusion should answer the research questions, restate the most important numbers and application value, and avoid introducing new results.

## Reproducibility and publication checks

Before submission, verify:

- title names the task, method, and setting;
- abstract contains a gap, method components, validation scale, and numeric outcomes;
- abstract word count is within the article-type ceiling (≤ 250 for Research Article, ≤ 200 for Method); keywords 3–5 (or 3–6 for Data Note/Method);
- total body word count is within the article-type ceiling (≤ 7000 for Research Article, ≤ 3000 for Data Note, 2500–4000 for Method); check with the same counter the portal uses;
- each introduction gap maps to a numbered contribution, method element, and result;
- data, labels, preprocessing, split, thresholds, parameters, hardware, and repetitions are recoverable;
- baseline comparisons are fair and include uncertainty or statistical tests where appropriate;
- ablation, sensitivity, robustness, subgroup, or failure analysis supports the main claim;
- operational metrics (safety, delay, emissions, cost, latency, reliability, or workload) accompany generic accuracy metrics;
- figures and tables form an evidence chain: framework, data/scenario, main comparison, mechanism/ablation, and error or boundary analysis;
- data availability, code, funding, conflict of interest, ethics/consent, author contributions, and generative-AI-use disclosures follow the current publisher requirements (all six are required by Taylor & Francis for JITS);
- when a bilingual (e.g., English + Chinese) twin of the manuscript is maintained for internal review, each subsection, numeric value, citation key, and equation body matches 1:1 between the two files; labels in the twin use a consistent prefix (e.g., `zh:` for the Chinese file) so refs resolve locally without collision;
- claims use "in this dataset/scenario" when external validity is not established.

For detailed article-level evidence and reusable patterns, read [references/article-patterns.md](references/article-patterns.md). For a fill-in manuscript skeleton, read [references/manuscript-template.md](references/manuscript-template.md).
