# 第二战役 Round03 — 规划算法理论审（审 v12）

专项：记号封闭性全文扫描（每个数学符号首次出现处是否有定义）。

## P0

无。

## major

无。（A3-1 由工程审提出，理论侧确认：重叠判定按邻近阈值外扩等价于对膨胀区间求连通分量，分组单调变粗，包络下界性质与引理、定理结论均不受影响，修复不引入理论破绽。）

## minor

- **T3-1**（§2 式 eq:prob_union）：$\bar{O}_i=\bigcup_{t\in[0,T]}O_i(t)$ 中 $T$ 无定义，且命题 prop:decoupled_infeasible 用 $T_{\text{pred}}$ 表示同一预测时域，一物二符。**修复**：统一为 $T_{\text{pred}}$，在 §2 首次出现处给出"预测时域"定义，命题处自然衔接。

## 确认项

- $\hat{W}(C_j)$ 定义已补（round02 T2-1），本轮全文符号扫描再无悬空记号：$\delta_i,\Theta_i,u_i,v_i,g_p,U_p,V_p,V_p(s),\tau(s),\mathcal{T},s_j^{ub,\mathrm{SBD}},\kappa_{\max},d_{cluster},\mathcal{B}_W(s)$ 均在首次出现处或紧邻处定义。
- 伪代码引用 eq:time_varying_gap（round02 T2-2）后，算法行与 §3.2/§3.3 的公式链一致。
- $2^n$（全局）与 $2^k$（单分量）的口径区分句保留，与 §1 贡献句、§3.5 复杂度段三处一致。

SCORE: P0=0 major=0 minor=1
