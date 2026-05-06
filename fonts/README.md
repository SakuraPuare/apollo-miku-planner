# Local Fonts

These fonts are vendored so XeLaTeX builds do not depend on whatever font
versions happen to be installed on the current machine.

- `tex-gyre/`: TeX Gyre Termes from TeX Live.
- `fandol/`: Fandol CJK fonts from TeX Live.

The TeX entry point is `fonts/local-fonts.tex`. Build files set
`\ProjectFontDir` and input that file before typesetting project content.
