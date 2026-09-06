# Related-work matrix（核验版）

本矩阵只记录已打开原始论文、出版社页面或作者机构存档后确认的内容；“差异”是基于全文/摘要的可核验比较，不根据标题猜测。

| 工作 | 规划表征 | 空间/时间组合 | 解耦 QP | 不确定性/安全 | MIKU 的真实差异 | 证据 |
|---|---|---|---|---|---|---|
| Kant & Zucker, IJRR 1986 | path-velocity decomposition | 无显式多智能体标签 | 是 | 未建模 | 在经典解耦接口上增加有限同伦候选与证书搜索 | DOI 10.1177/027836498600500304 |
| McNaughton et al., ICRA 2011 | conformal spatiotemporal lattice | 联合时空格点 | 否 | 动态占据 | MIKU 保留两阶段 QP，但不能声称首次处理时空组合 | DOI 10.1109/ICRA.2011.5980223 |
| Esterle et al., ITSC 2018 | path/speed + maneuver reasoning | before/after/right/left，semantic language，跨周期一致性 | 部分 | 场景预测 | 直接覆盖 MIKU 的时序语义；MIKU 需以有限域证书和鲁棒管作可检验差异 | [原始 PDF](https://mediatum.ub.tum.de/doc/1454706/w5auv2cma08cty4chbv6h17s3.Spatiotemporal_Motion_Planning_with_Combinatorial_Reasoning_for_Autonomous_Driving.pdf) |
| Fan et al., Apollo EM 2018 | Apollo path/speed stack | ST decision | 是 | 固定缓冲 | 仅可作为平台基础；不可把 Apollo 模块本身写成原创 | arXiv:1807.08048 |
| Cheng et al., ICRA 2022 | GP + incremental refinement | 候选/迭代协调 | 部分 | GP 预测 | MIKU 的证书化候选域与 QP 回退仍需实证差异 | DOI 10.1109/ICRA46639.2022.9812405 |
| Han et al., T-ITS 2024 | spatial-temporal joint optimization | 联合走廊/动态障碍 | 否 | safe corridor、signed distance | MIKU 以较低连续优化维度换取候选近似；必须报告质量—开销差 | [IEEE 页面](https://ieeexplore.ieee.org/document/10285583) |
| Yoon et al., T-ITS 2024 | spatio-temporal corridor lane change | 显式时空走廊 | 否/混合 | corridor | MIKU 的差异只能是固定 QP 接口与有限同伦证书，不是“首次 ST corridor” | DOI 10.1109/TITS.2024.3388380 |
| Deolasee et al., 2022 | trapezoidal prism + Bézier | 联合时空走廊 | 否 | 连续时间安全保证 | MIKU 提供较窄的恒加速/分段线性/轴对齐矩形条件证书，不宣称覆盖其连续走廊模型 | [arXiv](https://arxiv.org/abs/2209.15150) |
| Kessler et al., T-IV 2023 | mixed-integer Apollo stack | 离散行为与路径 | 是/混合 | 约束相关 | MIKU 需与其比较候选覆盖与计算代价，不能只对自建 B3 | DOI 10.1109/TIV.2022.3162671 |
| Tariq et al., IV 2025 / T-IV 2026 | Frenet corridor / sparse graph | obstacle-specific nodes | path then speed | risk-aware clearance | 近期直接竞争者，已有 CARLA/硬件证据；当前稿缺外部复现 | [FCP arXiv](https://arxiv.org/abs/2505.03695), [FEP IEEE](https://ieeexplore.ieee.org/document/11214467) |
| CommonRoad benchmark (Althoff et al., IVS 2017) | 标准 XML 道路/动态障碍/目标 | 可组合 benchmark | 取决于 planner | 真实/手工场景 | 当前仓库已导入四个公开 XML；官方 Reactive Planner runner 完成四场景协议覆盖，2 个 valid solution、2 个 planner failure | [场景下载页](https://commonroad.in.tum.de/scenarios/), [commonroad-io](https://github.com/CommonRoad/commonroad-io) |

## 对 MIKU 主张的覆盖判定

| 主张 | 最近工作是否直接覆盖 | 可保留的窄化表述 |
|---|---|---|
| “统一 before/after/left/right 语义” | 是（Esterle 2018） | “在鲁棒占据和固定 QP 接口下的有限候选编译” |
| “Top-K 全局空间同伦” | 部分；当前实现只对截断图精确 | “诊断模式给定候选图的 K-best；认证模式对显式有限域做证书化搜索” |
| “鲁棒占据安全保证” | 形式类似已有集合安全方法，但条件更窄 | “在显式误差包络、恒加速执行、分段线性路径和连续扫掠检查满足时的条件命题” |
| “Apollo 实时部署” | 已登记 Apollo Planning 源码 commit、Planning/CyberRT/Dreamview 运行资产；批量源码构建仍受工具包路径缺失影响 | “Apollo Planning 源码级实现与在环运行证据”；新的绝对耗时必须引用 runtime 原始产物 |
| “二区竞争力” | 不能由自生成场景推出 | 等外部 benchmark、外部方法和复审完成后再判 |
