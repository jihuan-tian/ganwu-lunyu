.PHONY: all artwork body pdf clean

all: pdf

artwork:
	python3 tools/generate_artwork.py

from-odt:
	python3 tools/odt_to_tex.py

pdf: artwork
	latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
	cp -f main.pdf 感悟论语.pdf

clean:
	latexmk -C main.tex
	rm -f main.pdf 感悟论语.pdf
