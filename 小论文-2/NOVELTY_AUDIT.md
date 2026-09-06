# MIKU 新颖性审计（第一轮，2026-09-05）

## 审计结论

当前稿件不能把“Top-K 空间 + beam 时间 + 双 QP + 鲁棒管”分别包装成五个原创贡献。逐项核验后，现有实现更准确的定位是：一个基于路径—速度解耦原型的候选组织实验。空间最大间隙、时间 before/after 语义、滚动语义保持和安全走廊均已有直接先行工作或明显的自然组合。唯一可保留的中心升级是：在保留路径/速度 QP 的条件下，对显式有限空间—时间同伦域做可终止的联合搜索，并返回可检查的最优性 gap；该升级现已接入 `experiment_methods.run_method`，主实验的 MIKU 候选使用全部正宽空间带与全部有限安全窗。

## 逐项主张核验

| 论文主张 | 最近先行工作（已核验） | 相同点 | 当前新增困难/差异 | 当前证据与判断 |
|---|---|---|---|---|
| 路径—速度解耦保留实时 QP | Kant & Zucker (1986), Apollo EM (Fan et al., 2018), Zhou et al. (2021) | 均顺序求解空间路径与速度 | MIKU 只改变离散约束组织；不是新求解器 | 工程整合，不单独构成原创算法 |
| before/after/left/right 组合与语义保持 | Esterle et al., ITSC 2018, DOI 10.1109/ITSC.2018.8570003；其原始 PDF 明确描述 before/after/right/left、横纵解耦和 semantic language | 直接覆盖动态障碍的时序/方向组合和跨周期一致性 | MIKU 计划使用鲁棒占据与双向 ST 盒约束 | 现稿“首次统一时序同伦”不可成立；必须改为差异化问题定义 |
| 多障碍物 $2^k\to k+1$ 连续分割 | Bender et al. (2015) 的 maneuver variants；Esterle et al. (2018) 的组合推理；传统排序/间隙扫描 | 都利用有限通行带代替任意二元组合 | MIKU 的固定截面区间扫描可作为受限模型下的精确性质 | 仅对固定截面、固定区间成立；不是动态路径全局定理 |
| Top-K 空间同伦 | McNaughton et al. (2011) 时空格点；Kessler et al. (2023) Apollo 混合整数；常规 K-best DP | 均保留多个候选并排序 | MIKU 在分层带图上保留每终端 K 条前缀 | 只能称“给定截断分层图内精确”；当前 Top-3 局部预剪枝破坏全域保证 |
| 多冲突因果时间图 | Esterle et al. (2018) 组合决策；Liu et al. (2017) temporal optimization；Yoon et al. (2024) ST corridor | 都将动态冲突映射为时间/走廊约束 | MIKU 用安全窗补集和 FIFO 站点边；认证模式枚举全部安全窗 | 证书只覆盖显式有限窗域；直接 API 默认 beam=8 仍是启发式 |
| 双向 ST 走廊 | Deolasee et al. (2022) trapezoidal prism corridor；Yoon et al. (2024) ST corridor；Zhang et al. (2023) interactive ST corridor | 均在时空域表达通过/让行 | MIKU 把标签编译回速度 QP | 代码以安全窗端点编译是正确的；旧论文错误地使用了相反的占用端点，现已修正 |
| 鲁棒预测占据管 | Han et al. (2024) safe corridor；Yang et al. (2023) prediction-based pedestrian planning；CIAO* (Schoels et al., 2021) | 都用预测占据/安全集合处理不确定性 | MIKU 使用随时间增长的轴对齐半径 | 路径投影未使用 uncertainty，候选也未做鲁棒验证；主张不成立 |
| 滚动同伦锁定 | Esterle et al. (2018) semantic consistency；常见 MPC hysteresis/commitment | 都抑制周期决策抖动 | MIKU 对 pass-before 轨迹暂时执行旧轨迹 | 属工程滞回；无递归可行性或终端集证明 |
| Apollo 集成 | Fan et al. (2018), Apollo 官方仓库 | 采用 Apollo Planning path QP / speed QP 接口 | MIKU 改动已落入 Apollo Planning 源码提交，并有 CyberRT/Dreamview 运行资产 | 源码 commit、补丁、fixture 和 runtime dump 已登记；宿主机重建仍需恢复 Apollo 工具包路径 |

## 三条路线比较与裁判选择

| 路线 | 学术价值 | 实现/验证 | 选择 |
|---|---:|---:|---|
| A：有限联合同伦惰性 best-first + 最优性证书 | 5/5 | 4/5 | **选定核心升级** |
| B：Pareto 完备时间标签 | 4/5 | 3/5 | 作为 A 的时间层补强 |
| C：连续时间扫掠安全/终端安全集 | 5/5 | 5/5 | 必须补齐正确性；不单独冒充中心创新 |

路线 A 的可接受主张必须限定为“给定有限候选域”。当所有正宽空间分割、所有安全时间窗均进入候选域，且每个叶有可采纳下界时，best-first 搜索可在队列耗尽时证明有限域最优；预算中止时只报告 `U-L` gap。它不等价于连续全局最优，也不能替代公开外部基准。

## 必须保留的反例

1. 高排名空间/时间候选 OSQP 可解但真值碰撞，低排名候选安全：证明“OSQP solved 即可行”错误。
2. 两个采样点分离、采样间中心穿越矩形：证明离散碰撞检查不蕴含连续安全。
3. 首安全窗与末安全窗的端点约束：用于防止论文再次把安全窗端点写成相反的占用端点。
4. 第 4 个空间带或第 9 个时间分支才可行：证明固定 Top-3/beam-8 会丢失有限域可行解；认证模式通过 `None` 配置避免该截断。

## 参考来源（原始页面）

- [Esterle et al., ITSC 2018 原始 PDF](https://mediatum.ub.tum.de/doc/1454706/w5auv2cma08cty4chbv6h17s3.Spatiotemporal_Motion_Planning_with_Combinatorial_Reasoning_for_Autonomous_Driving.pdf)
- [Han et al., IEEE T-ITS 2024](https://ieeexplore.ieee.org/document/10285583)
- [Tariq et al., Frenet Corridor Planner, arXiv 2505.03695](https://arxiv.org/abs/2505.03695)
- [Deolasee et al., trapezoidal prism corridors, arXiv 2209.15150](https://arxiv.org/abs/2209.15150)
- [CommonRoad 公共场景与 benchmark 说明](https://commonroad.in.tum.de/scenarios/)

**当前裁决：Major Revision。** 路线 A 已接入主流水线，时序语义和连续证书也已修正并测试，公开 CommonRoad XML 已完成官方 Reactive Planner 四场景协议覆盖，并登记 Apollo Planning 源码与 CyberRT/Dreamview runtime 资产；当前结果仍不足以单独声称达到二区竞争水平，主要剩余问题是审稿风险、非平凡联合域展示和投稿格式。
