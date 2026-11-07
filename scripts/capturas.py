"""Corta o PDF exportado pelo Power BI Desktop em um PNG por página.

    python scripts/capturas.py

Antes: no Power BI Desktop, Arquivo → Exportar → Exportar para PDF, salvando powerbi/capturas/paginas.pdf
(ver powerbi/roteiro.md, seção "Capturas"). A captura da visão de modelo (05-modelo.png) é feita à mão.
"""
import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / 'powerbi' / 'capturas'
NOMES = ['01-municipio.png', '02-comparacao.png', '03-previsao.png', '04-como-ler.png']
DPI = 160


def main():
    pdf = PASTA / 'paginas.pdf'
    if not pdf.exists():
        sys.exit(f'não achei {pdf.relative_to(RAIZ)}: exporte o relatório para PDF primeiro (powerbi/roteiro.md).')
    doc = pymupdf.open(pdf)
    if doc.page_count != len(NOMES):
        sys.exit(f'o PDF tem {doc.page_count} páginas e o roteiro pede {len(NOMES)}: confira a ordem das páginas no relatório.')
    for pagina, nome in zip(doc, NOMES):
        pagina.get_pixmap(dpi=DPI).save(PASTA / nome)
        print('gravado', (PASTA / nome).relative_to(RAIZ))


if __name__ == '__main__':
    main()
