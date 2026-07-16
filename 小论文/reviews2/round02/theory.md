# 第二战役 Round02 — 规划算法理论审（审 v11）

复核 round01 修复，并对算法伪代码与记号封闭性做第二遍专项。

## P0

无。

## major

无。round01 两处 major 修复确认：$V_p(s)$ 时变定义已在式 eq:time_varying_gap 后补全（grep 计 1）；引理引入句已显式给出单截面目标。

## minor

- **T2-1**（§3.2 式 eq:global_width 前后）：$\hat{W}(C_j)$ 未显式定义，仅能从前句"保守包络…取所有 $u_i$ 的最小值与所有 $v_i$ 的最大值"推断为分量包络宽度。**修复**：式前补"记分量 $C_j$ 的包络宽度为 $\hat{W}(C_j)$"半句。
- **T2-2**（算法 alg:miku 第 8 行）：组内间隙计算引用静态定义式 eq:gap_def，但伪代码位于逐 $s$ 循环内、使用的是时变边界 $u_i(s)$，更准确的引用是时变式 eq:time_varying_gap。v9 同病，第一战役未发现。**修复**：改引 eq:time_varying_gap。
- **T2-3**（§2 形式化段）：Overfull 7.7pt，由行内式 $l^{+}(\mathbf{d}) = \min\big(\cdot\big)$ 的 \big 定界符加宽导致断行点不足。**修复**：该段两处 \big 改普通括号，语义不变。

## 确认项

- 命题 2.1 证明要点的 $\kappa_{\max}$ 衔接句已恢复，恢复侧声明范围（横向通行性 + 曲率允许时对应运动学可行轨迹）与 v9 等价。
- §3.4 凸性表述收敛为指回 §3.3 后，命题 prop:feasibility_recovery 的前提链（几何条件 + 盒内可行解存在 + $s_j^{ub}\geq s_j^{lb}$）完整无损。
- 复杂度链 $O(k\log k)$ / $O(n\log n+K)$ / 密度有界前提 / 最坏 $O(n^2)$ 在 §3.2、§3.5、§4.3 三处口径一致。

SCORE: P0=0 major=0 minor=3
