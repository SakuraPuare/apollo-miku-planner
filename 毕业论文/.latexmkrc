$recorder = 1;
$xelatex = 'xelatex -interaction=nonstopmode -shell-escape -recorder -no-pdf %O %S';
$pdf_mode = 5;  # xelatex -> xdvipdfmx
$biber = 'biber %O %S';
$bibtex_use = 2;
