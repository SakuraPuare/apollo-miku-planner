# MIKU 可复现性记录

本记录对应“交互感知时空同伦走廊”版本。主实验、随机消融、联合网格参照、滚动重规划和外部 CommonRoad 审计是互补协议，所有论文数值均由 `generated/*.tex` 自动注入。有限域证书的目标函数严格复用 path/speed QP 的完整二次项，不再使用独立的认证 surrogate。

## 环境快照

- 日期：2026-09-06
- CPU：Intel Core i9-14900HX（32 逻辑处理器）
- Linux：7.2.2-arch1-1
- uv 运行时：0.12.9 / 3.14.7
- NumPy / SciPy / OSQP / Matplotlib：2.4.4 / 1.17.1 / 1.1.1 / 3.10.9
- latexmk：4.88

随机种子固定场景、轨迹和统计量；墙钟耗时仍会随系统负载变化。论文中的主实验计时来自单进程顺序执行。随机消融可并行生成，但其并行墙钟值不用于实时性结论。

当前固定版本的自动验证结果为 `134 passed, 20 skipped`；20 个跳过项来自缺失的 `outputs/thesis.docx` 文档工具资源，并不是 Apollo/CyberRT 集成测试。核心几何、时间图、QP、联合候选搜索、连续扫掠安全、滚动承诺、生成物一致性、CommonRoad 审计产物和 Apollo runtime 映射审计测试全部执行并通过。Apollo Planning 源码 commit、Planning/CyberRT/Dreamview runtime 资产和 fixture 索引见项目根目录 manifest；当前宿主机重新构建仍受 Apollo 工具包路径缺失影响，绝对耗时必须引用已登记的原始 runtime 产物。

## 完整复现命令

从仓库根目录运行：

```bash
uv run pytest -q
uv run ruff check .
PYTHONPATH=可视化 uv run python 可视化/apollo_pipeline.py
PYTHONPATH=可视化 uv run python 可视化/run_ablation.py
PYTHONPATH=可视化 uv run python 可视化/sensitivity_analysis.py
PYTHONPATH=可视化 uv run python 可视化/run_randomized_experiments.py --seeds 100
PYTHONPATH=可视化 uv run python 可视化/run_randomized_ablation.py --seeds 100
PYTHONPATH=可视化 uv run python 可视化/run_joint_reference_experiments.py --seeds 10
PYTHONPATH=可视化 uv run python 可视化/run_closed_loop_experiments.py --seeds 100
PYTHONPATH=可视化 uv run python 可视化/run_joint_search_stress.py
PYTHONPATH=可视化 uv run python 可视化/generate_submission_figures.py
PYTHONPATH=可视化 uv run python 可视化/generate_failure_case_figure.py
PYTHONPATH=可视化 uv run python 可视化/run_commonroad_adapter_smoke.py
PYTHONPATH=可视化 uv run python 可视化/run_commonroad_batch.py
uv run python 可视化/generate_commonroad_macros.py
uv run --with commonroad-io==2026.1 python 可视化/validate_commonroad_native.py --output 小论文-2/generated/commonroad_native_audit.json
uv run --no-project --python 3.11 --with commonroad-reactive-planner python 可视化/run_commonroad_reactive.py --steps 100
uv run --no-project --python 3.11 --with commonroad-reactive-planner python 可视化/run_commonroad_miku_native.py --steps 100
uv run python 可视化/generate_commonroad_macros.py
uv run python tools/audit_apollo_runtime_mapping.py --output apollo_runtime_mapping_audit.json
uv run python 小论文-2/check_submission_gates.py
cd 小论文-2
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error main_ieee.tex
```

上述 `--seeds 100` 生成当前论文的每类 100 个样本；`--seeds 500` 可用于额外的扩展稳健性运行，但不对应当前已固定宏和 PDF 数值。

CommonRoad 扩展审计集（不替代主四场景统计）使用两个原生运行器追加 `--extended`，
结果写入 `commonroad_miku_native_extended_results.json` 和
`commonroad_reactive_extended_results.json`；扩展集包含 16 个公开 Lankershim XML。

## 协议和产物

| 协议 | 规模 | 入口 | 主要产物 |
|---|---:|---|---|
| 最大间隙穷举 oracle | 4,000 个区间实例 | `tests/test_miku_geometry.py` | 测试断言 |
| 全局 K-best 空间图 oracle | 100 个随机分层图 | `tests/test_miku_geometry.py` | Top-3 排名与全枚举一致 |
| 时间窗点集 oracle | 1,000 个随机区间族、约 23.9 万查询点 | `tests/test_miku_time.py` | 测试断言 |
| 7 类配对主实验 | 700 场景 × 4 方法（2,800 次） | `run_randomized_experiments.py` | `randomized_raw.csv`, `randomized_summary.csv`, `paired_statistics.csv`, JSON/图/宏；原始行含 `joint_*` 证书列 |
| 7 模块随机消融 | 700 场景 × 8 配置（5,600 次） | `run_randomized_ablation.py` | `randomized_ablation_raw.csv`, summary/paired/JSON/宏 |
| B3 联合网格参照 | 70 场景 × 2 方法 | `run_joint_reference_experiments.py` | `joint_reference_raw.csv`, summary/paired/JSON/宏 |
| 非平凡联合域压力诊断 | 1--5 个空间冲突层 × 3 次 | `run_joint_search_stress.py` | raw/summary/JSON/宏与 `joint_search_scaling.pdf`；走廊距离下界与实际评估/域大小比例 |
| 轨迹边界与首页 teaser | 2 个固定种子案例 | `generate_failure_case_figure.py` | `failure_case_qualitative.pdf` 与 `teaser.pdf`；由同一规划代码自动重放 |
| CommonRoad 受限 adapter smoke | 1 个公开 Lankershim XML | `run_commonroad_adapter_smoke.py` | `commonroad_adapter_smoke.json`；公开 XML 到受限 Frenet planner 调用链，含采样轨迹残差包络，非 benchmark 性能 |
| CommonRoad 四场景批量诊断 | 4 个公开 Lankershim XML × 2 方法 | `run_commonroad_batch.py` | `commonroad_batch_raw.csv`, `commonroad_batch_results.json`；统一受限转换诊断（中心点线性插值可被包络覆盖，原始 occupancy 不保留），论文中仅作负向兼容性审计，不是官方 benchmark 分数 |
| CommonRoad 官方语义审计 | 4 个公开 Lankershim XML | `validate_commonroad_native.py`（可选 `commonroad-io==2026.1`） | `commonroad_native_audit.json`；官方解析器实体/形状/预测状态计数，不是性能 benchmark |
| CommonRoad Reactive Planner 正式覆盖 | 4 个公开 Lankershim XML | `run_commonroad_reactive.py --steps 100`（隔离 3.11 runtime） | `commonroad_reactive_results.json` 与 `commonroad_reactive_solutions/*.xml`；官方 reader、路线参考线、Reactive Planner、标准 solution writer 和 drivability checker；4 行结果全部保留，当前 0 valid |
| CommonRoad MIKU 原生输出边界 | 4 个公开 Lankershim XML × B0/MIKU | `run_commonroad_miku_native.py --steps 100`（隔离 3.12 runtime） | `commonroad_miku_native_results.json` 与 `commonroad_miku_native_solutions/*.xml`；官方 planning problem、RoutePlanner reference path、逐状态矩形形状/姿态占用包络、CommonRoad KS/InputState、solution writer 和 evaluator 均调用；全部源障碍物先审计，路线相关子集进入约束（24--42 个/场景），MIKU 2 valid、1 planner failure、1 invalid solution；交通控制规则仅记录，不作一般 leaderboard 分数 |
| 投稿门槛自动裁判 | 当前 HEAD 的 PDF、生成物和审计文件 | `check_submission_gates.py` | JSON 格式逐项报告通过项、阻塞项和 `accept`/`major_revision` 裁决；缺失外部证据默认不通过 |
| Apollo runtime 映射审计 | `/home/kent/core-11.0/dumps` 与 fixture manifest | `tools/audit_apollo_runtime_mapping.py` | `apollo_runtime_mapping_audit.json`；确认 Planning/CyberRT/Dreamview dump 存在，并在缺少场景/config 标识时明确保持 `pending`，不把历史 runtime 资产升级为 native benchmark |
| 滚动重规划 | 700 场景 × 2 方法 | `run_closed_loop_experiments.py` | `closed_loop_raw.csv`, summary/paired/JSON/宏；MIKU 行汇总每轮 `joint_*` 证书 |
| 权重灵敏度 | 80 条完整轨迹 | `sensitivity_analysis.py` | `sensitivity_trajectory.csv`, JSON/宏 |

## 指标定义

原生 CommonRoad 结果还记录障碍物相关性和失败阶段：所有源动态障碍物均被解析、投影
和计数，但只有扫掠占用与可达路线走廊相交的对象进入规划约束；其余对象保留为
`route_irrelevant_obstacles`，不静默丢弃。投影修复和相关性过滤后，MIKU 仍未取得
valid solution；失败/无效轨迹分别保留官方 evaluator 结果。该诊断只解释失败位置，
不改变安全约束，也不把失败转写成性能分数。

- 无碰撞到达要求轨迹到达评价线且真值实体几何无碰撞。
- 实体矩形穿透超过 1 mm 计碰撞；最小有符号间距保留原值。
- 未成功样本的配对通行时间记为场景时域加 5 s，避免只比较成功子集。
- 比例差和连续指标的 95% CI 由 5,000 次配对 bootstrap 生成；成功/碰撞同时报告精确 McNemar 检验。
- 预测含噪场景中，规划器接收扰动观测，安全评价使用未扰动真值。
- 滚动耗时是单场景全部规划周期的累计值，不是单周期延迟。
- B3 与 MIKU 使用相同威胁裕度和鲁棒预测管；B3 含离散网格与 beam 截断，不称为连续全局最优。

详细主张对应关系见 `CLAIM_TRACEABILITY.md`。MIKU 主实验候选接受流程要求连续扫掠验证通过；证书采用速度 QP 节点间恒加速度纵向运动，在每个被穿越的路径站点处分段，对各段的纵横向二次相对运动解析求交，并仅在有界误差模型下成立。它不能解释为真实车辆全局安全证明。
