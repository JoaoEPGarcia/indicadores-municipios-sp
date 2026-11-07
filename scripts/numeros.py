"""Todo número impresso do projeto, calculado aqui e só aqui.

    python scripts/numeros.py

Lê os dados tratados, o modelo semântico (TMDL), os resultados das conferências e o registro de números
usados nas figuras, e escreve:
  relatorio/numeros.tex     cada número como macro LaTeX (\\newcommand{\\NumX}{...})
  NUMEROS_CANONICOS.md      uma linha por número: valor, o que é, de onde sai e onde aparece
  README.md                 montado a partir de docs/README.modelo.md, trocando cada {{NumX}} pelo valor

O README não se edita direto: edite docs/README.modelo.md e rode este script.
Os números ficam sem unidade (o texto escreve "{{NumX}}%" ou "\\NumX\\%").
Um número que depende de um passo ainda não feito (a conferência no Power BI, a planilha) sai como PENDENTE,
e o script avisa.
"""
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))
import comum  # noqa: E402
# O registro e os marcadores são os mesmos que scripts/verificar_textos.py confere.
from comum import MACRO, MARCADOR, MODELO_README, NOME_NUMERO, NUMEROS_USADOS, PENDENTE, REGISTRO_TEX  # noqa: E402

TRATADOS = RAIZ / 'dados' / 'tratados'
TMDL = RAIZ / 'powerbi' / 'painel-municipios-sp.SemanticModel' / 'definition'

# Verbo de cada Indicador para o título da Figura 1 ("Ibirá gasta 18,7% mais com saúde...").
FRASE_INDICADOR = {
    'receita_pc': ('tem', 'de receita corrente por habitante'),
    'saude_pc': ('gasta', 'com saúde por habitante'),
    'educacao_pc': ('gasta', 'com educação por habitante'),
    'dependencia_transf': ('depende', 'de transferências'),
}
INDICADORES_FIGURA_1 = ['receita_pc', 'saude_pc', 'educacao_pc', 'dependencia_transf']


# ── grafia ──────────────────────────────────────────────────────────────
def fmt(v, casas=1):
    """Vírgula decimal e ponto de milhar: 12345.6 → '12.345,6'."""
    s = f'{v:,.{casas}f}'
    return s.replace(',', '#').replace('.', ',').replace('#', '.')


def fmt_int(v):
    return fmt(v, 0)


class Registro(dict):
    def add(self, nome, valor, descricao, origem='scripts/numeros.py'):
        if not re.fullmatch(NOME_NUMERO, nome):
            raise ValueError(f'nome de macro LaTeX inválido: {nome} (só letras depois de "Num")')
        if nome in self:
            raise ValueError(f'número repetido: {nome}')
        self[nome] = dict(valor=str(valor), descricao=descricao, origem=origem)


# ── leitura ─────────────────────────────────────────────────────────────
def ler():
    d = {}
    d['mun'] = pd.read_csv(TRATADOS / 'dim_municipio.csv')
    d['ind'] = pd.read_csv(TRATADOS / 'dim_indicador.csv')
    d['fato'] = pd.read_csv(TRATADOS / 'indicadores_longo.csv')
    d['ref'] = pd.read_csv(TRATADOS / 'referencia_faixa.csv')
    d['prev'] = pd.read_csv(TRATADOS / 'previsao_receita_total.csv')
    d['met'] = pd.read_csv(TRATADOS / 'backtest_metodos.csv')
    d['cob'] = pd.read_csv(TRATADOS / 'backtest_cobertura.csv')
    d['quant'] = pd.read_csv(TRATADOS / 'modelo_quantis.csv')
    d['excl'] = pd.read_csv(TRATADOS / 'exclusoes_declaracao.csv')
    con = sqlite3.connect(TRATADOS / 'amostra.sqlite')
    d['pos'] = pd.read_sql('SELECT cod_ibge, ano, indicador_id, posicao_na_faixa FROM v_posicao', con)
    return d


def ler_tmdl():
    """Tabelas, relações e medidas do modelo semântico, lidas dos arquivos TMDL."""
    tabelas = {p.stem: p.read_text(encoding='utf-8') for p in (TMDL / 'tables').glob('*.tmdl')}
    rel = (TMDL / 'relationships.tmdl').read_text(encoding='utf-8')
    relacoes = re.findall(r'fromColumn: (\w+)\.\w+\s+toColumn: (\w+)\.\w+', rel)
    medidas = sum(len(re.findall(r'^\tmeasure ', t, flags=re.M)) for t in tabelas.values())
    return tabelas, relacoes, medidas


def ultimo_valor(d, cod, ind):
    """(ano, valor, mediana, posição) do último ano com dado do município no Indicador."""
    f = d['fato'][(d['fato'].cod_ibge == cod) & (d['fato'].indicador_id == ind)].sort_values('ano')
    if f.empty:
        return None
    ano, valor = int(f.ano.iloc[-1]), float(f.valor.iloc[-1])
    faixa = d['mun'].set_index('cod_ibge').faixa_porte[cod]
    r = d['ref'][(d['ref'].faixa_porte == faixa) & (d['ref'].ano == ano) & (d['ref'].indicador_id == ind)].iloc[0]
    p = d['pos'][(d['pos'].cod_ibge == cod) & (d['pos'].ano == ano) & (d['pos'].indicador_id == ind)].posicao_na_faixa.iloc[0]
    return dict(ano=ano, valor=valor, mediana=float(r.mediana), p25=float(r.p25), p75=float(r.p75),
                n=int(r.n), posicao=float(p) / 100, faixa=faixa)


def ponderada(g, col):
    return (g[col] * g.n_teste).sum() / g.n_teste.sum()


# ── os números ──────────────────────────────────────────────────────────
def calcular():
    d = ler()
    N = Registro()
    mun, fato = d['mun'], d['fato']

    # Base de dados
    N.add('NumMunicipios', fmt_int(len(mun)), 'municípios de SP na base')
    N.add('NumIndicadores', len(d['ind']), 'Indicadores definidos por escrito')
    N.add('NumIndicadoresComparaveis', len(comum.INDICADORES_PAINEL), 'Indicadores comparados com a faixa (todos menos a receita total)')
    N.add('NumAnoInicial', int(fato.ano.min()), 'primeiro ano da série')
    N.add('NumAnoFinal', int(fato.ano.max()), 'último ano da série')
    N.add('NumLinhasFato', fmt_int(len(fato)), 'linhas da tabela fato (município × ano × Indicador com dado)')
    N.add('NumFaixas', mun.faixa_porte.nunique(), 'Faixas de porte do Censo 2022')
    n_anos = fato.ano.max() - fato.ano.min() + 1
    N.add('NumMunicipioAnos', fmt_int(len(mun) * n_anos), 'declarações possíveis à DCA (municípios × anos)')
    N.add('NumExclusoes', len(d['excl']), 'valores declarados excluídos pela regra de qualidade')
    N.add('NumMunicipiosComExclusao', d['excl'].cod_ibge.nunique(), 'municípios com pelo menos um valor excluído')
    N.add('NumAnoPrevInicial', int(d['prev'].ano.min()), 'primeiro ano previsto')
    N.add('NumAnoPrevFinal', int(d['prev'].ano.max()), 'último ano previsto')
    N.add('NumMunicipiosComPrevisao', fmt_int(d['prev'].cod_ibge.nunique()), 'municípios com Previsão da receita')

    # Modelo semântico
    tabelas, relacoes, medidas = ler_tmdl()
    fatos = sorted({f for f, _ in relacoes})
    dims = sorted({t for _, t in relacoes})
    N.add('NumTabelasFato', len(fatos), f'tabelas fato do modelo (lado "muitos" das relações: {", ".join(fatos)})')
    N.add('NumDimensoes', len(dims), f'dimensões do modelo (lado "um": {", ".join(dims)})')
    N.add('NumRelacoes', len(relacoes), 'relações do modelo, todas 1:N e de direção única')
    N.add('NumMedidas', medidas, 'medidas DAX no modelo')

    # Conferência das medidas
    sys.path.insert(0, str(RAIZ / 'scripts'))
    from conferir_powerbi import ler_conferencia  # noqa: E402
    celulas = ler_conferencia()
    N.add('NumCelulasConferencia', len(celulas), 'células de powerbi/conferencia.md (valor esperado de uma medida)', 'scripts/conferir_powerbi.py')
    N.add('NumMunicipiosConferencia', len({c['municipio'] for c in celulas}), 'municípios sorteados para a conferência', 'scripts/gerar_conferencia.py')
    res = RAIZ / 'powerbi' / 'resultado_conferencia.csv'
    if res.exists():
        r = list(csv.DictReader(open(res, encoding='utf-8')))
        N.add('NumCelulasBatem', sum(int(x['bate']) for x in r), 'células em que a medida DAX devolveu o valor esperado', 'scripts/conferir_powerbi.py')
    else:
        N.add('NumCelulasBatem', PENDENTE, 'células em que a medida DAX devolveu o valor esperado', 'scripts/conferir_powerbi.py')
    comp = RAIZ / 'powerbi' / 'resultado_conferencia_completa.csv'
    if comp.exists():
        r = list(csv.DictReader(open(comp, encoding='utf-8')))
        N.add('NumCelulasCompletas', fmt_int(sum(int(x['celulas']) for x in r)), 'células da conferência completa (3 medidas × município × ano × Indicador)', 'scripts/conferir_powerbi.py')
        N.add('NumDivergenciasCompletas', sum(int(x['divergentes']) for x in r), 'divergências entre DAX e SQLite na conferência completa', 'scripts/conferir_powerbi.py')
    else:
        N.add('NumCelulasCompletas', PENDENTE, 'células da conferência completa', 'scripts/conferir_powerbi.py')
        N.add('NumDivergenciasCompletas', PENDENTE, 'divergências entre DAX e SQLite na conferência completa', 'scripts/conferir_powerbi.py')

    # Município de exemplo
    cod, candidatos = comum.municipio_de_exemplo()
    m = mun.set_index('cod_ibge').loc[cod]
    faixa = m.faixa_porte
    N.add('NumExemplo', m.municipio, 'município de exemplo, sorteado com semente fixa', 'scripts/comum.py')
    N.add('NumExemploCandidatos', candidatos, 'municípios com série completa entre os quais o exemplo foi sorteado', 'scripts/comum.py')
    N.add('NumExemploFaixa', faixa[3:].replace('De', 'de').replace('Até', 'até').replace('Mais', 'mais'), 'Faixa de porte do exemplo')
    N.add('NumExemploNaFaixa', int((mun.faixa_porte == faixa).sum()), 'municípios na Faixa de porte do exemplo')
    N.add('NumExemploPopulacao', fmt_int(m.populacao_censo_2022), 'população do exemplo no Censo 2022')

    # Figura 1: o Indicador com a maior diferença para a mediana
    ult = {i: ultimo_valor(d, cod, i) for i in comum.INDICADORES_PAINEL}
    dif = {i: ult[i]['valor'] / ult[i]['mediana'] - 1 for i in INDICADORES_FIGURA_1}
    foco = max(dif, key=lambda i: abs(dif[i]))
    verbo, objeto = FRASE_INDICADOR[foco]
    N.add('NumFigUmVerbo', verbo, 'verbo do título da Figura 1 (segue o Indicador de maior diferença)')
    N.add('NumFigUmObjeto', objeto, 'complemento do título da Figura 1')
    N.add('NumFigUmDif', fmt(abs(dif[foco]) * 100, 1), 'diferença do exemplo para a mediana da faixa, em %, no Indicador mais distante dos quatro da Figura 1')
    N.add('NumFigUmSentido', 'mais' if dif[foco] > 0 else 'menos', 'acima (mais) ou abaixo (menos) da mediana')
    N.add('NumFigUmAno', ult[foco]['ano'], 'ano do valor da Figura 1')
    for i, nome in [('receita_pc', 'Receita'), ('saude_pc', 'Saude'), ('educacao_pc', 'Educacao'),
                    ('dependencia_transf', 'Dependencia')]:
        N.add(f'NumDif{nome}', ('+' if dif[i] > 0 else '−') + fmt(abs(dif[i]) * 100, 1),
              f'diferença do exemplo para a mediana da faixa em {i}, {ult[i]["ano"]}, em %')

    # Figura 2: em quantos Indicadores o exemplo fica acima da mediana
    acima = [i for i in comum.INDICADORES_PAINEL if ult[i]['valor'] > ult[i]['mediana']]
    N.add('NumFigDoisAcima', len(acima), 'Indicadores em que o exemplo fica acima da mediana da faixa, no último ano de cada um')
    extremo = max(comum.INDICADORES_PAINEL, key=lambda i: abs(ult[i]['posicao'] - 0.5))
    nomes = d['ind'].set_index('indicador_id').nome
    N.add('NumFigDoisExtremo', nomes[extremo], 'Indicador em que o exemplo está mais perto de uma ponta da faixa')
    N.add('NumFigDoisExtremoPos', fmt(ult[extremo]['posicao'] * 100, 0), 'Posição na faixa do exemplo nesse Indicador, em %')

    # Figura 3: Previsão da receita do exemplo
    p = d['prev'][d['prev'].cod_ibge == cod].set_index('ano')
    af = int(p.index.max())
    rt = fato[(fato.cod_ibge == cod) & (fato.indicador_id == 'receita_total')].set_index('ano').valor
    N.add('NumExemploReceitaUltima', fmt(rt.iloc[-1], 1), f'receita corrente total do exemplo em {int(rt.index[-1])}, R$ milhões de 2025')
    N.add('NumExemploPrevista', fmt(p.previsto[af], 1), f'Previsão da receita do exemplo para {af}, R$ milhões de 2025')
    N.add('NumExemploInfOitenta', fmt(p.inferior_80[af], 1), 'limite inferior do Intervalo de previsão de 80%')
    N.add('NumExemploSupOitenta', fmt(p.superior_80[af], 1), 'limite superior do Intervalo de previsão de 80%')
    N.add('NumExemploInfNoventaCinco', fmt(p.inferior_95[af], 1), 'limite inferior do Intervalo de previsão de 95%')
    N.add('NumExemploSupNoventaCinco', fmt(p.superior_95[af], 1), 'limite superior do Intervalo de previsão de 95%')

    # Figura 4 e texto: Teste contra o passado
    met = d['met'].set_index(['metodo', 'horizonte'])
    for metodo, nome in [('tendencia3', 'Escolhido'), ('ingenuo', 'Ingenuo'), ('tendencia5', 'Reta')]:
        for h, hn in [(1, 'Um'), (2, 'Dois'), (3, 'Tres')]:
            N.add(f'NumErro{nome}{hn}', fmt(met.erro_medio_abs_pct[(metodo, h)], 1),
                  f'erro médio absoluto, em %, do método {metodo} a {h} ano(s)', 'scripts/modelo.py')
        N.add(f'NumVies{nome}Tres', ('+' if met.vies_pct[(metodo, 3)] > 0 else '−') + fmt(abs(met.vies_pct[(metodo, 3)]), 1),
              f'viés médio, em %, do método {metodo} a 3 anos', 'scripts/modelo.py')
    N.add('NumOrigensTeste', d['cob'].origem_fora.nunique(), 'anos de origem do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumOrigemInicial', int(d['cob'].origem_fora.min()), 'primeira origem do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumOrigemFinal', int(d['cob'].origem_fora.max()), 'última origem do Teste contra o passado', 'scripts/modelo.py')
    cob = d['cob']
    for nivel, nn in [(80, 'Oitenta'), (95, 'NoventaCinco')]:
        g = cob[cob.nivel == nivel]
        N.add(f'NumCob{nn}Sem', fmt(ponderada(g, 'cobertura_sem_ajuste'), 0), f'cobertura do intervalo de {nivel}% sem ajuste, em %', 'scripts/modelo.py')
        N.add(f'NumCob{nn}Com', fmt(ponderada(g, 'cobertura_com_ajuste'), 0), f'cobertura do intervalo de {nivel}% depois do ajuste, em %', 'scripts/modelo.py')
        por_origem = {o: ponderada(gg, 'cobertura_com_ajuste') for o, gg in g.groupby('origem_fora')}
        pior = min(por_origem, key=por_origem.get)
        N.add(f'NumCob{nn}Pior', fmt(por_origem[pior], 0), f'cobertura do intervalo de {nivel}% na pior origem deixada de fora, depois do ajuste, em %', 'scripts/modelo.py')
        N.add(f'NumCob{nn}PiorOrigem', int(pior), f'a pior origem deixada de fora para o intervalo de {nivel}%', 'scripts/modelo.py')
        esc = d['quant'][d['quant'].nivel == nivel].escala.unique()
        N.add(f'NumEscala{nn}', fmt(float(esc[0]), 2), f'fator de alargamento do intervalo de {nivel}%', 'scripts/modelo.py')

    # Planilha (preenchido por scripts/conferir_excel.py)
    planilha = RAIZ / 'excel' / 'resultado_conferencia_excel.json'
    if planilha.exists():
        r = json.loads(planilha.read_text(encoding='utf-8'))
        N.add('NumCelulasExcel', fmt_int(r['celulas']), 'células da aba Painel conferidas contra o SQLite', 'scripts/conferir_excel.py')
        N.add('NumCelulasExcelBatem', fmt_int(r['batem']), 'células da aba Painel iguais ao SQLite', 'scripts/conferir_excel.py')
        N.add('NumMunicipiosExcel', r['municipios'], 'municípios testados na planilha', 'scripts/conferir_excel.py')
    else:
        for nome, desc in [('NumCelulasExcel', 'células da aba Painel conferidas contra o SQLite'),
                           ('NumCelulasExcelBatem', 'células da aba Painel iguais ao SQLite'),
                           ('NumMunicipiosExcel', 'municípios testados na planilha')]:
            N.add(nome, PENDENTE, desc, 'scripts/conferir_excel.py')
    numeros_do_relatorio(N)
    return N


# ── saídas ──────────────────────────────────────────────────────────────
def onde_aparece(N):
    """Procura cada número nos textos e no registro das figuras."""
    usados = {}         # texto: os números que ele usa, por marcador ou macro
    for caminho in [RAIZ / MODELO_README, *sorted((RAIZ / 'relatorio').glob('**/*.tex'))]:
        if caminho.exists() and caminho != RAIZ / REGISTRO_TEX:
            texto = caminho.read_text(encoding='utf-8')
            usados[caminho.relative_to(RAIZ).as_posix()] = set(MARCADOR.findall(texto)) | set(MACRO.findall(texto))
    registros = {}      # figuras e planilha: cada gerador grava os números que imprime
    for usado in NUMEROS_USADOS:
        arq = RAIZ / usado
        if arq.exists():
            for alvo, nomes in json.loads(arq.read_text(encoding='utf-8')).items():
                registros[f'{Path(usado).parent.as_posix()}/{alvo}'] = nomes
    onde = {}
    for nome in N:
        lugares = [f for f, nomes in usados.items() if nome in nomes]
        lugares += [alvo for alvo, nomes in registros.items() if nome in nomes]
        onde[nome] = lugares
    return onde


def escrever_tex(N):
    linhas = ['% GERADO por scripts/numeros.py. Não edite à mão: rode o script de novo.',
              '% Registro de cada número em NUMEROS_CANONICOS.md.']
    for k, v in N.items():
        valor = v['valor'].replace('%', r'\%').replace('−', '$-$')
        linhas.append(f'\\newcommand{{\\{k}}}{{{valor}}}')
    destino = RAIZ / REGISTRO_TEX
    destino.parent.mkdir(exist_ok=True)
    destino.write_text('\n'.join(linhas) + '\n', encoding='utf-8')


def escrever_canonicos(N, onde):
    linhas = ['# Números canônicos', '',
              'Cada número impresso no README, no relatório e nos títulos das figuras tem uma linha aqui. '
              'Arquivo **gerado** por `scripts/numeros.py`: para mudar um número, mude o script ou o dado, rode '
              '`python scripts/numeros.py` e confira os lugares da coluna "Onde aparece". Valores monetários em reais de 2025 (IPCA, média do ano).',
              '', '| Número | Valor | O que é | Sai de | Onde aparece |', '|---|---|---|---|---|']
    for k, v in N.items():
        lugares = ', '.join(f'`{l}`' for l in onde[k]) or '(ainda não usado)'
        linhas.append(f"| `\\{k}` | {v['valor']} | {v['descricao']} | `{v['origem']}` | {lugares} |")
    (RAIZ / 'NUMEROS_CANONICOS.md').write_text('\n'.join(linhas) + '\n', encoding='utf-8')


def escrever_readme(N):
    modelo = RAIZ / MODELO_README
    if not modelo.exists():
        return
    texto = modelo.read_text(encoding='utf-8')
    texto = re.sub(r'<!--.*?-->\n?', '', texto, flags=re.S)
    faltam = sorted(set(MARCADOR.findall(texto)) - set(N))
    if faltam:
        sys.exit(f'README.modelo.md usa números que não existem: {faltam}')
    texto = MARCADOR.sub(lambda mm: N[mm.group(1)]['valor'], texto)
    (RAIZ / 'README.md').write_text(texto, encoding='utf-8')


# ══ Relatório em LaTeX (ticket 07) ═════════════════════════════════════
# Os números que só o relatório usa e os arquivos que ele lê de relatorio/gerados/: linhas de tabela
# (com \linhasde) e trechos de código (com \input), todos com a primeira linha "% GERADO". As linhas de
# tabela usam as macros \Num... em vez do valor, para que "Onde aparece" as encontre.
GERADOS = RAIZ / 'relatorio' / 'gerados'
PLANILHA = RAIZ / 'excel' / 'painel-municipios-sp.xlsx'
CABECALHO_GERADO = '% GERADO por scripts/numeros.py. Não edite à mão: rode o script de novo.'
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
         'Outubro', 'Novembro', 'Dezembro']
# Funções da planilha como o Excel em português as mostra (o arquivo as guarda em inglês).
FUNCOES_PT = {'XLOOKUP': 'PROCX', 'IF': 'SE', 'AND': 'E', 'ISNUMBER': 'ÉNÚM', 'SUMPRODUCT': 'SOMARPRODUTO',
              'MAXIFS': 'MÁXIMOSES', 'NA': 'NÃO.DISP', 'SEQUENCE': 'SEQUÊNCIA', 'MATCH': 'CORRESP', 'LET': 'LET'}
# Papel e grão de cada tabela do modelo estrela, e o CSV que ela lê (dim_ano é calculada no modelo).
TABELAS_MODELO = [
    ('fato_indicador', 'fato', 'município, ano e Indicador', 'indicadores_longo.csv'),
    ('ref_faixa', 'fato', 'Faixa de porte, ano e Indicador', 'referencia_faixa.csv'),
    ('previsao', 'fato', 'município e ano previsto', 'previsao_receita_total.csv'),
    ('dim_municipio', 'dimensão', 'município', 'dim_municipio.csv'),
    ('dim_indicador', 'dimensão', 'Indicador', 'dim_indicador.csv'),
    ('dim_ano', 'dimensão', 'ano', None),
]
NOME_METODO = {'ingenuo': 'Repetir o último valor', 'tendencia': 'Tendência dos {} últimos anos',
               'reta': 'Reta dos {} últimos anos'}


def _camel(texto):
    """'Comparação na faixa' → 'ComparacaoNaFaixa': parte de nome de macro (só letras)."""
    import unicodedata
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return ''.join(p[:1].upper() + p[1:] for p in re.findall(r'[A-Za-z]+', sem_acento))


def _tt(nome):
    return r'\texttt{' + nome.replace('_', r'\_') + '}'


def medidas_por_pasta():
    """{pasta de exibição sem o número de ordem: [medidas]}, na ordem do TMDL."""
    texto = (TMDL / 'tables' / 'Medidas.tmdl').read_text(encoding='utf-8')
    pastas = {}
    for bloco in re.split(r'(?=^\tmeasure )', texto, flags=re.M)[1:]:
        nome = re.match(r"\tmeasure (?:'([^']+)'|(\S+))", bloco)
        pasta = re.search(r'^\t\tdisplayFolder: (?:\d+\.\s*)?(.+)$', bloco, re.M).group(1).strip()
        pastas.setdefault(pasta, []).append(nome.group(1) or nome.group(2))
    return pastas


def numeros_do_relatorio(N):
    import datetime
    hoje = datetime.date.today()
    N.add('NumMesCapa', MESES[hoje.month - 1], 'mês da capa do relatório (o mês em que o registro foi gerado)')
    N.add('NumAnoCapa', hoje.year, 'ano da capa do relatório (o ano em que o registro foi gerado)')

    sql = (RAIZ / 'sql' / '20_indicadores.sql').read_text(encoding='utf-8')
    base = re.search(r'CREATE VIEW v_fator_\d+ AS.*?WHERE ano = (\d{4})', sql, re.S).group(1)
    N.add('NumAnoBaseReais', base, 'ano-base dos reais (IPCA médio do ano)', 'sql/20_indicadores.sql')
    baixo, alto = re.search(r'rc_liq\s*/\s*rc_liq_outros\s*<\s*([\d.]+)\s*OR\s*rc_liq\s*/\s*rc_liq_outros\s*>\s*([\d.]+)',
                            sql).groups()
    if abs(float(baixo) * float(alto) - 1) > 1e-9:
        raise ValueError(f'a regra da declaração deixou de ser simétrica ({baixo} e {alto}): reescreva o texto')
    N.add('NumRegraFator', fmt_int(float(alto)), 'quantas vezes acima ou abaixo da média dos outros anos o valor sai',
          'sql/20_indicadores.sql')

    linhas = {t: len(pd.read_csv(TRATADOS / arq)) for t, _, _, arq in TABELAS_MODELO if arq}
    N.add('NumLinhasRefFaixa', fmt_int(linhas['ref_faixa']), 'linhas de ref_faixa (Faixa de porte × ano × Indicador)')
    N.add('NumLinhasPrevisao', fmt_int(linhas['previsao']), 'linhas de previsao (município × ano previsto)')
    anos_fim = max(int(N['NumAnoFinal']['valor']), int(N['NumAnoPrevFinal']['valor']))
    N.add('NumLinhasDimAno', anos_fim - int(N['NumAnoInicial']['valor']) + 1,
          'linhas de dim_ano (do primeiro ano dos dados ao último previsto)')

    pastas = medidas_por_pasta()
    N.add('NumPastasMedidas', len(pastas), 'pastas de exibição das medidas DAX')
    for pasta, medidas in pastas.items():
        N.add(f'NumMedidasPasta{_camel(pasta)}', len(medidas), f'medidas DAX na pasta "{pasta}"')
    paginas = [p for p in (RAIZ / 'powerbi' / 'painel-municipios-sp.Report' / 'definition' / 'pages').iterdir() if p.is_dir()]
    N.add('NumPaginasPainel', len(paginas), 'páginas do painel no Power BI', 'scripts/gerar_relatorio_pbi.py')

    comp = RAIZ / 'powerbi' / 'resultado_conferencia_completa.csv'
    N.add('NumMedidasCompletas', len(list(csv.DictReader(open(comp, encoding='utf-8')))) if comp.exists() else PENDENTE,
          'medidas conferidas em cada linha da fato na conferência completa', 'scripts/conferir_powerbi.py')

    val = (TRATADOS / 'validacao.txt').read_text(encoding='utf-8')
    comparados = re.findall(r'^\[OK\] \w+: SQL = pandas: (\d+) valores, só no SQL (\d+), só no pandas (\d+), '
                            r'maior diferença (\S+)$', val, re.M)
    total = sum(int(c[0]) for c in comparados)
    iguais = sum(int(c[0]) for c in comparados if c[1] == c[2] == '0' and float(c[3]) == 0)
    N.add('NumValoresValidados', fmt_int(total), 'valores dos Indicadores refeitos em pandas e comparados com o SQL', 'scripts/validar.py')
    N.add('NumValoresValidadosIguais', fmt_int(iguais), 'desses, os iguais ao SQL (diferença máxima zero)', 'scripts/validar.py')

    met = pd.read_csv(TRATADOS / 'backtest_metodos.csv')
    janelas = {m: int(re.sub(r'\D', '', m)) for m in met.metodo.unique() if re.search(r'\d', m)}
    N.add('NumMetodos', met.metodo.nunique(), 'métodos de previsão testados contra o passado', 'scripts/modelo.py')
    N.add('NumHorizontes', int(met.horizonte.max()), 'anos à frente da Previsão da receita e do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumJanelaEscolhido', janelas['tendencia3'], 'anos da tendência do método escolhido', 'scripts/modelo.py')
    N.add('NumJanelaReta', janelas['tendencia5'], 'anos da reta do método concorrente', 'scripts/modelo.py')
    for nivel, nn in [(80, 'Oitenta'), (95, 'NoventaCinco')]:
        N.add(f'NumNivel{nn}', nivel, 'nível de um Intervalo de previsão, em %', 'scripts/modelo.py')


def formula_da_planilha(aba, celula):
    """A fórmula de uma célula da planilha gerada, como o Excel em português a mostra: PROCX no lugar de
    XLOOKUP, ponto e vírgula entre os argumentos, sem os prefixos _xlfn. e _xlpm. do arquivo."""
    import openpyxl
    v = openpyxl.load_workbook(PLANILHA)[aba][celula].value
    f = getattr(v, 'text', v).replace('_xlfn.', '').replace('_xlpm.', '')
    saida, i, colchete = [], 0, 0
    while i < len(f):
        c = f[i]
        if c == '"':                                   # texto: copia até as aspas de fechamento
            fim = f.index('"', i + 1)
            saida.append(f[i:fim + 1])
            i = fim + 1
            continue
        m = None if colchete else re.match(r'[A-Z][A-Z.]*(?=\()', f[i:])
        if m and (i == 0 or not re.match(r'[\w.]', f[i - 1])):
            saida.append(FUNCOES_PT.get(m.group(0), m.group(0)))
            i += len(m.group(0))
            continue
        colchete += (c == '[') - (c == ']')
        saida.append(';' if c == ',' and not colchete else c)
        i += 1
    return ''.join(saida)


def quebrar_formula(f):
    """A fórmula em várias linhas, para caber na página: um argumento por linha na função de fora (no LET,
    um nome e o seu valor por linha), alinhados depois do parêntese."""
    abre = f.index('(')
    args, atual, prof, texto = [], '', 0, False
    for c in f[abre + 1:-1]:
        texto ^= c == '"'
        if not texto:
            prof += (c == '(') - (c == ')')
        if c == ';' and prof == 0 and not texto:
            args.append(atual.strip())
            atual = ''
        else:
            atual += c
    args.append(atual.strip())
    if f[:abre].endswith('LET'):
        args = ['; '.join(args[k:k + 2]) for k in range(0, len(args) - 1, 2)] + [args[-1]]
    recuo = ' ' * (abre + 1)
    return f[:abre + 1] + (';\n' + recuo).join(args) + ')'


def medida_dax(nome):
    """A expressão de uma medida, lida do TMDL, sem os comentários de linha e com dois espaços de recuo."""
    texto = (TMDL / 'tables' / 'Medidas.tmdl').read_text(encoding='utf-8')
    m = re.search(r"^\tmeasure '" + re.escape(nome) + r"' =(.*)\n((?:\t\t\t.*\n|[ \t]*\n)*)", texto, re.M)
    corpo = [l[3:].replace('\t', '  ') for l in m.group(2).splitlines()
             if l.strip() and not l.strip().startswith('--')]
    return '\n'.join([f'{nome} ={m.group(1)}'.rstrip()] + ['  ' + l for l in corpo])


def _codigo(destino, codigo):
    destino.write_text('\n'.join([CABECALHO_GERADO, r'\begin{verbatim}', codigo, r'\end{verbatim}']) + '\n',
                       encoding='utf-8')


def _linhas(destino, linhas):
    destino.write_text('\n'.join([CABECALHO_GERADO] + [l + r' \\' for l in linhas]) + '\n', encoding='utf-8')


def escrever_gerados_relatorio(N):
    GERADOS.mkdir(parents=True, exist_ok=True)
    _, relacoes, _ = ler_tmdl()
    liga = {}
    for f, d in relacoes:
        liga.setdefault(f, []).append(d)
        liga.setdefault(d, []).append(f)
    papeis = {t: p for t, p, _, _ in TABELAS_MODELO}
    if set(liga) != set(papeis) or any((papeis[f], papeis[d]) != ('fato', 'dimensão') for f, d in relacoes):
        raise ValueError('as relações do TMDL não batem com TABELAS_MODELO: atualize a lista')
    macro_linhas = {'fato_indicador': r'\NumLinhasFato', 'ref_faixa': r'\NumLinhasRefFaixa',
                    'previsao': r'\NumLinhasPrevisao', 'dim_municipio': r'\NumMunicipios',
                    'dim_indicador': r'\NumIndicadores', 'dim_ano': r'\NumLinhasDimAno'}
    _linhas(GERADOS / 'tabelas_modelo.tex', [
        f'{_tt(t)} & {p} & {g} & {macro_linhas[t]} & ' + ', '.join(_tt(x) for x in sorted(liga[t]))
        for t, p, g, _ in TABELAS_MODELO])

    _linhas(GERADOS / 'pastas_medidas.tex', [
        f'{pasta} & \\NumMedidasPasta{_camel(pasta)} & ' + '; '.join(medidas[:3])
        + ('; \\ldots' if len(medidas) > 3 else '')
        for pasta, medidas in medidas_por_pasta().items()])

    _linhas(GERADOS / 'conferencias.tex', [
        r'Indicadores: SQL e pandas & cada valor refeito em pandas, sem olhar o SQL & \NumValoresValidados & \NumValoresValidadosIguais',
        r'Medidas DAX e tabela de conferência & valores esperados de \NumMunicipiosConferencia{} municípios sorteados & \NumCelulasConferencia & \NumCelulasBatem',
        r'Medidas DAX e SQLite & \NumMedidasCompletas{} medidas em cada linha da fato & \NumCelulasCompletas & \NumDivergenciasCompletas{} divergências',
        r'Planilha e SQLite & aba Painel calculada no Excel para a web, \NumMunicipiosExcel{} municípios & \NumCelulasExcel & \NumCelulasExcelBatem',
    ])

    met = pd.read_csv(TRATADOS / 'backtest_metodos.csv')
    linhas = []
    for metodo, nome, rotulo in [('ingenuo', 'Ingenuo', NOME_METODO['ingenuo']),
                                 ('tendencia3', 'Escolhido', NOME_METODO['tendencia'].format(r'\NumJanelaEscolhido{}')),
                                 ('tendencia5', 'Reta', NOME_METODO['reta'].format(r'\NumJanelaReta{}'))]:
        escolhido = bool(met[met.metodo == metodo].escolhido.max())
        celulas = ([rotulo + (' (escolhido)' if escolhido else '')]
                   + [f'\\NumErro{nome}{h}\\%' for h in ('Um', 'Dois', 'Tres')] + [f'\\NumVies{nome}Tres\\%'])
        linhas.append(' & '.join(f'\\textbf{{{c}}}' if escolhido else c for c in celulas))
    _linhas(GERADOS / 'teste_metodos.tex', linhas)

    _linhas(GERADOS / 'cobertura.tex', [
        f'\\NumNivel{nn}\\% & \\NumCob{nn}Sem\\% & \\NumEscala{nn} & \\NumCob{nn}Com\\% & '
        f'\\NumCob{nn}Pior\\% (origem \\NumCob{nn}PiorOrigem)' for nn in ('Oitenta', 'NoventaCinco')])

    _codigo(GERADOS / 'dax_mediana.tex', medida_dax('Mediana da faixa'))
    _codigo(GERADOS / 'dax_posicao.tex', medida_dax('Posição na faixa'))
    _codigo(GERADOS / 'excel_procx.tex', quebrar_formula(formula_da_planilha('Painel', 'E13')))
    _codigo(GERADOS / 'excel_let.tex', quebrar_formula(formula_da_planilha('Painel', 'D13')))
# ══ fim do relatório em LaTeX ══════════════════════════════════════════


def main():
    N = calcular()
    escrever_gerados_relatorio(N)
    onde = onde_aparece(N)
    escrever_tex(N)
    escrever_canonicos(N, onde)
    escrever_readme(N)
    pend = [k for k, v in N.items() if v['valor'] == PENDENTE]
    print(f'{len(N)} números gravados em relatorio/numeros.tex e NUMEROS_CANONICOS.md.')
    if pend:
        usados_pend = [k for k in pend if onde[k]]
        print(f'  [aviso] {len(pend)} pendentes ({", ".join(pend)}).')
        if usados_pend:
            print(f'  [ERRO] pendentes já usados em texto: {", ".join(usados_pend)}')
            sys.exit(1)


if __name__ == '__main__':
    main()
