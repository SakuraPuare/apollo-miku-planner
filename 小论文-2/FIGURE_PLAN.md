# 图形计划（以审稿问题为入口）

当前二区稿已接入框架图、证据 dashboard、失败轨迹诊断和联合搜索压力图；下表同时标出已完成图形与仍属投稿前增强项。所有实验图必须由 CSV/JSON 生成，不手工改柱高或轨迹。

| 图 | 回答的审稿问题 | 数据/图源 | 一眼结论 | 位置/状态 |
|---|---|---|---|---|
| Teaser：同场景路径—速度失配 | 为什么时间盲解耦会丢解？ | `generated/failure_cases.csv` + `generate_failure_case_figure.py` 轨迹重放 | B0 固定空间侧导致停车，MIKU 保留可行时空带并选择 `pass-before` | 引言首页；`generated/teaser.pdf` 已生成并接入两稿 |
| 平台无关算法主链 | 哪些是 MIKU，哪些是求解器？ | `fig_q34_miku_framework.tex`；代码 `joint_homotopy_search.py` | 候选、证书和 QP 的数据流分开 | 方法首图；已生成并接入两稿 |
| 连续分割图 | $2^k$ 如何化为 $k+1$？ | 由 `miku_geometry.py` 真实区间生成 TikZ | 端部/中间间隙与排序前缀最大值 | 理论小节；源文件已有，正文以定理/算法和 oracle 测试为主，独立图仍为增强项 |
| 时间窗/ST 图 | before、after、intermediate 如何编译？ | `miku_time.py` 和端点单测 | 先/后通过的端点约束方向正确 | 方法时间小节；公式、端点测试和算法流程已接入，独立示意图仍为增强项 |
| 证书搜索树 | 为什么不是固定 beam？ | 新搜索返回的节点、LB/UB、gap JSON | 可终止、预算截断有 gap，不再暗示全局最优 | 压力规模图已接入；详细搜索树图仍为增强项 |
| 典型轨迹对比 | MIKU 的收益来自哪类困难？ | 固定种子失败样本与主实验 CSV | 延迟横穿、含噪降级显示 SL/ST/安全边界 | 两案例失败图已生成并接入；覆盖七类的完整轨迹对比仍为增强项 |
| 分族成功率 + 95% CI | 总体提升是否由单一族驱动？ | `paired_statistics.csv` 分层 bootstrap | 窄路驱动主要收益，切入/含噪存在负效应 | 四联证据图(a)；已生成并接入两稿 |
| 运行时间 ECDF | P95 是否被少量尾部掩盖？ | `randomized_raw.csv` 每次运行 runtime 列 | B2 的完整分布显示更长尾部 | 四联证据图(b)；已生成并接入两稿 |
| 消融效应 forest plot | 模块是否有独立作用？ | `randomized_ablation_paired.csv` | 点估计与 CI 显示 A1/A2/A7 近零及 A6 负效应 | 四联证据图(c)；已生成并接入两稿 |
| 失败构成/连续安全 | 何时失效，降级是否安全？ | `generate_failure_case_figure.py` 重放 `delayed_crossing/9` 与 `prediction_noise/18` | 延迟横穿展示 `pass_before` 可达性；含噪样本展示碰撞与 fail-closed 停车的边界 | `generated/failure_case_qualitative.pdf` 已生成并接入；明确为算法级仿真诊断 |

## 视觉验收

- 字体、单位、图例和色盲配色在双栏缩放下可读。
- 图中数值必须来自运行产物；源文件注释记录 CSV/JSON 路径和 commit。
- 不把示意图当实验结果；不把 Python 原型轨迹标成真实 Apollo/CyberRT。
- 失败图至少标出碰撞时刻、障碍物、同伦标签、QP 状态和是否触发降级。
