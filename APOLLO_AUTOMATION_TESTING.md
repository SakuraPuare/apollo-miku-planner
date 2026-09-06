# Apollo Planning 自动化测试规范

## 定位

Dreamview 点选运行、Apollo 运行回放和批量自动化回归都是同一条 Apollo
Planning/CyberRT 链路。网页操作适合场景选择和可视化验收，固定输入的自动化入口
适合批量回归；两者不构成算法、平台或数据语义差异。

自动化入口直接编译、调用 Apollo 源码中的 Planning 核心模块，由项目入口固定场景、
车辆状态、参考线、障碍物预测、动力学参数和规划配置，然后自动采集 Apollo 链路输出。
这与算法比赛固定输入输出接口的测试原则相同。

## 测试层级

### L1：Apollo 源码模块回归

使用最小 protobuf 或等价规划 fixture，覆盖几何边界、障碍物投影、时间窗、QP 边界和
失败降级。输出使用 golden 文件比较，并声明浮点容差。

### L2：Apollo Planning 批量回放

使用固定的 Apollo 官方场景、官方车辆动力学参数和记录的规划状态，按 Planning 周期
批量回放，检查轨迹、约束、状态码、降级原因和分阶段耗时。论文表格和消融实验默认
来自这一层。

### L3：Apollo/CyberRT 在环

通过 Cyber channel、组件配置和实际消息序列运行 Planning，保存输入输出、组件日志
和 Dreamview 可视化记录。Dreamview 点选只是触发/观察方式，不是唯一回归入口。

### L4：Apollo closed-loop

在 Apollo 官方场景集和官方车辆动力学模型下运行完整闭环，记录规划、控制、车辆状态、
碰撞/越界事件和终止原因。论文引用的每组结果必须具备场景、配置、提交和原始输出索引。

## 等价性验收

自动化入口合格需同时满足：

- 核心调用点来自固定 Apollo 源码提交，Apollo 修改补丁可追踪；
- 输入消息字段、单位、时间戳和车辆参数与在环链路一致；
- 相同 fixture 在批量回放与 Dreamview/CyberRT 在环模式下的关键轨迹、边界和状态码，
  在预先声明的容差内一致；
- 异常、超时和 fallback 状态码保持一致；
- 批量运行只改变操作方式，不改变 Apollo 算法、消息语义或动力学模型；
- 每个结果都能反查到场景、配置、源码提交、入口提交和原始输出。

如果入口替换 Apollo 核心算法、改变消息/动力学语义，或只保留近似数学模型，才必须
另标为等价复现；是否通过 Dreamview 点击不影响这一判断。

## 数据命名

- L3/L4 由 Apollo/CyberRT runtime 直接产生：Apollo runtime 运行数据。
- L1/L2 直接调用 Apollo 源码核心模块产生：Apollo Planning 算法数据或 Apollo
  Planning 自动化回归数据。
- 只有替换核心逻辑或语义后生成：Apollo-compatible/等价复现数据。

“Apollo 官方 benchmark/官方统计”只用于 Apollo 官方发布文件或确实由官方发布链路
提供的数据；自有实验数据按上述 Apollo Planning 数据标签报告，不因为使用自动化入口
而降级，也不因为使用 Apollo 源码而冒充官方发布统计。
