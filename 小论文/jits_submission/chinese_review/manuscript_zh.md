<h1 align="center">动态多障碍交通中的交互感知时空同伦约束路径—速度规划</h1>

> 中文校对稿，仅用于作者核对技术含义、术语、数字、图注和声明，不作为期刊投稿文件。

**作者：** JiaWang Liao，YuFei Hu，ChaoYang Shi，ChengJiao Sun（通讯作者）<br>
**单位：** 湖北文理学院计算机工程学院，湖北省襄阳市隆中路296号，邮政编码 441053<br>
**通讯邮箱：** jiao1952@126.com

# 摘要

路径—速度分解有利于高效规划，但可能丢失交互时序信息。无时间意识的路径边界会把不同时间发生的占用合并，逐障碍物的侧向选择还可能产生相互冲突的阻塞。本文提出多障碍交互感知运动学约束统一方法 MIKU。该方法保留下游路径二次规划和速度二次规划，通过依赖到达时间的投影避免合并时间上不相交的占用，通过威胁感知裕度和连续划分生成群组级横向带，并利用时空同伦图将安全通行时间窗编译为站位—时间盒约束。在固定截面区间模型下，最大间隙扫描将 $k$ 个障碍物的侧向分配搜索从 $O(2^k)$ 降为 $O(k\log k)$，并在 4,000 个确定性区间实例上与穷举结果一致。在覆盖七类交通构型的 3,500 个配对仿真场景中，MIKU 将无碰撞到达目标率从 62.7% 提高到 77.5%，差值为 14.8 个百分点，95% 置信区间为 13.5--16.0，并将碰撞率从 2.2% 降至 1.1%，平均进度提高 8.9 个百分点。规划时间的中位数和第 95 百分位分别为 9.98 ms 和 55.93 ms，但第 99 百分位为 221.8 ms，高于基线的 138.9 ms。独立的 700 场景滚动重规划实验和 Apollo 11.0 接口案例支持重规划行为与软件接入判断，但不构成道路测试。结果表明，在不替换既有凸优化器的前提下，在约束接口处保留交互时序能够减少不必要的停车，但仍需接受尾部延迟和仿真到道路验证的限制。

**关键词：** 自动驾驶；路径—速度分解；时空同伦；动态障碍物；运动规划

# 引言 {#zh:sec:introduction}

自动驾驶车辆需要在动态交通中持续前进，同时满足碰撞规避和乘坐舒适性要求。因此，过度保守的运动规划并非没有代价。反复触发的兜底停车会降低服务可靠性、阻碍周围交通，并削弱智能交通系统应有的机动性收益。运动规划综述因此通常将可行性、安全性、舒适性和计算代价视为相互耦合的运营结果，而不是可以相互替代的单一指标
(González et al. 2016; Paden et al. 2016; Schwarting et al. 2018)。

路径—速度分解（path--velocity
decomposition，PVD）适合在线运行，因为它在站位—横向（station--lateral，SL）坐标中生成横向路径，在站位—时间（station--time，ST）坐标中优化纵向速度
(Kant and Zucker 1986; Werling et al. 2010; Zhou et al.
2021)。工业实现由此可以求解两个结构化二次规划（quadratic
program，QP），并通过路径边界和 ST 边界向求解器传递环境信息 (Fan et al.
2018; Zhang et al. 2020; Wang et al.
2022)。然而，这种分解也可能丢失密集动态场景所需要的关键信息。由当前时刻快照或整个预测时域的并集构成的路径边界，无法区分某一区域是当前被占用，还是在自车到达时已经空闲。此外，逐障碍物做出的不可逆侧向选择，可能以互不兼容的方式抬高路径下界并压低路径上界，即使联合选择后仍存在可通行的通道。

联合时空搜索、混合整数优化和走廊方法可以协调这些决策，但通常需要替换原有求解器、扩大状态空间，或反复调用路径和速度阶段
(McNaughton et al. 2011; Kessler et al. 2023; Yoon et al.
2024)。本文考察的是另一种可能性，即能否在已有 PVD
栈的约束接口处恢复丢失的交互信息。本文提出的多障碍交互感知运动学约束统一方法（Multi-obstacle
Interaction-aware Kinematic constraint
Unification，MIKU）构造随时间变化的横向带，选择空间和时间同伦类别，并将其编译为两个
QP 已经支持的盒约束。

本文围绕以下四个研究问题展开：

1.  与匹配的 PVD
    基线相比，交互感知约束构造在多大程度上能够改善无碰撞到达目标和交通进度。

2.  哪些空间、时间和不确定性处理组件造成了观测到的效果。

3.  在哪些运行条件下，鲁棒性、舒适性或计算代价会限制方法收益。

4.  在不改变下游 QP 结构的情况下，同一约束接口能否接入已有的 PVD
    软件栈。

![MIKU
针对的失效模式。即使群组级连续通道仍然存在，独立的侧向选择也可能使路径下界和上界相互穿越。图内变量和模块名称保留英文，以便与实现对应。](figures/fig_teaser_en.pdf){#zh:fig:teaser
width="\\textwidth"}

本文的主要贡献如下。

1.  在中心坐标边界中形式化了依赖到达时间的 SL
    投影和群组级障碍物侧向分配。连续划分引理将 $k$ 个活动障碍物的 $2^k$
    种分配缩减为 $k+1$ 个候选点，并在固定截面区间模型下通过 $O(k\log k)$
    最大间隙扫描确定最宽横向带。

2.  通过不确定性扩展占用管、可安全通行时间窗和分层时间同伦图，将空间决策连接到速度规划。选定的时序条件仍然表现为线性
    ST 盒约束，因此保留下游路径 QP 和速度 QP
    的目标函数、运动学等式、凸性及稀疏结构。

3.  通过匹配的证据链检验每项主张，包括 4,000
    个确定性区间检查、带置信区间和组件消融的 3,500 个配对场景、独立的
    700 场景滚动重规划实验、有限网格联合参考以及三个 Apollo 11.0
    接口案例。分析在报告收益的同时，也报告不利的尾部延迟和依赖条件的权衡。

第 [2](#zh:sec:related_work){reference-type="ref"
reference="zh:sec:related_work"}
节将约束接口方法置于联合规划器和分解式规划器之间进行定位。第 [3](#zh:sec:problem){reference-type="ref"
reference="zh:sec:problem"} 节定义 PVD
接口及其两种失效机制。第 [4](#zh:sec:method){reference-type="ref"
reference="zh:sec:method"} 节介绍
MIKU，第 [5](#zh:sec:experimental_design){reference-type="ref"
reference="zh:sec:experimental_design"}
节和第 [6](#zh:sec:results){reference-type="ref"
reference="zh:sec:results"}
节说明评估设计与结果，第 [7](#zh:sec:discussion){reference-type="ref"
reference="zh:sec:discussion"}--[9](#zh:sec:conclusion){reference-type="ref"
reference="zh:sec:conclusion"} 节讨论工程含义、局限和结论。

# 相关工作 {#zh:sec:related_work}

## 联合时空规划

联合规划器通过搜索或优化扩展状态保留几何和时间耦合。共形时空格栅直接协调位置、速度和时间
(McNaughton et al. 2011)。瞬时分析方法以及 SLT
形式化方法也在密集交通中联合处理横向和纵向决策 (Yang and Li 2021; Hu et
al. 2023, 2025; Qiao
2025)。混合整数形式化则可以用离散变量编码障碍物侧向选择 (Kessler et al.
2023)。这些方法具有较强的协调能力，但其扩大的搜索空间、整数决策或非线性规划结构，与许多
PVD 栈使用的两个串联凸 QP
存在结构差异。因此，本文后续使用的有限网格联合搜索只作为计算参考，不将其声称为连续问题的最优解。

## 分解式与迭代式协调

PVD 规划器先优化路径，再优化速度轮廓，从而获得计算可处理性 (Kant and
Zucker 1986; Werling et al.
2010)。凸平滑和分段加加速度优化使这种结构适用于面向生产的软件 (Fan et
al. 2018; Zhou et al. 2021; Zhang et al.
2020)。时间优化、迭代锚定、候选配对和风险感知协调能够在两个阶段之间回传信息
(C. Liu et al. 2017; Chen et al. 2019; Zhang et al. 2023; Han et al.
2026; Liu et al.
2024)。但它们的有效性取决于每个阶段暴露了哪些信息。反复更新到达时间，无法恢复已经被不可逆局部侧向决策丢弃的横向类别。

安全走廊方法在连续优化之前显式给出可行域。空间飞行走廊展示了凸集如何连接离散搜索和轨迹优化
(S. Liu et al. 2017)，近期自动驾驶研究又将这一思想扩展到时空换道走廊或
Frenet 走廊 (Yoon et al. 2024; Tariq et al. 2025)。MIKU
同样强调显式可行域，但关注更窄的接口问题，即如何在不替换路径 QP 和速度
QP 的情况下，生成相互一致的 SL 边界与 ST 边界。

## 交互预测与安全裕度

预测感知规划能够处理静态障碍物轮廓无法表达的行人和车辆交互 (Yang et al.
2023; Jeong and Yi
2021)。这类预测仍然存在不确定性，因此规划器需要区分用于估计到达时刻的名义状态和用于碰撞检查的占用集合。MIKU
使用前者查询并排序候选方案，同时用有界的位置误差和速度误差扩展后者。进一步的威胁相关附加裕度按照碰撞紧迫性、横向重叠、相对运动、目标类型和局部密度分配有限的横向空间，其中碰撞时间仅作为一个归一化紧迫性因子
(Minderhoud and Bovy 2001)。

表 [\[zh:tab:method_classes\]](#zh:tab:method_classes){reference-type="ref"
reference="zh:tab:method_classes"}
从求解器层面总结了这些差异。已有方法在各自假设下都具有价值，但仍缺少一种
PVD 栈，能够在保留下游 QP
的同时，联合协调依赖时间的投影、群组级侧向选择以及速度阶段的时序约束。

<a id="zh:tab:method_classes"></a>

| 方法族 | 时空协调方式 | 对求解器的影响 | 本文所处理的接口缺口 |
|---|---|---|---|
| 无时间意识的 PVD | 先路径后速度 | 两个结构化 QP | 丢失依赖到达时刻的占用信息和群组选择 |
| 迭代式 PVD | 反复更新路径与速度 | 多次调用求解器 | 仅靠时序无法恢复已丢弃的横向类别 |
| 联合格栅或混合整数规划 | 耦合状态或离散变量 | 扩大搜索或更换优化器 | 不保留原有的双 QP 接口 |
| 安全走廊规划 | 优化前构造凸可行集 | 走廊生成器加连续求解器 | 往往只关注选定走廊，而非耦合的空间和时间类别 |
| MIKU | 将空间和时间同伦编译为边界 | 保留两个下游 QP | 处理到达时序、群组决策和跨阶段约束传递 |

# 问题形式化与证据范围 {#zh:sec:problem}

## 路径—速度接口

考虑与道路对齐的 Frenet 坐标系，其中 $s$ 表示站位，$l$
表示相对于参考线的横向位移。PVD 规划器首先在 SL 空间中优化横向路径
$l(s)$，随后在 ST 空间中优化纵向运动 $s(t)$。令路径状态为
$\mathbf{x}_p=(l_j,l'_j,l''_j)_{j=0}^{K}$，速度状态为
$\mathbf{x}_v=(s_r,v_r,a_r)_{r=0}^{N}$，则常见的下游求解器可写为
$$\begin{align}
 \mathbf{x}_p^*={}&\arg\min_{\mathbf{x}_p}
 \frac{1}{2}\mathbf{x}_p^{\mathsf T}H_p\mathbf{x}_p+q_p^{\mathsf T}\mathbf{x}_p,\\[-2pt]
 &\quad\text{s.t. }A_p\mathbf{x}_p=b_p,\quad l_j^-\leq l_j\leq l_j^+, \label{zh:eq:path_qp}\\
 \mathbf{x}_v^*={}&\arg\min_{\mathbf{x}_v}
 \frac{1}{2}\mathbf{x}_v^{\mathsf T}H_v\mathbf{x}_v+q_v^{\mathsf T}\mathbf{x}_v,\\[-2pt]
 &\quad\text{s.t. }A_v\mathbf{x}_v=b_v,\quad s_r^{lb}\leq s_r\leq s_r^{ub},\\[-2pt]
 &\qquad 0\leq v_r\leq v_{\max},\quad a_{\min}\leq a_r\leq a_{\max}. \label{zh:eq:speed_qp}
\end{align}$$ 其中，$H_p$ 和 $H_v$ 编码平滑性代价，$A_p$ 和 $A_v$
编码分段加加速度运动学等式。路径边界集合
$\mathcal{B}_l=\{[l_j^-,l_j^+]\}$ 与 ST 位置边界集合
$\mathcal{B}_s=\{[s_r^{lb},s_r^{ub}]\}$ 是环境信息的接口。MIKU
只改变这两个接口，不改变下游目标矩阵、运动学等式和 QP 求解器。

## 中心坐标障碍物模型

对于障碍物 $i$，令 $O_i(t)=[s_i^-(t),s_i^+(t)]\times[l_i^-(t),l_i^+(t)]$
表示其物理矩形。若道路物理边界为
$[l_{\mathrm{road}}^-,l_{\mathrm{road}}^+]$，自车宽度为
$W_{\mathrm{ego}}$，路侧裕度为
$d_{\mathrm{road}}$，则自车中心的可行区间为 $$\begin{equation}
 [L^-,L^+]=[l_{\mathrm{road}}^-+W_{\mathrm{ego}}/2+d_{\mathrm{road}},\ l_{\mathrm{road}}^+-W_{\mathrm{ego}}/2-d_{\mathrm{road}}].
 \label{zh:eq:center_road}
\end{equation}$$
传递给中心坐标规划器的障碍物区间会一次性扩展自车宽度的一半以及障碍物特定的附加裕度
$d_{\mathrm{buf},i}$： $$\begin{equation}
 [u_i,v_i]=[l_i^- -W_{\mathrm{ego}}/2-d_{\mathrm{buf},i},\ l_i^+ +W_{\mathrm{ego}}/2+d_{\mathrm{buf},i}].
 \label{zh:eq:center_forbidden}
\end{equation}$$
式 ([\[zh:eq:center_road\]](#zh:eq:center_road){reference-type="ref"
reference="zh:eq:center_road"})--式 ([\[zh:eq:center_forbidden\]](#zh:eq:center_forbidden){reference-type="ref"
reference="zh:eq:center_forbidden"})中的四个量均指自车中心。因此，间隙宽度表示中心位置可用的宽度，后续可行性测试不再重复减去车辆宽度。

在某一站位处的 $k$
个活动障碍物集合中，将每个障碍物分配到自车带的左侧（$L$）或右侧（$R$）。对于决策向量
$\mathbf{d}$，得到的中心带为 $$\begin{equation}
 l^-(\mathbf{d})=\max\left(L^-,\max_{i\in\mathcal{L}}v_i\right),\qquad
 l^+(\mathbf{d})=\min\left(L^+,\min_{i\in\mathcal{R}}u_i\right),
 \label{zh:eq:center_band}
\end{equation}$$ 其中空集合的极值项省略。当数值容差为 $\varepsilon$
时，若
$W(\mathbf{d})=l^+(\mathbf{d})-l^-(\mathbf{d})\geq\varepsilon$，则该中心带可行。

## 两种失效机制与研究边界

当路径阶段忽略时间时，可能用预测时域上的并集替代动态占用
$$\begin{equation}
 \overline{O}_i=\bigcup_{t\in[0,T_{\mathrm{pred}}]}O_i(t),
 \label{zh:eq:prob_union}
\end{equation}$$
从而把不同时间被占用的位置当成同时存在。相反，逐障碍物的贪心策略可能在尚未看到同一纵向连通分量中另一个障碍物影响之前，就提前确定侧向。两种机制都可能造成
$l^+(s)<l^-(s)$，即使从时间上保持一致的通道仍然存在。

本文检验的是，在边界接口处恢复缺失的到达时间信息和群组级信息，是否能够改善规划结果。主要证据来自直道路段、恒定速度障碍物模型和有界扰动场景。3,500
个场景实验是匹配的数值评估，不是公共数据或道路现场研究。Apollo Planning
仅用于接口和代表性行为证据，不将其视为物理道路测试或 Apollo
原生运行时间基准。

# MIKU 方法 {#zh:sec:method}

## 总体流程

MIKU 重建无时间意识的 PVD 和逐障碍物 PVD
所丢失的两类信息。首先估计自车到达时间
$\tau(s)$，并查询依赖时间的障碍物占用。随后计算依赖威胁的中心边界，对纵向连通的障碍物进行分组，并选择连续的横向带。在路径
QP
求解之后，用不确定性扩展的占用管定义安全通行时间窗。分层时间同伦图选择具有因果一致性的时间窗序列，并将其写入
ST 位置边界。图 [2](#zh:fig:miku_flow){reference-type="ref"
reference="zh:fig:miku_flow"} 总结了数据流。

![MIKU 在 PVD
规划栈中的约束构造与传递。图内模块和变量名称保留英文，以便与实现对应。](figures/fig_framework_en.pdf){#zh:fig:miku_flow
width="\\textwidth"}

## 威胁感知裕度 {#zh:sec:method_threat}

对于障碍物 $i$，MIKU
将碰撞紧迫性、横向重叠、相对运动、目标类型和局部交互密度组合为归一化威胁分数：
$$\begin{equation}
 \Theta_i=w_1f_{\mathrm{TTC}}(i)+w_2f_{\mathrm{overlap}}(i)+w_3f_{\mathrm{vel}}(i)+w_4f_{\mathrm{type}}(i)+w_5f_{\mathrm{inter}}(i).
 \label{zh:eq:threat_score}
\end{equation}$$ 所有因子均位于 $[0,1]$，权重为
$(0.30,0.20,0.15,0.10,0.25)$。当自车位于障碍物后方且正在接近时，$\mathrm{TTC}_i=(s_i-s_{\mathrm{ego}})/(\dot{s}_{\mathrm{ego}}-\dot{s}_i)$，否则取
$+\infty$。分段线性 TTC 因子在 $\mathrm{TTC}_i\leq2.0$ s 时取 1，在
$\mathrm{TTC}_i\geq7.0$ s 时取 0，中间区间线性下降 (Minderhoud and Bovy
2001)。重叠因子和相对速度因子为 $$\begin{align}
 f_{\mathrm{overlap}}(i)&=\min\!\left(1,\frac{\max(0,\min(l_i^+,l_{\mathrm{ego}}^+)-\max(l_i^-,l_{\mathrm{ego}}^-))}{\max(0.1,\min(W_i,W_{\mathrm{ego}}))}\right),\\
 f_{\mathrm{vel}}(i)&=\sigma(v_{\mathrm{rel},i}/v_{\max}),\qquad \sigma(x)=\frac{1}{1+e^{-5x}}.
\end{align}$$ 其中 $W_i=l_i^+-l_i^-$
表示障碍物宽度。截断操作使障碍物宽于自车时的重叠因子仍处于
$[0,1]$。易受伤道路使用者、机动车、未知可移动物体、静态障碍物和小型标记物的类型因子分别为
$1.0$、$0.7$、$0.5$、$0.3$ 和 $0.15$。密度在 10 m
邻域内计算，单个障碍物的密度取 0。附加裕度为 $$\begin{equation}
 d_{\mathrm{buf},i}=d_{\mathrm{buf,min}}+(d_{\mathrm{buf,max}}-d_{\mathrm{buf,min}})\Theta_i,
 \label{zh:eq:dynamic_delta}
\end{equation}$$ 其中
$[d_{\mathrm{buf,min}},d_{\mathrm{buf,max}}]=[0.10,0.40]$
m。该项只改变边界数值，不改变排序或扫描结构。

## 连续横向划分与最大间隙 {#zh:sec:method_band}

纵向区间相互重叠的障碍物被分配到同一个连通分量。按较低站位边缘排序，并维护最大的上界，即可在
$O(n\log n)$ 时间内构造所有分量。在一个分量内部，再按 $u_i$
对活动区间排序，$u_i$ 相同时按 $v_i$
降序排列。下面的引理限制侧向分配搜索范围。

::: {#zh:lem:continuous_partition .lemma}
**引理 1** (连续最优划分).
*对于式 ([\[zh:eq:center_band\]](#zh:eq:center_band){reference-type="ref"
reference="zh:eq:center_band"})中的中心带目标，存在一个最优分配，使得按
$u_i$ 排序的障碍物中，前缀被分配到 $L$ 侧，后缀被分配到 $R$
侧。因此只需考察 $k+1$ 个分割点。*
:::

*证明。* 若两侧均非空，令 $\beta=\min_{i\in\mathcal{R}}u_i$。将当前位于
$\mathcal{L}$ 且满足 $u_i\geq\beta$ 的每个障碍物移到
$\mathcal{R}$。由于每个被移动的下边缘都不小于
$\beta$，上界保持不变，而从 $\mathcal{L}$
中移除元素不会抬高下界，因此带宽不会减小。重复该操作即可得到连续分割。空侧情况对应
$p=0$ 或 $p=k$。对于 $u_i$ 相同的情况按 $v_i$
降序排列即可消除歧义。$\Box$

对于分割点 $p$，定义前缀最大值和候选上边缘 $$\begin{equation}
 V_0=L^-,\qquad V_p=\max\left(L^-,\max_{1\leq q\leq p}v_{(q)}\right),
 \label{zh:eq:prefix_v}
\end{equation}$$ $$\begin{equation}
 U_p=\begin{cases}\min(L^+,u_{(p+1)}),&p<k,\\L^+,&p=k,\end{cases}\qquad g_p=U_p-V_p.
 \label{zh:eq:gap_def}
\end{equation}$$

::: {#zh:thm:max_gap .theorem}
**定理 2** (最大间隙最优性). *对于固定截面区间模型，最优中心带宽度为
$W^*=\max_{p=0,\ldots,k}g_p$。候选解通过排序和一次前缀扫描获得，复杂度为
$O(k\log k)$。*
:::

*证明。* 对于分割点
$p$，式 ([\[zh:eq:center_band\]](#zh:eq:center_band){reference-type="ref"
reference="zh:eq:center_band"})给出下边缘 $V_p$ 和最紧的上边缘
$U_p$，因此带宽为
$g_p$。引理 [1](#zh:lem:continuous_partition){reference-type="ref"
reference="zh:lem:continuous_partition"} 保证存在连续最优分割，枚举
$k+1$ 个分割点即可取得最优值。$\Box$

该定理只对固定截面区间抽象成立，不能证明完整非凸轨迹问题的连续全局最优性。MIKU
在每个分量中保留 $Q=3$
个最宽的正带，并通过动态规划在带宽与横向中心变化之间进行权衡。若分量 $j$
中的带 $B_{jq}$ 具有中心 $c_{jq}$ 和宽度 $g_{jq}$，则序列最小化
$$\begin{equation}
 -\sum_jg_{jq_j}+\lambda_s\left(|c_{1q_1}-l_0|+\sum_{j>1}|c_{jq_j}-c_{j-1,q_{j-1}}|\right),
 \label{zh:eq:spatial_homotopy}
\end{equation}$$ 递推关系为 $$\begin{equation}
 D_{jq}=-g_{jq}+\min_r\{D_{j-1,r}+\lambda_s|c_{jq}-c_{j-1,r}|\}.
 \label{zh:eq:spatial_dp}
\end{equation}$$

![固定截面最大间隙问题的连续分割候选。四个排序后的禁行区间产生五个候选分割点。当区间上边缘相互嵌套时，需要维护前缀最大值。图内变量保留英文。](figures/fig_max_gap_en.pdf){#zh:fig:max_gap
width="82%"}

## 依赖到达时间的投影 {#zh:sec:method_projection}

在站位 $s$
处，路径阶段查询预计自车到达时刻对应的障碍物占用。根据当前状态并采用恒定加速度近似，有
$$\begin{equation}
 \tau(s)=\frac{-v_{\mathrm{ego}}+\sqrt{v_{\mathrm{ego}}^2+2a_{\mathrm{ego}}(s-s_{\mathrm{ego}})}}{a_{\mathrm{ego}}},
 \label{zh:eq:arrival_time}
\end{equation}$$ 当 $|a_{\mathrm{ego}}|<10^{-3}$
时使用恒速极限。判别式为负时，将该点标记为位于规划时域之外。在滚动重规划中，$\tau(s)$
由上一次速度解插值得到，并在每个周期更新。

数值场景采用 $s_i(t)=s_{i,0}+v_{s,i}t$ 和
$l_i(t)=l_{i,0}+v_{l,i}t$。对于有界预测误差，时刻 $t$ 的纵向和横向扩展为
$$\begin{equation}
 \epsilon_{s,i}(t)=\epsilon_{s0,i}+t\epsilon_{vs,i},\qquad
 \epsilon_{l,i}(t)=\epsilon_{l0,i}+t\epsilon_{vl,i}.
 \label{zh:eq:prediction_tube}
\end{equation}$$ 在构造 ST
占用图之前，将物理障碍物和自车轮廓按上述量扩展。名义的 $\tau(s)$
用于选择并排序候选方案，碰撞检查则使用扩展后的占用。

## 时间同伦与 ST 传递 {#zh:sec:method_temporal}

对于冲突区域 $c$，令 $I_{cr}=[t_{cr}^{in},t_{cr}^{out}]$
表示路径与预测占用管之间的每个重叠区间。经过时间安全扩展 $\eta_c$
后，安全时间窗为 $$\begin{equation}
 \mathcal{W}_c=[0,T]\setminus\bigcup_r[t_{cr}^{in}-\eta_c,t_{cr}^{out}+\eta_c].
 \label{zh:eq:safe_windows}
\end{equation}$$ 将这些时间窗与最早可到达时间相交，得到
$W_{cq}=[\alpha_{cq},\beta_{cq}]$。对于按站位排序的冲突点，当满足
$$\begin{equation}
 \hat t_c\geq\hat t_{c-1}+\frac{s_c-s_{c-1}}{v_{\max}},\qquad \hat t_c\in W_{cq}
 \label{zh:eq:temporal_edge}
\end{equation}$$ 时，连接相邻节点。节点代价衡量其与 $\tau(s_c)$
的偏离，边代价抑制在障碍物前后通行之间进行不必要的切换。带宽受限的动态规划选择一条具有因果关系的序列。

对于选定的时间窗，其语义以线性盒约束进入速度 QP： $$\begin{equation}
 \begin{aligned}
 s_j^{ub}&=\min(s_j^{ub,0},s_c^- -\epsilon_s),&&t_j<\alpha_{cq},\\
 s_j^{lb}&=\max(s_j^{lb,0},s_c^+ +\epsilon_s),&&t_j\geq\beta_{cq}.
 \end{aligned}
 \label{zh:eq:window_to_st}
\end{equation}$$
如果没有完整的可达时间窗序列，规划器会在第一个不可达冲突之前施加停车上界。下游速度
QP 仍然是具有相同目标函数和运动学等式的凸 QP。

## 算法与复杂度

### 算法 1：MIKU 约束编译

**输入：** 道路边界、自车状态以及 $n$ 个障碍物的预测轨迹<br>
**输出：** 中心路径边界和 ST 位置边界

1. 估计 $\tau(s)$，并为每个障碍物计算依赖威胁的中心区间。
2. 对站位区间排序并构造纵向连通分量。
3. 对每个连通分量，按 $(u_i,-v_i)$ 排序，计算前缀最大值，并保留 $Q$ 个最宽的正带。
4. 依据空间同伦目标选择连续的空间同伦序列。
5. 将选定的侧向分配写入各站位的活动路径边界。
6. 构造不确定性扩展的占用管和安全时间窗。
7. 依据时间边条件选择具有因果关系的时间同伦序列，并将其编译为 ST 盒约束。
8. 若启用迭代，则根据速度解更新 $\tau(s)$，直到达到迭代上限或收敛。
9. 返回路径边界和 ST 边界。

对于 $K$ 个路径采样点、$m$ 个分量、每个分量至多 $Q$
个空间候选以及有界时间束宽度 $B$，排序和分组的代价为
$O(n\log n)$。若每个终端空间带保留 $K_s$
个前缀，分层空间动态规划的代价为 $O(mK_sQ^2\log(K_sQ))$。对于 $h$
个冲突点以及每层 $R$ 个可达时间窗，时间束扩展和排序的代价为
$O(hBR\log(BR))$。实现采用 $Q=3$、$K_s=3$ 和 $B=8$。占用查询的代价为
$O(nK)$，朴素交互密度计算在最坏情况下为 $O(n^2)$。

# 实验设计 {#zh:sec:experimental_design}

评估过程将统计规划证据与机制证据、软件集成证据分开。统计实验使用确定性场景生成器和固定随机种子，使每种方法接收相同的规划输入和相同的车辆约束。碰撞与间隙根据单独保留的真实场景进行评估。Apollo
Planning 作为第二条证据流，用于检查接口兼容性和代表性行为。

## 实验协议与场景

主要开环协议包含 3,500 个配对场景，七类场景各使用 500
个随机种子，分别为交叉行人、车辆切入、带对向交通的停放车辆、窄间隙多障碍物、交错动态障碍物、预测噪声和延迟交叉。障碍物与自车参数在各类场景的范围内采样，随机种子和场景类别共同确定完整案例。除预测噪声类别只在规划输入中注入有界误差外，规划场景和真实场景完全相同。生成器、原始行、元数据和哈希值均放入补充材料。

4,000 个实例的几何检查使用 20 个确定性随机种子，每个种子生成 200
个固定截面区间实例。每个实例包含 0 到 8
个可能重叠、嵌套或穿越道路边界的禁行区间。扫描算法与全部 $2^k$
种侧向分配的穷举结果进行比较。该实验检验的是给定区间模型下中心带宽度是否相等，不检验跟踪误差或完整轨迹最优性。

为了测试滚动行为，独立的 700 场景协议在每类场景中使用 100
个随机种子。每隔 0.5 s
执行当前计划的第一个片段，更新自车和障碍物状态，并再次调用规划器，直到到达目标或达到场景时域。这些案例不与
3,500 个开环案例合并。最后，70
个分层有限网格联合参考案例在每类场景中使用 10 个随机种子，网格间距为
$\Delta t=0.5$ s、$\Delta s=0.5$ m、$\Delta l=0.25$ m 和 $\Delta v=1.0$
m/s，束宽为 20,000。它明确是粗粒度有限搜索，不是连续全局最优解。

## 基线与实现

匹配的 PVD 基线按照约束接口交换的信息定义：

- B0 无时间意识，使用固定的局部侧向策略。

- B1 增加依赖到达时间的投影，但保留逐障碍物的贪心侧向选择。

- B2 在 B1 策略中允许三次到达时间细化迭代。

- MIKU 增加群组级连续划分、Top-$K$
  空间同伦、威胁感知裕度、不确定性扩展占用、时间同伦，以及最多两次交替更新的规划迭代。

四种方法共享相同的路径 QP 和速度 QP
目标、运动学约束、场景输入和数值指标实现。B3
是有限网格联合参考，按设计使用不同求解器。实现运行在 Intel i9-14900HX
处理器、64 GB 内存和 Arch Linux 环境上。Apollo 集成使用 Apollo 11.0
的路径边界和 ST 边界接口，所验证的是编译后约束能够进入现有规划链，并非
Apollo 原生基准测试。

## 结果指标与统计分析

主要结果指标是无碰撞到达目标率。当运行在完整时域内保持无碰撞，并且达到
$s_{\mathrm{end}}\geq s_{\max}-1$ m
时，判定为成功。碰撞率根据真实矩形评估，退化停车率记录无碰撞但停车或未到达目标的运行。进度比、平均速度、加加速度均方根、最小带符号间隙、最小纵向碰撞时间、带惩罚的行驶时间和完整规划延迟共同提供运营、安全、舒适性和计算背景。无碰撞到达时，带惩罚的行驶时间等于到达时间，否则等于场景时域加
5 s。运行时间包括完整的方法调用，B2 包括其全部协调迭代。

对于每个固定随机种子，先计算 MIKU
减去基线的差值，再进行聚合。连续指标使用 5,000 次重采样的配对百分位
Bootstrap 区间，二元成功和碰撞结果使用精确 McNemar 检验，效应量采用配对
Cohen's $d_z$。运行时间报告第 50、95 和 99
百分位，因为单一典型周期值可能掩盖运营尾部。本文不进行外部排行榜比较。B0--B2
是内部匹配变体，B3 是有限计算参考。

## 机制与接口案例

四个确定性机制案例暴露两类目标失效，即无时间意识的占用处理和不兼容的逐障碍物侧向选择。四个配对控制案例只改变时间范围或横向位置，使基线保持可行。三个
Apollo Dreamview
案例分别展示动态超车、窄间隙通行和单车道绕行。它们是定性的接口案例，与数值实验协议分开报告。

# 结果 {#zh:sec:results}

## RQ1：主要比较 {#zh:subsec:results_main}

固定截面测试显示，$O(k\log k)$ 扫描与穷举枚举在全部 4,000
个生成实例上完全一致。中心带宽度的最大绝对差小于 $10^{-12}$
的数值测试容差。该结果只确立固定截面定理所声称的内容，不表示完整轨迹规划器具有全局最优性。

表 [\[zh:tab:main_results\]](#zh:tab:main_results){reference-type="ref"
reference="zh:tab:main_results"} 报告 3,500 个配对场景的结果。MIKU 将 B0
的无碰撞到达目标率从 62.69% 提高到 77.46%，配对差值为 14.77
个百分点，95% 置信区间为 13.54--15.97，精确 McNemar 检验
$p=1.94\times10^{-133}$。碰撞率从 2.17% 降至 1.14%，差值为 $-1.03$
个百分点，95% 置信区间为 $-1.37$ 至
$-0.71$，$p=2.91\times10^{-11}$。平均进度提高 8.93
个百分点，加加速度均方根降低 0.120 m/s$^3$，带惩罚行驶时间减少 0.81
s。平均间隙的总体差值为 $-0.010$ m，95% 置信区间为
$[-0.024,0.004]$，因此成功率和碰撞率的改善不能解释为间隙普遍增大。

<a id="zh:tab:main_results"></a>

| 指标 | B0 | B1 | B2 | MIKU |
|---|---:|---:|---:|---:|
| 无碰撞到达目标（%） | 62.69 | 52.37 | 62.09 | **77.46** |
| 碰撞（%） | 2.17 | 2.14 | 2.23 | **1.14** |
| 退化停车（%） | 35.40 | 45.77 | 35.97 | **21.51** |
| 进度比（%） | 77.52 | 71.07 | 76.62 | **86.45** |
| 加加速度均方根（m/s$^3$） | 1.252 | 1.315 | 1.300 | **1.132** |
| 运行时间第 50 百分位（ms） | 10.11 | 11.37 | 31.20 | **9.98** |
| 运行时间第 95 百分位（ms） | 56.79 | 63.24 | 169.49 | **55.93** |
| 运行时间第 99 百分位（ms） | 138.88 | 169.73 | 463.05 | 221.80 |

图 [4](#zh:fig:evidence_dashboard){reference-type="ref"
reference="zh:fig:evidence_dashboard"}
中的类别级结果显示了总体差异的来源。窄间隙多障碍物类别的成功率增益最大，为
65.4 个百分点，其次是延迟交叉类别的 26.8
个百分点。在本协议中，交叉行人和车辆切入类别的总体成功率没有差异，这与基线已经具有可行时间响应的案例相符。预测噪声类别的成功率提高
3.2 个百分点，碰撞率降低 7.0 个百分点，但进度下降 1.12
个百分点，加加速度均方根增加 0.041 m/s$^3$。

有限网格参考体现的是计算代价权衡，而不是胜负比较。在 70 个案例中，B3
的目标到达率为 80.0%，MIKU 为 77.1%，配对差值为 $-2.86$ 个百分点，95%
置信区间为 $[-11.43,5.71]$，$p=.754$。B3 的运行时间中位数为 1,835.43
ms，MIKU 为 10.44 ms。因此，在这一小规模、粗网格实验中，MIKU
以显著更低的实测代价接近有限网格参考的成功率，但两个求解器优化的是不同表示。

![冻结的 3,500 场景协议的证据汇总。面板 (a) 给出各场景类别中 MIKU 相对
B0 的配对成功率效应及 95% Bootstrap 区间，(b) 给出完整规划延迟分布，(c)
给出完整方法相对消融方法的成功率效应，(d) 将 MIKU
结果分解为成功到达、安全但未到达和碰撞。图内面板文字保留英文。](figures/evidence_dashboard.pdf){#zh:fig:evidence_dashboard
width="\\textwidth"}

## RQ2：机制与消融 {#zh:subsec:results_ablation}

在相同的 3,500 个场景上进行减法消融，以隔离各个机制。移除 Top-$K$
空间同伦后，成功率相对于完整 MIKU 降低 10.17
个百分点，移除威胁感知裕度后降低 10.74
个百分点。移除时间同伦图后，延迟交叉类别的成功率从 89.6% 降至
66.8%，类别特定损失为 22.8
个百分点。移除鲁棒占用管后，预测噪声类别的碰撞率从 3.6% 增至
11.0%。到达时间投影和纵向分组带来的总体变化较小，说明它们的价值集中在特定构型，而非均匀作用于所有类别。

<a id="zh:tab:ablation_results"></a>

| 变体 | 移除组件 | 成功率（%） | 碰撞率（%） | 进度（%） |
|---|---|---:|---:|---:|
| A1 | 到达时间投影 | 77.34 | 1.23 | 86.73 |
| A2 | 纵向分组 | 76.94 | 1.14 | 85.89 |
| A3 | Top-$K$ 空间同伦 | 67.29 | 1.14 | 79.53 |
| A4 | 威胁感知裕度 | 66.71 | 1.14 | 78.85 |
| A5 | 时间同伦图 | 74.20 | 1.17 | 84.29 |
| A6 | 鲁棒占用管 | 76.97 | 2.20 | 86.60 |
| A7 | 交替细化 | 76.63 | 1.03 | 85.92 |
| MIKU | 无 | **77.46** | **1.14** | **86.45** |

机制案例为这些结果提供了几何解释。在窄通道案例中，逐障碍物策略不断抬高和降低相互对置的路径边界，直到中心区间变为空，而群组级划分在协调障碍物侧向选择后保留了一条连续带。在延迟交叉类别中，时间图保留障碍物前通行和障碍物后通行两种候选，并强制其满足因果顺序。这些案例用于定位失效机制，不能替代类别级总体估计。

![窄间隙多障碍物机制示意。群组级划分在协调障碍物侧向选择后保留连续的中心带。图内变量和模块名称保留英文。](figures/fig_narrow_en.pdf){#zh:fig:narrow_mechanism
width="\\textwidth"}

## RQ3：鲁棒性、副作用与延迟尾部 {#zh:subsec:results_robustness}

预测噪声子组同时展示了收益和代价。MIKU 相对 B0 将碰撞率降低 7.0
个百分点，但平均进度为 59.73%，低于 B0 的 60.85%，加加速度均方根为 2.274
m/s$^3$，高于 B0 的 2.234
m/s$^3$。这与以下解释一致，即当误差界相对于可用通道较大时，不确定性扩展占用会产生保守行为。

完整调用的运行时间中位数和第 95 百分位与 B0 相近或更低，但第 99
百分位并非如此。MIKU 的第 99 百分位为 221.80 ms，B0 为 138.88
ms，图 [4](#zh:fig:evidence_dashboard){reference-type="ref"
reference="zh:fig:evidence_dashboard"}
中的经验延迟曲线显示了上尾分化。由于 B2
始终执行三次协调迭代，它在所有报告分位数上都更慢。因此，这些结果支持的是典型周期效率判断，而不是硬实时保证。

独立的滚动重规划协议从另一个角度展示累积行为。在 700 个案例中，成功率从
62.29% 增至 72.29%，配对差值为 10.0 个百分点，95% 置信区间为
7.57--12.57，而两种方法的碰撞率均为 1.29%。平均进度从 82.55% 增至
90.25%，但单回合运行时间第 95 百分位从 827.20 ms 增至 1,361.51
ms。由于该协议执行并重新规划，而不是只评估一次开环调用，因此将其作为鲁棒性证据单独报告，不与表 [\[zh:tab:main_results\]](#zh:tab:main_results){reference-type="ref"
reference="zh:tab:main_results"} 合并。

## RQ4：PVD 软件接口证据 {#zh:subsec:results_apollo}

Apollo 11.0 实现通过已有的路径边界和 ST 边界接口传递生成的路径约束与 ST
约束，同时保留下游 QP 目标和运动学等式。三个代表性 Dreamview
案例展示了动态超车、窄通道通行和单车道绕行。这些案例说明抽象约束编译具有兼容的软件插入点，并能够产生预期的定性行为。但它们不能证明物理道路安全、Apollo
原生延迟、硬件在环性能或完整的端到端正确性。

<figure id="zh:fig:apollo_cases">
<div class="minipage">
<img src="figures/dreamview/scn01_during.png" />
<p>动态超车</p>
</div>
<div class="minipage">
<img src="figures/dreamview/scn02_during.png" />
<p>窄通道</p>
</div>
<div class="minipage">
<img src="figures/dreamview/scn03_during.png" />
<p>单车道绕行</p>
</div>
<figcaption>代表性的 Apollo Dreamview
接口案例。截图是定性的集成证据，不用于计算上述统计结果。</figcaption>
</figure>

# 讨论 {#zh:sec:discussion}

## 证据能够确立的内容

本文的主要结果是约束接口效应，而不是声称某一个优化器支配所有替代方法。MIKU
保留 PVD
求解器，但改变障碍物信息何时以及以何种方式到达求解器。最大收益出现在窄间隙多障碍物和延迟交叉构型中，恰好是预测时域并集或不可逆局部侧向选择会移除可行替代方案的情形。在
B0
已经容易处理的构型中，例如交叉行人和车辆切入类别，总体成功率没有变化。相比所有案例都统一提升，这种结果模式更直接地支持本文提出的机制。

消融实验提供了第二层支持。Top-$K$
空间同伦和威胁感知裕度解释了总体成功率差异的大部分，而时间同伦图主要在障碍物前后两种通行均可到达时发挥作用。鲁棒占用管在预测噪声下减少碰撞，但相应的进度和加加速度代价表明，面向安全的扩展会消耗可用空间。这些权衡与将可行性、安全性和舒适性视为竞争性运营结果的走廊规划和预测感知规划研究一致
(Yoon et al. 2024; Yang et al. 2023; Liu et al. 2024)。

## 运营含义

对于基于 PVD
的自动驾驶车辆规划栈，一个可操作的设计规则是在确定路径边界之前保留交互时序，然后将选定的时间语义传递给速度阶段。这样可以在不引入新的下游非线性或混合整数求解器的情况下，减少不必要的兜底停车。该规则尤其适用于窄施工区、临时车道绕行以及多个障碍物共享同一纵向分量的混合交通场景。部署时仍应配备延迟监控器和兜底策略，因为运行时间上尾和不确定性扩展案例仍然具有实际影响。

## 与替代方法的关系

有限网格参考在小规模比较中取得略高的成功率，但运行时间中位数约高出两个数量级。这一比较说明扩展联合搜索与编译式
PVD 接口之间存在质量—代价权衡，并不能证明 MIKU
在全局上更优。同样，迭代式 B2
基线表明，当缺失信息是已经丢弃的横向类别时，简单重复 PVD
阶段并不足够。因此，MIKU
的贡献在于约束的表示和传递，而不是声称所有部署都不需要迭代或联合搜索。

## 对评估的启示

3,500 个场景的数值协议、700 个场景的滚动协议和 Apollo
接口案例彼此分开，对于正确解释结果十分重要。第一类估计匹配场景层面的效应，第二类测试重规划下的累积行为，第三类检查工程插入点。将它们合并为一个总分会夸大外部有效性。后续评估应使用公共或道路采集轨迹、与近期外部规划器的匹配比较，并在目标硬件预算下进行原生运行时间测量。

# 局限性 {#zh:sec:limitations}

本文证据有五项明确边界。第一，主要场景在直道路段生成，障碍物采用恒定速度模型。这可能高估预测占用的规律性，也没有测试道路曲率、车道拓扑、天气和事故影响。下一项研究应在不同道路几何上回放公共轨迹和道路采集轨迹。第二，预测噪声模型使用有界位置误差和速度误差，因此碰撞结果只适用于给定误差包络，而不适用于任意预测器。下一步需要经过校准的多模态预测分布。第三，B0--B2
是内部匹配的 PVD 变体，B3 是有限粗网格参考。本文不作公共数据集上的 SOTA
声称，也不作公平的跨数据集比较。下一项比较应实现一个近期外部规划器的匹配版本。第四，Apollo
证据覆盖接口兼容性和代表性 Dreamview 行为，不覆盖 Apollo
原生性能、硬件在环执行、物理道路测试或端到端安全证明。在作出部署声明之前，需要原生闭环测量和受控道路测试。第五，最大间隙定理只对固定截面区间抽象和保留的候选集精确成立，不能证明完整非凸轨迹问题的连续全局最优性。后续形式化可以研究障碍物顺序发生变化时的完备性。

# 结论 {#zh:sec:conclusion}

本文提出了面向动态多障碍交通路径—速度规划的交互感知约束编译器
MIKU。依赖到达时间的投影、连续群组级划分、不确定性扩展占用和时间同伦，将丢失的交互信息转换为
SL 边界和 ST 边界，同时保留下游路径 QP 和速度
QP。固定截面定理将侧向分配搜索化为 $O(k\log k)$ 扫描，并在 4,000
个确定性实例上与穷举枚举一致。在 3,500
个配对场景中，相对于无时间意识的基线，无碰撞到达目标率从 62.7% 提高到
77.5%，碰撞率从 2.2% 降至
1.1%，最大效应出现在窄间隙和延迟交叉构型。典型延迟保持在约 10 ms，但第
99 百分位尾部更高，滚动重规划也提高了单回合运行时间第 95
百分位，因此当前结果支持有界仿真和接口层面的结论，不支持硬实时或道路部署保证。下一项研究应使用经过校准的公共或道路轨迹，并结合原生运行时间测量验证同一约束传递机制。

# 数据可用性声明 {#数据可用性声明 .unnumbered}

匿名复现实验包包含冻结的场景生成器、配置文件、聚合结果、原始行和分析脚本。论文录用后，材料将在持久化公共仓库中发布。审稿期间，编辑流程可以向通讯作者合理申请这些材料。

# 代码可用性声明 {#代码可用性声明 .unnumbered}

复现正文数值表所需的分析与评估脚本已包含在补充材料压缩包中。Apollo
集成文件和完整软件包将在录用后随公共仓库发布，但需遵守上游 Apollo
组件的许可条件。

# 基金 {#基金 .unnumbered}

本研究得到襄阳市异构大数据市级重点实验室、湖北省优势特色学科群"新能源汽车与智慧交通"以及湖北省重点研发计划（项目编号
2025BEB002）的支持。

# 利益冲突声明 {#利益冲突声明 .unnumbered}

作者声明不存在利益冲突。

# CRediT 作者贡献 {#credit-作者贡献 .unnumbered}

JiaWang Liao
负责概念化、方法、软件、形式化分析、数据整理、可视化和论文初稿撰写。YuFei
Hu 负责方法、验证、调查和论文审阅与编辑。ChaoYang Shi
负责软件、验证、调查、可视化和论文审阅与编辑。ChengJiao Sun
负责监督、项目管理、基金获取、概念化以及论文审阅与编辑。全体作者均审阅并批准最终稿件。

# AI 使用声明 {#ai-使用声明 .unnumbered}

OpenAI Codex（GPT-5，访问时间为 2026 年 9
月）用于将作者已有的中文稿翻译、文字编辑并按期刊呈现需要重组。该工具未用于原创或得出科学论证，也未用于生成底层数据或分析。引用选择和书目信息已根据作者的原始材料及正式记录核验。JiaWang
Liao
对完整英文稿进行审阅和核验，包括全部科学主张、公式、引用和数值结果。作者已查阅适用的工具使用条款，确认这种使用适合发表，并对全文内容的原创性、完整性和准确性，包括参考文献的准确性，承担全部责任。

::::::::::::::::::::::::::::: {#refs .references .csl-bib-body .hanging-indent}
::: {#ref-chen2019em .csl-entry}
Chen, Jianyu, Wei Zhan, and Masayoshi Tomizuka. 2019. "Autonomous
Driving Motion Planning with Constrained Iterative LQR." *IEEE
Transactions on Intelligent Vehicles* 4 (2): 244--54.
<https://doi.org/10.1109/TIV.2019.2904385>.
:::

::: {#ref-fan2018baidu .csl-entry}
Fan, Haoyang, Fan Zhu, Changchun Liu, et al. 2018. *Baidu Apollo EM
Motion Planner*. <https://arxiv.org/abs/1807.08048>.
:::

::: {#ref-gonzalez2016 .csl-entry}
González, David, Joshué Pérez, Vicente Milanés, and Fawzi Nashashibi.
2016. "A Review of Motion Planning Techniques for Automated Vehicles."
*IEEE Transactions on Intelligent Transportation Systems* 17 (4):
1135--45. <https://doi.org/10.1109/TITS.2015.2498841>.
:::

::: {#ref-han2026_contingency .csl-entry}
Han, Wei, Bo Leng, Peizhi Zhang, and Lu Xiong. 2026. "Safety-Critical
Kinematically-Executable Overtake Planning via Contingency Path-Speed
Iterative Algorithm for Automated Valet Parking." *IET Intelligent
Transport Systems* 20 (1): e70140. <https://doi.org/10.1049/itr2.70140>.
:::

::: {#ref-hu2023_hybrid_astar_slt .csl-entry}
Hu, Jie, Zhihao Zhang, Ruinan Chen, et al. 2023. "Spatiotemporal Joint
Planning for Intelligent Vehicles Based on an Improved Hybrid A\*."
*Automotive Engineering*, ahead of print.
<https://doi.org/10.19562/j.chinasae.qcgc.2023.07.003>.
:::

::: {#ref-hu2025_dp_nmpc .csl-entry}
Hu, Jie, Jiachen Zheng, Silong Zhou, Wenlong Zhao, Zhiling Zhang, and
Maojia Yao. 2025. "Spatiotemporal Joint Trajectory Planning for
Intelligent Vehicles on Structured Roads." *Automotive Engineering*,
ahead of print. <https://doi.org/10.19562/j.chinasae.qcgc.2025.05.003>.
:::

::: {#ref-jeong2021ml .csl-entry}
Jeong, Yonghwan, and Kyongsu Yi. 2021. "Target Vehicle Motion
Prediction-Based Motion Planning Framework for Autonomous Driving in
Uncontrolled Intersections." *IEEE Transactions on Intelligent
Transportation Systems* 22 (1): 168--77.
<https://doi.org/10.1109/TITS.2019.2955721>.
:::

::: {#ref-kant1986pvd .csl-entry}
Kant, Kamal, and Steven W. Zucker. 1986. "Toward Efficient Trajectory
Planning: The Path-Velocity Decomposition." *The International Journal
of Robotics Research* 5 (3): 72--89.
<https://doi.org/10.1177/027836498600500304>.
:::

::: {#ref-kessler2023 .csl-entry}
Kessler, Tobias, Klemens Esterle, and Alois Knoll. 2023. "Mixed-Integer
Motion Planning on German Roads Within the Apollo Driving Stack." *IEEE
Transactions on Intelligent Vehicles* 8 (1): 851--67.
<https://doi.org/10.1109/TIV.2022.3162671>.
:::

::: {#ref-liu2017speed .csl-entry}
Liu, Changliu, Wei Zhan, and Masayoshi Tomizuka. 2017. "Speed Profile
Planning in Dynamic Environments via Temporal Optimization." *2017 IEEE
Intelligent Vehicles Symposium*, 154--59.
<https://doi.org/10.1109/IVS.2017.7995713>.
:::

::: {#ref-pathspeedstructured2024 .csl-entry}
Liu, Fang, Xiaowen Zhao, Weixing Su, and Yonggang Wen. 2024. "Dynamic
Path-Speed Planning Algorithm for Autonomous Driving on Structured
Roads." *Proceedings of the Institution of Mechanical Engineers, Part D:
Journal of Automobile Engineering* 238 (10-11): 3172--93.
<https://doi.org/10.1177/09544070231181626>.
:::

::: {#ref-liu2017sfc .csl-entry}
Liu, Sikang, Michael Watterson, Kartik Mohta, et al. 2017. "Planning
Dynamically Feasible Trajectories for Quadrotors Using Safe Flight
Corridors in 3-D Complex Environments." *IEEE Robotics and Automation
Letters* 2 (3): 1688--95. <https://doi.org/10.1109/LRA.2017.2663526>.
:::

::: {#ref-mcnaughton2011lattice .csl-entry}
McNaughton, Matthew, Chris Urmson, John M. Dolan, and Jin-Woo Lee. 2011.
"Motion Planning for Autonomous Driving with a Conformal Spatiotemporal
Lattice." *2011 IEEE International Conference on Robotics and
Automation*, 4889--95. <https://doi.org/10.1109/ICRA.2011.5980223>.
:::

::: {#ref-minderhoud2001extended .csl-entry}
Minderhoud, Michiel M., and Piet H. L. Bovy. 2001. "Extended
Time-to-Collision Measures for Road Traffic Safety Assessment."
*Accident Analysis & Prevention* 33 (1): 89--97.
<https://doi.org/10.1016/S0001-4575(00)00019-1>.
:::

::: {#ref-paden2016 .csl-entry}
Paden, Brian, Michal Čáp, Sze Zheng Yong, Dmitry Yershov, and Emilio
Frazzoli. 2016. "A Survey of Motion Planning and Control Techniques for
Self-Driving Urban Vehicles." *IEEE Transactions on Intelligent
Vehicles* 1 (1): 33--55. <https://doi.org/10.1109/TIV.2016.2578706>.
:::

::: {#ref-qiao2025stjoint .csl-entry}
Qiao, Ying. 2025. "Study on a Spatiotemporal Joint Trajectory-Planning
Algorithm for Autonomous Driving on Structured Roads." Master's thesis,
Harbin Institute of Technology.
<https://doi.org/10.27061/d.cnki.ghgdu.2025.003637>.
:::

::: {#ref-schwarting2018planning .csl-entry}
Schwarting, Wilko, Javier Alonso-Mora, and Daniela Rus. 2018. "Planning
and Decision-Making for Autonomous Vehicles." *Annual Review of Control,
Robotics, and Autonomous Systems* 1 (1): 187--210.
<https://doi.org/10.1146/annurev-control-060117-105157>.
:::

::: {#ref-frenetcorridor2025 .csl-entry}
Tariq, Faizan M., Zheng-Hang Yeh, Avinash Singh, David Isele, and
Sangjae Bae. 2025. "Frenet Corridor Planner: An Optimal Local Path
Planning Framework for Autonomous Driving." *2025 IEEE Intelligent
Vehicles Symposium (IV)*, 686--93.
<https://doi.org/10.1109/IV64158.2025.11097649>.
:::

::: {#ref-wang2022_jfr .csl-entry}
Wang, Haiming, Liangliang Zhang, Qi Kong, et al. 2022. "Motion Planning
in Complex Urban Environments: An Industrial Application on Autonomous
Last-Mile Delivery Vehicles." *Journal of Field Robotics* 39 (8):
1258--85. <https://doi.org/10.1002/rob.22107>.
:::

::: {#ref-werling2010 .csl-entry}
Werling, Moritz, Julius Ziegler, Sören Kammel, and Sebastian Thrun.
2010. "Optimal Trajectory Generation for Dynamic Street Scenarios in a
Frenet Frame." *2010 IEEE International Conference on Robotics and
Automation*, 987--93. <https://doi.org/10.1109/ROBOT.2010.5509799>.
:::

::: {#ref-yangbo2023ped .csl-entry}
Yang, Bo, Song Yan, Zheng Wang, and Kimihiko Nakano. 2023. "Prediction
Based Trajectory Planning for Safe Interactions Between Autonomous
Vehicles and Moving Pedestrians in Shared Spaces." *IEEE Transactions on
Intelligent Transportation Systems* 24 (10): 10513--24.
<https://doi.org/10.1109/TITS.2023.3281157>.
:::

::: {#ref-yang2021_ia_planner .csl-entry}
Yang, Xiaoyu, and Huiyun Li. 2021. *IA Planner: Motion Planning Using
Instantaneous Analysis for Autonomous Vehicle in the Dense Dynamic
Scenarios on Highways*. <https://arxiv.org/abs/2103.10909>.
:::

::: {#ref-yoon2024stcorridor .csl-entry}
Yoon, Youngmin, Changhee Kim, Heeseong Lee, Dabin Seo, and Kyongsu Yi.
2024. "Spatio-Temporal Corridor-Based Motion Planning of Lane Change
Maneuver for Autonomous Driving in Multi-Vehicle Traffic." *IEEE
Transactions on Intelligent Transportation Systems* 25 (10): 13163--83.
<https://doi.org/10.1109/TITS.2024.3388380>.
:::

::: {#ref-zhou2021pathqp .csl-entry}
Zhang, Yajia, Hongyi Sun, Jinyun Zhou, Jiacheng Pan, Jiangtao Hu, and
Jinghao Miao. 2020. "Optimal Vehicle Path Planning Using Quadratic
Optimization for Baidu Apollo Open Platform." *2020 IEEE Intelligent
Vehicles Symposium (IV)*, 978--84.
<https://doi.org/10.1109/IV47402.2020.9304787>.
:::

::: {#ref-zhang2023_dp_rcg .csl-entry}
Zhang, Ziyu, Chunyan Wang, Wanzhong Zhao, Mingchun Cao, Jinqiang Liu,
and Kunhao Xu. 2023. "Path-Speed Decoupling Planning Method Based on
Risk Cooperative Game for Intelligent Vehicles." *IEEE Transactions on
Transportation Electrification*, ahead of print.
<https://doi.org/10.1109/TTE.2023.3316124>.
:::

::: {#ref-zhou2021dliaps .csl-entry}
Zhou, Jinyun, Runxin He, Yu Wang, et al. 2021. "Autonomous Driving
Trajectory Optimization with Dual-Loop Iterative Anchoring Path
Smoothing and Piecewise-Jerk Speed Optimization." *IEEE Robotics and
Automation Letters* 6 (2): 439--46.
<https://doi.org/10.1109/LRA.2020.3045925>.
:::
:::::::::::::::::::::::::::::
