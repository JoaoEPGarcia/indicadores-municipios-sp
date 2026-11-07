"""Gera excel/painel-municipios-sp.xlsx com Python (XlsxWriter), sem abrir o Excel.

    python scripts/montar_excel.py                       # grava excel/painel-municipios-sp.xlsx
    python scripts/montar_excel.py --saida outra.xlsx    # grava em outro lugar (os testes usam isto)

A planilha é completada no Excel para a web (docs/adr/0004-planilha-sem-power-query.md): lá se insere a
tabela dinâmica e a segmentação da aba Explorar, e lá as fórmulas são calculadas. O script faz o resto:

  1. Dados: os CSV de dados/tratados/ entram como cinco tabelas nomeadas (tIndicadores, tMunicipios, tFato,
     tReferencia, tPrevisao). A tabela Fato recebe o nome do Indicador, mesclado aqui.
  2. Painel: escolha do município e do Indicador por lista, cartões e tabela com PROCX, gráfico de linhas.
  3. Explorar: só as instruções; a área a partir da linha 8 fica vazia para a tabela dinâmica e a segmentação.
  4. Previsão: série observada e prevista, com os Intervalos de previsão, frase e gráfico.
  5. Leia-me e Fontes e licenças.

As fórmulas vão em inglês, como o arquivo as guarda (XLOOKUP, LET, SEQUENCE); o Excel em português as mostra
como PROCX, LET e SEQUÊNCIA. O arquivo pede prefixos que o Excel não mostra (_xlfn. nas funções novas, _xlpm.
nos nomes do LET): a função `fx` os põe. As fórmulas com vetores vão como fórmula de matriz dinâmica, que é o
que o Excel 365 grava quando a pessoa digita. O valor guardado de cada fórmula fica vazio: quem calcula é o
Excel, ao abrir. Cores e fonte vêm do kit (estilo/estilo_portfolio.py); os números escritos em texto vêm de
scripts/numeros.py.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'estilo'))
sys.path.insert(0, str(RAIZ / 'scripts'))

import estilo_portfolio as ep  # noqa: E402
import comum  # noqa: E402
import numeros  # noqa: E402
from gerar_tema import zebra  # noqa: E402

SAIDA = RAIZ / 'excel' / 'painel-municipios-sp.xlsx'
TRATADOS = RAIZ / 'dados' / 'tratados'
FONTE = 'Lato'
ORIGEM = 'scripts/montar_excel.py'      # marca da planilha de referência (nome definido OrigemDaPlanilha)

DESTAQUE, NEUTRO, TINTA, TINTA2 = ep.DESTAQUE, ep.NEUTRO, ep.TINTA, ep.TINTA_SECUNDARIA
CLARO, GRADE, BRANCO = ep.GRAY_20, ep.GRAY_20, ep.BRANCO
ZEBRA = zebra()
REALCE_ENTRADA = ep.misturar(ep.AZUL, 0.85)    # célula onde o leitor escolhe
ESTILO_TABELA = 'Table Style Light 1'          # cinza, sem cor: o mais perto da zebra do kit entre os prontos

# Linhas e células que o passo a passo e o conferidor citam.
LINHA_TABELA = 13           # primeira linha da tabela dos sete Indicadores (Painel)
LINHA_DADOS_GRAFICO = 46    # anos do gráfico do Painel; as séries vêm logo abaixo
LINHA_PREVISAO = 8          # primeira linha da série da aba Previsão
CANTO_DINAMICA = 'D8'       # canto da tabela dinâmica da aba Explorar


# ── fórmulas ─────────────────────────────────────────────────────────────
FUNCOES_NOVAS = ('XLOOKUP', 'LET', 'SEQUENCE', 'MAXIFS')
VETORIAL = re.compile(r'\b(XLOOKUP|SEQUENCE|LET|SUMPRODUCT|MAXIFS)\(')


def _fatiar(f):
    """Divide a fórmula em pedaços: ('fixo', texto entre aspas ou entre colchetes) e ('codigo', o resto)."""
    pedacos, i = [], 0
    while i < len(f):
        if f[i] == '"':
            j = i + 1
            while j < len(f):
                if f[j] == '"' and (j + 1 == len(f) or f[j + 1] != '"'):
                    break
                j += 2 if f[j] == '"' else 1
            pedacos.append(('fixo', f[i:j + 1]))
            i = j + 1
        elif f[i] == '[':
            prof, j = 0, i
            while j < len(f):
                prof += {'[': 1, ']': -1}.get(f[j], 0)
                if prof == 0:
                    break
                j += 1
            pedacos.append(('fixo', f[i:j + 1]))
            i = j + 1
        else:
            j = i
            while j < len(f) and f[j] not in '"[':
                j += 1
            pedacos.append(('codigo', f[i:j]))
            i = j
    return pedacos


def _nomes_do_let(f):
    """Os nomes que cada LET da fórmula define (os argumentos ímpares, menos o último)."""
    nomes = set()
    codigo = ''.join(t if tipo == 'codigo' else ' ' * len(t) for tipo, t in _fatiar(f))
    for m in re.finditer(r'\bLET\(', codigo):
        args, prof, ini = [], 0, m.end()
        for k in range(m.end(), len(codigo)):
            c = codigo[k]
            if c == '(':
                prof += 1
            elif c == ')' and prof > 0:
                prof -= 1
            elif c == ')' or (c == ',' and prof == 0):
                args.append(f[ini:k].strip())
                ini = k + 1
                if c == ')':
                    break
        nomes |= set(args[:-1:2])
    return nomes


def fx(f):
    """Fórmula como o arquivo a guarda: _xlfn. nas funções novas e _xlpm. nos nomes do LET (fora de texto e de colchete)."""
    nomes = _nomes_do_let(f)
    saida = []
    for tipo, t in _fatiar(f):
        if tipo == 'codigo':
            t = re.sub(r'(?<![\w.])(' + '|'.join(FUNCOES_NOVAS) + r')\(', r'_xlfn.\1(', t)
            if nomes:
                t = re.sub(r'(?<![\w.$!])(' + '|'.join(sorted(nomes, key=len, reverse=True)) + r')(?![\w(!])',
                           r'_xlpm.\1', t)
        saida.append(t)
    return ''.join(saida)


class Aba:
    """Uma aba com os formatos do kit; escreve texto e fórmula com fonte, cor e formato de número."""

    def __init__(self, wb, ws):
        self.wb, self.ws, self._formatos = wb, ws, {}

    def formato(self, **p):
        p = {'font_name': FONTE, 'font_size': 10, 'font_color': TINTA, 'valign': 'vcenter', **p}
        chave = tuple(sorted(p.items()))
        if chave not in self._formatos:
            self._formatos[chave] = self.wb.add_format(p)
        return self._formatos[chave]

    def texto(self, celula, valor, tam=10, negrito=False, cor=TINTA, quebra=False, **extra):
        f = self.formato(font_size=tam, bold=negrito, font_color=cor, text_wrap=quebra,
                         valign='top' if quebra else 'vcenter', **extra)
        self.ws.write(celula, valor, f)

    def formula(self, celula, f, num=None, negrito=False, cor=TINTA, tam=10, comum=False, **extra):
        """Fórmula com vetor ou função nova vai como matriz dinâmica; `comum=True` força a fórmula comum."""
        props = dict(bold=negrito, font_color=cor, font_size=tam, **extra)
        if num:
            props['num_format'] = num
        fmt = self.formato(**props)
        if VETORIAL.search(f) and not comum:
            self.ws.write_dynamic_array_formula(f'{celula}:{celula}', fx(f), fmt, '')
        else:
            self.ws.write_formula(celula, fx(f), fmt, '')

    def mesclar(self, intervalo, valor='', **p):
        self.ws.merge_range(intervalo, valor, self.formato(**p))


def grafico_linhas(wb, titulo, tam_titulo, negrito=True):
    g = wb.add_chart({'type': 'line'})
    fonte = {'name': FONTE, 'color': TINTA2}
    g.set_title({'name': titulo, 'name_font': {'name': FONTE, 'size': tam_titulo, 'bold': negrito, 'color': TINTA}})
    g.set_y_axis({'major_gridlines': {'visible': True, 'line': {'color': GRADE, 'dash_type': 'dash'}},
                  'line': {'none': True}, 'num_font': fonte, 'num_format': '#,##0'})
    g.set_x_axis({'num_font': fonte, 'line': {'color': GRADE}})
    g.set_legend({'position': 'bottom', 'font': fonte})
    g.set_chartarea({'border': {'none': True}})
    return g


def serie(g, nome, valores, categorias, cor, espessura, marcador=False, traco=None):
    linha = {'color': cor, 'width': espessura}
    if traco:
        linha['dash_type'] = traco
    g.add_series({'name': nome, 'values': valores, 'categories': categorias, 'line': linha,
                  'marker': ({'type': 'circle', 'size': 6, 'fill': {'color': cor}, 'border': {'color': BRANCO}}
                             if marcador else {'type': 'none'})})


# ── dados ────────────────────────────────────────────────────────────────
# (aba, tabela, arquivo); a ordem das colunas é a do CSV.
DADOS = [
    ('Indicadores', 'tIndicadores', 'dim_indicador.csv'),
    ('Municípios', 'tMunicipios', 'dim_municipio.csv'),
    ('Dados', 'tFato', 'indicadores_longo.csv'),
    ('Referência', 'tReferencia', 'referencia_faixa.csv'),
    ('Previsões', 'tPrevisao', 'previsao_receita_total.csv'),
]


def ler_dados():
    d = {tabela: pd.read_csv(TRATADOS / arquivo) for _, tabela, arquivo in DADOS}
    # a mescla que a tabela dinâmica precisa: o nome do Indicador ao lado do código, como um PROCV feito uma vez
    nomes = d['tIndicadores'].set_index('indicador_id').nome
    d['tFato']['indicador'] = d['tFato'].indicador_id.map(nomes)
    return d


def tabela(aba, nome, df):
    ws = aba.ws
    linhas = [[None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v) for v in r]
              for r in df.itertuples(index=False)]
    ws.add_table(0, 0, len(df), len(df.columns) - 1, {
        'name': nome, 'style': ESTILO_TABELA, 'data': linhas,
        'columns': [{'header': c, 'header_format': aba.formato(bold=True)} for c in df.columns]})
    for k, c in enumerate(df.columns):
        tamanhos = df[c].astype(str).str.len()
        quebra = tamanhos.max() > 60
        largura = min(60, max(10, len(c) + 2, int(tamanhos.quantile(0.9)) + 2))
        ws.set_column(k, k, largura, aba.formato(text_wrap=quebra, valign='top' if quebra else 'vcenter'))
    ws.freeze_panes(1, 0)


# ── abas ─────────────────────────────────────────────────────────────────
def aba_painel(a, N, n_anos, ano0):
    ws = a.ws
    ws.hide_gridlines(2)
    ws.set_column('A:A', 2)
    ws.set_column('B:B', 44)
    ws.set_column('C:C', 30)
    ws.set_column('D:H', 15)
    a.texto('B1', 'Indicadores dos municípios de São Paulo', 16, True)
    a.texto('B2', 'Escolha o município e o indicador nas células azuis. Tudo nesta aba e na aba "Previsão" se recalcula.',
            cor=TINTA2)

    rotulos = ['Município (escolha na lista)', 'Código IBGE', 'Faixa de porte (municípios parecidos)', 'Municípios na faixa',
               'População (Censo 2022)', 'Região geográfica imediata (IBGE)']
    for k, r in enumerate(rotulos):
        a.texto(f'B{4 + k}', r)
    a.texto('C4', N['NumExemplo']['valor'], bg_color=REALCE_ENTRADA)
    ws.data_validation('C4', {'validate': 'list', 'source': '=ListaMunicipios'})
    esq = dict(align='left')
    a.formula('C5', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[cod_ibge], "escolha um município")', '0', **esq)
    a.formula('C6', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[faixa_porte], "")', **esq)
    a.formula('C7', '=COUNTIFS(tMunicipios[faixa_porte], $C$6)', '#,##0', **esq)
    a.formula('C8', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[populacao_censo_2022], "")', '#,##0', **esq)
    a.formula('C9', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[regiao_imediata], "")', **esq)

    a.texto('B11', 'Último valor de cada indicador, comparado com os municípios da faixa', 12, True)
    cab = ['Indicador', 'Unidade', 'Último ano com dado', 'Valor do município', 'Mediana da faixa',
           'Diferença para a mediana', 'Posição na faixa (0% a 100%)']
    for k, h in enumerate(cab):
        a.texto(xl_rowcol_to_cell(LINHA_TABELA - 2, 1 + k), h, negrito=True, quebra=True, bottom=1, bottom_color=TINTA2)
    ws.set_row(LINHA_TABELA - 2, 30)
    # coluna A, discreta: o código do Indicador, que as fórmulas da linha usam
    for k, ind in enumerate(comum.INDICADORES_PAINEL):
        r = LINHA_TABELA + k
        z = dict(bg_color=ZEBRA) if k % 2 == 0 else {}
        dir_ = dict(align='right', **z)
        a.texto(f'A{r}', ind, 8, cor=CLARO)
        a.formula(f'B{r}', f'=XLOOKUP($A{r}, tIndicadores[indicador_id], tIndicadores[nome])', **z)
        a.formula(f'C{r}', f'=XLOOKUP($A{r}, tIndicadores[indicador_id], tIndicadores[unidade])', cor=TINTA2, **z)
        a.formula(f'D{r}', f'=LET(a, MAXIFS(tFato[ano], tFato[cod_ibge], $C$5, tFato[indicador_id], $A{r}), IF(a=0, "n.d.", a))',
                  '0', **dir_)
        a.formula(f'E{r}', f'=XLOOKUP(1, (tFato[cod_ibge]=$C$5)*(tFato[ano]=$D{r})*(tFato[indicador_id]=$A{r}), tFato[valor], "n.d.")',
                  '#,##0.0', **dir_)
        a.formula(f'F{r}', f'=XLOOKUP(1, (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]=$D{r})*(tReferencia[indicador_id]=$A{r}), '
                           f'tReferencia[mediana], "n.d.")', '#,##0.0', **dir_)
        a.formula(f'G{r}', f'=IF(AND(ISNUMBER(E{r}), ISNUMBER(F{r})), E{r}/F{r}-1, "n.d.")', '+0.0%;-0.0%;0.0%', **dir_)
        a.formula(f'H{r}', (
            f'=LET(v, E{r}, ano, $D{r}, ind, $A{r}, faixa, $C$6,'
            f' n, XLOOKUP(1, (tReferencia[faixa_porte]=faixa)*(tReferencia[ano]=ano)*(tReferencia[indicador_id]=ind), tReferencia[n], 0),'
            f' menores, SUMPRODUCT((tFato[faixa_porte]=faixa)*(tFato[ano]=ano)*(tFato[indicador_id]=ind)*(tFato[valor]<v)),'
            f' IF(AND(ISNUMBER(v), n>1), menores/(n-1), "n.d."))'), '0%', **dir_)
    a.mesclar('B21:H21', 'Como ler: a mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. A posição diz quantos '
                         'municípios da faixa têm valor menor: 0% é o menor valor, 100% o maior. Estar acima ou abaixo da mediana não '
                         'é, por si, bom nem ruim.', font_size=9, font_color=TINTA2, text_wrap=True, valign='top')
    ws.set_row(20, 36)

    # gráfico: um Indicador por vez, escolhido em C24
    a.texto('B23', 'Evolução de um indicador', 12, True)
    a.texto('B24', 'Indicador do gráfico (escolha na lista)')
    a.texto('C24', 'Receita corrente por habitante', bg_color=REALCE_ENTRADA)
    ws.data_validation('C24', {'validate': 'list', 'source': '=ListaIndicadores'})
    a.formula('D24', '=XLOOKUP($C$24, tIndicadores[nome], tIndicadores[indicador_id], "")', cor=CLARO)
    a.formula('B25', '=$C$24&": "&$C$4&" e a mediana dos "&$C$7&" municípios da faixa"', negrito=True)

    # dados do gráfico, mais abaixo, à vista de quem quiser conferir
    base = LINHA_DADOS_GRAFICO
    a.texto(f'B{base - 1}', 'Dados do gráfico (fórmulas; "#N/D" faz o gráfico pular o ano sem dado, em vez de desenhar zero)',
            9, True, TINTA2)
    a.formula(f'C{base}', f'=SEQUENCE(1, {n_anos}, {ano0})', '0', tam=9)
    series = [('Município', None), ('Mediana da faixa', 'mediana'), ('1º quartil da faixa', 'p25'), ('3º quartil da faixa', 'p75')]
    for k, (rot, col) in enumerate(series):
        r = base + 1 + k
        a.texto(f'B{r}', rot, 9, cor=TINTA2)
        for j in range(n_anos):
            cel = xl_rowcol_to_cell(r - 1, 2 + j)
            ano = xl_rowcol_to_cell(base - 1, 2 + j, row_abs=True)
            if col is None:
                f = f'=XLOOKUP(1, (tFato[cod_ibge]=$C$5)*(tFato[ano]={ano})*(tFato[indicador_id]=$D$24), tFato[valor], NA())'
            else:
                f = (f'=XLOOKUP(1, (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]={ano})*(tReferencia[indicador_id]=$D$24), '
                     f'tReferencia[{col}], NA())')
            a.formula(cel, f, '#,##0.0', tam=9)

    def linha(r):        # r: número da linha como o Excel mostra (1 = primeira)
        return ['Painel', r - 1, 2, r - 1, 1 + n_anos]

    anos = linha(base)
    g = grafico_linhas(a.wb, ['Painel', 24, 1], 12)          # título ligado a B25
    serie(g, '1º quartil da faixa', linha(base + 3), anos, CLARO, 1)
    serie(g, '3º quartil da faixa', linha(base + 4), anos, CLARO, 1)
    serie(g, 'Mediana da faixa', linha(base + 2), anos, NEUTRO, 2)
    serie(g, ['Painel', 3, 2], linha(base + 1), anos, DESTAQUE, 2.5, marcador=True)    # nome ligado a C4
    g.set_size({'width': 1013, 'height': 400})
    ws.insert_chart('B27', g)
    ws.activate()


def aba_previsao(a, N, ano0, ano_fim):
    ws = a.ws
    ws.hide_gridlines(2)
    ws.set_column('A:A', 2)
    ws.set_column('B:B', 10)
    ws.set_column('C:H', 16)
    a.texto('B1', 'Previsão da receita corrente', 16, True)
    a.formula('B2', '="Município: "&Painel!$C$4&" (troque na aba Painel). R$ milhões a preços de "&$D$4&"."', cor=TINTA2)
    a.mesclar('B4:C4', 'Último ano observado')
    a.formula('D4', '=MIN(tPrevisao[ano])-1', '0')
    a.mesclar('B5:C5', 'Último ano previsto')
    a.formula('D5', '=MAX(tPrevisao[ano])', '0')

    cab = ['Ano', 'Receita observada', 'Receita prevista', 'Limite inferior 80%', 'Limite superior 80%',
           'Limite inferior 95%', 'Limite superior 95%']
    for k, h in enumerate(cab):
        a.texto(xl_rowcol_to_cell(LINHA_PREVISAO - 2, 1 + k), h, negrito=True, quebra=True, bottom=1, bottom_color=TINTA2)
    ws.set_row(LINHA_PREVISAO - 2, 30)
    n = ano_fim - ano0 + 1
    p0 = LINHA_PREVISAO
    for k in range(n):
        r = p0 + k
        z = dict(bg_color=ZEBRA) if k % 2 == 0 else {}
        if k == 0:
            a.formula(f'B{r}', f'=SEQUENCE({n}, 1, MIN(tFato[ano]))', '0', **z)
        else:
            a.texto(f'B{r}', None, **z)      # a SEQUÊNCIA derrama aqui; a célula só leva o formato
        a.formula(f'C{r}', f'=XLOOKUP(1, (tFato[cod_ibge]=Painel!$C$5)*(tFato[ano]=$B{r})*(tFato[indicador_id]="receita_total"), '
                           'tFato[valor], NA())', '#,##0.0', **z)
        for j, col in enumerate(['previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95']):
            a.formula(xl_rowcol_to_cell(r - 1, 3 + j),
                      f'=IF($B{r}=$D$4, $C{r}, XLOOKUP(1, (tPrevisao[cod_ibge]=Painel!$C$5)*(tPrevisao[ano]=$B{r}), '
                      f'tPrevisao[{col}], NA()))', '#,##0.0', **z)
    ult = p0 + n - 1
    fr = ult + 2
    # A frase vai em célula mesclada: fórmula comum (não de matriz dinâmica), porque não há vetor nela.
    a.mesclar(f'B{fr}:H{fr}', font_size=12, text_wrap=True, valign='top')
    a.formula(f'B{fr}', (
        f'=LET(a, $D$5, m, Painel!$C$4, linha, MATCH(a, $B${p0}:$B${ult}, 0),'
        f' p, INDEX($D${p0}:$D${ult}, linha), inf_80, INDEX($E${p0}:$E${ult}, linha), sup_80, INDEX($F${p0}:$F${ult}, linha),'
        f' inf_95, INDEX($G${p0}:$G${ult}, linha), sup_95, INDEX($H${p0}:$H${ult}, linha),'
        f' IFERROR("Em "&a&", a receita corrente de "&m&" fica perto de R$ "&FIXED(p, 1)&" milhões (a preços de "&$D$4&"). '
        f'No intervalo de 80% do teste contra o passado, entre R$ "&FIXED(inf_80, 1)&" e R$ "&FIXED(sup_80, 1)&" milhões; no de 95%, '
        f'entre R$ "&FIXED(inf_95, 1)&" e R$ "&FIXED(sup_95, 1)&" milhões.",'
        f' "Este município não tem os anos recentes de receita válidos: sem previsão."))'),
        tam=12, text_wrap=True, valign='top', comum=True)
    ws.set_row(fr - 1, 48)
    aviso = ('Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em '
             'conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o '
             f'passado de municípios do mesmo porte, alargado até a cobertura do teste chegar ao nível prometido. Com '
             f'{N["NumCobOitentaPiorOrigem"]["valor"]} deixado de fora, o intervalo de 80% cobriu só {N["NumCobOitentaPior"]["valor"]}%: '
             'use o de 95% como leitura prudente. Projeto de portfólio feito com dado público.')
    a.mesclar(f'B{fr + 1}:H{fr + 1}', aviso, font_size=9, font_color=TINTA2, text_wrap=True, valign='top', bg_color=ZEBRA)
    ws.set_row(fr, 64)

    def col(c):
        return ['Previsão', p0 - 1, c, ult - 1, c]

    anos = col(1)
    g = grafico_linhas(a.wb, ['Previsão', 1, 1], 11, negrito=False)      # título ligado a B2
    serie(g, 'Limite inferior 95%', col(6), anos, NEUTRO, 1, traco='round_dot')
    serie(g, 'Limite superior 95%', col(7), anos, NEUTRO, 1, traco='round_dot')
    serie(g, 'Limite inferior 80%', col(4), anos, DESTAQUE, 1)
    serie(g, 'Limite superior 80%', col(5), anos, DESTAQUE, 1)
    serie(g, 'Receita prevista', col(3), anos, DESTAQUE, 2, traco='dash')
    serie(g, 'Receita observada', col(2), anos, DESTAQUE, 2.5, marcador=True)
    g.set_size({'width': 853, 'height': 453})
    ws.insert_chart('J7', g)


def aba_explorar(a, N):
    ws = a.ws
    ws.hide_gridlines(2)
    ws.set_column('A:A', 2)
    ws.set_column('B:B', 30)
    a.texto('B1', 'Explorar: tabela dinâmica dos indicadores', 16, True)
    a.texto('B2', 'Média do valor por ano e Indicador, para o município escolhido na segmentação. Com um município, '
                  'cada célula é o valor da fonte. Botão direito → Atualizar depois de mudar os dados.', cor=TINTA2)
    a.texto('B4', f'Tabela dinâmica: clique em {CANTO_DINAMICA} → Inserir → Tabela Dinâmica, sobre a tabela tFato (aba Dados), '
                  f'nesta planilha, em Explorar!${CANTO_DINAMICA[0]}${CANTO_DINAMICA[1:]}. Linhas: ano. Colunas: indicador. '
                  'Valores: valor, resumido por Média, com o nome "Valor (média)" e uma casa decimal. Totais gerais desligados.',
            cor=TINTA2)
    a.texto('B5', 'Segmentação: com a tabela dinâmica selecionada, Inserir → Segmentação de Dados → municipio. Ponha-a na '
                  f'coluna B, a partir da linha 8, e escolha {N["NumExemplo"]["valor"]}.', cor=TINTA2)
    a.texto('B6', f'A área a partir da linha 8 fica vazia para as duas: a tabela dinâmica começa em {CANTO_DINAMICA}. '
                  'O passo a passo (excel/PASSO_A_PASSO.md, passo 5) explica cada escolha.', 9, cor=TINTA2)


def aba_leiame(a, N):
    ws = a.ws
    ws.hide_gridlines(2)
    ws.set_column('A:A', 2)
    ws.set_column('B:B', 110)
    a.texto('B1', 'Indicadores dos municípios de São Paulo', 16, True)
    v = {k: N[k]['valor'] for k in N}
    blocos = [
        ('O que é', f'Uma planilha que junta, para os {v["NumMunicipios"]} municípios de SP, {v["NumIndicadores"]} indicadores de finanças, '
                    f'educação, saúde e economia, de {v["NumAnoInicial"]} a {v["NumAnoFinal"]}, e compara cada município com os de mesmo '
                    'porte. Tem ainda uma previsão simples da receita, com a incerteza à vista. Projeto de portfólio feito com dado público.'),
        ('Como usar', '1) Na aba "Painel", escolha o município na célula azul. 2) Leia os cartões e a tabela. 3) Escolha um indicador '
                      'para o gráfico. 4) Na aba "Previsão", leia a projeção da receita. A aba "Explorar" é uma tabela dinâmica com '
                      'segmentação de município.'),
        ('De onde vêm os números', 'As abas "Indicadores", "Municípios", "Dados", "Referência" e "Previsões" são tabelas nomeadas com os '
                                   'CSV de dados/tratados/ do repositório, gravadas pelo script scripts/montar_excel.py (a tabela da aba '
                                   '"Dados" recebe o nome do Indicador ao lado do código). As abas "Painel" e "Previsão" só têm fórmulas '
                                   '(PROCX, LET, SEQUÊNCIA, SOMARPRODUTO) sobre essas tabelas. A tabela dinâmica e a segmentação da aba '
                                   '"Explorar" são inseridas à mão, no Excel para a web. Para dados novos, rode o script de novo.'),
        ('Como ler a comparação', 'A mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. A posição vai de 0% (menor valor '
                                  'da faixa) a 100% (maior). Estar acima ou abaixo não é bom nem ruim por si: depende de escolhas e do '
                                  'contexto do município.'),
        ('Cuidados', 'Valores em reais de 2025 (IPCA). Os indicadores por habitante têm um degrau entre 2021 e 2022, porque a população '
                     'passa a vir do Censo 2022. A receita total (R$ milhões) não tem esse degrau. O Ideb é bienal, e município sem rede '
                     'municipal fica sem Ideb. Município que não entregou a declaração ao Tesouro no ano fica "n.d.": nada foi estimado.'),
        ('Fontes', 'Tesouro Nacional (Siconfi), IBGE, INEP e DataSUS. Licenças: aba "Fontes e licenças".'),
    ]
    r = 3
    for titulo, corpo in blocos:
        a.texto(f'B{r}', titulo, 11, True)
        a.texto(f'B{r + 1}', corpo, quebra=True)
        ws.set_row(r, 15 * max(2, len(corpo) // 100 + 1))
        r += 3


FONTES = [
    ('DCA, anexos I-C e I-E (Siconfi)', 'Tesouro Nacional', 'Receitas correntes, deduções, transferências e despesa por função',
     'A página de APIs diz que os dados são "disponibilizados para livre utilização". Sem instrução de citação.',
     'Lido. Texto formal de licença da base: não encontrado.'),
    ('População (SIDRA 6579 e 9514), PIB dos Municípios (5938), IPCA (1737), Localidades', 'IBGE',
     'População, PIB, deflator, lista de municípios',
     'Dado aberto de órgão federal, sob o Decreto 8.777/2016: "licença aberta que permita sua livre utilização, consumo ou '
     'cruzamento, limitando-se a creditar a autoria ou a fonte".',
     'As páginas de termos do IBGE bloqueiam acesso automatizado: o texto próprio do IBGE não foi lido.'),
    ('Ideb, anos iniciais, por município (divulgação 2023)', 'INEP', 'Ideb observado, rede municipal',
     'A Portaria Inep nº 380/2020 define dados abertos como os "sob licença aberta [...] limitando-se a creditar sua autoria ou a fonte".',
     'Portaria 380 lida; Portaria 496/2021 (CC BY 4.0) não lida em fonte primária.'),
    ('SINASC, arquivos DNSP', 'Ministério da Saúde (DataSUS)', 'Nascidos vivos por consultas de pré-natal',
     '"Os dados estão disponíveis de forma pública e anonimizada." O rodapé dos sites do Ministério traz CC BY-ND 3.0 para o '
     'conteúdo do site, não declarado para os arquivos de dados.',
     'Lido. Licença do arquivo de microdados: não está escrita no FTP.'),
]


def aba_fontes(a):
    ws = a.ws
    ws.hide_gridlines(2)
    a.texto('A1', 'Fontes e licenças', 16, True)
    a.texto('A2', 'Condição comum a todas: creditar a fonte. Esta aba não é parecer jurídico.', cor=TINTA2)
    for k, h in enumerate(['Base', 'Órgão', 'O que foi usado', 'Condição de uso encontrada', 'Situação']):
        a.texto(xl_rowcol_to_cell(3, k), h, negrito=True, bottom=1, bottom_color=TINTA2)
    for i, linha in enumerate(FONTES):
        z = dict(bg_color=ZEBRA) if i % 2 == 0 else {}
        for k, t in enumerate(linha):
            a.texto(xl_rowcol_to_cell(4 + i, k), t, 9, quebra=True, **z)
        ws.set_row(4 + i, 78)
    for k, w in enumerate((34, 22, 30, 60, 40)):
        ws.set_column(k, k, w)


ABAS = ['Leia-me', 'Painel', 'Explorar', 'Previsão', 'Indicadores', 'Fontes e licenças',      # leitura
        'Municípios', 'Dados', 'Referência', 'Previsões']                                       # dados, no fim


def montar(saida):
    N = numeros.calcular()
    ano0 = int(N['NumAnoInicial']['valor'])
    ano_fim_obs = int(N['NumAnoFinal']['valor'])
    ano_fim_prev = int(N['NumAnoPrevFinal']['valor'])
    d = ler_dados()

    saida.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(str(saida), {'default_format_properties': {'font_name': FONTE, 'font_size': 10}})
    abas = {nome: Aba(wb, wb.add_worksheet(nome)) for nome in ABAS}
    for aba, nome, _ in DADOS:
        tabela(abas[aba], nome, d[nome])
        print(f'  tabela {nome} na aba "{aba}": {len(d[nome])} linhas')

    wb.define_name('ListaMunicipios', '=tMunicipios[municipio]')
    wb.define_name('ListaIndicadores', '=tIndicadores[nome]')
    wb.define_name('OrigemDaPlanilha', f'="{ORIGEM}"')
    wb.set_custom_property('Origem', ORIGEM)
    wb.set_properties({'title': 'Indicadores dos municípios de São Paulo', 'comments': f'Gerada por {ORIGEM}'})

    aba_leiame(abas['Leia-me'], N)
    aba_painel(abas['Painel'], N, ano_fim_obs - ano0 + 1, ano0)
    aba_explorar(abas['Explorar'], N)
    aba_previsao(abas['Previsão'], N, ano0, ano_fim_prev)
    aba_fontes(abas['Fontes e licenças'])
    wb.close()
    print('gravado', saida)

    # os números que a planilha imprime em texto, para a coluna "Onde aparece" de NUMEROS_CANONICOS.md
    usados = {saida.name: ['NumExemplo', 'NumMunicipios', 'NumIndicadores', 'NumAnoInicial', 'NumAnoFinal',
                           'NumCobOitentaPiorOrigem', 'NumCobOitentaPior']}
    (saida.parent / 'numeros_usados.json').write_text(json.dumps(usados, ensure_ascii=False, indent=2) + '\n',
                                                      encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--saida', type=Path, default=SAIDA, help='arquivo a gravar (padrão: excel/painel-municipios-sp.xlsx)')
    montar(ap.parse_args().saida.resolve())


if __name__ == '__main__':
    main()
