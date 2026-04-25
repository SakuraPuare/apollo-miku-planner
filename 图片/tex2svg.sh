#!/bin/bash
# tex2svg.sh - 自动识别tex文件中的图题并转换为SVG
# 用法: ./tex2svg.sh [input.tex] [output_dir]

set -e

# 默认参数
INPUT_TEX="${1:-figures.tex}"
OUTPUT_DIR="${2:-.}"

# 检查输入文件
if [ ! -f "$INPUT_TEX" ]; then
    echo "错误: 找不到文件 $INPUT_TEX"
    exit 1
fi

# 检查依赖
if ! command -v pdf2svg &> /dev/null; then
    echo "错误: 需要安装 pdf2svg"
    echo "macOS: brew install pdf2svg"
    echo "Ubuntu: sudo apt install pdf2svg"
    exit 1
fi

if ! command -v xelatex &> /dev/null; then
    echo "错误: 需要安装 xelatex (TeX Live)"
    exit 1
fi

# 获取文件名（不含扩展名）
BASENAME=$(basename "$INPUT_TEX" .tex)
PDF_FILE="${BASENAME}.pdf"

echo "=== TeX to SVG 转换工具 ==="
echo "输入文件: $INPUT_TEX"
echo ""

# 提取图题
# 匹配模式: % ====...  后跟 % 图题名称  再跟 % ====...
echo "正在解析图题..."
TITLES=()
while IFS= read -r line; do
    # 去除前后空白和 % 符号
    title=$(echo "$line" | sed 's/^[[:space:]]*%[[:space:]]*//' | sed 's/[[:space:]]*$//')
    if [ -n "$title" ]; then
        TITLES+=("$title")
        echo "  找到图题: $title"
    fi
done < <(grep -A1 '^%[[:space:]]*=\{10,\}' "$INPUT_TEX" | grep -v '^%[[:space:]]*=\{10,\}' | grep -v '^--$' | grep '^%' | grep -v '编译\|用途\|开题')

# 如果没有找到图题，使用默认命名
if [ ${#TITLES[@]} -eq 0 ]; then
    echo "警告: 未找到图题，将使用默认命名"
fi

echo ""
echo "正在编译 LaTeX..."
xelatex -interaction=nonstopmode "$INPUT_TEX" > /dev/null 2>&1 || true

# 检查 PDF 是否生成
if [ ! -f "$PDF_FILE" ]; then
    echo "错误: LaTeX 编译失败，PDF 文件未生成"
    xelatex -interaction=nonstopmode "$INPUT_TEX" 2>&1 | tail -20
    exit 1
fi

# 获取 PDF 页数
PAGE_COUNT=$(pdfinfo "$PDF_FILE" 2>/dev/null | grep "Pages:" | awk '{print $2}' || echo "0")

# 如果 pdfinfo 不可用，尝试其他方法
if [ "$PAGE_COUNT" = "0" ] || [ -z "$PAGE_COUNT" ]; then
    # 使用 pdf2svg 尝试转换来计算页数
    PAGE_COUNT=0
    for i in {1..100}; do
        if pdf2svg "$PDF_FILE" /dev/null $i 2>/dev/null; then
            ((PAGE_COUNT++))
        else
            break
        fi
    done
fi

echo "PDF 生成成功，共 $PAGE_COUNT 页"
echo ""

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 转换每一页
echo "正在转换为 SVG..."
for ((i=1; i<=PAGE_COUNT; i++)); do
    # 确定文件名
    if [ $i -le ${#TITLES[@]} ] && [ -n "${TITLES[$((i-1))]}" ]; then
        # 使用图题作为文件名，替换不安全字符
        TITLE="${TITLES[$((i-1))]}"
        SAFE_NAME=$(echo "$TITLE" | tr '/' '_' | tr ':' '_' | tr ' ' '_')
        SVG_NAME="${i}_${SAFE_NAME}.svg"
    else
        SVG_NAME="${BASENAME}_page${i}.svg"
    fi

    OUTPUT_PATH="${OUTPUT_DIR}/${SVG_NAME}"

    echo "  第 ${i} 页 -> ${SVG_NAME}"
    pdf2svg "$PDF_FILE" "$OUTPUT_PATH" $i
done

echo ""
echo "=== 转换完成 ==="
echo "输出目录: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/*.svg 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
