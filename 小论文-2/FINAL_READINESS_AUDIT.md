# Final Readiness Audit — T-IV first submission route

更新时间：2026-09-06。该审计区分“已满足”“已满足但有边界”和“正式阻塞”，不把
历史 runtime 资产、受限 CommonRoad adapter 或用户陈述升级成新实验结论。

## Verdict

目标首投：IEEE T-IV Regular Paper；T-ITS 为备选。当前裁决：**Accept for submission
after final mechanical checks**。这不是录用保证，而是 P0/P1/P2 投稿前门禁已闭环。

运行命令：

```bash
uv run python 小论文-2/check_submission_gates.py --venue tiv
```

当前正式阻塞：无（T-IV/T-ITS Regular Paper 路线）。

未满足但不属于 T-IV 当前正式阻塞的诊断项：

- `native_apollo_cyberrt=false`：当前正文不宣称本轮新增 native Apollo runtime 性能；
  已用 `apollo_runtime_mapping_audit.json` 明确标记逐场景映射 pending。
- `ral_page_limit=false`：只在改投 RA-L 时生效；当前 T-IV/T-ITS 英文稿为 9 页，满足
  10 页 Regular Paper 路线。

## Requirement-by-requirement evidence

| Requirement | Status | Evidence |
|---|---|---|
| 目标期刊路线 | 已满足 | T-IV 首投、T-ITS 备选；`HIGH_TIER_READINESS.md`；英文稿 9 页 |
| 有清晰且不夸大的核心主张 | 已满足但有边界 | `NOVELTY_AUDIT.md`、`RELATED_WORK_MATRIX.md`、`CLAIM_TRACEABILITY.md` |
| 认证目标与实现一致 | 已满足 | `apollo_pipeline.pipeline_objective`；`eq:qp-objective`；目标一致性测试 |
| 有限域下界可审计 | 已满足但有边界 | `joint_homotopy_search.py`、stress JSON、path-QP lower-bound tests；不宣称连续全局最优 |
| CommonRoad 外部来源 | 已满足 | 官方 XML、`commonroad_native_audit.json`、CommonRoad 文献条目 |
| 独立竞争方法 | 已满足但结果非全有效 | Reactive Planner 4 场景：2 valid、2 planner failure；失败计入 |
| MIKU 标准 solution/evaluator 边界 | 已满足但仍有失败 | `run_commonroad_miku_native.py`；主四场景 2 valid、1 planner failure、1 evaluator-invalid；官方 solution/evaluator 调用 |
| CommonRoad scoped benchmark | 已满足但有边界 | 官方路线/目标、逐状态矩形形状姿态占用包络、solution/evaluator；交通规则仅记录 |
| Apollo/CyberRT/Dreamview 边界 | 已满足但不扩张性能结论 | `apollo_evidence_manifest.json`、`apollo_runtime_mapping_audit.json`、正文 provenance 段落 |
| Apollo 逐场景 runtime 映射 | 未满足，已审计 | 54 个 dump 无 fixture/config 标识；`mapping_status=pending` |
| 统计实验重生成 | 已满足 | 700 主场景、700 滚动、消融/联合参照/stress 生成物 |
| 中英文稿、引用、页数 | 已满足 | `main.pdf` 10 页、`main_ieee.pdf` 9 页；无 LaTeX citation/overfull 警告 |
| 可复现性 | 已满足 | `REPRODUCIBILITY.md`、一键命令、原始 CSV/JSON/宏、archive manifests |
| 自动化验收 | 已满足 | `134 passed, 20 skipped`；Ruff；`git diff --check` |
| 独立审稿致命问题清零 | 已满足 | `INDEPENDENT_REVIEW.md` 两条独立复核均为无致命问题 |

## Submission decision

当前可以交付的是一份**可编译、可复现、证据边界诚实的 T-IV/T-ITS 投稿稿**。投稿信中
必须把 CommonRoad 结果称为 scoped compatibility benchmark，并保留 MIKU 四次规划失败；
这两点是适用范围说明，不是需要隐藏的缺口。
