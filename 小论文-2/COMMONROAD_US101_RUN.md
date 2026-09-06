# CommonRoad US101 lanelet-goal 留出审计

更新时间：2026-09-06

US101 场景使用 CommonRoad 官方 `goalState/position/lanelet ref`，不是 point 或 rectangle。
adapter 现在将目标 lanelet 的左右边界投影为 goal station/lateral 区间，并用同一官方
reader、reference path、BMW-320i KS solution writer 和 evaluator 运行。

```text
uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_miku_native.py --family us101 --steps 100 \
  --output 小论文-2/generated/commonroad_miku_native_us101_results.json

uv run --no-project --python 3.11 --with commonroad-reactive-planner \
  python 可视化/run_commonroad_reactive.py --family us101 --steps 100 \
  --output 小论文-2/generated/commonroad_reactive_us101_results.json
```

| protocol | scenarios | valid | planner failure | evaluator-invalid |
|---|---:|---:|---:|---:|
| MIKU native | 4 | 2 | 1 | 1 |
| B0 native | 4 | 2 | 1 | 1 |
| Reactive Planner | 4 | 0 | 1 | 3 |

US101 证明 lanelet-form goal 的读取、区间编译和官方输出链路可运行；MIKU 与 B0 仍同为
2/4，因此这不是性能优胜证据。失败结果完整保留在 generated JSON 中。
