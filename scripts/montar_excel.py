"""Monta excel/painel-municipios-sp.xlsx comandando o próprio Excel (automação COM, pywin32).

    python scripts/montar_excel.py

Precisa do Excel 365 (ou 2021) instalado nesta máquina: PROCX, LET e SEQUÊNCIA não existem nas versões
anteriores, e o Power Query só se grava pelo Excel. O script faz, em ordem, o mesmo que excel/PASSO_A_PASSO.md
ensina a fazer à mão:

  1. Power Query: um parâmetro com a pasta dos CSV, uma função que lê um CSV e cinco consultas
     (Municípios, Indicadores, Fato, Referência, Previsões), carregadas como tabelas.
     A consulta Fato mescla o nome do Indicador vindo da consulta Indicadores.
  2. Painel: escolha do município e do Indicador por lista, cartões e tabela com PROCX, gráfico de linhas.
  3. Explorar: tabela dinâmica sobre a tabela Fato, com segmentação de município.
  4. Previsão: série observada e prevista, com os Intervalos de previsão, frase e gráfico.
  5. Leia-me e Fontes e licenças.

As fórmulas vão pela propriedade Formula2, em inglês (XLOOKUP, LET, SEQUENCE); o Excel em português as mostra
como PROCX, LET e SEQUÊNCIA. Cores e fonte vêm do kit (estilo/estilo_portfolio.py). Os números escritos em
texto vêm de scripts/numeros.py.
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'estilo'))
sys.path.insert(0, str(RAIZ / 'scripts'))

import estilo_portfolio as ep  # noqa: E402
import comum  # noqa: E402
import numeros  # noqa: E402
from gerar_tema import zebra  # noqa: E402

SAIDA = RAIZ / 'excel' / 'painel-municipios-sp.xlsx'
PASTA = str(RAIZ / 'dados' / 'tratados') + '\\'
FONTE = 'Lato'

# ── constantes do Excel (enumerações do modelo de objetos) ────────────────
xlSrcExternal, xlYes, xlCmdSql = 0, 1, 2
xlValidateList, xlValidAlertStop, xlBetween = 3, 1, 1
xlLine = 4
xlDatabase, xlRowField, xlColumnField, xlPageField, xlAverage = 1, 1, 2, 3, -4106
xlCategory, xlValue = 1, 2
xlMarkerStyleCircle, xlMarkerStyleNone = 8, -4142
msoLineDash, msoLineRoundDot, msoLineSolid = 4, 3, 1
xlOpenXMLWorkbook = 51
xlEdgeBottom, xlContinuous, xlThin = 9, 1, 2
xlHeaderRow, xlRowStripe1 = 1, 5
xlLeft, xlCenter, xlTop = -4131, -4108, -4160
xlCalculationAutomatic = -4105


def rgb(hexa):
    """'#E41A1C' → inteiro BGR que o Excel espera."""
    h = hexa.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r + g * 256 + b * 65536


DESTAQUE, NEUTRO, TINTA, TINTA2 = rgb(ep.DESTAQUE), rgb(ep.NEUTRO), rgb(ep.TINTA), rgb(ep.TINTA_SECUNDARIA)
CLARO, GRADE, BRANCO = rgb(ep.GRAY_20), rgb(ep.GRAY_20), rgb(ep.BRANCO)
ZEBRA = rgb(zebra())
REALCE_ENTRADA = rgb(ep.misturar(ep.AZUL, 0.85))   # célula onde o leitor escolhe


# ── Power Query ──────────────────────────────────────────────────────────
M_LER_CSV = '''(arquivo as text) as table =>
let
    Fonte = Csv.Document(File.Contents(PastaDados & arquivo), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true])
in
    Cabecalho'''


def m_tipos(arquivo, tipos, passos_extra=''):
    lista = ', '.join(f'{{"{c}", {t}}}' for c, t in tipos)
    ultimo = 'Tipos'
    corpo = f'''let
    Fonte = LerCsv("{arquivo}"),
    Tipos = Table.TransformColumnTypes(Fonte, {{{lista}}}, "en-US")'''
    if passos_extra:
        corpo += ',\n' + passos_extra[0]
        ultimo = passos_extra[1]
    return corpo + f'\nin\n    {ultimo}'


TXT, INT, NUM = 'type text', 'Int64.Type', 'type number'
CONSULTAS = [
    # (nome da consulta, tabela, aba, M)
    ('Municipios', 'tMunicipios', 'Municípios', m_tipos('dim_municipio.csv', [
        ('cod_ibge', INT), ('municipio', TXT), ('regiao_imediata', TXT), ('regiao_intermediaria', TXT),
        ('populacao_censo_2022', INT), ('faixa_porte', TXT)])),
    ('Indicadores', 'tIndicadores', 'Indicadores', m_tipos('dim_indicador.csv', [
        ('indicador_id', TXT), ('nome', TXT), ('unidade', TXT), ('formula', TXT), ('fonte', TXT),
        ('periodicidade', TXT), ('meta', TXT), ('sentido', TXT), ('casas', INT), ('ordem', INT)])),
    ('Fato', 'tFato', 'Dados', m_tipos('indicadores_longo.csv', [
        ('cod_ibge', INT), ('municipio', TXT), ('faixa_porte', TXT), ('ano', INT), ('indicador_id', TXT), ('valor', NUM)],
        ('''    ComIndicador = Table.NestedJoin(Tipos, {"indicador_id"}, Indicadores, {"indicador_id"}, "dim", JoinKind.LeftOuter),
    Expandida = Table.ExpandTableColumn(ComIndicador, "dim", {"nome"}, {"indicador"})''', 'Expandida'))),
    ('Referencia', 'tReferencia', 'Referência', m_tipos('referencia_faixa.csv', [
        ('faixa_porte', TXT), ('ano', INT), ('indicador_id', TXT), ('n', INT), ('minimo', NUM), ('maximo', NUM),
        ('media', NUM), ('p25', NUM), ('mediana', NUM), ('p75', NUM)])),
    ('Previsao', 'tPrevisao', 'Previsões', m_tipos('previsao_receita_total.csv', [
        ('cod_ibge', INT), ('municipio', TXT), ('grupo_porte', TXT), ('ano', INT), ('metodo', TXT), ('previsto', NUM),
        ('inferior_80', NUM), ('superior_80', NUM), ('inferior_95', NUM), ('superior_95', NUM)])),
]


def carregar_consulta(wb, ws, consulta, tabela):
    conexao = (f'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location={consulta};'
               'Extended Properties=""')
    lo = ws.ListObjects.Add(SourceType=xlSrcExternal, Source=conexao, Destination=ws.Range('$A$1'))
    lo.QueryTable.CommandType = xlCmdSql
    lo.QueryTable.CommandText = [f'SELECT * FROM [{consulta}]']
    lo.QueryTable.BackgroundQuery = False
    lo.QueryTable.RefreshStyle = 1          # xlInsertDeleteCells
    lo.QueryTable.AdjustColumnWidth = True
    lo.QueryTable.Refresh(False)
    lo.Name = tabela
    lo.TableStyle = 'Portfolio'
    return lo


# ── formatação ───────────────────────────────────────────────────────────
def estilo_tabela(wb):
    ts = wb.TableStyles.Add('Portfolio')
    cab = ts.TableStyleElements(xlHeaderRow)
    cab.Font.Bold = True
    cab.Font.Color = TINTA
    cab.Borders(xlEdgeBottom).Color = TINTA2
    ts.TableStyleElements(xlRowStripe1).Interior.Color = ZEBRA


def texto(ws, celula, valor, tam=10, negrito=False, cor=TINTA, quebra=False):
    c = ws.Range(celula)
    c.Value = valor
    c.Font.Name = FONTE
    c.Font.Size = tam
    c.Font.Bold = negrito
    c.Font.Color = cor
    c.WrapText = quebra
    c.VerticalAlignment = xlTop if quebra else xlCenter
    return c


def formula(ws, celula, f, formato=None, negrito=False, cor=TINTA):
    c = ws.Range(celula)
    c.Formula2 = f
    c.Font.Name = FONTE
    c.Font.Bold = negrito
    c.Font.Color = cor
    if formato:
        c.NumberFormat = formato
    return c


def validacao_lista(celula, nome_definido):
    v = celula.Validation
    v.Delete()
    v.Add(xlValidateList, xlValidAlertStop, xlBetween, f'={nome_definido}')
    v.IgnoreBlank = True
    v.InCellDropdown = True
    celula.Interior.Color = REALCE_ENTRADA


def serie(grafico, nome, valores, categorias, cor, espessura, marcador=False, traco=msoLineSolid):
    s = grafico.SeriesCollection().NewSeries()
    s.Name = nome
    s.Values = valores
    s.XValues = categorias
    s.Format.Line.Visible = True
    s.Format.Line.ForeColor.RGB = cor
    s.Format.Line.Weight = espessura
    s.Format.Line.DashStyle = traco
    if marcador:
        s.MarkerStyle = xlMarkerStyleCircle
        s.MarkerSize = 6
        s.MarkerBackgroundColor = cor
        s.MarkerForegroundColor = BRANCO
    else:
        s.MarkerStyle = xlMarkerStyleNone
    return s


def grafico_linhas(ws, esquerda, topo, largura, altura):
    forma = ws.Shapes.AddChart2(227, xlLine, esquerda, topo, largura, altura)
    g = forma.Chart
    while g.SeriesCollection().Count:
        g.SeriesCollection(1).Delete()
    g.ChartArea.Format.TextFrame2.TextRange.Font.Name = FONTE
    g.ChartArea.Format.Line.Visible = False
    g.Axes(xlValue).MajorGridlines.Format.Line.ForeColor.RGB = GRADE
    g.Axes(xlValue).MajorGridlines.Format.Line.DashStyle = msoLineDash
    g.Axes(xlValue).Format.Line.Visible = False
    g.HasLegend = True
    g.Legend.Position = -4107        # embaixo
    return g


# ── abas ─────────────────────────────────────────────────────────────────
def aba_painel(wb, ws, N, n_anos, ano0):
    ws.Cells.Font.Name = FONTE
    ws.Columns('A').ColumnWidth = 2
    ws.Columns('B').ColumnWidth = 44
    ws.Columns('C').ColumnWidth = 30
    for col in 'DEFGH':
        ws.Columns(col).ColumnWidth = 15
    texto(ws, 'B1', 'Indicadores dos municípios de São Paulo', 16, True)
    texto(ws, 'B2', 'Escolha o município e o indicador nas células azuis. Tudo nesta aba e na aba "Previsão" se recalcula.',
          10, cor=TINTA2)

    rotulos = ['Município (escolha na lista)', 'Código IBGE', 'Faixa de porte (municípios parecidos)', 'Municípios na faixa',
               'População (Censo 2022)', 'Região geográfica imediata (IBGE)']
    for k, r in enumerate(rotulos):
        texto(ws, f'B{4 + k}', r)
    ws.Range('C4').Value = N['NumExemplo']['valor']
    validacao_lista(ws.Range('C4'), 'ListaMunicipios')
    formula(ws, 'C5', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[cod_ibge], "escolha um município")', '0')
    formula(ws, 'C6', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[faixa_porte], "")')
    formula(ws, 'C7', '=COUNTIFS(tMunicipios[faixa_porte], $C$6)', '#,##0')
    formula(ws, 'C8', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[populacao_censo_2022], "")', '#,##0')
    formula(ws, 'C9', '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[regiao_imediata], "")')
    for c in ('C5', 'C6', 'C7', 'C8', 'C9'):
        ws.Range(c).HorizontalAlignment = xlLeft

    texto(ws, 'B11', 'Último valor de cada indicador, comparado com os municípios da faixa', 12, True)
    cab = ['Indicador', 'Unidade', 'Último ano com dado', 'Valor do município', 'Mediana da faixa',
           'Diferença para a mediana', 'Posição na faixa (0% a 100%)']
    for k, h in enumerate(cab):
        c = texto(ws, ws.Cells(12, 2 + k).Address, h, negrito=True, quebra=True)
        c.Borders(xlEdgeBottom).Color = TINTA2
    ws.Rows(12).RowHeight = 30
    # coluna A, discreta: o código do Indicador, que as fórmulas da linha usam
    for k, ind in enumerate(comum.INDICADORES_PAINEL):
        r = 13 + k
        texto(ws, f'A{r}', ind, 8, cor=CLARO)
        formula(ws, f'B{r}', f'=XLOOKUP($A{r}, tIndicadores[indicador_id], tIndicadores[nome])')
        formula(ws, f'C{r}', f'=XLOOKUP($A{r}, tIndicadores[indicador_id], tIndicadores[unidade])')
        ws.Range(f'C{r}').Font.Color = TINTA2
        formula(ws, f'D{r}', f'=LET(a, MAXIFS(tFato[ano], tFato[cod_ibge], $C$5, tFato[indicador_id], $A{r}), IF(a=0, "n.d.", a))', '0')
        formula(ws, f'E{r}', f'=XLOOKUP(1, (tFato[cod_ibge]=$C$5)*(tFato[ano]=$D{r})*(tFato[indicador_id]=$A{r}), tFato[valor], "n.d.")',
                '#,##0.0')
        formula(ws, f'F{r}', f'=XLOOKUP(1, (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]=$D{r})*(tReferencia[indicador_id]=$A{r}), '
                             f'tReferencia[mediana], "n.d.")', '#,##0.0')
        formula(ws, f'G{r}', f'=IF(AND(ISNUMBER(E{r}), ISNUMBER(F{r})), E{r}/F{r}-1, "n.d.")', '+0.0%;-0.0%;0.0%')
        formula(ws, f'H{r}', (
            f'=LET(v, E{r}, ano, $D{r}, ind, $A{r}, faixa, $C$6,'
            f' n, XLOOKUP(1, (tReferencia[faixa_porte]=faixa)*(tReferencia[ano]=ano)*(tReferencia[indicador_id]=ind), tReferencia[n], 0),'
            f' menores, SUMPRODUCT((tFato[faixa_porte]=faixa)*(tFato[ano]=ano)*(tFato[indicador_id]=ind)*(tFato[valor]<v)),'
            f' IF(AND(ISNUMBER(v), n>1), menores/(n-1), "n.d."))'), '0%')
        if k % 2 == 0:
            ws.Range(f'B{r}:H{r}').Interior.Color = ZEBRA
    ws.Range('D13:H19').HorizontalAlignment = -4152      # à direita
    texto(ws, 'B21', 'Como ler: a mediana é a dos municípios do mesmo porte (Censo 2022) no mesmo ano. A posição diz quantos '
                     'municípios da faixa têm valor menor: 0% é o menor valor, 100% o maior. Estar acima ou abaixo da mediana não '
                     'é, por si, bom nem ruim.', 9, cor=TINTA2, quebra=True)
    ws.Range('B21:H21').Merge()
    ws.Rows(21).RowHeight = 36

    # gráfico: um Indicador por vez, escolhido em C24
    texto(ws, 'B23', 'Evolução de um indicador', 12, True)
    texto(ws, 'B24', 'Indicador do gráfico (escolha na lista)')
    ws.Range('C24').Value = 'Receita corrente por habitante'
    validacao_lista(ws.Range('C24'), 'ListaIndicadores')
    formula(ws, 'D24', '=XLOOKUP($C$24, tIndicadores[nome], tIndicadores[indicador_id], "")')
    ws.Range('D24').Font.Color = CLARO
    formula(ws, 'B25', '=$C$24&": "&$C$4&" e a mediana dos "&$C$7&" municípios da faixa"', negrito=True)

    # dados do gráfico, mais abaixo, à vista de quem quiser conferir
    base = 46
    texto(ws, f'B{base - 1}', 'Dados do gráfico (fórmulas; "#N/D" interrompe a linha onde não há dado)', 9, True, TINTA2)
    formula(ws, f'C{base}', f'=SEQUENCE(1, {n_anos}, {ano0})', '0')
    for k, (rot, col) in enumerate([('Município', None), ('Mediana da faixa', 'mediana'),
                                    ('1º quartil da faixa', 'p25'), ('3º quartil da faixa', 'p75')]):
        r = base + 1 + k
        texto(ws, f'B{r}', rot, 9, cor=TINTA2)
        for j in range(n_anos):
            cel = ws.Cells(r, 3 + j).Address
            ano = ws.Cells(base, 3 + j).Address
            if col is None:
                f = f'=XLOOKUP(1, (tFato[cod_ibge]=$C$5)*(tFato[ano]={ano})*(tFato[indicador_id]=$D$24), tFato[valor], NA())'
            else:
                f = (f'=XLOOKUP(1, (tReferencia[faixa_porte]=$C$6)*(tReferencia[ano]={ano})*(tReferencia[indicador_id]=$D$24), '
                     f'tReferencia[{col}], NA())')
            formula(ws, cel, f, '#,##0.0').Font.Size = 9
    fim = ws.Cells(base, 2 + n_anos).Address.replace('$', '')
    anos = ws.Range(f'C{base}:{fim}')

    def linha(r):
        return ws.Range(ws.Cells(r, 3), ws.Cells(r, 2 + n_anos))

    topo = ws.Range('B27').Top
    g = grafico_linhas(ws, ws.Range('B27').Left, topo, 760, 300)
    serie(g, '1º quartil da faixa', linha(base + 3), anos, CLARO, 1)
    serie(g, '3º quartil da faixa', linha(base + 4), anos, CLARO, 1)
    serie(g, 'Mediana da faixa', linha(base + 2), anos, NEUTRO, 2)
    serie(g, '=Painel!$C$4', linha(base + 1), anos, DESTAQUE, 2.5, marcador=True)
    g.HasTitle = True
    g.ChartTitle.Text = 'x'
    g.ChartTitle.Formula = '=Painel!$B$25'
    g.ChartTitle.Format.TextFrame2.TextRange.Font.Size = 12
    g.ChartTitle.Format.TextFrame2.TextRange.Font.Bold = True
    ws.Activate()
    wb.Windows(1).DisplayGridlines = False


def aba_previsao(wb, ws, N, ano0, ano_fim):
    ws.Cells.Font.Name = FONTE
    ws.Columns('A').ColumnWidth = 2
    ws.Columns('B').ColumnWidth = 10
    for col in 'CDEFGH':
        ws.Columns(col).ColumnWidth = 16
    texto(ws, 'B1', 'Previsão da receita corrente', 16, True)
    formula(ws, 'B2', '="Município: "&Painel!$C$4&" (troque na aba Painel). R$ milhões a preços de "&$D$4&"."', cor=TINTA2)
    texto(ws, 'B4', 'Último ano observado')
    ws.Range('B4:C4').Merge()
    formula(ws, 'D4', '=MIN(tPrevisao[ano])-1', '0')
    texto(ws, 'B5', 'Último ano previsto')
    ws.Range('B5:C5').Merge()
    formula(ws, 'D5', '=MAX(tPrevisao[ano])', '0')

    cab = ['Ano', 'Receita observada', 'Receita prevista', 'Limite inferior 80%', 'Limite superior 80%',
           'Limite inferior 95%', 'Limite superior 95%']
    for k, h in enumerate(cab):
        c = texto(ws, ws.Cells(7, 2 + k).Address, h, negrito=True, quebra=True)
        c.Borders(xlEdgeBottom).Color = TINTA2
    ws.Rows(7).RowHeight = 30
    n = ano_fim - ano0 + 1
    formula(ws, 'B8', f'=SEQUENCE({n}, 1, MIN(tFato[ano]))', '0')
    colunas = [None, 'previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95']
    for k in range(n):
        r = 8 + k
        formula(ws, f'C{r}', f'=XLOOKUP(1, (tFato[cod_ibge]=Painel!$C$5)*(tFato[ano]=$B{r})*(tFato[indicador_id]="receita_total"), '
                             'tFato[valor], NA())', '#,##0.0')
        for j, col in enumerate(colunas[1:]):
            cel = ws.Cells(r, 4 + j).Address.replace('$', '')
            formula(ws, cel, f'=IF($B{r}=$D$4, $C{r}, XLOOKUP(1, (tPrevisao[cod_ibge]=Painel!$C$5)*(tPrevisao[ano]=$B{r}), '
                             f'tPrevisao[{col}], NA()))', '#,##0.0')
        if k % 2 == 0:
            ws.Range(f'B{r}:H{r}').Interior.Color = ZEBRA
    ult = 8 + n - 1
    formula(ws, f'B{ult + 2}', (
        f'=LET(a, $D$5, m, Painel!$C$4, linha, MATCH(a, $B$8:$B${ult}, 0),'
        f' p, INDEX($D$8:$D${ult}, linha), lo8, INDEX($E$8:$E${ult}, linha), hi8, INDEX($F$8:$F${ult}, linha),'
        f' lo9, INDEX($G$8:$G${ult}, linha), hi9, INDEX($H$8:$H${ult}, linha),'
        f' IFERROR("Em "&a&", a receita corrente de "&m&" fica perto de R$ "&FIXED(p, 1)&" milhões (a preços de "&$D$4&"). '
        f'No intervalo de 80% do teste contra o passado, entre R$ "&FIXED(lo8, 1)&" e R$ "&FIXED(hi8, 1)&" milhões; no de 95%, '
        f'entre R$ "&FIXED(lo9, 1)&" e R$ "&FIXED(hi9, 1)&" milhões.",'
        f' "Este município não tem os anos recentes de receita válidos: sem previsão."))'))
    ws.Range(f'B{ult + 2}:H{ult + 2}').Merge()
    ws.Range(f'B{ult + 2}').WrapText = True
    ws.Range(f'B{ult + 2}').Font.Size = 12
    ws.Rows(ult + 2).RowHeight = 48
    aviso = ('Previsão simples, sem informação de fora da série: repete a tendência recente da receita do município. Não leva em '
             'conta mudança de lei, de alíquota, de convênio nem de gestão. O intervalo mostra o quanto o método errou ao prever o '
             f'passado de municípios do mesmo porte, alargado até a cobertura do teste chegar ao nível prometido. Com '
             f'{N["NumCobOitentaPiorOrigem"]["valor"]} deixado de fora, o intervalo de 80% cobriu só {N["NumCobOitentaPior"]["valor"]}%: '
             'use o de 95% como leitura prudente. Projeto de portfólio feito com dado público.')
    c = texto(ws, f'B{ult + 3}', aviso, 9, cor=TINTA2, quebra=True)
    ws.Range(f'B{ult + 3}:H{ult + 3}').Merge()
    ws.Range(f'B{ult + 3}:H{ult + 3}').Interior.Color = ZEBRA
    ws.Rows(ult + 3).RowHeight = 64

    anos = ws.Range(f'B8:B{ult}')
    g = grafico_linhas(ws, ws.Range('J7').Left, ws.Range('J7').Top, 640, 340)
    serie(g, 'Limite inferior 95%', ws.Range(f'G8:G{ult}'), anos, NEUTRO, 1, traco=msoLineRoundDot)
    serie(g, 'Limite superior 95%', ws.Range(f'H8:H{ult}'), anos, NEUTRO, 1, traco=msoLineRoundDot)
    serie(g, 'Limite inferior 80%', ws.Range(f'E8:E{ult}'), anos, DESTAQUE, 1)
    serie(g, 'Limite superior 80%', ws.Range(f'F8:F{ult}'), anos, DESTAQUE, 1)
    serie(g, 'Receita prevista', ws.Range(f'D8:D{ult}'), anos, DESTAQUE, 2, traco=msoLineDash)
    serie(g, 'Receita observada', ws.Range(f'C8:C{ult}'), anos, DESTAQUE, 2.5, marcador=True)
    g.HasTitle = True
    g.ChartTitle.Text = 'x'
    g.ChartTitle.Formula = '=Previsão!$B$2'
    g.ChartTitle.Format.TextFrame2.TextRange.Font.Size = 11
    ws.Activate()
    wb.Windows(1).DisplayGridlines = False


def aba_explorar(wb, ws, N):
    ws.Cells.Font.Name = FONTE
    texto(ws, 'B1', 'Explorar: tabela dinâmica dos indicadores', 16, True)
    texto(ws, 'B2', 'Média do valor por ano e Indicador, para o município escolhido na segmentação. Com um município, '
                    'cada célula é o valor da fonte. Botão direito → Atualizar depois de mudar os dados.', 10, cor=TINTA2)
    cache = wb.PivotCaches().Create(SourceType=xlDatabase, SourceData='tFato', Version=8)
    pt = cache.CreatePivotTable(TableDestination=ws.Range('B8'), TableName='dinIndicadores', DefaultVersion=8)
    pt.PivotFields('ano').Orientation = xlRowField
    pt.PivotFields('indicador').Orientation = xlColumnField
    campo = pt.AddDataField(pt.PivotFields('valor'), 'Valor (média)', xlAverage)
    campo.NumberFormat = '#,##0.0'
    pt.PivotFields('municipio').Orientation = xlPageField
    pt.PivotFields('municipio').CurrentPage = N['NumExemplo']['valor']
    pt.ColumnGrand = False
    pt.RowGrand = False
    pt.TableStyle2 = 'PivotStyleLight1'
    seg = wb.SlicerCaches.Add2(pt, 'municipio')
    seg.Slicers.Add(ws, None, 'SegMunicipio', 'Município', ws.Range('B4').Top, ws.Range('M4').Left, 180, 260)
    ws.Activate()
    wb.Windows(1).DisplayGridlines = False


def aba_leiame(ws, N):
    ws.Cells.Font.Name = FONTE
    ws.Columns('A').ColumnWidth = 2
    ws.Columns('B').ColumnWidth = 110
    texto(ws, 'B1', 'Indicadores dos municípios de São Paulo', 16, True)
    v = {k: N[k]['valor'] for k in N}
    blocos = [
        ('O que é', f'Uma planilha que junta, para os {v["NumMunicipios"]} municípios de SP, {v["NumIndicadores"]} indicadores de finanças, '
                    f'educação, saúde e economia, de {v["NumAnoInicial"]} a {v["NumAnoFinal"]}, e compara cada município com os de mesmo '
                    'porte. Tem ainda uma previsão simples da receita, com a incerteza à vista. Projeto de portfólio feito com dado público.'),
        ('Como usar', '1) Na aba "Painel", escolha o município na célula azul. 2) Leia os cartões e a tabela. 3) Escolha um indicador '
                      'para o gráfico. 4) Na aba "Previsão", leia a projeção da receita. A aba "Explorar" é uma tabela dinâmica com '
                      'segmentação de município.'),
        ('De onde vêm os números', 'As abas "Municípios", "Indicadores", "Dados", "Referência" e "Previsões" são tabelas carregadas pelo '
                                   'Power Query a partir dos CSV de dados/tratados/ do repositório (Dados → Consultas e Conexões). Para '
                                   'apontar para outra pasta, mude o parâmetro PastaDados e clique em Dados → Atualizar Tudo. As abas '
                                   '"Painel" e "Previsão" só têm fórmulas (PROCX, LET, SEQUÊNCIA) sobre essas tabelas.'),
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
        texto(ws, f'B{r}', titulo, 11, True)
        texto(ws, f'B{r + 1}', corpo, 10, quebra=True)
        ws.Rows(r + 1).RowHeight = 15 * max(2, len(corpo) // 100 + 1)
        r += 3
    ws.Activate()
    ws.Parent.Windows(1).DisplayGridlines = False


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


def aba_fontes(ws):
    ws.Cells.Font.Name = FONTE
    texto(ws, 'A1', 'Fontes e licenças', 16, True)
    texto(ws, 'A2', 'Condição comum a todas: creditar a fonte. Esta aba não é parecer jurídico.', 10, cor=TINTA2)
    cab = ['Base', 'Órgão', 'O que foi usado', 'Condição de uso encontrada', 'Situação']
    for k, h in enumerate(cab):
        texto(ws, ws.Cells(4, 1 + k).Address, h, negrito=True).Borders(xlEdgeBottom).Color = TINTA2
    for i, linha in enumerate(FONTES):
        for k, t in enumerate(linha):
            texto(ws, ws.Cells(5 + i, 1 + k).Address, t, 9, quebra=True)
        ws.Rows(5 + i).RowHeight = 78
        if i % 2 == 0:
            ws.Range(ws.Cells(5 + i, 1), ws.Cells(5 + i, 5)).Interior.Color = ZEBRA
    for col, w in zip('ABCDE', (34, 22, 30, 60, 40)):
        ws.Columns(col).ColumnWidth = w
    ws.Activate()
    ws.Parent.Windows(1).DisplayGridlines = False


def main():
    import win32com.client as win32

    N = numeros.calcular()
    ano0 = int(N['NumAnoInicial']['valor'])
    ano_fim_obs = int(N['NumAnoFinal']['valor'])
    ano_fim_prev = int(N['NumAnoPrevFinal']['valor'])

    xl = win32.DispatchEx('Excel.Application')
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.ScreenUpdating = False
    try:
        wb = xl.Workbooks.Add()
        wb.Styles('Normal').Font.Name = FONTE
        wb.Styles('Normal').Font.Size = 10
        estilo_tabela(wb)

        # Power Query
        wb.Queries.Add('PastaDados', f'"{PASTA}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
                       'Pasta dos CSV tratados, terminada em barra invertida')
        wb.Queries.Add('LerCsv', M_LER_CSV, 'Lê um CSV de PastaDados e promove o cabeçalho')
        for nome, _, _, m in CONSULTAS:
            wb.Queries.Add(nome, m)

        # abas na ordem de leitura; as de dados vão para o fim
        nomes_abas = ['Leia-me', 'Painel', 'Explorar', 'Previsão', 'Indicadores', 'Fontes e licenças',
                      'Municípios', 'Dados', 'Referência', 'Previsões']
        primeira = wb.Worksheets(1)
        primeira.Name = nomes_abas[0]
        for nome in nomes_abas[1:]:
            nova = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
            nova.Name = nome
        for consulta, tabela, aba, _ in CONSULTAS:
            t0 = time.time()
            carregar_consulta(wb, wb.Worksheets(aba), consulta, tabela)
            print(f'  consulta {consulta} → tabela {tabela} na aba "{aba}" ({time.time() - t0:.0f} s)')

        wb.Names.Add('ListaMunicipios', RefersTo='=tMunicipios[municipio]')
        wb.Names.Add('ListaIndicadores', RefersTo='=tIndicadores[nome]')

        aba_painel(wb, wb.Worksheets('Painel'), N, ano_fim_obs - ano0 + 1, ano0)
        aba_explorar(wb, wb.Worksheets('Explorar'), N)
        aba_previsao(wb, wb.Worksheets('Previsão'), N, ano0, ano_fim_prev)
        aba_leiame(wb.Worksheets('Leia-me'), N)
        aba_fontes(wb.Worksheets('Fontes e licenças'))

        xl.Calculation = xlCalculationAutomatic
        xl.CalculateFull()
        wb.Worksheets('Painel').Activate()
        SAIDA.parent.mkdir(exist_ok=True)
        if SAIDA.exists():
            SAIDA.unlink()
        wb.SaveAs(str(SAIDA), xlOpenXMLWorkbook)
        print('gravado', SAIDA.relative_to(RAIZ))
        # os números que a planilha imprime em texto, para a coluna "Onde aparece" de NUMEROS_CANONICOS.md
        usados = {SAIDA.name: ['NumExemplo', 'NumMunicipios', 'NumIndicadores', 'NumAnoInicial', 'NumAnoFinal',
                               'NumCobOitentaPiorOrigem', 'NumCobOitentaPior']}
        (SAIDA.parent / 'numeros_usados.json').write_text(json.dumps(usados, ensure_ascii=False, indent=2) + '\n',
                                                         encoding='utf-8')
        wb.Close(False)
    finally:
        xl.ScreenUpdating = True
        xl.Quit()


if __name__ == '__main__':
    main()
