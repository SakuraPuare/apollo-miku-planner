# JITS sample evidence and reusable patterns

The supplied directory contains 39 MinerU Markdown conversions. The citation line in each article identifies *Journal of Intelligent Transportation Systems*, volume 30, issues 3–5 (2026). The numbers below are evidence from those papers, not acceptance-rate statistics.

## Repeated patterns across the 39 papers

- Titles combine a task or consequence with a method and a setting, constraint, stakeholder, or data source.
- Abstracts follow problem/gap → named method and modules → data or scenario → quantitative result → application value and boundary.
- Introductions classify prior work, identify a concrete missing capability, number two to four contributions, and give a roadmap.
- Methods lead with a framework figure or problem definition, then expose assumptions, variables, formulas, algorithms, thresholds, and experimental settings.
- Results combine strong baselines with ablation, sensitivity or robustness, and a case or deployment interpretation.
- Discussion explains mechanisms and trade-offs and reports negative or non-significant findings that matter to safety or usability.
- Limitations are specific (single site, simulation, missing exogenous variables, ideal communication, sampling bias, privacy, or complexity) and paired with a feasible next study.
- Publication-facing material commonly includes data availability, code or software information, funding, disclosures, ethics/consent where relevant, and AI-use statements.

## Evidence examples by article type

### Control and optimization

- Cooperative lane-changing control: macro CCGDP and micro MLBSA are mapped to two gaps; a 1,200 m, 4,800 s simulation varies flow, CAV penetration, and exit demand. It reports lane-change success, speed variability, total risk, and fuel, with component and sensitivity results.
- Dynamic arterial offset: five physical factors are derived before the adaptive model; four real intersections are evaluated in both directions against current timing and an advanced ABC method. Delay and stop-rate trade-offs are retained.
- Eco-PCC and unified MPC: theory is connected to calibrated vehicle data, multiple scenarios, sensor-error tests, runtime, and safety/comfort costs. The papers distinguish closed-loop from open-loop evidence and simulation limits.
- Tram coordination, bus operation, school-bus recourse, hard-shoulder MARL, stochastic platoons, and perimeter control all make operational constraints explicit and compare solution quality with computation time or service consequences.

### Prediction, perception, and re-identification

- Metro IPF-HMGNN: hierarchical flow conservation is defined as a measurable constraint; Wuxi AFC data, multiple GNN backbones, graph structures, horizons, ablations, and transfer tests are reported. MAE/RMSE reductions reach 49.562%/53.878% for a transfer-station task and 35.324%/36.177% for a hierarchical task.
- Citywide bus G-MGCN: distance, similarity, and route-pattern graphs plus periodic modeling are isolated by ablation across 30/45/60 minute horizons. The study reports 512 stops, about 950,000 card records, and RMSE reductions of 21.98%, 27.31%, and 29.25%.
- GIS + YOLO intersection geometry: a policy deadline and agency record gap motivate an end-to-end pipeline. It reports 99,349 candidate intersections, 79,824 post-processed outputs, mAP .956, and a 1,200-record manual check, including categorized misses and mismatches.
- Vehicle re-identification papers pair a mechanism-level failure (noise propagation or detector linkage) with a module-level remedy, public benchmarks, ablations, and precision/recall/F1 or mAP/RANK metrics. One reports NODE F1=.9328 (precision 94.5%, recall 92.1%); another reports VeRi mAP=.795 and RANK-1=.961 with code information.
- Vehicle classification and object detection report accuracy together with repeated-run variation, latency, false-positive rate, FLOPs, memory, or model size. The SCOPE paper reports 94% accuracy, 15 ms latency, and 3.2% false-positive rate, while also flagging task-definition and fairness checks needed in a new submission.

Additional evidence from the same sample reinforces the pattern:

- Timetable resilience integrates train paths, turnback, and depot resources, then checks the method against actual operations, a genetic algorithm, and other cities. It reports cost and solve-time changes together, so “resilience” is tied to a measurable service decision.
- Dynamic traffic-speed forecasting separates directed spatial structure, adaptive embeddings, long-range attention, and scheduled sampling. METR-LA and PEMS-BAY tests, 15/30/60-minute horizons, ablations, cross-dataset transfer, and runtime make each claimed mechanism auditable.
- Heavy-vehicle weight identification and radar–visual accident perception use an end-to-end engineering chain. Triggering, lightweight detection, data augmentation, sensor fusion, calibration, and error categories are each tested before the final field-facing result.
- TransitTalk, robotaxi enforcement surveys, Wi-Fi occupancy, and perceived-risk studies show that JITS also accepts human, policy, and service work when the research questions are explicit, participant or field sampling is transparent, statistical models are interpretable, and recommendations follow from measured concerns rather than generic claims.

### Human factors, policy, and service research

- Trajectory guidance uses predeclared H1–H4 hypotheses, 35 participants and 140 trials, randomized emergency events, vehicle/eye-tracking/workload/emissions measures, and non-parametric tests. It reports both benefits (waiting time −28.99%, emissions/fuel −5.31%) and non-significant or adverse effects.
- Driver stress combines street-view segmentation, explainable ML, and a physiological measure; it reports model fit plus SHAP main and interaction effects and turns them into roadway/ADAS recommendations while limiting claims because of sample and measurement boundaries.
- Robotaxi research surveys 3,498 usable traffic-police responses, uses Fisher tests and ordered logit with marginal effects, and turns concerns into training, cybersecurity, and regulatory actions. Convenience sampling and self-report bias remain explicit.
- Wi-Fi occupancy and scooter UBI papers treat privacy and noisy labels as part of the contribution. They report where clustering or anonymization loses information and why a task-specific operating rule remains useful.

## How to use this evidence

Select only the comparisons relevant to the target manuscript. Use the numerical examples as a reminder to report scale and effect size, never as target values. If a claim cannot be supported by a matched baseline, an uncertainty statement, or a clearly bounded scenario, weaken the claim or add the missing experiment.
