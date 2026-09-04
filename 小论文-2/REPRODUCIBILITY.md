# MIKU 可复现性记录

本记录对应“交互感知时空同伦走廊”版本。主实验、随机消融、联合网格参照和滚动重规划是四种互补协议，所有论文数值均由 `generated/*.tex` 自动注入。

## 环境快照

- 日期：2026-09-04
- CPU：Intel Core i9-14900HX（32 逻辑处理器）
- Linux：7.2.2-arch1-1
- uv / Python：0.12.9 / 3.14.7
- NumPy / SciPy / OSQP / Matplotlib：2.4.4 / 1.17.1 / 1.1.1 / 3.10.9
- latexmk：4.88

随机种子固定场景、轨迹和统计量；墙钟耗时仍会随系统负载变化。论文中的主实验计时来自单进程顺序执行。随机消融可并行生成，但其并行墙钟值不用于实时性结论。

当前固定版本的自动验证结果为 `108 passed, 20 skipped`；20 个跳过项来自缺失的 `outputs/thesis.docx` 文档工具资源，并不是 Apollo/CyberRT 集成测试。核心几何、时间图、QP、联合候选搜索、连续扫掠安全、滚动承诺、生成物一致性和 CommonRoad 审计产物测试全部执行并通过。另有 CommonRoad 公共 XML 的可选在线 smoke 验证。仓库当前没有原生 Apollo/CyberRT 运行证据，计时只能解释为 Python/NumPy/OSQP 原型。

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
uv run --with commonroad-io==2026.1 python 可视化/validate_commonroad_native.py --output 小论文-2/generated/commonroad_native_audit.json
cd 小论文-2
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error main_ieee.tex
```

上述 `--seeds 100` 生成当前论文的每类 100 个样本；`--seeds 500` 可用于额外的扩展稳健性运行，但不对应当前已固定宏和 PDF 数值。

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
| CommonRoad 四场景批量诊断 | 4 个公开 Lankershim XML × 2 方法 | `run_commonroad_batch.py` | `commonroad_batch_raw.csv`, `commonroad_batch_results.json`；统一受限转换诊断（轨迹包络不覆盖样本间 occupancy），非官方 benchmark |
| CommonRoad 官方语义审计 | 4 个公开 Lankershim XML | `validate_commonroad_native.py`（可选 `commonroad-io==2026.1`） | `commonroad_native_audit.json`；官方解析器实体/形状/预测状态计数，不是性能 benchmark |
| 滚动重规划 | 700 场景 × 2 方法 | `run_closed_loop_experiments.py` | `closed_loop_raw.csv`, summary/paired/JSON/宏；MIKU 行汇总每轮 `joint_*` 证书 |
| 权重灵敏度 | 80 条完整轨迹 | `sensitivity_analysis.py` | `sensitivity_trajectory.csv`, JSON/宏 |

## 指标定义

- 无碰撞到达要求轨迹到达评价线且真值实体几何无碰撞。
- 实体矩形穿透超过 1 mm 计碰撞；最小有符号间距保留原值。
- 未成功样本的配对通行时间记为场景时域加 5 s，避免只比较成功子集。
- 比例差和连续指标的 95% CI 由 5,000 次配对 bootstrap 生成；成功/碰撞同时报告精确 McNemar 检验。
- 预测含噪场景中，规划器接收扰动观测，安全评价使用未扰动真值。
- 滚动耗时是单场景全部规划周期的累计值，不是单周期延迟。
- B3 与 MIKU 使用相同威胁裕度和鲁棒预测管；B3 含离散网格与 beam 截断，不称为连续全局最优。

详细主张对应关系见 `CLAIM_TRACEABILITY.md`。MIKU 主实验候选接受流程要求连续扫掠验证通过；证书采用速度 QP 节点间恒加速度纵向运动，在每个被穿越的路径站点处分段，对各段的纵横向二次相对运动解析求交，并仅在有界误差模型下成立。它不能解释为真实车辆全局安全证明。
