# 二区稿 Lean 证明

`Paper2.lean` 对论文声明的五元素有限空间--时间候选域建立可重复证书：所有候选均
已评估，返回候选为该有限域中的最小目标，认证下界与 incumbent 相等，绝对 gap 为零。

运行：

```bash
cd lean_proofs/MIKUProofs
lake env lean ../../小论文-2/lean/Paper2.lean
```

该证书不外推到连续空间、Python heap/beam 截断、浮点求解器或 Apollo/CyberRT 全栈。
有限搜索的通用契约见 `lean_proofs/MIKUProofs/FiniteSearch.lean` 与 `Certificates.lean`。
