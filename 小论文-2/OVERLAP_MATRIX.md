# 两稿重合矩阵与投稿伦理说明

## 文件边界

- `小论文/` 是导师要求停止技术修改的旧稿；本次只读审计，未纳入本轮技术提交。
- `小论文-2/` 是升级稿；允许算法、代码、实验、图表和中英文稿修改。

## 重合审计

采用去除 LaTeX 命令、数字和停用词后的 token 计数，并辅以段落/公式主题人工核对。结果不是抄袭判定，而是投稿冲突预警：

| 比较 | 统计结果 | 主题重合 | 伦理含义 |
|---|---:|---|---|
| `小论文/main.tex` vs `小论文-2/submission_body.tex` | 550 个共享规范化 token；余弦式重合约 0.267 | PVD/Apollo、威胁裕度、最大间隙、ST 走廊、相同实验族 | 若二区稿只改写旧稿，不能同时投稿 |
| `小论文/main.tex` vs `小论文-2/submission_body_en.tex` | 591 个共享规范化 token；余弦式重合约 0.180 | 数学对象、基线命名、场景和结果叙事 | 英文稿必须声明继承关系，不得伪装独立工作 |
| `小论文-2/submission_body.tex` vs `submission_body_en.tex` | 605 个共享规范化 token；余弦式重合约 0.330 | 中英文同一算法与数据 | 这是必要的一稿双语一致性，不是两篇独立投稿 |

## 结论

二区稿当前仍继承旧稿的问题定义、Apollo 风格求解主干、部分图形和场景生成器。只有在路线 A 的联合证书搜索、连续安全验证、外部 benchmark 和新数据全部完成后，才能把两稿区分为“不同研究问题/不同证据包”；否则应视为同一研究的扩展版，不能并行投稿。任何投稿都必须在 cover letter 中如实披露旧稿及其技术关系，遵守期刊关于重复投稿、扩展稿和自引的规定。

## 可复核命令

```bash
git diff -- 小论文
python - <<'PY'
from pathlib import Path
import re
def norm(p):
    t=Path(p).read_text(errors='ignore').lower()
    t=re.sub(r'%.*','',t); t=re.sub(r'\\[a-zA-Z]+',' ',t)
    return set(re.findall(r'[a-z0-9_\u4e00-\u9fff]+',t))
for a,b in [('小论文/main.tex','小论文-2/submission_body.tex'),('小论文/main.tex','小论文-2/submission_body_en.tex')]:
    print(a,b,len(norm(a)&norm(b)))
PY
```
