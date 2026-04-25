TEX      := xelatex
TEXFLAGS := -interaction=nonstopmode
BIBER    := biber

FIGDIR   := 图片
THESISDIR:= 毕业论文
SLIDEDIR := 答辩演示
KAITIDIR := 开题答辩

SVGDIR   := $(FIGDIR)/svg
PDFDIR   := $(FIGDIR)/pdf

# 图源文件（figures.tex 的依赖）
FIGS     := $(wildcard $(FIGDIR)/fig_*.tex)
FIGMAIN  := $(FIGDIR)/figures.tex
FIGPDF   := $(FIGDIR)/figures.pdf

.PHONY: all figures svg pdf thesis slides kaiti clean help

# ══════════════════════════════════════════════════
#  默认：图片 + SVG + 论文 + 答辩演示
# ══════════════════════════════════════════════════
all: svg thesis slides

# ── 图片 ─────────────────────────────────────────
$(FIGPDF): $(FIGMAIN) $(FIGS)
	-cd $(FIGDIR) && $(TEX) $(TEXFLAGS) figures.tex >/dev/null 2>&1
	@test -f $(FIGPDF) || { echo "错误: figures.pdf 未生成"; exit 1; }

figures: $(FIGPDF)

# ── SVG 导出 ─────────────────────────────────────
svg: $(FIGPDF)
	@mkdir -p $(SVGDIR)
	cd $(FIGDIR) && bash tex2svg.sh figures.tex svg

# ── 单页 PDF 导出（裁白边）─────────────────────
pdf: $(FIGPDF)
	@mkdir -p $(PDFDIR)
	pdfseparate $(FIGPDF) $(PDFDIR)/%d.pdf
	@for f in $(PDFDIR)/*.pdf; do pdfcrop "$$f" "$$f" >/dev/null 2>&1; done
	@echo "已导出 $$(ls $(PDFDIR)/*.pdf | wc -l) 个裁剪后的 PDF"

# ── 论文（latexmk 自动判断编译次数，xdv 中间格式加速）────────
# 论文直接 \input TikZ 源文件，不依赖 figures.pdf，可与 svg 并行
thesis:
	cd $(THESISDIR) && latexmk thesis.tex >/dev/null 2>&1
	@test -f $(THESISDIR)/thesis.pdf || { echo "错误: thesis.pdf 未生成"; exit 1; }
	@echo "✓ 论文: $(THESISDIR)/thesis.pdf"

# ── 答辩演示 ─────────────────────────────────────
slides: $(SLIDEDIR)/main.pdf
$(SLIDEDIR)/main.pdf: $(SLIDEDIR)/main.tex
	-cd $(SLIDEDIR) && $(TEX) $(TEXFLAGS) main.tex >/dev/null 2>&1
	@test -f $(SLIDEDIR)/main.pdf || { echo "错误: slides main.pdf 未生成"; exit 1; }
	@echo "✓ 答辩演示: $(SLIDEDIR)/main.pdf"

# ── 开题答辩 ─────────────────────────────────────
kaiti: $(KAITIDIR)/slides.pdf
$(KAITIDIR)/slides.pdf: $(KAITIDIR)/slides.tex $(wildcard $(KAITIDIR)/figures/*.tex)
	cd $(KAITIDIR) && $(TEX) $(TEXFLAGS) slides.tex >/dev/null 2>&1
	@echo "✓ 开题答辩: $(KAITIDIR)/slides.pdf"

# ── 清理 ─────────────────────────────────────────
clean:
	rm -f $(FIGPDF) $(FIGDIR)/figures.{aux,log}
	rm -rf $(SVGDIR) $(PDFDIR)
	rm -f $(THESISDIR)/main.{pdf,aux,log,toc,bbl,blg,out,bcf,run.xml,xdv,fls,fdb_latexmk}
	rm -f $(SLIDEDIR)/main.{pdf,aux,log,nav,out,snm,toc,vrb}
	rm -f $(KAITIDIR)/slides.{pdf,aux,bbl,log,nav,out,snm,toc}

# ── 帮助 ─────────────────────────────────────────
help:
	@echo "make          图片SVG + 论文 + 答辩演示"
	@echo "make figures  编译 figures.pdf"
	@echo "make svg      导出 SVG"
	@echo "make pdf      导出裁白边单页 PDF"
	@echo "make thesis   编译论文"
	@echo "make slides   编译答辩演示"
	@echo "make kaiti    编译开题答辩"
	@echo "make clean    清理所有生成文件"
