TEX      := xelatex
TEXFLAGS := -interaction=nonstopmode -halt-on-error -shell-escape
BIBER    := biber

# 编译前必须存在于 PATH 的外部命令（缺一则立即失败）
DEPS     := $(TEX) $(BIBER) pdflatex bibtex pdfcrop pdf2svg latexmk uv pandoc
FONT_FILES := \
	fonts/local-fonts.tex \
	fonts/tex-gyre/texgyretermes-regular.otf \
	fonts/tex-gyre/texgyretermes-bold.otf \
	fonts/tex-gyre/texgyretermes-italic.otf \
	fonts/tex-gyre/texgyretermes-bolditalic.otf \
	fonts/fandol/FandolSong-Regular.otf \
	fonts/fandol/FandolSong-Bold.otf \
	fonts/fandol/FandolKai-Regular.otf \
	fonts/fandol/FandolHei-Regular.otf \
	fonts/fandol/FandolHei-Bold.otf \
	fonts/fandol/FandolFang-Regular.otf

FIGDIR   := 图片
THESISDIR:= 毕业论文
SLIDEDIR := 答辩演示
KAITIDIR := 开题答辩
FOREIGNDIR := 外文文献
DEFENSEDIR := 毕业答辩

SVGDIR   := $(FIGDIR)/svg
BUILDDIR := $(FIGDIR)/build

# 单图源（每个 fig_*.tex 一图；排除 fig_slide_* 答辩专用复合图）
FIGSRC   := $(filter-out $(FIGDIR)/fig_slide_%.tex,$(wildcard $(FIGDIR)/fig_*.tex))
# 数据驱动图（metric_score.py 自动生成，位于 data/ablation/）也纳入 svg 流水线
ABLATION_FIG_SRC := $(FIGDIR)/data/ablation/score_radar.tex $(FIGDIR)/data/ablation/score_heatmap.tex
FIGSRC   += $(ABLATION_FIG_SRC)
FIGNAMES := $(notdir $(FIGSRC:.tex=))
PREAMBLE := $(FIGDIR)/_figpreamble.tex
SVGS     := $(addprefix $(SVGDIR)/,$(addsuffix .svg,$(FIGNAMES)))

# 仿真链路 stamp 文件与目标（必须在 thesis target 之前定义，否则 $(VAR) 展开为空）
DATA_STAMP    := $(FIGDIR)/data/.stamp
FIGS_STAMP    := $(FIGDIR)/.figs_stamp
METRICS_TEX   := $(THESISDIR)/_experiment_metrics.tex
ABLATION_CSV  := $(FIGDIR)/data/ablation/ablation.csv
ABLATION_TEX  := $(THESISDIR)/_ablation_macros.tex
SENSITIVITY_TEX := $(THESISDIR)/_sensitivity_macros.tex
CONTEXT_TEX   := $(THESISDIR)/_experiment_context.tex

# docx 转换：工具/tex_to_docx.py 把 chapters 扁平化后经 pandoc → python-docx 后处理
OUTPUTDIR     := outputs
DOCX          := $(OUTPUTDIR)/thesis.docx
DOCX_TOOL     := 工具/tex_to_docx.py
DOCX_CORE     := $(wildcard 工具/tex_to_docx_core/*.py)
DOCX_CSL      := 工具/gbt7714.csl
DOCX_TEMPLATE := 模板/湖北文理学院计算机工程学院2026届本科毕业论文模板样例.docx
CHAPTERS_SRC  := $(wildcard $(THESISDIR)/chapters/*.tex)
THESIS_TEX    := $(THESISDIR)/thesis.tex
INFO_SRC      := $(THESISDIR)/info.tex
BIB_SRC       := $(THESISDIR)/references.bib

.PHONY: all check-deps svg svg-clean svg-print thesis docx slides kaiti foreign foreign-original foreign-translation defense defense-slides defense-slides-all defense-script thesis-print docx-print print clean help sim sim-data sim-figs sim-metrics sim-ablation sim-sensitivity sim-context
.PRECIOUS: $(BUILDDIR)/wrap_%.tex $(BUILDDIR)/wrap_%.pdf $(BUILDDIR)/wrap_%-crop.pdf

# ══════════════════════════════════════════════════
#  依赖检查（未安装所需命令时不进入编译）
# ══════════════════════════════════════════════════
check-deps:
	@for cmd in $(DEPS); do \
	  command -v "$$cmd" >/dev/null 2>&1 || { \
	    printf '%s\n' "错误: 未找到命令 \"$$cmd\"（PATH 中不可用）。请先安装对应依赖后再编译。" >&2; \
	    exit 1; \
	  }; \
	done
	@echo "✓ 外部依赖检查通过 ($(words $(DEPS)) 个命令)"
	@for file in $(FONT_FILES); do \
	  test -f "$$file" || { \
	    printf '%s\n' "错误: 缺少本地字体文件 \"$$file\"。请确认 fonts/ 目录完整。" >&2; \
	    exit 1; \
	  }; \
	done
	@echo "✓ 本地字体检查通过 ($(words $(FONT_FILES)) 个文件)"

# ══════════════════════════════════════════════════
#  默认：并行 SVG + 论文 + 答辩演示
#  全量推荐：make -j$(nproc)
# ══════════════════════════════════════════════════
all: svg thesis docx print slides kaiti foreign defense

# ══════════════════════════════════════════════════
#  SVG 并行编译（每图独立 xelatex，-j N 并行）
# ══════════════════════════════════════════════════

svg: check-deps $(FIGS_STAMP) $(SVGS)
	@echo "✓ SVG 共 $(words $(SVGS)) 个 → $(SVGDIR)/"

# 1) 生成单图 wrapper（统一 preamble + \input{<name>}）
$(BUILDDIR)/wrap_%.tex: $(FIGDIR)/%.tex Makefile | $(BUILDDIR)
	@printf '%s\n' \
	  '\documentclass[UTF8,fontset=none]{ctexart}' \
	  '\input{_figpreamble}' \
	  '\input{../../$(CONTEXT_TEX)}' \
	  '\input{../../$(METRICS_TEX)}' \
	  '\input{../../$(ABLATION_TEX)}' \
	  '\begin{document}' \
	  '\begin{figure}[H]\centering' \
	  '\input{$*}' \
	  '\end{figure}' \
	  '\end{document}' > $@

# 1b) data/ablation/score_*.tex 的 wrapper（因源文件不在 FIGDIR 根目录）
#     源文件由 sim 流水线生成，必须等 FIGS_STAMP 完成
$(ABLATION_FIG_SRC): $(FIGS_STAMP)
$(BUILDDIR)/wrap_score_%.tex: $(FIGDIR)/data/ablation/score_%.tex Makefile | $(BUILDDIR)
	@printf '%s\n' \
	  '\documentclass[UTF8,fontset=none]{ctexart}' \
	  '\input{_figpreamble}' \
	  '\input{../../$(CONTEXT_TEX)}' \
	  '\begin{document}' \
	  '\begin{figure}[H]\centering' \
	  '\input{score_$*}' \
	  '\end{figure}' \
	  '\end{document}' > $@

# 2) 单图编译；TEXINPUTS=.:..: 显式 cwd 优先，再到父目录找源 fig 与 preamble
$(BUILDDIR)/wrap_%.pdf: $(BUILDDIR)/wrap_%.tex $(PREAMBLE) $(FIGDIR)/%.tex $(CONTEXT_TEX) $(METRICS_TEX) $(ABLATION_TEX) $(FONT_FILES)
	@cd $(BUILDDIR) && TEXINPUTS=.:..:../data/ablation: $(TEX) $(TEXFLAGS) wrap_$*.tex >/dev/null 2>&1 || { \
	  echo "✗ $* 编译失败，尾部日志："; \
	  tail -30 $(BUILDDIR)/wrap_$*.log 2>/dev/null; \
	  exit 1; }

# 2b) data/ablation/score_* 图编译（依赖指向 data/ablation/ 下的源）
$(BUILDDIR)/wrap_score_%.pdf: $(BUILDDIR)/wrap_score_%.tex $(PREAMBLE) $(FIGDIR)/data/ablation/score_%.tex $(CONTEXT_TEX) $(FONT_FILES)
	@cd $(BUILDDIR) && TEXINPUTS=.:..:../data/ablation: $(TEX) $(TEXFLAGS) wrap_score_$*.tex >/dev/null 2>&1 || { \
	  echo "✗ score_$* 编译失败，尾部日志："; \
	  tail -30 $(BUILDDIR)/wrap_score_$*.log 2>/dev/null; \
	  exit 1; }

# 3) 裁白边
$(BUILDDIR)/wrap_%-crop.pdf: $(BUILDDIR)/wrap_%.pdf
	@pdfcrop --margin 2 $< $@ >/dev/null 2>&1

# 4) PDF → SVG（去掉 wrap_ 前缀，svg 文件名 1:1 对应 fig_*.tex）
$(SVGDIR)/%.svg: $(BUILDDIR)/wrap_%-crop.pdf | $(SVGDIR)
	@pdf2svg $< $@
	@echo "  ✓ $*.svg"

$(BUILDDIR):
	@mkdir -p $(BUILDDIR)

$(SVGDIR):
	@mkdir -p $(SVGDIR)

svg-clean:
	rm -rf $(SVGDIR) $(BUILDDIR)

# ══════════════════════════════════════════════════
#  论文 / 答辩 / 开题
# ══════════════════════════════════════════════════
thesis: check-deps $(METRICS_TEX) $(ABLATION_TEX) $(SENSITIVITY_TEX) $(CONTEXT_TEX) svg
	cd $(THESISDIR) && latexmk thesis.tex >/dev/null 2>&1
	@test -f $(THESISDIR)/thesis.pdf || { echo "错误: thesis.pdf 未生成"; exit 1; }
	@echo "✓ 论文: $(THESISDIR)/thesis.pdf"

# ══════════════════════════════════════════════════
#  DOCX 转换（pandoc + python-docx 后处理）
#  与 thesis 同源：依赖 chapters + 仿真宏 + bib + svg + 转换脚本本身
# ══════════════════════════════════════════════════
docx: $(DOCX)
$(DOCX): $(DOCX_TOOL) $(DOCX_CORE) $(DOCX_CSL) $(DOCX_TEMPLATE) $(THESIS_TEX) $(CHAPTERS_SRC) $(INFO_SRC) $(BIB_SRC) $(METRICS_TEX) $(ABLATION_TEX) $(SENSITIVITY_TEX) $(CONTEXT_TEX) | check-deps svg
	@mkdir -p $(OUTPUTDIR)
	uv run $(DOCX_TOOL) -o $(DOCX)
	@test -f $(DOCX) || { echo "错误: $(DOCX) 未生成"; exit 1; }
	@echo "✓ 论文 docx: $(DOCX)"

# ══════════════════════════════════════════════════
#  灰度打印版（PDF + DOCX）
#  策略：PDF 用 \PrintVersionFlag 源码级灰度 + Ghostscript 兜底外部位图
#        DOCX 用 magick 转灰度 SVG 后重新生成
# ══════════════════════════════════════════════════
PRINT_PDF  := $(OUTPUTDIR)/thesis_print.pdf
PRINT_DOCX := $(OUTPUTDIR)/thesis_print.docx
SVG_PRINT_DIR := $(FIGDIR)/svg_print

print: thesis-print docx-print

thesis-print: check-deps $(METRICS_TEX) $(ABLATION_TEX) $(SENSITIVITY_TEX) $(CONTEXT_TEX) svg | $(OUTPUTDIR)
	cd $(THESISDIR) && latexmk -jobname=thesis_print -usepretex='\def\PrintVersionFlag{1}' thesis.tex >/dev/null 2>&1
	gs -sDEVICE=pdfwrite -sColorConversionStrategy=Gray -dProcessColorModel=/DeviceGray \
	   -dCompatibilityLevel=1.5 -dNOPAUSE -dBATCH -o $(PRINT_PDF) $(THESISDIR)/thesis_print.pdf >/dev/null 2>&1
	@test -f $(PRINT_PDF) || { echo "错误: $(PRINT_PDF) 未生成"; exit 1; }
	@echo "✓ 灰度打印版 PDF: $(PRINT_PDF)"

docx-print: $(DOCX_TOOL) $(DOCX_CORE) $(DOCX_CSL) $(DOCX_TEMPLATE) $(THESIS_TEX) $(CHAPTERS_SRC) $(INFO_SRC) $(BIB_SRC) $(METRICS_TEX) $(ABLATION_TEX) $(SENSITIVITY_TEX) $(CONTEXT_TEX) | check-deps svg $(OUTPUTDIR)
	@mkdir -p $(SVG_PRINT_DIR)
	@for f in $(SVGDIR)/*.svg; do \
	  magick "$$f" -colorspace Gray "$(SVG_PRINT_DIR)/$$(basename $$f)" 2>/dev/null || cp "$$f" "$(SVG_PRINT_DIR)/$$(basename $$f)"; \
	done
	SVG_DIR_OVERRIDE=$(CURDIR)/$(SVG_PRINT_DIR) uv run $(DOCX_TOOL) -o $(PRINT_DOCX)
	@test -f $(PRINT_DOCX) || { echo "错误: $(PRINT_DOCX) 未生成"; exit 1; }
	@echo "✓ 灰度打印版 DOCX: $(PRINT_DOCX)"

$(OUTPUTDIR):
	@mkdir -p $(OUTPUTDIR)

# ══════════════════════════════════════════════════
#  仿真链路（增量构建：源码改了才重生，chapter 不被修改）
#  依赖链：apollo_pipeline.py ─→ data stamp ─→ figs stamp ─→ svg
#                                          └→ metrics.tex ─→ thesis
# ══════════════════════════════════════════════════
# 1) 数据：apollo_pipeline.py 改了才重跑
$(DATA_STAMP): 可视化/apollo_pipeline.py
	@cd 可视化 && uv run apollo_pipeline.py >/dev/null
	@mkdir -p $(FIGDIR)/data && touch $@
	@echo "✓ 仿真数据: $(FIGDIR)/data/"

# 2) 实验图源：data 或 _gen_exp_figs.py 改了才重生
$(FIGS_STAMP): $(DATA_STAMP) $(FIGDIR)/_gen_exp_figs.py
	@cd $(FIGDIR) && uv run _gen_exp_figs.py >/dev/null
	@touch $@
	@echo "✓ 实验图源: $(FIGDIR)/fig_exp_*.tex"

# 3) 指标宏：data 或 _gen_metrics_tex.py 改了才重写
$(METRICS_TEX): $(DATA_STAMP) 可视化/_gen_metrics_tex.py
	@cd 可视化 && uv run _gen_metrics_tex.py >/dev/null
	@echo "✓ 指标宏: $(METRICS_TEX)"

# 4) 消融数据：apollo_pipeline.py 或 run_ablation.py 改了才重跑 6 变体 × 4 场景
$(ABLATION_CSV): 可视化/apollo_pipeline.py 可视化/run_ablation.py
	@cd 可视化 && uv run run_ablation.py >/dev/null
	@echo "✓ 消融数据: $(ABLATION_CSV)"

# 5) 消融评分宏与 LaTeX 三件套：ablation.csv 或 metric_score.py 改了才重写
$(ABLATION_TEX): $(ABLATION_CSV) 可视化/metric_score.py
	@cd 可视化 && uv run metric_score.py >/dev/null
	@echo "✓ 消融评分: $(ABLATION_TEX)"

# 6) 灵敏度分析宏：apollo_pipeline.py 或 sensitivity_analysis.py 改了才重写
$(SENSITIVITY_TEX): 可视化/apollo_pipeline.py 可视化/sensitivity_analysis.py
	@cd 可视化 && uv run sensitivity_analysis.py >/dev/null
	@echo "✓ 灵敏度宏: $(SENSITIVITY_TEX)"

# 7) 论文上下文宏：从仿真场景定义与方法常量生成
$(CONTEXT_TEX): 可视化/apollo_pipeline.py 可视化/_gen_context_tex.py
	@cd 可视化 && uv run _gen_context_tex.py >/dev/null
	@echo "✓ 场景参数宏: $(CONTEXT_TEX)"

# 便捷别名
sim-data:     check-deps $(DATA_STAMP)
sim-figs:     check-deps $(FIGS_STAMP)
sim-metrics:  check-deps $(METRICS_TEX)
sim-ablation: check-deps $(ABLATION_TEX)
sim-sensitivity: check-deps $(SENSITIVITY_TEX)
sim-context:  check-deps $(CONTEXT_TEX)
sim:          check-deps sim-figs sim-metrics sim-ablation sim-sensitivity sim-context
	@echo "✓ 仿真产物已增量更新"

slides: $(SLIDEDIR)/slides.pdf
$(SLIDEDIR)/slides.pdf: $(SLIDEDIR)/slides.tex $(FONT_FILES) | check-deps
	-cd $(SLIDEDIR) && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1
	@test -f $(SLIDEDIR)/slides.pdf || { echo "错误: 答辩演示 slides.pdf 未生成"; exit 1; }
	@echo "✓ 答辩演示: $(SLIDEDIR)/slides.pdf"

kaiti: $(KAITIDIR)/slides.pdf
$(KAITIDIR)/slides.pdf: $(KAITIDIR)/slides.tex $(wildcard $(KAITIDIR)/figures/*.tex) $(FONT_FILES) | check-deps
	cd $(KAITIDIR) && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1
	@echo "✓ 开题答辩: $(KAITIDIR)/slides.pdf"

# ══════════════════════════════════════════════════
#  毕业答辩（beamer slides + 独立讲稿，两份 PDF）
# ══════════════════════════════════════════════════
defense: defense-slides defense-slides-all defense-script
	@echo "✓ 毕业答辩: $(DEFENSEDIR)/slides.pdf (16:9, 4:3, 16:10) + $(DEFENSEDIR)/script.pdf"

defense-slides: $(DEFENSEDIR)/slides.pdf
$(DEFENSEDIR)/slides.pdf: $(DEFENSEDIR)/slides.tex $(DEFENSEDIR)/preamble.tex $(METRICS_TEX) $(ABLATION_TEX) $(CONTEXT_TEX) $(FONT_FILES) | check-deps
	cd $(DEFENSEDIR) && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1
	@test -f $(DEFENSEDIR)/slides.pdf || { echo "错误: 毕业答辩 slides.pdf 未生成"; exit 1; }
	@echo "✓ 毕业答辩幻灯片: $(DEFENSEDIR)/slides.pdf (16:9)"

defense-slides-all: $(DEFENSEDIR)/slides.pdf $(DEFENSEDIR)/slides_4x3.pdf $(DEFENSEDIR)/slides_16x10.pdf

$(DEFENSEDIR)/slides_4x3.pdf: $(DEFENSEDIR)/slides.tex $(DEFENSEDIR)/preamble.tex $(METRICS_TEX) $(ABLATION_TEX) $(CONTEXT_TEX) $(FONT_FILES) | check-deps
	cd $(DEFENSEDIR) && sed 's/aspectratio=169/aspectratio=43/' slides.tex > .slides_43.tex \
	  && $(TEX) $(TEXFLAGS) -jobname=slides_4x3 .slides_43.tex >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) -jobname=slides_4x3 .slides_43.tex >/dev/null 2>&1 \
	  && rm -f .slides_43.tex
	@test -f $(DEFENSEDIR)/slides_4x3.pdf || { echo "错误: slides_4x3.pdf 未生成"; exit 1; }
	@echo "✓ 毕业答辩幻灯片: $(DEFENSEDIR)/slides_4x3.pdf (4:3)"

$(DEFENSEDIR)/slides_16x10.pdf: $(DEFENSEDIR)/slides.tex $(DEFENSEDIR)/preamble.tex $(METRICS_TEX) $(ABLATION_TEX) $(CONTEXT_TEX) $(FONT_FILES) | check-deps
	cd $(DEFENSEDIR) && sed 's/aspectratio=169/aspectratio=1610/' slides.tex > .slides_1610.tex \
	  && $(TEX) $(TEXFLAGS) -jobname=slides_16x10 .slides_1610.tex >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) -jobname=slides_16x10 .slides_1610.tex >/dev/null 2>&1 \
	  && rm -f .slides_1610.tex
	@test -f $(DEFENSEDIR)/slides_16x10.pdf || { echo "错误: slides_16x10.pdf 未生成"; exit 1; }
	@echo "✓ 毕业答辩幻灯片: $(DEFENSEDIR)/slides_16x10.pdf (16:10)"

defense-script: $(DEFENSEDIR)/script.pdf
$(DEFENSEDIR)/script.pdf: $(DEFENSEDIR)/script.tex $(DEFENSEDIR)/preamble.tex $(FONT_FILES) | check-deps
	cd $(DEFENSEDIR) && $(TEX) $(TEXFLAGS) script.tex >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) script.tex >/dev/null 2>&1
	@test -f $(DEFENSEDIR)/script.pdf || { echo "错误: 毕业答辩 script.pdf 未生成"; exit 1; }
	@echo "✓ 毕业答辩讲稿: $(DEFENSEDIR)/script.pdf"


# ══════════════════════════════════════════════════
#  外文文献原文及译文
# ══════════════════════════════════════════════════
foreign: foreign-original foreign-translation

foreign-original: $(FOREIGNDIR)/original/original.pdf
$(FOREIGNDIR)/original/original.pdf: $(FOREIGNDIR)/original/original.tex $(FOREIGNDIR)/original/refs.bib | check-deps
	cd $(FOREIGNDIR)/original && pdflatex $(TEXFLAGS) original.tex >/dev/null 2>&1 \
	  && bibtex original >/dev/null 2>&1 \
	  && pdflatex $(TEXFLAGS) original.tex >/dev/null 2>&1 \
	  && pdflatex $(TEXFLAGS) original.tex >/dev/null 2>&1
	@test -f $(FOREIGNDIR)/original/original.pdf || { echo "错误: 外文文献原文未生成"; exit 1; }
	@echo "✓ 外文文献原文: $(FOREIGNDIR)/original/original.pdf"

foreign-translation: $(FOREIGNDIR)/translation/translation.pdf
$(FOREIGNDIR)/translation/translation.pdf: $(FOREIGNDIR)/translation/translation.tex $(FOREIGNDIR)/translation/refs.bib $(FONT_FILES) | check-deps
	cd $(FOREIGNDIR)/translation && $(TEX) $(TEXFLAGS) translation.tex >/dev/null 2>&1 \
	  && $(BIBER) translation >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) translation.tex >/dev/null 2>&1 \
	  && $(TEX) $(TEXFLAGS) translation.tex >/dev/null 2>&1
	@test -f $(FOREIGNDIR)/translation/translation.pdf || { echo "错误: 外文文献译文未生成"; exit 1; }
	@echo "✓ 外文文献译文: $(FOREIGNDIR)/translation/translation.pdf"

# ══════════════════════════════════════════════════
#  清理
# ══════════════════════════════════════════════════
clean:
	rm -rf $(SVGDIR) $(BUILDDIR)
	rm -f $(THESISDIR)/_experiment_metrics.tex $(THESISDIR)/_ablation_macros.tex $(THESISDIR)/_sensitivity_macros.tex $(THESISDIR)/_experiment_context.tex
	rm -f $(THESISDIR)/thesis.{pdf,aux,log,toc,bbl,blg,out,bcf,run.xml,xdv,fls,auxlock}
	rm -f $(THESISDIR)/thesis_print.{pdf,aux,log,toc,bbl,blg,out,bcf,run.xml,xdv,fls,auxlock}
	rm -f $(SLIDEDIR)/slides.{pdf,aux,log,nav,out,snm,toc,vrb,auxlock}
	rm -f $(KAITIDIR)/slides.{pdf,aux,log,nav,out,snm,toc,vrb,auxlock}
	rm -rf $(THESISDIR)/thesis-figure*.{md5,vrb,pdf,dpth,auxlock,log,xml,dep}
	rm -rf $(SLIDEDIR)/slides-figure*.{md5,vrb,pdf,dpth,auxlock,log,xml,dep}
	rm -rf $(KAITIDIR)/slides-figure*.{md5,vrb,pdf,dpth,auxlock,log,xml,dep}
	rm -f $(FOREIGNDIR)/original/original.{pdf,aux,log,bbl,blg,bcf,run.xml,toc,out}
	rm -f $(FOREIGNDIR)/translation/translation.{pdf,aux,log,bbl,blg,bcf,run.xml,toc,out}
	rm -f $(DEFENSEDIR)/slides.{pdf,aux,log,nav,out,snm,toc,vrb,auxlock}
	rm -f $(DEFENSEDIR)/slides_4x3.{pdf,aux,log,nav,out,snm,toc,vrb,auxlock}
	rm -f $(DEFENSEDIR)/slides_16x10.{pdf,aux,log,nav,out,snm,toc,vrb,auxlock}
	rm -f $(DEFENSEDIR)/script.{pdf,aux,log,out,toc}
	rm -rf $(DEFENSEDIR)/slides-figure*.{md5,vrb,pdf,dpth,auxlock,log,xml,dep}
	rm -f $(DOCX)
	rm -f $(PRINT_PDF) $(PRINT_DOCX)
	rm -rf $(SVG_PRINT_DIR)

# ══════════════════════════════════════════════════
#  帮助
# ══════════════════════════════════════════════════
help:
	@echo "make check-deps 检查 TeX / pdfcrop / pdf2svg / latexmk / uv / pandoc / 字体是否可用"
	@echo "make            并行 SVG + 论文 + docx + 答辩"
	@echo "make -jN svg    并行编译全部单图 SVG（推荐 N=$$(nproc)）"
	@echo "make svg-clean  清空 svg/ 与 build/ 目录"
	@echo "make thesis     编译论文"
	@echo "make docx       转换论文为 Word docx ($(DOCX))"
	@echo "make print      一次性生成灰度打印版 PDF + DOCX"
	@echo "make thesis-print  灰度打印版 PDF"
	@echo "make docx-print    灰度打印版 DOCX"
	@echo "make slides     编译答辩演示"
	@echo "make kaiti      编译开题答辩"
	@echo "make foreign    编译外文文献原文及译文"
	@echo "make defense    编译毕业答辩 (slides 三比例 + 讲稿)"
	@echo "make clean      清理全部生成物"
