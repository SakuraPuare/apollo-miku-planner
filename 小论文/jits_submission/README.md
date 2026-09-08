# MIKU JITS submission workspace

This directory is the prepared submission workspace for the Journal of
Intelligent Transportation Systems Research Article
“Interaction-Aware Space--Time Homotopy Constraints for Path--Velocity
Planning in Dynamic Multi-Obstacle Traffic.” It contains a named version for
the standard submission and a separately validated anonymous version to use
only if the live submission portal requests double-anonymous review.

## Files to upload

- `manuscript.pdf`: named manuscript with the supplied author, affiliation,
  funding, CRediT, disclosure, and corresponding-author information.
- `anonymous.pdf`: double-anonymous manuscript; the PDF metadata author is
  `Anonymous` and identifying declarations are withheld.
- `manuscript.tex`, `anonymous.tex`, `named_metadata.tex`, `sections/`,
  `figures/`, `interact.cls`, and `references.bib`: complete LaTeX source for
  clean recompilation. Identified declaration fragments are the files ending
  in `_named.tex` under `sections/`.
- `supplement/`: frozen data, source code, tests, provenance, and reproduction
  instructions.
- `cover_letter.md`: editor-facing cover letter draft.
- `submission_checklist.md`: final portal and author-confirmation checklist.
- `author_information.md`: named-version metadata for the submission portal;
  do not include it in a double-anonymous reviewer file set.

The `deliverables/` directory contains the final named and anonymous PDFs,
source archives, a standalone supplement archive, and their SHA-256 manifest.
Run `./package_submission.sh` after validation to rebuild this upload set.
Generated auxiliary files and visual inspection images under `build/` are
working files and are excluded from the submission archives.

## Clean build

With TeX Live and `latexmk` installed:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -jobname=anonymous anonymous.tex
```

The class file is the Interact author template extracted from the supplied
`InteractAPALaTeX.zip`. Both commands were tested from this directory. A
clean build should finish without undefined citations or cross-references.

## Validation and packaging

```bash
python3 validate_submission.py
./package_submission.sh
cd deliverables && sha256sum -c SHA256SUMS
```

The packaging script compiles both manuscripts, creates identity-separated
source trees in a temporary directory, checks the anonymous tree and PDF for
the supplied identity tokens, and writes the upload artifacts.

## Anonymous-review handling

Upload `anonymous.pdf` for a double-anonymous review workflow, or use the
anonymous source archive if the portal requests source files. Upload the
named PDF, cover letter, and author metadata only in the identified/editor
parts of the portal. The named source archive contains a separate metadata
file; it should not be used as the anonymous source set.

## Evidence policy

The 3,500-case headline statistics come only from the frozen
`miku-random-v2` archive identified in `supplement/README.md`. The 700-case
rolling protocol, 70-case finite-grid reference, and Apollo screenshots are
reported as separate evidence streams. No statement in this package should be
read as a road test, native Apollo benchmark, public-dataset comparison, or
continuous global-optimality result.
