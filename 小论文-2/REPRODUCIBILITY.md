# MIKU 可复现性记录

本文档记录 `小论文-2` 的可执行证据链。随机主实验、粗网格联合参照和规划器滚动重规划是三种不同协议，不得混合解读。

## 环境快照

- 日期：2026-09-03
- 起始基线：`6605686ae61286b75b92a7c4db69ec52dd042052`
- CPU：Intel Core i9-14900HX（32 逻辑处理器）
- Linux：`7.2.2-arch1-1`
- uv / Python：`0.12.9 / 3.14.7`
- NumPy / SciPy / OSQP / Matplotlib：`2.4.4 / 1.17.1 / 1.1.1 / 3.10.9`
- latexmk：`4.88`

墙钟耗时依赖当前硬件、系统负载和固定的方法运行顺序；随机种子能固定轨迹与指标，不能使耗时位完全确定。

## 一次性复现命令

从仓库根目录运行：

```bash
uv run pytest -q
uv run ruff check .
PYTHONPATH=可视化 uv run python 可视化/apollo_pipeline.py
PYTHONPATH=可视化 uv run python 可视化/run_ablation.py
PYTHONPATH=可视化 uv run python 可视化/sensitivity_analysis.py
PYTHONPATH=可视化 uv run python 可视化/run_randomized_experiments.py
PYTHONPATH=可视化 uv run python 可视化/run_randomized_ablation.py
PYTHONPATH=可视化 uv run python 可视化/run_joint_reference_experiments.py
PYTHONPATH=可视化 uv run python 可视化/run_closed_loop_experiments.py
cd 小论文-2
uv run latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

本记录对应的最终验收结果为 `64 passed, 20 skipped`，Ruff 通过，8 个确定性场景全部返回路径与速度解，LaTeX 无未解析引用、交叉引用或 `Overfull` 警告。

## 协议与产物

| 协议 | 样本 | 入口 | 主要产物 |
|---|---:|---|---|
| 最大间隙 oracle | 4,000 | `tests/test_miku_geometry.py` | 测试断言 |
| 确定性机理/消融 | 8 场景 / 24 条 | `apollo_pipeline.py`, `run_ablation.py` | `generated/ablation.csv`, `ablation.json` |
| 六类配对主实验 | 600 个场景×4 方法 | `run_randomized_experiments.py` | `randomized_raw.csv`, `randomized_summary.csv`, `paired_statistics.csv`, `failure_cases.csv`, JSON/图/宏 |
| B3 粗网格联合参照 | 30 个场景×2 方法 | `run_joint_reference_experiments.py` | `joint_reference_raw.csv`, `joint_reference_summary.csv`, `joint_reference_paired.csv`, JSON/宏 |
| 规划器滚动重规划 | 60 个场景×4 方法 | `run_closed_loop_experiments.py` | `closed_loop_raw.csv`, `closed_loop_summary.csv`, `closed_loop_paired.csv`, JSON/宏 |
| 灵敏度 | 80 条权重轨迹 + 24 个单因子端点 | `sensitivity_analysis.py` | `sensitivity_trajectory.csv`, JSON/宏 |

表格数值由 `generated/*.tex` 宏引入正文。耗时位每次运行会重新生成；成功率、碰撞率、轨迹指标和配对 bootstrap 在固定种子下可重算。

## 指标和边界

- 无碰撞到达要求轨迹达到 `s_max - 1 m` 且真值几何评估无碰撞。
- 实体矩形穿透超过 1 mm 计碰撞；最小有符号间距不截断。
- 未无碰撞到达的通行时间记为场景时域加 5 s，同时单独报告降级停车率。
- 95% CI 来自 5,000 次配对 bootstrap；效应量为配对 Cohen `d_z`。
- B3 有粗网格和 beam 截断，不是连续全局最优或安全上界。
- 滚动协议只闭合规划器状态更新，不包含感知器、控制器和车辆执行器，不是实车路测。
- C5 占用补集安全时窗通过单元/oracle 测试，但消融中无独立正收益且 P2 回归，所以主 MIKU 默认关闭。

详细主张对应关系见 `CLAIM_TRACEABILITY.md`。
