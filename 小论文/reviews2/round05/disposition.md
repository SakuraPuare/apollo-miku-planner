# Round05 处置单（v14 → v15）

| 编号 | 级别 | 处置 | 落点 |
|---|---|---|---|
| T5-1 | minor | 修复：误差量级句 $\Delta t$ 改 $T_c$ 并行内定义 $T_c$/$a_{\max}$，消除与速度 QP 离散步长 $\Delta t$ 的一符两用 | §3.3 |
| M5-1 | minor | 修复：消融失效事实链三处补场景编号并与表 tab:exp_scenarios 构型名对齐（P1/P2、P4 维修封闭加借道、P3 窄路双侧交通锥） | §4.4 |

## 编译验证

- v15.tex：16 页，overfull=0，exit=0。

→ 产出 v15.tex，round06 审 v15。
