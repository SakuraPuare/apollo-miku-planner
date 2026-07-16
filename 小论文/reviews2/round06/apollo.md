# 第二战役 Round06 — Apollo 工程审（审 v15）

专项：§3.1 对 Apollo 现状描述的代码事实复核。

## P0

无。

## major

无。

## minor

无。

## 确认项

- GetBufferBetweenADCCenterAndEdge 统一裕度、obstacle_lat_buffer 额外缓冲、nudge 0.5\,m/s 速度阈值二分、static/nonstatic 双参数 0.3/0.4\,m 走不同代码路径——四项声明与第一战役代码核实结论一致，无漂移。
- $T_{max}{=}7.0$\,s "与 Apollo ST 图时间视野一致"与 §3.3 速度阶段 7\,s 视野声明相互印证。
- M5-1 修复后消融失效场景编号（P1/P2/P4/P3）与场景表一致，工程叙事链闭合。

SCORE: P0=0 major=0 minor=0
