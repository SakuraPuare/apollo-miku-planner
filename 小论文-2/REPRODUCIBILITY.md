# MIKU 可复现性记录

本文档记录 `小论文-2` 当前已经实际运行的验证链。它不把未完成的随机闭环实验或强基线对比记为已验证结论。

## 基线与环境

- 记录日期：2026-09-03
- 起始 Git 提交：`6605686ae61286b75b92a7c4db69ec52dd042052`
- uv：`0.12.9`
- Python：`3.14.7`
- NumPy / SciPy / OSQP / Matplotlib：`2.4.4 / 1.17.1 / 1.1.1 / 3.10.9`
- latexmk：`4.88`

## 已验证命令

```bash
uv run pytest
uv run ruff check 可视化/miku_geometry.py 可视化/miku_time.py tests
cd 可视化 && uv run apollo_pipeline.py
cd 可视化 && uv run run_ablation.py
cd 可视化 && uv run sensitivity_analysis.py
cd 小论文-2 && uv run latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

当前结果：MIKU 核心测试 41 项通过；全量 `pytest` 另有 20 项既有 DOCX 格式测试因 `outputs/thesis.docx` 不存在而跳过。Apollo 全链路入口完成 8 个确定性场景，路径与速度 QP 均返回可用解。论文生成 13 页 PDF，无未解析引用、交叉引用或 `Overfull` 警告。

## 定理与反例检验

- `可视化/miku_geometry.py` 实现基于前缀最大值的 `O(k log k)` 最大中心间隙求解器。
- `tests/test_miku_geometry.py` 使用 20 个固定种子生成 4,000 个随机小规模实例，逐例对照全部 `2^k` 方向分配的穷举最优宽度。
- 回归反例包含 $v_i$ 非单调的嵌套禁行区间；它能暴露只使用相邻 $v_p$ 而未使用 $V_p=\max(v_1,\ldots,v_p)$ 时的间隙高估。

## 数据与生成链

- 8 个确定性场景的输入、SL/ST 曲线和元数据：`图片/data/<scene>/`。
- 消融原始数据：`图片/data/ablation/ablation.csv` 与 `ablation.json`。
- 实验主入口：`可视化/apollo_pipeline.py`。
- 消融与灵敏度入口：`可视化/run_ablation.py` 与 `可视化/sensitivity_analysis.py`。

## 当前证据边界

- 现有 8 个场景是确定性机理实验，不支持对自然交通分布的统计普适性外推。
- C5 速度侧走廊注入在当前 4 个压力场景中未成为活跃约束；关闭 C5 后已报告指标与完整方法相同，故它不是当前证据支持的独立性能贡献。
- `可视化/miku_time.py` 已实现从障碍物占据直接生成先通过/后通过安全窗、窗交集与空集停车降级；它已通过单元和随机 oracle 检查，但尚未被接入随机闭环性能实验。
- 公平强基线、每类 100 个固定种子的随机闭环实验、安全指标与置信区间仍属待完成项，在完成前不应使用“显著提升”。

## 当前产物校验

```text
4871863f37680d2f18d3b4716d4eab812a0b44ffeab17876781fe6108c97e4bf  小论文-2/main.pdf
56d5e1c2e6469db8b43603f643d6384588b017cce9e1754bd11697ae917966ae  小论文-2/main.tex
7ebdd71190afe8ce1f2a08f04de97ead144ba0b673b9c7d959ed9da51300452b  可视化/apollo_pipeline.py
d9101283080b04e8bb543d739a29ee00f7df36d41cfdb3e943c7f66dfadd8038  可视化/miku_geometry.py
a271abf1a81d14d35b8b17dab9af05b52d29cab4a46bad30282d04359e33844b  可视化/miku_time.py
```

上述校验值是本记录生成时的快照；修改源码或重新编译后应同步刷新，不应将旧校验值视为新产物的证明。
