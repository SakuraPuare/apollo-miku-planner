# CommonRoad 跨道路族留出审计

更新时间：2026-09-06

## Protocol

Peachtree 与 Lankershim 使用相同的官方 CommonRoad reader、RoutePlanner reference path、
station-varying lanelet polygon cross-section、矩形状态占用包络、MIKU/B0、BMW-320i
`InputState`、solution writer 和官方 evaluator。Peachtree 不参与 Lankershim 调参，作为
第二道路族的留出审计集。

```text
uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_miku_native.py --family peachtree --steps 100 \
  --output 小论文-2/generated/commonroad_miku_native_peachtree_results.json

uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_reactive.py --family peachtree --steps 100 \
  --output 小论文-2/generated/commonroad_reactive_peachtree_results.json
```

## Results

| protocol | scenarios | valid | planner failure | evaluator-invalid |
|---|---:|---:|---:|---:|
| MIKU native | 4 | 1 | 3 | 0 |
| B0 native | 4 | 1 | 2 | 1 |
| Reactive Planner | 4 | 0 | 1 | 3 |

该留出集证明适配器和官方输出协议可以迁移到不同 NGSIM 道路族，但不证明 MIKU 相对 B0
的性能优越性；MIKU 与 B0 均只有 1/4 valid。失败行保留在 JSON，不能被删除或转化为
兼容成功。该结果也说明当前“二区泛化”目标仍未完成，需要更多道路族和完整车辆可达性
约束。
