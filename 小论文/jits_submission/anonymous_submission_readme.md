# Anonymous submission set

This set is prepared for a double-anonymous review workflow. `anonymous.pdf`
is the review manuscript; the source tree contains only the anonymous branch,
generic sections, non-identifying figures, and the frozen replication
material. Identified author metadata, the cover letter, funding details, and
the named declaration fragments are intentionally absent.

The source can be rebuilt with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -jobname=anonymous anonymous.tex
```

The replication package is included for editorial reproducibility. It does
not contain a public author identity or a field-test claim.
