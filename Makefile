TEX      := xelatex
TEXFLAGS := -interaction=nonstopmode -halt-on-error
BIBER    := biber

FIGDIR   := 图片
THESISDIR:= 毕业论文
SLIDEDIR := 答辩演示
KAITIDIR := 开题答辩

SVGDIR   := $(FIGDIR)/svg
BUILDDIR := $(FIGDIR)/build

# 单图源（每个 fig_*.tex 一图）
FIGSRC   := $(wildcard $(FIGDIR)/fig_*.tex)
FIGNAMES := $(notdir $(FIGSRC:.tex=))
PREAMBLE := $(FIGDIR)/_figpreamble.tex
SVGS     := $(addprefix $(SVGDIR)/,$(addsuffix .svg,$(FIGNAMES)))

.PHONY: all svg svg-clean thesis slides kaiti clean help
.PRECIOUS: $(BUILDDIR)/wrap_%.tex $(BUILDDIR)/wrap_%.pdf $(BUILDDIR)/wrap_%-crop.pdf

# ══════════════════════════════════════════════════
#  默认：并行 SVG + 论文 + 答辩演示
#  全量推荐：make -j$(nproc)
# ══════════════════════════════════════════════════
all: svg thesis slides

# ══════════════════════════════════════════════════
#  SVG 并行编译（每图独立 xelatex，-j N 并行）
# ══════════════════════════════════════════════════

svg: $(SVGS)
	@echo "✓ SVG 共 $(words $(SVGS)) 个 → $(SVGDIR)/"

# 1) 生成单图 wrapper（统一 preamble + \input{<name>}）
$(BUILDDIR)/wrap_%.tex: $(FIGDIR)/%.tex | $(BUILDDIR)
	@printf '%s\n' \
	  '\documentclass[UTF8]{ctexart}' \
	  '\input{_figpreamble}' \
	  '\begin{document}' \
	  '\begin{figure}[H]\centering' \
	  '\input{$*}' \
	  '\end{figure}' \
	  '\end{document}' > $@

# 2) 单图编译；TEXINPUTS=.:..: 显式 cwd 优先，再到父目录找源 fig 与 preamble
$(BUILDDIR)/wrap_%.pdf: $(BUILDDIR)/wrap_%.tex $(PREAMBLE) $(FIGDIR)/%.tex
	@cd $(BUILDDIR) && TEXINPUTS=.:..: $(TEX) $(TEXFLAGS) wrap_$*.tex >/dev/null 2>&1 || { \
	  echo "✗ $* 编译失败，尾部日志："; \
	  tail -30 $(BUILDDIR)/wrap_$*.log 2>/dev/null; \
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
thesis:
	cd $(THESISDIR) && latexmk thesis.tex >/dev/null 2>&1
	@test -f $(THESISDIR)/thesis.pdf || { echo "错误: thesis.pdf 未生成"; exit 1; }
	@echo "✓ 论文: $(THESISDIR)/thesis.pdf"

slides: $(SLIDEDIR)/main.pdf
$(SLIDEDIR)/main.pdf: $(SLIDEDIR)/main.tex
	-cd $(SLIDEDIR) && $(TEX) $(TEXFLAGS) main.tex >/dev/null 2>&1
	@test -f $(SLIDEDIR)/main.pdf || { echo "错误: slides main.pdf 未生成"; exit 1; }
	@echo "✓ 答辩演示: $(SLIDEDIR)/main.pdf"

kaiti: $(KAITIDIR)/slides.pdf
$(KAITIDIR)/slides.pdf: $(KAITIDIR)/slides.tex $(wildcard $(KAITIDIR)/figures/*.tex)
	cd $(KAITIDIR) && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1
	@echo "✓ 开题答辩: $(KAITIDIR)/slides.pdf"

# ══════════════════════════════════════════════════
#  清理
# ══════════════════════════════════════════════════
clean:
	rm -rf $(SVGDIR) $(BUILDDIR)
	rm -f $(THESISDIR)/main.{pdf,aux,log,toc,bbl,blg,out,bcf,run.xml,xdv,fls,fdb_latexmk}
	rm -f $(SLIDEDIR)/main.{pdf,aux,log,nav,out,snm,toc,vrb}
	rm -f $(KAITIDIR)/slides.{pdf,aux,bbl,log,nav,out,snm,toc}

# ══════════════════════════════════════════════════
#  帮助
# ══════════════════════════════════════════════════
help:
	@echo "make            并行 SVG + 论文 + 答辩"
	@echo "make -jN svg    并行编译全部单图 SVG（推荐 N=$$(nproc)）"
	@echo "make svg-clean  清空 svg/ 与 build/ 目录"
	@echo "make thesis     编译论文"
	@echo "make slides     编译答辩演示"
	@echo "make kaiti      编译开题答辩"
	@echo "make clean      清理全部生成物"
