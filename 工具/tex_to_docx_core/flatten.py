from __future__ import annotations

import re
import sys
from pathlib import Path

from .config import (
    BODY_CHAPTERS,
    MACRO_SOURCES,
    POST_CHAPTERS,
    REFS_ANCHOR_TEXT,
    SVG_DIR,
    THESIS_DIR,
)

# =============================================================================
# Stage 1 — flatten
# =============================================================================

_NEWCMD_RE = re.compile(
    r"\\newcommand\{\\(?P<name>[A-Za-z]+)\}(?:\[\d+\])?\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}"
)


def load_newcommands(tex_text: str) -> dict[str, str]:
    """抽取形如 \\newcommand{\\Xxx}{yyy} 的无参宏。"""
    return {m.group("name"): m.group("body") for m in _NEWCMD_RE.finditer(tex_text)}


def expand_macros(text: str, macros: dict[str, str]) -> str:
    """多轮迭代替换直到稳定。支持 \\Name / \\Name{} 两种形式。"""
    for _ in range(6):
        new_text = text
        for name, value in macros.items():
            # \Name{}（吃掉空大括号）或 \Name（右边界非字母）
            new_text = re.sub(
                rf"\\{name}(?:\{{\}}|(?![A-Za-z]))",
                lambda _m, v=value: v,
                new_text,
            )
        if new_text == text:
            break
        text = new_text
    return text


def remove_environments(text: str, envs: list[str]) -> str:
    for env in envs:
        text = re.sub(
            rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}",
            "",
            text,
            flags=re.DOTALL,
        )
    return text


def strip_figure_inputs_and_adjustbox(text: str) -> str:
    """剥掉 \\adjustbox / \\resizebox 包裹保留 INNER；不再删 figure 块（图会走 svg 嵌入）。

    pandoc 的 LaTeX reader 不认 \\resizebox{w}{h}{INNER}，会把整块（包括 tabular）
    整个吞掉，表格从 docx 里彻底消失。因此必须在 flatten 阶段把 wrapper 脱掉，
    让 pandoc 直接看到里面的 tabular。
    """
    text = re.sub(
        r"\\adjustbox\{[^{}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}",
        r"\1",
        text,
    )
    text = _strip_wrapper_keep_inner(text, r"\\resizebox", num_size_args=2)
    # \scalebox{factor}{INNER} 同理
    text = _strip_wrapper_keep_inner(text, r"\\scalebox", num_size_args=1)
    return text


def _strip_wrapper_keep_inner(text: str, cmd_regex: str, num_size_args: int) -> str:
    """通用：把 \\cmd{arg1}...{argN}{INNER} 替换为 INNER（平衡花括号匹配，允许嵌套）。

    num_size_args 是 INNER 前面的尺寸/参数组数（\\resizebox=2, \\scalebox=1）。
    """
    out: list[str] = []
    i = 0
    pat = re.compile(cmd_regex)
    while i < len(text):
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        j = m.end()
        # 先跳过 num_size_args 组 {...}
        ok = True
        for _ in range(num_size_args):
            while j < len(text) and text[j] in " \t\n":
                j += 1
            if j >= len(text) or text[j] != "{":
                ok = False
                break
            depth = 1
            j += 1
            while j < len(text) and depth > 0:
                c = text[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                j += 1
        if not ok:
            # 匹配失败：保留原始 cmd 文本，避免破坏其他语义
            out.append(text[m.start() : j])
            i = j
            continue
        # 再读 INNER {...}
        while j < len(text) and text[j] in " \t\n":
            j += 1
        if j >= len(text) or text[j] != "{":
            out.append(text[m.start() : j])
            i = j
            continue
        inner_start = j + 1
        depth = 1
        j = inner_start
        while j < len(text) and depth > 0:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        inner_end = j - 1  # 去掉闭合的 }
        out.append(text[inner_start:inner_end])
        i = j
    return "".join(out)


def rewrite_figure_inputs(text: str, missing: list[str]) -> str:
    """把 figure 里的 \\input{../图片/fig_NAME} 替换为 \\includegraphics{绝对路径.svg}。
    没有对应 svg 的图名写入 missing 列表，原 \\input 留占位注释。

    例外颗粒度：如果 \\input 目标的 .tex 文件以 \\begin{tabular}（或其它非图环境）开头，
    说明这是纯表格数据片段（如 ../图片/data/ablation/score_table.tex 在 table 环境里被
    \\input 当表体），不是图——把 \\input 的相对路径改写成绝对路径，让 pandoc 在临时目录
    里也能 resolve 到并原样展开 tabular，避免误判成"图缺失"。
    """

    def _target_tex(raw_path: str):
        """把 \\input 的 LaTeX 路径解析成磁盘上的 .tex 文件路径（相对基准为 THESIS_DIR）。"""
        from pathlib import Path as _P

        if raw_path.endswith(".tex"):
            rel = _P(raw_path)
        else:
            rel = _P(raw_path + ".tex")
        if rel.is_absolute():
            return rel
        return (THESIS_DIR / rel).resolve()

    def _is_tabular_data(raw_path: str) -> bool:
        try:
            p = _target_tex(raw_path)
            if not p.exists():
                return False
            # 读前 512 字节找 \begin{tabular}，足够覆盖一行注释 + 开始环境
            head = p.read_text(encoding="utf-8", errors="ignore")[:512]
        except OSError:
            return False
        return bool(re.search(r"\\begin\{tabular\}", head))

    def _replace(m: re.Match[str]) -> str:
        raw_path = m.group(1).strip()
        # 非图、非宏（例如 _experiment_metrics.tex）保持原样
        if "图片" not in raw_path and "fig_" not in raw_path:
            return m.group(0)
        # 数据表 tabular：改写成绝对路径让 pandoc 自己 resolve，别走 SVG 替换
        if _is_tabular_data(raw_path):
            abs_path = _target_tex(raw_path)
            # 去掉 .tex 后缀符合 LaTeX \input 惯例
            abs_str = str(abs_path.with_suffix(""))
            return f"\\input{{{abs_str}}}"
        name = raw_path.split("/")[-1]
        svg = SVG_DIR / f"{name}.svg"
        if not svg.exists():
            missing.append(name)
            return f"\\textit{{[图缺失: {name}]}}"
        return f"\\includegraphics[width=0.8\\textwidth]{{{svg.as_posix()}}}"

    return re.sub(r"\\input\{([^}]+)\}", _replace, text)


def strip_figure_labels_and_refs(text: str) -> str:
    """figure 块里的 \\label{fig:xxx} 剥掉（pandoc 的 label 处理与 docx 不同步）。"""
    text = re.sub(r"\\label\{[^}]+\}", "", text)
    return text


def _extract_first_caption_star(block: str) -> tuple[str, str | None]:
    """抽取 figure/table 块里第一个 \\caption*{...} 的内容（平衡括号）。

    pandoc 把 figure 环境内的多个 caption 折成最后一个，`\\caption*` 会覆盖
    正式的 \\caption{...}，导致 docx 里图题丢失只剩副注。把副注从环境内抽走，
    挪到 \\end{figure}/\\end{table} 之后作独立段落，pandoc 即可正确识别主图题。

    返回 (去掉后的 block, 抽出的副注内容 or None)。
    """
    m = re.search(r"\\caption\*\s*\{", block)
    if not m:
        return block, None
    start = m.start()
    content_start = m.end()
    depth = 1
    i = content_start
    while i < len(block):
        c = block[i]
        if c == "\\" and i + 1 < len(block):
            i += 2  # 跳过 \{ \} \scriptsize 等转义/命令，不计入花括号深度
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                content = block[content_start:i]
                new_block = block[:start] + block[i + 1 :]
                return new_block, content
        i += 1
    return block, None


# 学校格式检测器不认多 cell 子图表格，figure 块里的所有 subfigure 整体替换为单张
# fig_merged_<label>.svg（由 图片/fig_merged_*.tex 经 svg 流水线生成，内部已含子图小标）。
def _collapse_subfigures_to_merged(block: str) -> str:
    """把 figure 块里所有 \\begin{subfigure}...\\end{subfigure} 整体替换为单个
    `\\includegraphics{SVG_DIR/fig_merged_<label>.svg}`。

    父 \\caption{...} 和父 \\label{fig:xxx} 保留；子 caption/子 label 随 subfigure 块一起丢弃。
    直接输出 includegraphics 而非 \\input 是因为本函数在 rewrite_figure_inputs 之后调用，
    再走 \\input 就 miss 掉 SVG 替换环节。"""
    if r"\begin{subfigure}" not in block:
        return block
    # 屏蔽 subfigure 块后再找父 label，避免命中子图里残留的 label
    masked = re.sub(
        r"\\begin\{subfigure\}.*?\\end\{subfigure\}",
        "",
        block,
        flags=re.DOTALL,
    )
    lab_m = re.search(r"\\label\{(fig:[^}]+)\}", masked)
    if not lab_m:
        return block  # 没有父 label，不替换
    merged_name = "fig_merged_" + lab_m.group(1)[len("fig:") :]
    svg_path = SVG_DIR / f"{merged_name}.svg"
    if not svg_path.exists():
        # merged svg 未生成，保留原 subfigure 结构（pandoc 会兜底渲成多 cell 表）
        return block

    # 删所有 subfigure 块
    new_block = re.sub(
        r"\\begin\{subfigure\}.*?\\end\{subfigure\}",
        "",
        block,
        flags=re.DOTALL,
    )
    # 清连接符（\hfill / \hspace{...} / \vspace{...}）和由此产生的孤立空行
    new_block = re.sub(r"\\hfill\b", "", new_block)
    new_block = re.sub(r"\\hspace\{[^}]*\}", "", new_block)
    new_block = re.sub(r"\\vspace\{[^}]*\}", "", new_block)
    new_block = re.sub(r"\n\s*\n\s*\n+", "\n\n", new_block)

    # 在 \begin{figure}[...]\centering 之后插入 \includegraphics
    insert_pat = re.compile(
        r"(\\begin\{figure\}(?:\[[^\]]*\])?\s*)(\\centering\s*)?",
        flags=re.DOTALL,
    )
    insert_m = insert_pat.search(new_block)
    if not insert_m:
        return block  # 结构异常，保守回退
    idx = insert_m.end()
    injected = (
        f"\\includegraphics[width=0.8\\textwidth]{{{svg_path.as_posix()}}}\n"
    )
    if insert_m.group(2) is None:
        injected = "\\centering\n" + injected
    return new_block[:idx] + injected + new_block[idx:]


def _prefix_outermost_caption(block: str, prefix: str) -> str:
    """在 figure/table 块里给最外层 \\caption{...} 前加编号前缀。
    屏蔽 subfigure 子块，避免命中子图 caption。"""
    sub_blocks: list[str] = []

    def _store(m: re.Match[str]) -> str:
        sub_blocks.append(m.group(0))
        return f"\x00SUB{len(sub_blocks) - 1}\x00"

    masked = re.sub(
        r"\\begin\{subfigure\}.*?\\end\{subfigure\}",
        _store,
        block,
        flags=re.DOTALL,
    )

    def _prefix_it(m: re.Match[str]) -> str:
        return f"\\caption{{{prefix}{m.group(1)}}}"

    masked = re.sub(
        r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}",
        _prefix_it,
        masked,
        count=1,
    )
    for i, b in enumerate(sub_blocks):
        masked = masked.replace(f"\x00SUB{i}\x00", b)
    return masked


def number_figures_and_tables(body: str) -> tuple[str, dict[str, str]]:
    """按章序号给 figure/table/equation/lemma/theorem/algorithm 打编号，
    改写 figure/table 的 caption，收集所有 \\label{X} → 编号字符串 的映射供 resolve_refs 用。
    """
    labels: dict[str, str] = {}
    state = {
        "chap": 0,
        "sec": 0,
        "fig": 0,
        "tab": 0,
        "eq": 0,
        "lem": 0,
        "thm": 0,
        "alg": 0,
        "lst": 0,
    }

    # (env_name, state_key, label_prefix, env_regex, caption_prefix_tmpl)
    # equation/align/gather/multline 族共享 eq 计数；lstlisting 的 label 在可选参数里，单独处理
    block_envs = [
        ("figure", "fig", "fig", r"\\begin\{figure\}.*?\\end\{figure\}", "图{num} "),
        ("table", "tab", "tab", r"\\begin\{table\}.*?\\end\{table\}", "表{num} "),
        (
            "equation",
            "eq",
            "eq",
            r"\\begin\{equation\*?\}.*?\\end\{equation\*?\}",
            None,
        ),
        ("alignenv", "eq", "eq", r"\\begin\{align\*?\}.*?\\end\{align\*?\}", None),
        ("gatherenv", "eq", "eq", r"\\begin\{gather\*?\}.*?\\end\{gather\*?\}", None),
        ("multenv", "eq", "eq", r"\\begin\{multline\*?\}.*?\\end\{multline\*?\}", None),
        ("lemma", "lem", "lem", r"\\begin\{lemma\}.*?\\end\{lemma\}", None),
        ("theorem", "thm", "thm", r"\\begin\{theorem\}.*?\\end\{theorem\}", None),
        ("algorithm", "alg", "alg", r"\\begin\{algorithm\}.*?\\end\{algorithm\}", "算法{num} "),
        (
            "listing",
            "lst",
            "lst",
            r"\\begin\{lstlisting\}(?:\[[^\]]*\])?.*?\\end\{lstlisting\}",
            None,
        ),
    ]

    parts = [
        r"(?P<chap>\\chapter\s*\{[^}]*\}(?:\s*\\label\{chap:[^}]+\})?)",
        r"(?P<sec>\\(?:section|subsection|subsubsection)\s*\*?\s*\{[^}]*\}(?:\s*\\label\{sec:[^}]+\})?)",
    ]
    for env, _, _, env_re, _ in block_envs:
        parts.append(rf"(?P<{env}>{env_re})")
    pattern = re.compile("|".join(parts), re.DOTALL)

    # 专用：equation 家族单独 pattern，用于扫嵌套在 theorem/lemma/algorithm 里的 eq
    eq_only_pattern = re.compile(
        "|".join(
            rf"(?:{env_re})" for env, key, _, env_re, _ in block_envs if key == "eq"
        ),
        re.DOTALL,
    )

    def _sweep_inner_equations(block: str) -> None:
        """扫块内 equation 族，推进 eq 计数并收录 label。不改文本。"""
        for m in eq_only_pattern.finditer(block):
            state["eq"] += 1
            num = f"{state['chap']}.{state['eq']}"
            _record(m.group(0), "eq", num)

    def _record(block: str, prefix: str, num: str) -> None:
        # 标准 \label{prefix:X}
        for lm in re.finditer(rf"\\label\{{({re.escape(prefix)}:[^}}]+)\}}", block):
            labels[lm.group(1)] = num
        # listings 包可选参数形式：label={lst:X} 或 label=lst:X
        if prefix == "lst":
            for lm in re.finditer(r"label\s*=\s*\{?(lst:[^,\]}\s]+)\}?", block):
                labels[lm.group(1)] = num

    def callback(m: re.Match[str]) -> str:
        if m.group("chap"):
            state["chap"] += 1
            for k in ("sec", "fig", "tab", "eq", "lem", "thm", "alg", "lst"):
                state[k] = 0
            block = m.group(0)
            _record(block, "chap", str(state["chap"]))
            return block
        if m.group("sec"):
            state["sec"] += 1
            block = m.group(0)
            _record(block, "sec", f"{state['chap']}.{state['sec']}")
            return block
        for env, key, prefix, _env_re, cap_tmpl in block_envs:
            g = m.group(env)
            if g is None:
                continue
            # theorem/lemma/algorithm 可能嵌套 equation，先扫内部 eq
            if key in ("lem", "thm", "alg"):
                _sweep_inner_equations(g)
            state[key] += 1
            num = f"{state['chap']}.{state[key]}"
            # 算法/代码 用短横线编号 "N-M"（学校规范），图/表/公式/定理/引理保留 "N.M"
            display_num = num.replace(".", "-", 1) if key in ("alg", "lst") else num
            _record(g, prefix, display_num)
            if cap_tmpl:
                g, star_note = _extract_first_caption_star(g)
                g = _prefix_outermost_caption(g, cap_tmpl.format(num=display_num))
                if env == "figure":
                    g = _collapse_subfigures_to_merged(g)
                if star_note is not None:
                    star_note = re.sub(
                        r"\\(?:scriptsize|footnotesize|small|tiny|normalsize)\s*",
                        "",
                        star_note,
                    ).strip()
                    if star_note:
                        g = g + f"\n\n\\noindent {star_note}\n\n"
                return g
            # listing: 单独从 [caption={...}] 可选参数提取标题，在块前插入"代码 X-Y 标题"段
            if key == "lst":
                cap_match = re.search(r"caption\s*=\s*\{([^}]*)\}", g)
                cap_text = cap_match.group(1) if cap_match else ""
                # 去掉 caption 里的 LaTeX 命令残留
                cap_text = re.sub(
                    r"\\(?:texttt|textbf|textit|emph|mbox)\s*\{([^}]*)\}",
                    r"\1",
                    cap_text,
                )
                cap_text = cap_text.replace("\\_", "_").strip()
                label_line = (
                    f"\n\n\\noindent\\textbf{{代码{display_num} \\ {cap_text}}}\n\n"
                )
                return label_line + g
            return g
        return m.group(0)

    return pattern.sub(callback, body), labels


def resolve_refs(body: str, label_map: dict[str, str]) -> str:
    """\\ref{X} 优先查 label_map 取真实编号；查不到降级 ??。"""

    def _ref(m: re.Match[str]) -> str:
        return label_map.get(m.group(1), "??")

    return re.sub(r"\\(?:ref|eqref|autoref|pageref)\{([^}]+)\}", _ref, body)


# =============================================================================
# algorithm2e → lstlisting（伪代码结构化重写）
# =============================================================================


def _read_braced(s: str, i: int) -> tuple[str, int]:
    """从 s[i]（必须是 '{'）开始读一对平衡大括号，返回 (内部文本, 结束位置+1)。"""
    assert s[i] == "{", f"expected '{{' at {i}, got {s[i]!r}"
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\" and j + 1 < len(s):
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1 : j], j + 1
        j += 1
    raise ValueError(f"unbalanced braces starting at {i}")


def _render_algo_body(body: str, indent: int = 0) -> list[str]:
    """把 algorithm2e 风格的伪代码体递归展开成缩进文本行。

    支持：\\ForEach{A}{B}、\\For{A}{B}、\\While{A}{B}、\\If{C}{T}、
    \\eIf{C}{T}{E}、\\KwIn{...}、\\KwOut{...}、\\KwRet ...、
    \\textcolor{...}{\\textit{// ...}}（注释）、以 \\; 结尾的语句行。
    """
    pad = "  " * indent
    lines: list[str] = []
    i = 0
    n = len(body)

    def _flush_stmt(text: str) -> None:
        text = text.strip()
        if not text:
            return
        # 清理行内残留的 tex 装饰
        text = re.sub(r"\\textit\{([^{}]*)\}", r"\1", text)
        text = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", text)
        text = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", text)
        text = re.sub(r"\s+", " ", text)
        lines.append(pad + text)

    buf: list[str] = []

    while i < n:
        c = body[i]
        # 注释：\textcolor{gray!30!black}{\textit{// ...}}
        m = re.match(
            r"\\textcolor\s*\{[^{}]*\}\s*\{\s*\\textit\s*", body[i:]
        )
        if m:
            # 读内部 \textit{...} 的大括号
            j = i + m.end()
            # 此时 j 指向 \textit 的参数 '{'
            if j < n and body[j] == "{":
                inner, j2 = _read_braced(body, j)
                # 包裹的外层 textcolor 的 '}'
                # body[j2] 应当是 '}'
                if j2 < n and body[j2] == "}":
                    j2 += 1
                # flush 之前累积的语句
                if buf:
                    _flush_stmt("".join(buf))
                    buf = []
                comment = inner.strip()
                # 跳过可能紧跟的 \;
                rest = body[j2:]
                m2 = re.match(r"\s*\\;", rest)
                if m2:
                    j2 += m2.end()
                lines.append(pad + comment)
                i = j2
                continue

        # \KwIn{...} / \KwOut{...}
        m = re.match(r"\\(KwIn|KwOut)\s*", body[i:])
        if m:
            j = i + m.end()
            if j < n and body[j] == "{":
                inner, j2 = _read_braced(body, j)
                if buf:
                    _flush_stmt("".join(buf))
                    buf = []
                kw = "输入：" if m.group(1) == "KwIn" else "输出："
                lines.append(pad + f"\\textbf{{{kw}}}" + inner.strip())
                i = j2
                continue

        # \KwRet ... \;
        m = re.match(r"\\KwRet\s+", body[i:])
        if m:
            j = i + m.end()
            # 读到 \; 或行尾
            end_m = re.search(r"\\;", body[j:])
            if end_m:
                payload = body[j : j + end_m.start()]
                j2 = j + end_m.end()
            else:
                payload = body[j:]
                j2 = n
            if buf:
                _flush_stmt("".join(buf))
                buf = []
            lines.append(pad + "\\textbf{返回} " + payload.strip())
            i = j2
            continue

        # \ForEach{A}{B} / \For{A}{B} / \While{A}{B}
        m = re.match(r"\\(ForEach|For|While)\s*", body[i:])
        if m:
            j = i + m.end()
            if j < n and body[j] == "{":
                head, j = _read_braced(body, j)
                if j < n and body[j] == "{":
                    inner, j2 = _read_braced(body, j)
                    if buf:
                        _flush_stmt("".join(buf))
                        buf = []
                    kw = {"ForEach": "foreach", "For": "for", "While": "while"}[
                        m.group(1)
                    ]
                    head_clean = re.sub(r"\s+", " ", head.strip())
                    lines.append(pad + f"\\textbf{{{kw}}} {head_clean} \\textbf{{do}}")
                    lines.extend(_render_algo_body(inner, indent + 1))
                    lines.append(pad + "\\textbf{end}")
                    i = j2
                    continue

        # \eIf{C}{T}{E}
        m = re.match(r"\\eIf\s*", body[i:])
        if m:
            j = i + m.end()
            if j < n and body[j] == "{":
                cond, j = _read_braced(body, j)
                if j < n and body[j] == "{":
                    tbr, j = _read_braced(body, j)
                    if j < n and body[j] == "{":
                        ebr, j2 = _read_braced(body, j)
                        if buf:
                            _flush_stmt("".join(buf))
                            buf = []
                        cond_clean = re.sub(r"\s+", " ", cond.strip())
                        lines.append(pad + f"\\textbf{{if}} {cond_clean} \\textbf{{then}}")
                        lines.extend(_render_algo_body(tbr, indent + 1))
                        lines.append(pad + "\\textbf{else}")
                        lines.extend(_render_algo_body(ebr, indent + 1))
                        lines.append(pad + "\\textbf{end}")
                        i = j2
                        continue

        # \If{C}{T}
        m = re.match(r"\\If\s*", body[i:])
        if m:
            j = i + m.end()
            if j < n and body[j] == "{":
                cond, j = _read_braced(body, j)
                if j < n and body[j] == "{":
                    tbr, j2 = _read_braced(body, j)
                    if buf:
                        _flush_stmt("".join(buf))
                        buf = []
                    cond_clean = re.sub(r"\s+", " ", cond.strip())
                    lines.append(pad + f"\\textbf{{if}} {cond_clean} \\textbf{{then}}")
                    lines.extend(_render_algo_body(tbr, indent + 1))
                    lines.append(pad + "\\textbf{end}")
                    i = j2
                    continue

        # \; 语句结束
        if body[i : i + 2] == "\\;":
            _flush_stmt("".join(buf))
            buf = []
            i += 2
            continue

        buf.append(c)
        i += 1

    if buf:
        _flush_stmt("".join(buf))

    return lines


def rewrite_algorithms(body: str) -> str:
    """把 \\begin{algorithm} ... \\end{algorithm} 展开成
    "\\noindent\\textbf{算法 X.Y ...}" 标题段 + 每行一段（quote 环境包裹）的伪代码，
    让 pandoc 把行内 ``$...$`` 识别为 inline math 渲染成 OMML 公式。
    缩进用全角空格（U+3000）保留（pandoc 对半角 leading spaces 会吞掉）。

    注意：此函数必须在 number_figures_and_tables 之后调用（此时 caption 已被改写
    为 "算法 X.Y ..." 形式），否则拿不到编号。
    """

    def _one(m: re.Match[str]) -> str:
        block = m.group(0)
        # 抽 caption
        cap_m = re.search(r"\\caption\s*\{([^}]*)\}", block)
        caption = cap_m.group(1).strip() if cap_m else "算法"
        # 抽 body：去掉 \begin/\end、\caption{...}、\label{...}
        inner = re.sub(r"\\begin\{algorithm\}\s*(?:\[[^\]]*\])?", "", block)
        inner = re.sub(r"\\end\{algorithm\}", "", inner)
        inner = re.sub(r"\\caption\s*\{[^}]*\}", "", inner)
        inner = re.sub(r"\\label\s*\{[^}]*\}", "", inner)
        try:
            lines = _render_algo_body(inner)
        except Exception:
            # 解析失败兜底：保留原样
            return block
        # 半角缩进 → 全角空格（每 2 个半角空格 ≈ 1 个全角），让 pandoc 不吞空白
        def _indent_to_cjk(line: str) -> str:
            stripped = line.lstrip(" ")
            nspace = len(line) - len(stripped)
            return "　" * (nspace // 2) + stripped
        body_paragraphs = "\n\n".join(_indent_to_cjk(ln) for ln in lines if ln.strip() or True)
        # 用 quote 环境给算法体一点左缩进样式；内部每行独立段落，
        # pandoc 识别 ``$...$`` 为 inline math → OMML
        return (
            f"\n\n\\noindent\\textbf{{{caption}}}\n\n"
            f"\\begin{{quote}}\n{body_paragraphs}\n\\end{{quote}}\n\n"
        )

    return re.sub(
        r"\\begin\{algorithm\}(?:\[[^\]]*\])?.*?\\end\{algorithm\}",
        _one,
        body,
        flags=re.DOTALL,
    )


def strip_cjk_font_commands(text: str) -> str:
    """剥离摘要块里的 ctexbook 字号/字体命令，pandoc 读的是 article。
    对 {\\heiti\\bfseries XXX} 这种散装重音（摘要里的"摘要："/"关键词："伪标题），
    先把 \\bfseries 转成 \\textbf，再剥 \\heiti / \\zihao 等。
    """
    # 1. {\heiti\bfseries 摘要：xxx} / {\bfseries Abstract: xxx} → \textbf{摘要：xxx}
    text = re.sub(
        r"\{(?:\\(?:heiti|songti|kaishu|fangsong)\s*)*\\bfseries\s+([^{}]+)\}",
        r"\\textbf{\1}",
        text,
    )
    # 2. \zihao{N} 直接删
    text = re.sub(r"\\zihao\{[-\w]+\}", "", text)
    # 3. \heiti / \songti / \kaishu / \bfseries 单独出现时删
    text = re.sub(r"\\(?:heiti|songti|kaishu|fangsong|bfseries)\b\s*", "", text)
    # 4. \setstretch{x} / 页面声明 / aligned 里的 \notag
    text = re.sub(r"\\setstretch\{[^}]*\}", "", text)
    text = re.sub(r"\\notag\b", "", text)
    text = re.sub(
        r"\\(?:thispagestyle|pagestyle|pagenumbering|phantomsection|addcontentsline|clearpage|vspace|hspace|noindent|mainmatter|label)\b(?:\{[^}]*\}){0,3}",
        "",
        text,
    )
    return text


def parse_bib_author_short(bib_path: Path) -> dict[str, str]:
    """解析 references.bib，返回 citekey → 短作者名 的映射。
    规则：
      - 1 作者：中文用全名，英文用姓（LastName）
      - 2 作者：中文 "A、B"，英文 "A and B"
      - 3+ 作者：中文 "A等"，英文 "A et al."
    """
    import re as _re

    text = bib_path.read_text(encoding="utf-8")

    def _balanced_braces(s: str, start: int) -> str:
        """从 s[start]（必须是 '{'）开始，返回平衡括号内的内容（不含最外层 {}）。"""
        assert s[start] == "{"
        depth = 0
        i = start
        while i < len(s):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return s[start + 1 : i]
            i += 1
        return s[start + 1 :]  # 未闭合兜底

    def _strip_latex_accents(s: str) -> str:
        """剥 LaTeX 重音命令：{\\'a} → a, {\\\"o} → o, {\\v{C}} → C 等"""
        # 递归剥 {...} 包裹
        s = _re.sub(r"\{\\['\"`^~=.vuHtcdb]\s*\{?([A-Za-z])\}?\}", r"\1", s)
        s = _re.sub(r"\\['\"`^~=.vuHtcdb]\s*\{?([A-Za-z])\}?", r"\1", s)
        # 剥残余 {}
        s = _re.sub(r"[{}]", "", s)
        return s.strip()

    def _short_of_one(a: str) -> str:
        a = _strip_latex_accents(a.strip())
        # 纯中文
        if _re.search(r"[一-鿿]", a):
            return a.split(",")[0].strip() if "," in a else a
        # 英文："LastName, FirstName" → LastName
        if "," in a:
            return a.split(",")[0].strip()
        # 英文 "First Last" → Last
        parts = a.split()
        return parts[-1] if parts else a

    result: dict[str, str] = {}

    # 逐条目解析
    for entry_m in _re.finditer(r"@\w+\{([^,\s]+)\s*,", text):
        key = entry_m.group(1).strip()
        # 找 author 字段
        pos = entry_m.end()
        # 在条目 body 里找 author = {...}
        author_m = _re.search(r"author\s*=\s*\{", text[pos : pos + 2000])
        if not author_m:
            continue
        # 用平衡括号提取 author 值
        abs_start = pos + author_m.end() - 1  # 指向 '{'
        raw = _balanced_braces(text, abs_start)

        # 多作者分隔：" and "
        parts = _re.split(r"\s+and\s+", raw)
        parts = [p for p in (pp.strip() for pp in parts) if p]
        if not parts:
            continue

        n = len(parts)
        is_zh = bool(_re.search(r"[一-鿿]", parts[0]))
        if n == 1:
            short = _short_of_one(parts[0])
        elif n == 2:
            a1 = _short_of_one(parts[0])
            a2 = _short_of_one(parts[1])
            short = f"{a1}、{a2}" if is_zh else f"{a1} and {a2}"
        else:
            a1 = _short_of_one(parts[0])
            short = f"{a1}等" if is_zh else f"{a1} et al."
        result[key] = short
    return result


# citet 作者短名映射缓存（首次调用 replace_natbib_cites 时 lazy 加载）
_BIB_AUTHORS_CACHE: dict[str, str] | None = None


def replace_natbib_cites(text: str) -> str:
    """把 \\citet{key} / \\citet{k1,k2} 展开成 "作者名\\cite{key}"，保留 pandoc 可识别的 \\cite 核心；
    \\citep / \\citep* 继续透传成 \\cite（按括号形式，pandoc 默认输出 [N]）。

    底层逻辑：pandoc 的 LaTeX reader 原生只认 \\cite，不支持 natbib 的 \\citet/\\citep 区分，
    直接暴力替换会丢作者名。抓手：预处理阶段读 bib 生成作者映射，把 citet 展开成
    "作者名" + "\\cite{key}"，让 pandoc 走正常 citation 路径生成 [N] 编号。
    """
    import re as _re

    global _BIB_AUTHORS_CACHE
    if _BIB_AUTHORS_CACHE is None:
        bib_path = THESIS_DIR / "references.bib"
        if bib_path.exists():
            try:
                _BIB_AUTHORS_CACHE = parse_bib_author_short(bib_path)
            except Exception:
                _BIB_AUTHORS_CACHE = {}
        else:
            _BIB_AUTHORS_CACHE = {}

    def _expand_citet(m):
        keys_raw = m.group(1)
        keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        # 取第一个 key 的作者作为前置"作者名"
        first = keys[0] if keys else ""
        author = _BIB_AUTHORS_CACHE.get(first, "")
        # 多 key 的情况：只用第一个作者代表，加"等"（中文）或" et al."（英文）
        if len(keys) >= 2 and author:
            if _re.search(r"[一-龥]", author):
                if not author.endswith("等"):
                    author = author + "等"
            else:
                if not author.endswith(" et al."):
                    # 去掉旧的 and 部分，用 et al.
                    author = author.split(" and ")[0] + " et al."
        keys_str = ", ".join(keys)
        if author:
            # 作者名 + \cite{...}；作者名和 \cite 之间不留空格，中文无须空格，
            # 英文 LaTeX 自动在 \cite 前不加空格（bracket 紧跟）
            return f"{author}\\cite{{{keys_str}}}"
        # bib 里找不到 author → 兜底透传
        return f"\\cite{{{keys_str}}}"

    # \citet{...} / \citet*{...}
    text = _re.sub(r"\\citet\*?\{([^}]+)\}", _expand_citet, text)
    # \citep / \citep* → 直接变 \cite（括号引用，输出 [N]）
    text = _re.sub(r"\\citep\*?\{", r"\\cite{", text)
    return text


def rewrite_abstract(raw: str, is_en: bool) -> str:
    """把摘要的 \\begin{center}...\\end{center}（论文标题行，我们不要）整块删掉，
    散装字体命令归一化，然后加 \\chapter*{摘要} 标题作为 docx 结构锚点（分页/分节依赖）。
    注意：H1 标题段会在 post_process 的 fold_abstract_heading_into_body 环节被折叠删除，
          段首 \\textbf{摘要：} / \\textbf{Abstract:} 粗体前缀保留——最终版面是
          "【粗体 摘要：】多障碍物..." 的带冒号前缀形式，而非独立居中的 H1。"""
    # 1. 整块删除 center 环境（里面是论文标题，另有封面用）
    cleaned = re.sub(
        r"\\begin\{center\}.*?\\end\{center\}",
        "",
        raw,
        flags=re.DOTALL,
    )
    # 2. 剥字体/页面命令（{\heiti\bfseries 摘要：} → \textbf{摘要：} 保留作段首粗体前缀）
    cleaned = strip_cjk_font_commands(cleaned)
    heading = "Abstract" if is_en else "摘要"
    return f"\n\\chapter*{{{heading}}}\n{cleaned}\n"


def rewrite_post_chapter(raw: str, fallback_title: str) -> str:
    """把后置章（致谢/附录/成果）归一化：
    - 剥 \\ctexset{...} / \\appendix / \\newfontfamily{...}[...] / \\lstset{...}
    - \\lstinputlisting[...]{path} → 占位提示段
    - \\chapter*{致\\hspace{2em}谢} 里的 \\hspace 等宽字命令清掉 → "致谢"
    - 若没有任何 \\chapter 指令，强行加 \\chapter*{fallback_title}
    - enumerate[label={[\\arabic*]}] → 预编号段落（pandoc 会吞自定义 label，
      所以必须在 flatten 阶段就把 [N] 塞进每个 item 的正文，绕过 pandoc 的 list 转换）
    """
    text = raw
    # \ctexset{...} —— 可能跨行、含嵌套，用暴力 brace-balance 替换
    text = _strip_balanced(text, r"\\ctexset")
    text = _strip_balanced(text, r"\\lstset")
    # \newfontfamily\name{Hack}[Scale=0.95] —— 两种 [...]/{...} 顺序都兜住
    text = re.sub(
        r"\\newfontfamily\\?\w*(?:\[[^\]]*\]|\{[^}]*\}){0,3}",
        "",
        text,
    )
    # \appendix 独立命令
    text = re.sub(r"\\appendix\b", "", text)
    # \lstinputlisting[opts]{path} → 占位
    text = re.sub(
        r"\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}",
        lambda m: f"\n\n\\textit{{（源码完整清单请参见项目仓库 {m.group(1)}）}}\n\n",
        text,
    )
    # \chapter*{致\hspace{2em}谢} → \chapter*{致谢}；先剥 hspace，再收紧空格
    text = re.sub(r"\\hspace\{[^}]*\}", "", text)
    # 把 enumerate[label={[\arabic*]}...] 整块转成预编号段落
    text = _hardcode_bracketed_enumerate(text)
    # 若原文没有任何 \chapter 指令，加一个 fallback 标题
    if not re.search(r"\\chapter\*?\s*\{", text):
        text = f"\\chapter*{{{fallback_title}}}\n" + text
    return text


def _hardcode_bracketed_enumerate(text: str) -> str:
    """pandoc 不支持 enumitem 的自定义 label={[\\arabic*]}，会把 enumerate 转成
    普通无编号列表。因此在 flatten 阶段就把这类 enumerate 展开为"[N] item 正文"
    形式的独立段落，绕过 pandoc 的 list 机制。
    仅针对 label={[\\arabic*]} / label=[\\arabic*] 这类成果章写法；不动默认 enumerate。
    """
    # 定位 \begin{enumerate}[...label={[\arabic*]}...]  …  \end{enumerate}
    pat = re.compile(
        r"\\begin\{enumerate\}\[(?P<opts>[^\]]*label\s*=\s*\{?\[\\arabic\*\]\}?[^\]]*)\]"
        r"(?P<body>.*?)\\end\{enumerate\}",
        re.DOTALL,
    )

    def _repl(m: re.Match[str]) -> str:
        body = m.group("body")
        # 按顶层 \item 切分（enumerate 里不嵌套 enumerate，我们这里简单地按 \item 切）
        items = re.split(r"(?m)^\s*\\item\s+", body)
        # 第一段是 \begin{enumerate} 后到第一个 \item 之间的文本（通常为空）
        prefix = items[0].strip()
        item_texts = items[1:]
        out_lines: list[str] = []
        if prefix:
            out_lines.append(prefix)
        n = 0
        for it in item_texts:
            # 去掉被注释掉的 item（% \item ...）和尾部空白
            # split 的元素此时不带 \item，但可能第一行本身是 "\item" 被注释时的残片
            it = it.rstrip()
            if not it.strip():
                continue
            n += 1
            out_lines.append(f"[{n}] {it}")
        # 用空行分段，确保 pandoc 识别为独立段落
        return "\n\n" + "\n\n".join(out_lines) + "\n\n"

    return pat.sub(_repl, text)


def _strip_balanced(text: str, head_regex: str) -> str:
    """从 head_regex 匹配点开始，吃掉其后**平衡**的一组 {...}（允许嵌套）。"""
    out = []
    i = 0
    pattern = re.compile(head_regex)
    while i < len(text):
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        j = m.end()
        # 吃掉空白后的 {...}（允许嵌套）
        while j < len(text) and text[j] in " \t\n":
            j += 1
        if j < len(text) and text[j] == "{":
            depth = 1
            j += 1
            while j < len(text) and depth > 0:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
        i = j
    return "".join(out)


def flatten_tex() -> str:
    # 1. 聚合所有宏
    macros: dict[str, str] = {}
    for f in MACRO_SOURCES:
        p = THESIS_DIR / f
        if p.exists():
            macros.update(load_newcommands(p.read_text(encoding="utf-8")))

    # 2. 读摘要 + 正文
    parts: list[str] = []
    parts.append(
        rewrite_abstract(
            (THESIS_DIR / "chapters" / "abstract_zh.tex").read_text(encoding="utf-8"),
            is_en=False,
        )
    )
    parts.append(
        rewrite_abstract(
            (THESIS_DIR / "chapters" / "abstract_en.tex").read_text(encoding="utf-8"),
            is_en=True,
        )
    )
    for i in BODY_CHAPTERS:
        p = THESIS_DIR / "chapters" / f"chapter{i}.tex"
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))

    # 参考文献 anchor：pandoc citeproc 会把条目自动注入到文档末尾，
    # 我们在此埋一个占位一级标题，post_process 里会把 Bibliography 段落整体搬到此处。
    parts.append(f"\n\\chapter*{{{REFS_ANCHOR_TEXT}}}\n")

    # 后置章：致谢 / 附录 / 成果
    for fname, fallback in POST_CHAPTERS:
        p = THESIS_DIR / "chapters" / fname
        if p.exists():
            parts.append(rewrite_post_chapter(p.read_text(encoding="utf-8"), fallback))

    body = "\n\n".join(parts)

    # 3. 宏展开 + 图引用重写 + 编号 + 剥 adjustbox/label + 规范化 cite + \ref 解析
    body = expand_macros(body, macros)
    missing_figs: list[str] = []
    body = rewrite_figure_inputs(body, missing_figs)
    body = strip_figure_inputs_and_adjustbox(body)
    # figure/table 编号必须在 strip_figure_labels_and_refs 之前，以读取 \label
    body, label_map = number_figures_and_tables(body)
    # algorithm 环境在此展开成 lstlisting（pandoc 读不懂 algorithm2e 宏），
    # 必须在 number_figures_and_tables 之后（caption 已含"算法 X.Y"），
    # 在 strip_figure_labels_and_refs 之前（label 已不需要）。
    body = rewrite_algorithms(body)
    body = strip_figure_labels_and_refs(body)
    body = strip_cjk_font_commands(body)
    body = replace_natbib_cites(body)
    # \ref 用真实编号替换，查不到再 ??
    body = resolve_refs(body, label_map)

    if missing_figs:
        uniq = sorted(set(missing_figs))
        print(f"[warn] {len(uniq)} 张图无对应 svg，已写占位：", file=sys.stderr)
        for n in uniq[:10]:
            print(f"       · {n}", file=sys.stderr)
        if len(uniq) > 10:
            print(f"       ... 还有 {len(uniq) - 10} 张", file=sys.stderr)

    # 4. 包装成 minimal book；用 book 是为了 \chapter 能被 pandoc 识别成 Heading 1，
    #    subsubsection 自然对应 Heading 4（post_process 里降级为三级标题样式）
    wrapper = (
        r"""\documentclass{book}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs,tabularx,multirow,longtable}
\usepackage{graphicx,hyperref}
\usepackage{url}
\begin{document}
"""
        + body
        + "\n\\end{document}\n"
    )
    return wrapper
