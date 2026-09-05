# MIKU 高水平期刊投稿准备度

本记录用于把当前成果直接推向 IEEE T-IV、IEEE T-ITS 或 IEEE RA-L，不是论文正文中的自我限定。

## 当前已完成

- 完整方法主线（研究原型）：鲁棒动态占据、连续分割定理、有限域联合惰性搜索、因果时间同伦图、双向 ST 走廊、连续扫掠证书、按需交替细化和滚动语义承诺。
- 已验证的理论闭环包括固定区间模型的 $2^k$ 至 $k+1$ 连续分割、给定分层图的 K-best、固定同伦凸性，以及声明运动/误差条件下的连续扫掠与有限域下界证书。它们不外推为任意车辆模型、连续全局最优或递归可行性证明。
- 配对实验证据：700 场景主实验、5,600 次规划的随机消融、70 对联合时空参照、700 对滚动重规划和 80 条灵敏度轨迹。
- 证据链：生成宏自动注入数值，原始 CSV/JSON、配对 bootstrap、精确 McNemar 检验、oracle 单测、联合搜索证书和主张追踪表均已纳入仓库。
- 稿件：中文完整稿 `main.tex`（10 页）与 IEEE 双栏英文稿 `main_ieee.tex`（9 页）。

## 目标期刊格式

| 期刊 | 当前适配 | 投稿前动作 |
|---|---|---|
| IEEE RA-L | 当前英文稿 9 页，尚未满足 6 页基础限额 | 先压缩至 6 页，再切换双匿名、删除可识别信息并准备补充视频 |
| IEEE T-IV | 方法、理论和系统级实验符合常规论文叙事 | 依期刊模板完成单匿名作者信息；可利用 10 页建议篇幅扩展公开基准实验 |
| IEEE T-ITS | 交互式规划、计算实时性和安全实验与范围匹配 | 按 Regular Paper 整理为不超过 10 页；扩展与公开规划器的外部对比 |

## 投稿决策

当前版本已达到**可投稿的二区候选稿**门槛；裁判结论为 Accept for submission after final mechanical checks。有限域认证目标已与 path/speed QP 的完整二次项统一，分支下界改为已求解 path-QP 值并完成新一轮主实验、消融、滚动、联合参照和 PDF 重建；Apollo Planning 源码与 CyberRT/Dreamview 运行资产已登记，且正文已明确系统证据边界。CommonRoad 官方竞品 runner、标准 solution 和 evaluator 已完成四场景正式覆盖，结果为 2 个 valid solution、2 个 planner failure；MIKU 的原生输出边界调用官方 planning problem、KSState、solution writer 和 evaluator，四个场景的 4 次 planner failure 原样保留，输入消费官方路线/目标和逐状态矩形形状姿态占用包络，因此只称为 scoped compatibility benchmark，不扩写为一般 leaderboard 性能。Apollo 逐场景 runtime 映射保留为非主张性诊断项，RA-L 六页限制只在选择 RA-L 时生效。

当前 HEAD 可用 `uv run python 小论文-2/check_submission_gates.py` 重复得到
`accept`。按 T-IV/T-ITS Regular Paper 路线，当前 9 页英文稿已满足 10 页建议篇幅；
若选择 RA-L 仍需六页压缩。

## 最后提交顺序

1. 首投选择 IEEE T-IV 或 T-ITS Regular Paper；当前 9 页 IEEE 稿已落在 10 页路线内，
   不要先按 RA-L 六页规则重写。
2. 原生 solution/evaluator 边界已经完成；下一步是把 planner 输入从受限 Frenet adapter
   升级为保持 lanelet、occupancy 和 planning-rule 语义的转换，并在同一 planning
   problem、vehicle model、dt、horizon 和 evaluator 下扩大公开场景。若真实结果仍为
   规划失败，保留失败，不能用 adapter 数字替代 benchmark。
3. 补齐 Apollo fixture 到 CyberRT/Dreamview runtime 输出的逐场景映射；若无法补齐，
   将平台结论限定为已登记的源码/资产/历史在环证据，不把算法级耗时写成新的 native
   runtime benchmark。
4. 两项证据完成后再做一次敌意复审、英文校对、引文核验、匿名/cover letter 和 artifact
   归档；在此之前继续改标题或堆图不会改变 gate 的 `major_revision`。
