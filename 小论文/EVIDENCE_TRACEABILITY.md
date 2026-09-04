# 三区/四区稿证据追溯说明

本文件固定 `小论文/main.tex` 的实验口径，防止与 `小论文-2` 后续回归测试产物混用。

## 1. 3,500 个配对随机场景

- 冻结协议：`miku-random-v2`
- 冻结提交：`29a337a`（`data(evaluation): refresh paired homotopy evidence`）
- 场景：7 类，每类 500 个固定随机种子，共 3,500 个配对场景
- 方法：B0、B1、B2、MIKU，共 14,000 条原始方法记录
- 原始记录：`小论文-2/generated/randomized_raw.csv`
- 汇总结果：`小论文-2/generated/randomized_summary.csv`
- 配对统计：`小论文-2/generated/paired_statistics.csv`
- 协议元数据：`小论文-2/generated/randomized_results.json`

可从冻结提交直接核验：

```bash
git show 29a337a:小论文-2/generated/randomized_results.json
git show 29a337a:小论文-2/generated/randomized_summary.csv
git show 29a337a:小论文-2/generated/paired_statistics.csv
```

正文总体结果对应冻结汇总中的 `all` 行：B0/B1/B2/MIKU 成功率分别为 62.7%/52.4%/62.1%/77.5%，碰撞率为 2.2%/2.1%/2.2%/1.1%，平均进度率为 77.5%/71.1%/76.6%/86.4%，jerk RMS 为 1.252/1.315/1.300/1.132 m/s³。运行时间使用同一冻结快照并四舍五入至两位小数。

当前工作树中 `224b3c4` 生成的 700 场景包是二区稿代码回归审计用的缩减样本，不参与本稿表格、插图或统计结论。

## 2. 减法消融

- 冻结提交：`29a337a`
- 原始记录：`小论文-2/generated/randomized_ablation_raw.csv`
- 汇总结果：`小论文-2/generated/randomized_ablation_summary.csv`
- 配对统计：`小论文-2/generated/randomized_ablation_paired.csv`
- 元数据：`小论文-2/generated/randomized_ablation_results.json`

正文 A1--A7 与 MIKU 的成功率、碰撞率和进度率均对应上述 3,500 场景冻结快照。

## 3. 联合时空参考

- 冻结提交：`29a337a`
- 协议：`miku-joint-reference-v2`
- 场景：7 类，每类 10 个种子，共 70 个场景
- 汇总：`小论文-2/generated/joint_reference_summary.csv`
- 元数据：`小论文-2/generated/joint_reference_results.json`

B3 是固定网格分辨率和有限 beam width 下的联合搜索参考，不声明连续全局最优。正文只用于比较通行能力与计算开销数量级。

## 4. Apollo 工程在环证据

- C++ 接口实现：`毕业论文/code/lane_follow_path.cc`、`毕业论文/code/path_bounds_decider_util.cc`、`毕业论文/code/piecewise_jerk_speed_optimizer.cc`
- 工程说明：`毕业论文/chapters/chapter8.tex` 第“Dreamview在环实验展示”节
- 原始关键帧：`图片/dreamview/scn01_*.png`、`scn02_*.png`、`scn03_*.png`
- 验证口径：百度 Apollo 官方场景/道路接口/障碍物消息与车辆模型，Dreamview `sim_control` 在环运行 MIKU Planning C++ 实现

该证据用于确认核心边界生成、接口传递和典型场景行为；完整 Top-K 空间同伦、时间同伦及鲁棒预测链的定量结果由冻结数值协议提供。批量统计与 Apollo 在环验证属于同一算法定义下、证据边界清晰的两类互补证据。

## 5. 论文创新主张的证据边界

- 连续分割与最大间隙结论：固定截面区间模型内的精确最优，不外推为一般非凸轨迹规划的全局最优。
- Top-K 空间同伦：在保留候选集合内求解连续同伦，不声明无界候选空间的完备性。
- 时间同伦：把所选安全窗编译为速度 QP 的线性盒约束，不改变原 QP 的凸性和稀疏结构。
- Apollo 在环：证明工程接口兼容性和典型场景行为；大样本收益由冻结数值协议提供。

## 6. 投稿前一致性检查

1. `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`
2. 检查正文所有样本数、百分比、置信区间和运行时间是否对应 `29a337a`
3. 确认未将 700 场景回归包更新进本稿
4. 确认 Dreamview 图像和 C++ 接口文件随补充材料提交
5. 确认 B3 始终表述为有限离散联合参考，而非连续全局最优
