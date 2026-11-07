"""As quatro páginas do painel do Power BI, escritas em código no formato PBIR.

    python scripts/gerar_relatorio_pbi.py [--saida PASTA_DO_RELATORIO]

Grava a pasta `.Report` do PBIP (por padrão `powerbi/painel-municipios-sp.Report`) no formato de
relatório aprimorado do Power BI (PBIR): `definition.pbir`, que aponta para o modelo semântico em
TMDL, e `definition/`, com um arquivo JSON por página e por visual. Apaga antes o `definition/` antigo
e o `report.json` do formato anterior, que não podem conviver com ele. Grava também o tema do kit
(o mesmo de scripts/gerar_tema.py) em `StaticResources/RegisteredResources/`, onde o relatório o registra.

O que cada página mostra, em que posição, com que medida e em que formato está em `powerbi/roteiro.md`,
que é a especificação legível destas páginas; a decisão de escrevê-las em código está no ADR 0003.
Nenhum número dos dados é digitado aqui: o município de exemplo vem de scripts/comum.py, os anos vêm
dos CSV de dados/tratados/, os nomes dos métodos vêm do TMDL e as cores vêm do kit e do tema.
Depois de gerar, abra `powerbi/painel-municipios-sp.pbip` no Power BI Desktop e atualize os dados.
"""
import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict, namedtuple
from enum import IntEnum
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))

import comum  # noqa: E402
import gerar_tema  # noqa: E402  (também põe estilo/ no caminho)
import estilo_portfolio as ep  # noqa: E402
import tmdl  # noqa: E402

SAIDA_PADRAO = RAIZ / 'powerbi' / 'painel-municipios-sp.Report'
MODELO = '../painel-municipios-sp.SemanticModel'

# Versões dos esquemas do PBIR. São as que o Power BI Desktop grava desde março de 2026
# (relatório 3.2.0, página 2.1.0, visual 2.7.0); o Desktop lê estas e as anteriores.
ESQUEMAS = 'https://developer.microsoft.com/json-schemas/fabric/item/report/'
V_DEFINICAO, V_RELATORIO, V_PAGINA, V_VISUAL = '2.0.0', '3.2.0', '2.1.0', '2.7.0'
V_PAGINAS, V_VERSAO = '1.0.0', '1.0.0'

LARGURA, ALTURA = 1280, 720
GRUPO_INDICADOR = 'Indicador'      # segmentação de Indicador, sincronizada nas páginas 1 e 2
GRUPO_MUNICIPIO = 'Municipio'      # segmentação de município, sincronizada nas páginas 1 e 3
MEDIDAS = 'Medidas'


# ── expressões do PBIR ──────────────────────────────────────────────────
def literal(v):
    if isinstance(v, bool):
        texto = 'true' if v else 'false'
    elif isinstance(v, int):
        texto = f'{v}L'
    elif isinstance(v, float):
        texto = repr(v).removesuffix('.0') + 'D'     # 1D, 2.5D, como o Desktop grava
    else:
        texto = "'" + str(v).replace("'", "''") + "'"
    return {'Literal': {'Value': texto}}


def lit(v):
    return {'expr': literal(v)}


def cor_fixa(hexa):
    return {'solid': {'color': lit(hexa.upper())}}


# No ThemeDataColor do Power BI, os ids 0 e 1 são o fundo e a cor de texto do tema; a cor i de
# dataColors é o id i + 2. Com o id 0, o vermelho de destaque saía branco.
PRIMEIRA_COR_DE_DADOS = 2


def cor_tema(indice, clarear=0.0):
    """Cor `indice` de dataColors do tema (0 = vermelho de destaque, 1 = cinza neutro), clareada na fração dada."""
    return {'solid': {'color': {'expr': {'ThemeDataColor': {'ColorId': PRIMEIRA_COR_DE_DADOS + indice,
                                                            'Percent': clarear}}}}}


def coluna(tabela, nome):
    return {'Column': {'Expression': {'SourceRef': {'Entity': tabela}}, 'Property': nome}}


def medida(nome):
    return {'Measure': {'Expression': {'SourceRef': {'Entity': MEDIDAS}}, 'Property': nome}}


def ref(campo):
    """O nome com que o visual se refere ao campo ('Tabela.Campo'), usado nos seletores de formato."""
    tipo = next(iter(campo))
    return f"{campo[tipo]['Expression']['SourceRef']['Entity']}.{campo[tipo]['Property']}"


def projecao(campo, rotulo=None, ativa=None):
    p = {'field': campo, 'queryRef': ref(campo), 'nativeQueryRef': rotulo or next(iter(campo.values()))['Property']}
    if rotulo:
        p['displayName'] = rotulo
    if ativa:
        p['active'] = True
    return p


def na_fonte(campo, apelido):
    """O mesmo campo, apontando para o apelido do From de um filtro (a forma que o filtro grava)."""
    tipo = next(iter(campo))
    return {tipo: {'Expression': {'SourceRef': {'Source': apelido}}, 'Property': campo[tipo]['Property']}}


def condicao_em(campo, valores, negar=False):
    em = {'In': {'Expressions': [na_fonte(campo, 'f')], 'Values': [[literal(v)] for v in valores]}}
    return {'Not': {'Expression': em}} if negar else em


class Comparacao(IntEnum):
    """O ComparisonKind das condições do PBIR: o número que o JSON grava para cada comparação."""
    IGUAL = 0
    MAIOR = 1
    MAIOR_OU_IGUAL = 2
    MENOR = 3
    MENOR_OU_IGUAL = 4


def comparacao(tipo, esquerda, valor):
    return {'Comparison': {'ComparisonKind': int(tipo), 'Left': esquerda, 'Right': literal(valor)}}


def condicao_comparacao(campo, tipo, valor):
    return comparacao(tipo, na_fonte(campo, 'f'), valor)


def filtro_semantico(campo, condicao):
    entidade = next(iter(campo.values()))['Expression']['SourceRef']['Entity']
    return {'Version': 2, 'From': [{'Name': 'f', 'Entity': entidade, 'Type': 0}],
            'Where': [{'Condition': condicao}]}


def filtro(nome, campo, condicao):
    """Filtro do painel de filtros (de visual ou de página)."""
    tipo = 'Categorical' if ('In' in condicao or 'Not' in condicao) else 'Advanced'
    return {'name': nome, 'field': campo, 'type': tipo, 'filter': filtro_semantico(campo, condicao),
            'howCreated': 'User'}


def paragrafos(*linhas, tamanho=10, negrito=False):
    # A pilha de fontes do tema: só 'Lato' o Desktop não resolve e cai numa serifada.
    estilo = {'fontSize': f'{tamanho}pt', 'fontFamily': gerar_tema.FONTE_TITULO if negrito else gerar_tema.FONTE}
    if negrito:
        estilo['fontWeight'] = 'bold'
    return [{'textRuns': [{'value': linha, 'textStyle': dict(estilo)}]} for linha in linhas]


# ── visuais ─────────────────────────────────────────────────────────────
class Visual:
    """Um visual da página: posição (x, y, largura, altura), tipo, campos, formato e texto alternativo."""

    def __init__(self, nome, caixa, tipo, texto_alternativo, *, ordem, papeis=None, objetos=None,
                 titulo=None, subtitulo=None, filtros=None, ordenar_por=None, sincronia=None, fundo=None):
        self.nome, self.caixa, self.tipo, self.ordem = nome, caixa, tipo, ordem
        self.texto_alternativo = texto_alternativo
        self.papeis, self.objetos = papeis or {}, objetos or {}
        self.titulo, self.subtitulo, self.filtros = titulo, subtitulo, filtros or []
        self.ordenar_por, self.sincronia, self.fundo = ordenar_por, sincronia, fundo

    def json(self, z):
        x, y, w, h = self.caixa
        visual = {'visualType': self.tipo}
        if self.papeis:
            visual['query'] = {'queryState': {papel: {'projections': p} for papel, p in self.papeis.items()}}
            if self.ordenar_por:
                visual['query']['sortDefinition'] = {
                    'sort': [{'field': self.ordenar_por, 'direction': 'Ascending'}], 'isDefaultSort': True}
        if self.objetos:
            visual['objects'] = self.objetos
        recipiente = {'general': [{'properties': {'altText': lit(self.texto_alternativo)}}],
                      'visualHeader': [{'properties': {'show': lit(False)}}]}
        if self.titulo is not None:
            texto = {'expr': self.titulo} if isinstance(self.titulo, dict) else lit(self.titulo)   # dict: fx
            recipiente['title'] = [{'properties': {'show': lit(True), 'text': texto, 'titleWrap': lit(True)}}]
        elif self.tipo != 'textbox':
            recipiente['title'] = [{'properties': {'show': lit(False)}}]
        if self.subtitulo:
            recipiente['subTitle'] = [{'properties': {'show': lit(True), 'text': lit(self.subtitulo),
                                                      'titleWrap': lit(True)}}]
        if self.fundo:
            recipiente['background'] = [{'properties': {'show': lit(True), 'color': cor_fixa(self.fundo),
                                                        'transparency': lit(0.0)}}]
        visual['visualContainerObjects'] = recipiente
        if self.sincronia:
            visual['syncGroup'] = {'groupName': self.sincronia, 'fieldChanges': True, 'filterChanges': True}
        visual['drillFilterOtherVisuals'] = True
        saida = {'$schema': f'{ESQUEMAS}definition/visualContainer/{V_VISUAL}/schema.json',
                 'name': self.nome,
                 'position': {'x': x, 'y': y, 'z': z, 'width': w, 'height': h, 'tabOrder': self.ordem},
                 'visual': visual}
        if self.filtros:
            saida['filterConfig'] = {'filters': self.filtros}
        return saida


def caixa_de_texto(nome, caixa, texto_alternativo, linhas, *, ordem, tamanho=10, negrito=False, fundo=None):
    v = Visual(nome, caixa, 'textbox', texto_alternativo, ordem=ordem, fundo=fundo,
               objetos={'general': [{'properties': {'paragraphs': paragrafos(*linhas, tamanho=tamanho,
                                                                                 negrito=negrito)}}]})
    return v


def titulo_da_pagina(nome, texto):
    """Título da página: caixa de texto em Lato Bold 20, a primeira coisa que o leitor de tela lê."""
    return caixa_de_texto(nome, (24, 16, 900, 40), f'Título da página: {texto}', [texto],
                          ordem=0, tamanho=20, negrito=True)


def segmentacao(nome, caixa, campo, rotulo, texto_alternativo, *, ordem, escolhido, modo='Dropdown',
                sincronia=None, filtros=None):
    """Segmentação de seleção única, já com o valor do estado padrão escolhido."""
    selecao = filtro_semantico(campo, condicao_em(campo, [escolhido]))
    objetos = {
        'data': [{'properties': {'mode': lit(modo)}}],
        'selection': [{'properties': {'strictSingleSelect': lit(True), 'singleSelect': lit(True)}}],
        'general': [{'properties': {'filter': {'filter': selecao}, 'selfFilterEnabled': lit(True)}}],
        'header': [{'properties': {'show': lit(True), 'text': lit(rotulo)}}],
    }
    return Visual(nome, caixa, 'slicer', texto_alternativo, ordem=ordem, papeis={'Values': [projecao(campo, ativa=True)]},
                  objetos=objetos, sincronia=sincronia, filtros=filtros)


def cartao(nome, caixa, campo, rotulo, texto_alternativo, *, ordem, filtros=None, tamanho=None, rotulo_visivel=True):
    """Cartão de um número. O número sai na cor de texto (o tema já faz), e não em vermelho, inteiro
    (unidade de exibição "nenhuma": 11.690, e não "12 Mil"), no formato da medida."""
    rotulos = {'labelDisplayUnits': lit(1.0)}
    if tamanho:
        rotulos['fontSize'] = lit(float(tamanho))
    objetos = {'labels': [{'properties': rotulos}],
               'categoryLabels': [{'properties': {'show': lit(rotulo_visivel)}}],
               'wordWrap': [{'properties': {'show': lit(True)}}]}
    return Visual(nome, caixa, 'card', texto_alternativo, ordem=ordem,
                  papeis={'Values': [projecao(campo, rotulo)]}, objetos=objetos, filtros=filtros)


def estilo_de_linha(campo, largura, *, marcador=False, tracejado=None):
    p = {'strokeWidth': lit(float(largura)), 'showMarker': lit(marcador)}
    if tracejado:
        p['lineStyle'] = lit(tracejado)
    return {'properties': p, 'selector': {'metadata': ref(campo)}}


def cor_da_serie(campo, cor):
    return {'properties': {'fill': cor}, 'selector': {'metadata': ref(campo)}}


def cor_do_valor(campo, valor, cor):
    """Cor de um valor da legenda ou do eixo (o seletor aponta para o valor da coluna)."""
    alvo = comparacao(Comparacao.IGUAL, campo, valor)
    return {'properties': {'fill': cor}, 'selector': {'data': [{'scopeId': alvo}]}}


# ── o que vem dos dados ─────────────────────────────────────────────────
def contexto():
    """Os valores que as páginas usam e que saem dos dados: nada aqui é digitado."""
    municipios = {int(r['cod_ibge']): r['municipio'] for r in comum.ler_csv('dim_municipio.csv')}
    indicadores = {r['indicador_id']: r['nome'] for r in comum.ler_csv('dim_indicador.csv')}
    anos = defaultdict(set)
    for r in comum.ler_csv('indicadores_longo.csv'):
        anos[r['indicador_id']].add(int(r['ano']))
    cod, _ = comum.municipio_de_exemplo()
    previstos = {int(r['ano']) for r in comum.ler_csv('previsao_receita_total.csv')}

    metodos = {r['metodo']: int(r['escolhido']) for r in comum.ler_csv('backtest_metodos.csv')}
    escolhido = next(m for m, e in metodos.items() if e == 1)
    nomes_metodo = tmdl.ler().nomes_dos_metodos()

    niveis = sorted({int(r['nivel']) for r in comum.ler_csv('backtest_cobertura.csv')})
    nivel = niveis[0]                                  # o Intervalo de previsão mais estreito
    por_origem = comum.cobertura_por_origem(nivel)     # a mesma conta de scripts/numeros.py
    pior_origem = min(por_origem, key=por_origem.get)

    return {
        'exemplo': municipios[cod],
        'indicador_padrao': indicadores['saude_pc'],
        'resumo': {i: indicadores[i] for i in comum.INDICADORES_RESUMO},
        'ultimo_ano': max(max(a) for a in anos.values()),
        'ano_padrao': max(anos['saude_pc']),
        'ano_base': min(previstos) - 1,      # último ano observado; os reais são a preços dele
        'ultimo_previsto': max(previstos),
        'metodo_escolhido': nomes_metodo[escolhido],
        'outros_metodos': [nomes_metodo[x] for x in metodos if x != escolhido],
        'nivel': nivel,
        'niveis': niveis,
        'pior_origem': pior_origem,
    }


# Uma página: o nome da pasta, o título que o leitor vê, os visuais e as interações desligadas entre eles.
Pagina = namedtuple('Pagina', 'nome titulo visuais interacoes')


# ── as páginas ──────────────────────────────────────────────────────────
ANO = coluna('dim_ano', 'ano')
MUNICIPIO = coluna('dim_municipio', 'municipio')
INDICADOR = coluna('dim_indicador', 'nome')
ID_INDICADOR = coluna('dim_indicador', 'indicador_id')


# Ano e horizonte são inteiros: no eixo categórico, cada um vira um rótulo, sem "2.017,5" no meio.
EIXO_DE_ANOS = {'properties': {'axisType': lit('Categorical'), 'showAxisTitle': lit(False)}}


def so_anos_observados(nome, c):
    return filtro(nome, ANO, condicao_comparacao(ANO, Comparacao.MENOR_OU_IGUAL, c['ultimo_ano']))


def segmentacao_de_indicador(nome, caixa, ordem, c):
    # A Receita corrente total é da página 3 e fica fora da lista; a seleção é sincronizada nas páginas 1 e 2.
    return segmentacao(nome, caixa, INDICADOR, 'Indicador',
                       'Lista de Indicadores, um por vez: escolhe qual Indicador as séries, a tabela e a dispersão mostram.',
                       ordem=ordem, escolhido=c['indicador_padrao'], modo='Basic', sincronia=GRUPO_INDICADOR,
                       filtros=[filtro('sem_receita_total', ID_INDICADOR, condicao_em(ID_INDICADOR, ['receita_total'],
                                                                                          negar=True))])


def pagina_municipio(c):
    valor, mediana = medida('Valor'), medida('Mediana da faixa')
    q1, q3 = medida('1º quartil da faixa'), medida('3º quartil da faixa')
    visuais = [
        titulo_da_pagina('p1_titulo', 'Indicadores do município'),
        segmentacao('p1_municipio', (24, 64, 320, 72), MUNICIPIO, 'Município',
                    'Lista suspensa com busca: escolhe o município que todas as páginas mostram.',
                    ordem=1, escolhido=c['exemplo'], sincronia=GRUPO_MUNICIPIO),
        segmentacao_de_indicador('p1_indicador', (800, 272, 456, 156), 2, c),
        Visual('p1_evolucao', (24, 272, 760, 412), 'lineChart',
               'Gráfico de linhas por ano: onde o município está, ano a ano, em relação à mediana e aos quartis '
               'dos municípios da mesma faixa de porte, no Indicador escolhido.',
               ordem=3,
               papeis={'Category': [projecao(ANO, ativa=True)],
                       'Y': [projecao(valor, 'Município'), projecao(mediana, 'Mediana da faixa'),
                             projecao(q1, '1º quartil'), projecao(q3, '3º quartil')]},
               ordenar_por=ANO, titulo=medida('Título da evolução'), filtros=[so_anos_observados('ate_ultimo_ano', c)],
               objetos={
                   'dataPoint': [cor_da_serie(valor, cor_tema(0)), cor_da_serie(mediana, cor_tema(1)),
                                 cor_da_serie(q1, cor_tema(1, 0.6)), cor_da_serie(q3, cor_tema(1, 0.6))],
                   'lineStyles': [estilo_de_linha(valor, 2.5, marcador=True), estilo_de_linha(mediana, 2),
                                  estilo_de_linha(q1, 1), estilo_de_linha(q3, 1)],
                   # Legenda no topo: o rótulo na ponta da linha do município batia no do 3º quartil.
                   'legend': [{'properties': {'show': lit(True), 'position': lit('Top')}}],
                   'categoryAxis': [EIXO_DE_ANOS],
                   'valueAxis': [{'properties': {'showAxisTitle': lit(False)}}],
               }),
        cartao('p1_faixa', (360, 64, 300, 80), medida('Faixa de porte'), 'Faixa de porte',
               'Cartão: a Faixa de porte do município, que define com quem ele é comparado.', ordem=4, tamanho=20),
        cartao('p1_na_faixa', (676, 64, 200, 80), medida('Municípios na faixa'), 'Municípios na faixa',
               'Cartão: quantos municípios de SP estão na mesma Faixa de porte.', ordem=5, tamanho=20),
        cartao('p1_populacao', (892, 64, 220, 80), medida('População (Censo 2022)'), 'População (Censo 2022)',
               'Cartão: a população do município no Censo 2022.', ordem=6, tamanho=20),
    ]
    # Quatro cartões de resumo, cada um preso a um Indicador pelo próprio filtro; a segmentação de
    # Indicador não os filtra (ver visualInteractions na página).
    for i, (ident, nome) in enumerate(c['resumo'].items()):
        visuais.append(Visual(
            f'p1_resumo_{ident}', (24 + i * 312, 152, 296, 116), 'multiRowCard',
            f'Cartão de resumo: o último valor de {nome} no município, com a mediana da faixa no mesmo ano e o ano.',
            ordem=7 + i, titulo=nome,
            papeis={'Values': [projecao(medida('Último valor'), 'município'),
                               projecao(medida('Último valor da faixa'), 'mediana da faixa'),
                               projecao(medida('Ano do último valor'), 'ano')]},
            filtros=[filtro('so_este_indicador', ID_INDICADOR, condicao_em(ID_INDICADOR, [ident]))],
            objetos={'dataLabels': [{'properties': {'color': cor_fixa(ep.TINTA), 'fontSize': lit(14.0)}}]}))
    visuais += [
        Visual('p1_tabela', (800, 440, 456, 244), 'tableEx',
               'Tabela por ano: o valor do município, a mediana da faixa, a diferença para a mediana e a posição na faixa.',
               ordem=11,
               papeis={'Values': [projecao(ANO, 'Ano'), projecao(medida('Valor'), 'Valor'),
                                  projecao(medida('Mediana da faixa'), 'Mediana da faixa'),
                                  projecao(medida('Diferença para a mediana'), 'Diferença'),
                                  projecao(medida('Posição na faixa'), 'Posição na faixa')]},
               ordenar_por=ANO, filtros=[so_anos_observados('ate_ultimo_ano', c)],
               objetos={'total': [{'properties': {'totals': lit(False)}}]}),
        caixa_de_texto('p1_nota', (24, 688, 1232, 28),
                       'Nota de leitura sobre os quartis e sobre a mediana.',
                       ['As linhas cinza-claras são o 1º e o 3º quartil dos Municípios parecidos. '
                        'Estar acima ou abaixo da mediana não é, por si, bom nem ruim.'], ordem=12, tamanho=9),
    ]
    interacoes = [{'source': 'p1_indicador', 'target': f'p1_resumo_{i}', 'type': 'NoFilter'} for i in c['resumo']]
    return Pagina('municipio', 'Município', visuais, interacoes)


def pagina_comparacao(c):
    eh_escolhido = medida('É o escolhido')
    # Regra de cor (fx → Regras): o escolhido no vermelho de destaque, os outros no cinza neutro.
    ponto = {'Conditional': {'Cases': [
        {'Condition': comparacao(Comparacao.IGUAL, eh_escolhido, float(caso)),
         'Value': literal(cor.upper())} for caso, cor in ((1, ep.DESTAQUE), (0, ep.NEUTRO))]}}
    visuais = [
        titulo_da_pagina('p2_titulo', 'Comparação na faixa'),
        segmentacao('p2_municipio', (24, 64, 320, 72), coluna('sel_municipio', 'municipio'), 'Município',
                    'Lista suspensa com busca: escolhe o município destacado na dispersão. '
                    'Ela não filtra os outros municípios da faixa.', ordem=1, escolhido=c['exemplo']),
        segmentacao_de_indicador('p2_indicador', (24, 148, 320, 248), 2, c),
        segmentacao('p2_ano', (24, 408, 320, 72), ANO, 'Ano',
                    'Lista suspensa: escolhe o ano da comparação.', ordem=3, escolhido=c['ano_padrao']),
        Visual('p2_dispersao', (360, 64, 600, 636), 'scatterChart',
               'Dispersão: o município escolhido, em destaque, está no meio ou na ponta dos municípios da mesma '
               'faixa de porte? Cada ponto é um município; o eixo horizontal é o valor do Indicador e o vertical, '
               'a população, em escala logarítmica.',
               ordem=4, titulo='Os Municípios parecidos no Indicador e no ano escolhidos',
               subtitulo='Em vermelho, o município escolhido. População do Censo 2022, em escala logarítmica.',
               papeis={'Category': [projecao(MUNICIPIO, ativa=True)],
                       'X': [projecao(medida('Valor'), 'Valor')],
                       'Y': [projecao(medida('População (Censo 2022)'), 'População (Censo 2022)')]},
               filtros=[filtro('na_faixa', medida('Na faixa do escolhido'),
                               condicao_comparacao(medida('Na faixa do escolhido'), Comparacao.IGUAL, 1))],
               objetos={'dataPoint': [{'properties': {'fill': {'solid': {'color': {'expr': ponto}}}},
                                       'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}],
                        'valueAxis': [{'properties': {'axisScale': lit('log'), 'showAxisTitle': lit(True)}}],
                        'categoryAxis': [{'properties': {'showAxisTitle': lit(True)}}],
                        'categoryLabels': [{'properties': {'show': lit(False)}}],
                        'legend': [{'properties': {'show': lit(False)}}]}),
        cartao('p2_posicao', (980, 64, 276, 140), medida('Posição do escolhido'),
               'Posição na faixa (0 a 100%)',
               'Cartão: a Posição na faixa do município escolhido, de 0% (menor valor da faixa) a 100% (maior).', ordem=5),
        cartao('p2_valor', (980, 216, 276, 140), medida('Valor do escolhido'), 'Valor do município',
               'Cartão: o valor do Indicador no município escolhido, no ano escolhido.', ordem=6),
        cartao('p2_mediana', (980, 368, 276, 140), medida('Mediana da faixa do escolhido'), 'Mediana da faixa',
               'Cartão: a mediana do Indicador entre os municípios da mesma faixa, no ano escolhido.', ordem=7),
        cartao('p2_diferenca', (980, 520, 276, 140), medida('Diferença do escolhido'), 'Diferença para a mediana',
               'Cartão: a diferença do município escolhido para a mediana da faixa, em %.', ordem=8),
        caixa_de_texto('p2_nota', (24, 492, 320, 208), 'Nota de leitura da dispersão.',
                       ['Cada ponto é um dos Municípios parecidos (mesma Faixa de porte) que tem dado no ano.',
                        'Posição na faixa: 0% é o menor valor da faixa, e 100%, o maior.',
                        'A página mostra posição e grupo, e não uma lista do maior ao menor: nenhum lado do eixo é, '
                        'por si, melhor.'], ordem=9, tamanho=9),
    ]
    return Pagina('comparacao', 'Comparação na faixa', visuais, [])


def pagina_previsao(c):
    obs, prev = medida('Receita observada'), medida('Receita prevista (linha)')
    i80, s80 = medida('Limite inferior 80%'), medida('Limite superior 80%')
    i95, s95 = medida('Limite inferior 95%'), medida('Limite superior 95%')
    base = c['ano_base']
    aviso = ('Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. '
             'Não leva em conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o '
             'método errou ao prever o passado de municípios do mesmo porte, alargado até a cobertura do teste chegar '
             'ao nível prometido. A página "Como ler" mostra quanto ele cobriu em cada ano deixado de fora. '
             'Projeto de portfólio feito com dado público.')
    visuais = [
        titulo_da_pagina('p3_titulo', 'Previsão da receita'),
        segmentacao('p3_municipio', (24, 64, 320, 72), MUNICIPIO, 'Município',
                    'Lista suspensa com busca: escolhe o município da previsão (a mesma escolha da página Município).',
                    ordem=1, escolhido=c['exemplo'], sincronia=GRUPO_MUNICIPIO),
        Visual('p3_previsao', (24, 148, 840, 468), 'lineChart',
               'Gráfico de linhas: a receita corrente observada do município e a prevista para os próximos anos, '
               f'com os Intervalos de previsão de {" e de ".join(f"{n}%" for n in c["niveis"])}.',
               ordem=2, titulo='Receita corrente observada e prevista, com os Intervalos de previsão',
               subtitulo=f'R$ milhões, a preços de {base}. O eixo vertical não começa no zero.',
               papeis={'Category': [projecao(ANO, ativa=True)],
                       'Y': [projecao(obs, 'Observada'), projecao(prev, 'Prevista'),
                             projecao(i80, 'Limite inferior 80%'), projecao(s80, 'Limite superior 80%'),
                             projecao(i95, 'Limite inferior 95%'), projecao(s95, 'Limite superior 95%')]},
               ordenar_por=ANO,
               objetos={
                   'dataPoint': [cor_da_serie(obs, cor_tema(0)), cor_da_serie(prev, cor_tema(0)),
                                 cor_da_serie(i80, cor_tema(0, 0.5)), cor_da_serie(s80, cor_tema(0, 0.5)),
                                 cor_da_serie(i95, cor_tema(1)), cor_da_serie(s95, cor_tema(1))],
                   # observada sólida, prevista tracejada, as duas no vermelho (como na Figura 3)
                   'lineStyles': [estilo_de_linha(obs, 2.5, marcador=True, tracejado='solid'),
                                  estilo_de_linha(prev, 2, tracejado='dashed'),
                                  estilo_de_linha(i80, 1), estilo_de_linha(s80, 1),
                                  estilo_de_linha(i95, 1, tracejado='dotted'), estilo_de_linha(s95, 1, tracejado='dotted')],
                   'legend': [{'properties': {'show': lit(False)}}],
                   'seriesLabels': [{'properties': {'show': lit(True)}}],
                   'categoryAxis': [EIXO_DE_ANOS],
                   'valueAxis': [{'properties': {'showAxisTitle': lit(False)}}],
               }),
        cartao('p3_prevista', (880, 136, 376, 120), medida('Receita prevista no último ano'),
               f'R$ milhões em {c["ultimo_previsto"]}, a preços de {base}',
               'Cartão: a receita corrente prevista para o último ano da previsão, em R$ milhões.', ordem=3),
        cartao('p3_frase', (880, 272, 376, 344), medida('Texto da previsão'), 'Previsão',
               'A previsão em uma frase: o valor previsto para o último ano e os dois intervalos, em reais.',
               ordem=4, tamanho=14, rotulo_visivel=False),
        caixa_de_texto('p3_aviso', (24, 632, 1232, 80), 'Aviso sobre o que a previsão não considera.', [aviso],
                       ordem=5, tamanho=10, fundo=gerar_tema.zebra()),
    ]
    return Pagina('previsao', 'Previsão da receita', visuais, [])


def pagina_como_ler(c):
    erro, cobertura = medida('Erro médio absoluto'), medida('Cobertura com ajuste')
    metodo = coluna('backtest_metodos', 'metodo_nome')
    origem = coluna('backtest_cobertura', 'origem_fora')
    nivel = coluna('backtest_cobertura', 'nivel')
    fontes = [
        'Fontes. Receitas e despesas: Siconfi, Tesouro Nacional (DCA, anexos I-C e I-E). População, PIB dos '
        'Municípios e IPCA: IBGE. Ideb: INEP. Consultas de pré-natal: SINASC, Ministério da Saúde (DataSUS). '
        'Todas pedem que se credite a fonte; o README traz a condição de uso de cada uma.',
        'Cuidados. A população muda de base com o Censo 2022, e as séries por habitante dão um degrau no ano do '
        'Censo 2022 nos municípios que ele corrigiu. O Ideb é bienal, e município sem rede municipal fica sem Ideb. '
        'Municípios parecidos quer dizer só a mesma Faixa de porte.',
    ]
    # Largura de cada coluna da tabela dos Indicadores: somadas, cabem na tabela sem rolagem lateral, e o
    # texto longo (fórmula, fonte) quebra em linhas.
    colunas = [(INDICADOR, 'Indicador', 190), (coluna('dim_indicador', 'unidade'), 'Unidade', 160),
               (coluna('dim_indicador', 'formula'), 'Fórmula', 330), (coluna('dim_indicador', 'fonte'), 'Fonte', 290),
               (coluna('dim_indicador', 'periodicidade'), 'Periodicidade', 100),
               (coluna('dim_indicador', 'meta'), 'Meta', 130)]
    visuais = [
        titulo_da_pagina('p4_titulo', 'Como ler, fontes e limites'),
        Visual('p4_indicadores', (24, 64, 1232, 360), 'tableEx',
               'Tabela dos Indicadores: o nome, a unidade, a fórmula, a fonte, a periodicidade e a meta de cada um.',
               ordem=1, titulo='Os Indicadores e como cada um é calculado',
               papeis={'Values': [projecao(campo, rotulo) for campo, rotulo, _ in colunas]},
               objetos={'columnHeaders': [{'properties': {'wordWrap': lit(True)}}],
                        'values': [{'properties': {'wordWrap': lit(True)}}],
                        'columnWidth': [{'properties': {'value': lit(float(largura))}, 'selector': {'metadata': ref(campo)}}
                                        for campo, _, largura in colunas]}),
        Visual('p4_erro', (24, 440, 400, 272), 'lineChart',
               'Gráfico de linhas: o erro médio absoluto de cada método de previsão, por horizonte, no teste contra o passado.',
               ordem=2, titulo=f'{c["metodo_escolhido"]}: o método usado na previsão',
               # Sem legenda: os nomes dos métodos não cabem nela; o subtítulo diz qual linha é qual cor.
               subtitulo='Erro médio absoluto ao prever o passado, por anos à frente. Em vermelho, o método usado; '
                         f'em cinza, os demais: {" e ".join(c["outros_metodos"])}.',
               papeis={'Category': [projecao(coluna('backtest_metodos', 'horizonte'), 'Anos à frente', ativa=True)],
                       'Series': [projecao(metodo, 'Método')],
                       'Y': [projecao(erro, 'Erro médio absoluto')]},
               ordenar_por=coluna('backtest_metodos', 'horizonte'),
               objetos={'dataPoint': [cor_do_valor(metodo, c['metodo_escolhido'], cor_tema(0))]
                        + [cor_do_valor(metodo, m, cor_tema(1)) for m in c['outros_metodos']],
                        'legend': [{'properties': {'show': lit(False)}}],
                        'categoryAxis': [{'properties': {'axisType': lit('Categorical')}}],
                        'valueAxis': [{'properties': {'showAxisTitle': lit(False)}}]}),
        Visual('p4_cobertura', (440, 440, 400, 272), 'clusteredColumnChart',
               f'Gráfico de colunas: quanto o Intervalo de previsão de {c["nivel"]}% cobriu em cada ano deixado de fora '
               'no teste contra o passado, com a linha do nível prometido.',
               ordem=3, titulo=f'Cobertura do intervalo de {c["nivel"]}% por ano deixado de fora',
               subtitulo=f'Depois do alargamento. A linha marca {c["nivel"]}%; em vermelho, o ano de menor cobertura.',
               papeis={'Category': [projecao(origem, 'Ano deixado de fora', ativa=True)],
                       'Y': [projecao(cobertura, 'Cobertura')]},
               ordenar_por=origem,
               filtros=[filtro('nivel', nivel, condicao_em(nivel, [c['nivel']]))],
               objetos={'dataPoint': [{'properties': {'fill': cor_tema(1)}},
                                      cor_do_valor(origem, c['pior_origem'], cor_tema(0))],
                        'y1AxisReferenceLine': [{'properties': {
                            'show': lit(True), 'displayName': lit(f'{c["nivel"]}%'), 'value': lit(c['nivel'] / 100),
                            'lineColor': cor_tema(1), 'style': lit('dashed')}, 'selector': {'id': '1'}}],
                        'valueAxis': [{'properties': {'start': lit(0.0), 'showAxisTitle': lit(False)}}],
                        'categoryAxis': [EIXO_DE_ANOS]}),
        caixa_de_texto('p4_fontes', (856, 440, 400, 272), 'Fontes, licenças e cuidados de leitura.', fontes,
                       ordem=4, tamanho=10),
    ]
    return Pagina('como_ler', 'Como ler, fontes e limites', visuais, [])


# ── gravação ────────────────────────────────────────────────────────────
def gravar(arq, dados):
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def relatorio():
    tema = gerar_tema.NOME_ARQUIVO
    return {
        '$schema': f'{ESQUEMAS}definition/report/{V_RELATORIO}/schema.json',
        'themeCollection': {'customTheme': {
            'name': tema, 'type': 'RegisteredResources',
            'reportVersionAtImport': {'visual': V_VISUAL, 'report': V_RELATORIO, 'page': V_PAGINA}}},
        'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources',
                              'items': [{'name': tema, 'path': tema, 'type': 'CustomTheme'}]}],
        'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized',
                     'defaultDrillFilterOtherVisuals': True, 'allowChangeFilterTypes': True,
                     'useDefaultAggregateDisplayName': True},
    }


def gerar(saida, c):
    saida = Path(saida)
    definicao = saida / 'definition'
    if definicao.exists():
        shutil.rmtree(definicao)
    (saida / 'report.json').unlink(missing_ok=True)   # formato anterior ao PBIR

    gravar(saida / 'definition.pbir', {
        '$schema': f'{ESQUEMAS}definitionProperties/{V_DEFINICAO}/schema.json',
        'version': '4.0', 'datasetReference': {'byPath': {'path': MODELO}}})
    gravar(saida / 'StaticResources' / 'RegisteredResources' / gerar_tema.NOME_ARQUIVO, gerar_tema.tema())
    gravar(definicao / 'version.json', {'$schema': f'{ESQUEMAS}definition/versionMetadata/{V_VERSAO}/schema.json',
                                        'version': '2.0.0'})
    gravar(definicao / 'report.json', relatorio())

    paginas = [f(c) for f in (pagina_municipio, pagina_comparacao, pagina_previsao, pagina_como_ler)]
    for p in paginas:
        pasta = definicao / 'pages' / p.nome
        pagina = {'$schema': f'{ESQUEMAS}definition/page/{V_PAGINA}/schema.json', 'name': p.nome,
                  'displayName': p.titulo, 'displayOption': 'FitToPage', 'height': ALTURA, 'width': LARGURA}
        if p.interacoes:
            pagina['visualInteractions'] = p.interacoes
        gravar(pasta / 'page.json', pagina)
        for z, v in enumerate(p.visuais):
            gravar(pasta / 'visuals' / v.nome / 'visual.json', v.json(1000 * (z + 1)))
    gravar(definicao / 'pages' / 'pages.json', {
        '$schema': f'{ESQUEMAS}definition/pagesMetadata/{V_PAGINAS}/schema.json',
        'pageOrder': [p.nome for p in paginas], 'activePageName': paginas[0].nome})
    return paginas


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--saida', default=str(SAIDA_PADRAO), help='pasta .Report do PBIP (padrão: a do projeto)')
    args = ap.parse_args()
    paginas = gerar(args.saida, contexto())
    for p in paginas:
        print(f'{p.titulo}: {len(p.visuais)} visuais')
    print('gravado', args.saida)


if __name__ == '__main__':
    main()
