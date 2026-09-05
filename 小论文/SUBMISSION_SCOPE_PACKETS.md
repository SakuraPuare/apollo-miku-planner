# Journal-specific submission packets (internal)

The packets below are deliberately scoped to the evidence that is actually
available. They are working material for a cover letter and should be checked
against the journal's current author instructions immediately before submission.

## A. IET Intelligent Transport Systems

**Working title**

> MIKU: Interaction-Aware Space–Time Constraint Compilation for Path–Velocity Autonomous Driving Planning

**Abstract emphasis**

Frame MIKU as an implementable ITS planning component: it converts predicted
multi-obstacle interactions into time-varying path boundaries and ST timing
windows while reusing the existing path/speed QP structure. Emphasize paired
scenario evaluation, safety/throughput/comfort metrics, computational cost, and
Apollo Planning interface compatibility. State explicitly that the platform
evidence is simulation/interface validation, not physical-road testing.

**Contribution bullets**

1. A threat-aware, arrival-time-indexed constraint interface for multi-obstacle
   path–velocity planning.
2. A finite-domain spatial/time homotopy compilation procedure with an exact
   fixed-section gap solver and bounded candidate search.
3. Reproducible paired evaluation with collision, progress, jerk, runtime, and
   failure-case diagnostics, plus an auditable public-planner context.

**Cover-letter paragraph**

> The manuscript presents an engineering method for intelligent transportation
> systems rather than a new vehicle sensor or a physical-road deployment study.
> Its central contribution is an auditable interface that transfers dynamic
> interaction information from path construction to the downstream speed QP.
> The evaluation reports safety, progress, comfort, latency, ablations, and
> representative Apollo Planning interface behavior, with all aggregate claims
> tied to frozen artifacts. We do not claim a real-vehicle experiment or a
> continuous global optimum.

## B. Journal of Intelligent Transportation Systems

**Working title**

> Interaction-Aware Space–Time Constraint Unification for Dynamic Multi-Obstacle Vehicle Planning

**Abstract emphasis**

Lead with transportation-system relevance: dynamic obstacle interaction causes
overly conservative corridors and local passing conflicts in decoupled planners.
Report the 3,500 paired protocol as a frozen numerical experiment, then describe
Apollo as a Planning-compatible engineering platform. Add a sentence linking the
metrics to safety, mobility and comfort rather than only solver quality.

**Contribution bullets**

1. A transportation-oriented formulation of dynamic occupancy projection and
   group-level passing alternatives.
2. A constraint compiler that preserves the downstream QP objective and
   kinematic structure.
3. Statistical and mechanism-level evidence across seven traffic configurations,
   with explicit limitations on external-benchmark fairness and runtime replay.

**Cover-letter paragraph**

> This work addresses an intelligent-transportation planning bottleneck: a
> path–velocity decomposition can lose arrival-time information before the
> speed stage is solved. MIKU restores that information through a bounded
> space–time constraint interface and evaluates the resulting safety, mobility,
> comfort, and computational trade-offs. The manuscript is positioned as a
> reproducible planning-method study with Apollo Planning interface evidence;
> it does not present a physical-road test or an unsupported claim of universal
> optimality.

## C. Conservative four-zone vehicle/robotics route

**Working title**

> A Practical Multi-Obstacle Constraint Interface for Path–Velocity Motion Planning

**Abstract emphasis**

Reduce transportation-system rhetoric and foreground implementation, finite-domain
correctness conditions, QP reuse, and failure diagnostics. Keep the Apollo name in
the platform paragraph, not as the novelty claim. Retain the same limitations
sentence about simulation/interface evidence.

**Cover-letter paragraph**

> The manuscript contributes a practical motion-planning interface that compiles
> dynamic multi-obstacle constraints into an existing path–velocity optimization
> stack. The method is evaluated with deterministic mechanism cases, paired
> randomized experiments, ablations, runtime statistics, and a reproducible
> platform integration record. We have intentionally bounded the claims to the
> finite candidate model and the reported simulation/interface evidence.

## Common packet checklist

- Use the Q3 Chinese manuscript only after the 3,500-case archive is copied into
  the submission supplement.
- Do not describe the four CommonRoad MIKU adapter rows as a leaderboard score.
- Do not cite the failed Apollo runtime as a successful trajectory result.
- Keep internal verification implementation out of the manuscript and cover
  letter.
- Recheck current quartile, article type, page limit, APC, and required data
  availability statement on the journal website at submission time.

