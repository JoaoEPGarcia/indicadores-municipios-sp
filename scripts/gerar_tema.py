"""Tema do Power BI a partir do kit de estilo do portfólio.

    python scripts/gerar_tema.py

Nenhuma cor é digitada aqui: os hexadecimais vêm de `estilo/estilo_portfolio.py` (Set1 e escala
neutra) e o cinza da zebra vem de `estilo/modelo_relatorio.tex`, o mesmo do relatório em LaTeX.
Grava o tema em dois lugares: `powerbi/tema.json`, para quem quiser aplicá-lo à mão
(Exibir → Temas → Procurar temas), e dentro do relatório do PBIP, onde o Power BI Desktop já o encontra.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'estilo'))

import estilo_portfolio as ep  # noqa: E402

NOME_ARQUIVO = 'tema-portfolio.json'
SAIDAS = [
    RAIZ / 'powerbi' / 'tema.json',
    RAIZ / 'powerbi' / 'painel-municipios-sp.Report' / 'StaticResources' / 'RegisteredResources' / NOME_ARQUIVO,
]

# A Lato precisa estar instalada no Windows (ver powerbi/roteiro.md, passo 0). Sem ela, o Power BI
# cai para a próxima da lista.
FONTE = "Lato, 'Segoe UI', sans-serif"
FONTE_TITULO = "'Lato Bold', Lato, 'Segoe UI Semibold', sans-serif"


def zebra():
    texto = (RAIZ / 'estilo' / 'modelo_relatorio.tex').read_text(encoding='utf-8')
    return '#' + re.search(r'\\definecolor\{zebraclara\}\{HTML\}\{([0-9A-Fa-f]{6})\}', texto).group(1).upper()


def h(cor):
    return cor.upper()


def tema():
    ZEBRA = zebra()
    return {
        'name': 'Portfólio: indicadores dos municípios de SP',
        # Ordem: a série que o visual aponta (o Município selecionado) pega a primeira cor, o vermelho de
        # destaque; o contexto (mediana, quartis) pega o neutro; o azul fica para distribuição. As demais
        # seguem a Set1, sem o amarelo.
        'dataColors': [h(c) for c in [ep.DESTAQUE, ep.NEUTRO, ep.AZUL, ep.VERDE, ep.ROXO,
                                      ep.LARANJA, ep.MARROM, ep.ROSA]],
        'background': h(ep.BRANCO),
        'backgroundLight': ZEBRA,
        'backgroundNeutral': h(ep.GRAY_20),
        'foreground': h(ep.TINTA),
        'foregroundNeutralSecondary': h(ep.TINTA_SECUNDARIA),
        'tableAccent': h(ep.TINTA_SECUNDARIA),
        # Nenhum Indicador tem um lado "bom" que valha para todo município: as cores de sentimento
        # existem porque o Power BI as pede, e nenhum visual do roteiro as usa.
        'good': h(ep.VERDE),
        'neutral': h(ep.NEUTRO),
        'bad': h(ep.VERMELHO),
        'maximum': h(ep.SEQUENCIAL[-1]),
        'center': h(ep.SEQUENCIAL[2]),
        'minimum': h(ep.SEQUENCIAL[0]),
        'textClasses': {
            'title': {'fontFace': FONTE_TITULO, 'fontSize': 14, 'color': h(ep.TINTA)},
            'header': {'fontFace': FONTE_TITULO, 'fontSize': 12, 'color': h(ep.TINTA)},
            'label': {'fontFace': FONTE, 'fontSize': 10, 'color': h(ep.TINTA_SECUNDARIA)},
            # número grande de cartão em tinta, e não em vermelho: o vermelho fica só nas marcas
            'callout': {'fontFace': FONTE_TITULO, 'fontSize': 28, 'color': h(ep.TINTA)},
        },
        'visualStyles': {
            '*': {
                '*': {
                    'background': [{'show': True, 'color': {'solid': {'color': h(ep.BRANCO)}}, 'transparency': 0}],
                    'border': [{'show': False}],
                    'dropShadow': [{'show': False}],
                    'title': [{'fontFamily': FONTE_TITULO, 'fontSize': 12, 'fontColor': {'solid': {'color': h(ep.TINTA)}},
                               'alignment': 'left'}],
                    'categoryAxis': [{'gridlineShow': False, 'fontFamily': FONTE,
                                      'labelColor': {'solid': {'color': h(ep.TINTA_SECUNDARIA)}}}],
                    'valueAxis': [{'gridlineShow': True, 'gridlineColor': {'solid': {'color': h(ep.GRAY_20)}},
                                   'gridlineStyle': 'dashed', 'fontFamily': FONTE,
                                   'labelColor': {'solid': {'color': h(ep.TINTA_SECUNDARIA)}}}],
                    'legend': [{'show': False, 'fontFamily': FONTE,
                                'labelColor': {'solid': {'color': h(ep.TINTA_SECUNDARIA)}}}],
                    'labels': [{'fontFamily': FONTE, 'color': {'solid': {'color': h(ep.TINTA_SECUNDARIA)}}}],
                }
            },
            'page': {
                '*': {
                    'background': [{'color': {'solid': {'color': h(ep.BRANCO)}}, 'transparency': 0}],
                    'outspace': [{'color': {'solid': {'color': h(ep.BRANCO)}}}],
                }
            },
            'tableEx': {
                '*': {
                    'grid': [{'rowPadding': 4, 'gridHorizontal': False, 'gridVertical': False}],
                    'columnHeaders': [{'fontFamily': FONTE_TITULO, 'fontColor': {'solid': {'color': h(ep.TINTA)}},
                                       'backColor': {'solid': {'color': h(ep.BRANCO)}}}],
                    'values': [{'fontFamily': FONTE, 'fontColorPrimary': {'solid': {'color': h(ep.TINTA)}},
                                'backColorPrimary': {'solid': {'color': ZEBRA}},
                                'fontColorSecondary': {'solid': {'color': h(ep.TINTA)}},
                                'backColorSecondary': {'solid': {'color': h(ep.BRANCO)}}}],
                }
            },
            'card': {
                '*': {
                    'background': [{'show': True, 'color': {'solid': {'color': ZEBRA}}, 'transparency': 0}],
                    'categoryLabels': [{'fontFamily': FONTE, 'color': {'solid': {'color': h(ep.TINTA_SECUNDARIA)}}}],
                }
            },
        },
    }


def main():
    texto = json.dumps(tema(), ensure_ascii=False, indent=2) + '\n'
    for s in SAIDAS:
        s.parent.mkdir(parents=True, exist_ok=True)
        s.write_text(texto, encoding='utf-8')
        print('gravado', s.relative_to(RAIZ))


if __name__ == '__main__':
    main()
