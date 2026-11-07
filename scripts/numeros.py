"""Todo número impresso do projeto, calculado aqui e só aqui.

    python scripts/numeros.py

Lê os dados tratados, o modelo semântico (TMDL), os resultados das conferências e o registro de números
usados nas figuras, e escreve:
  relatorio/numeros.tex     cada número como macro LaTeX (\\newcommand{\\NumX}{...})
  NUMEROS_CANONICOS.md      uma linha por número: valor, o que é, de onde sai e onde aparece
  README.md                 montado a partir de docs/README.modelo.md, trocando cada {{NumX}} pelo valor

  relatorio/gerados/        linhas de tabela e trechos de código do relatório (scripts/relatorio_gerados.py)

O README não se edita direto: edite docs/README.modelo.md e rode este script.
Os números ficam sem unidade (o texto escreve "{{NumX}}%" ou "\\NumX\\%").
Um número que depende de um passo ainda não feito (a conferência no Power BI, a planilha) sai como PENDENTE,
e o script avisa. A planilha (scripts/montar_excel.py) usa só `calcular_dos_dados()`: os números que saem de
dados/tratados/, sem o modelo, as páginas do painel nem as conferências.
"""
import csv
import datetime
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))
import comum  # noqa: E402
import relatorio_gerados  # noqa: E402
import tmdl  # noqa: E402
# O registro e os marcadores são os mesmos que scripts/verificar_textos.py confere.
from comum import MACRO, MARCADOR, MODELO_README, NOME_NUMERO, NUMEROS_USADOS, PENDENTE, REGISTRO_TEX  # noqa: E402

TRATADOS = comum.TRATADOS

# Verbo de cada Indicador para o título da Figura 1 ("Ibirá gasta 18,7% mais com saúde...").
FRASE_INDICADOR = {
    'receita_pc': ('tem', 'de receita corrente por habitante'),
    'saude_pc': ('gasta', 'com saúde por habitante'),
    'educacao_pc': ('gasta', 'com educação por habitante'),
    'dependencia_transf': ('depende', 'de transferências'),
}
DATA_CONSULTA_FONTES = '14/10/2026'   # dia em que os textos de licença das fontes foram lidos (README, Fontes)
PAGINAS_PBIR = RAIZ / 'powerbi' / 'painel-municipios-sp.Report' / 'definition' / 'pages' / 'pages.json'
RESULTADO_PBI = RAIZ / 'powerbi' / 'resultado_conferencia.csv'
RESULTADO_PBI_COMPLETO = RAIZ / 'powerbi' / 'resultado_conferencia_completa.csv'
RESULTADO_EXCEL = comum.EXCEL / 'resultado_conferencia_excel.json'


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
    try:
        d['pos'] = pd.read_sql('SELECT cod_ibge, ano, indicador_id, posicao_na_faixa FROM v_posicao', con)
    finally:
        con.close()
    return d


def ler_resultado(arquivo):
    """As linhas de um CSV de resultado de conferência, ou None se ele ainda não existe."""
    if not arquivo.exists():
        return None
    with open(arquivo, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


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
    """Todo o registro, na ordem de relatorio/numeros.tex e de NUMEROS_CANONICOS.md."""
    d = ler()
    modelo = tmdl.ler()
    N = Registro()
    numeros_da_base(N, d)
    numeros_dos_dados_do_readme(N, d)
    numeros_do_painel_e_das_fontes(N)
    numeros_do_modelo(N, modelo)
    numeros_da_conferencia_do_painel(N)
    numeros_do_exemplo(N, d)
    numeros_do_teste(N, d)
    numeros_da_conferencia_da_planilha(N)
    numeros_do_relatorio(N, modelo)
    return N


def calcular_dos_dados():
    """Só os números que saem de dados/tratados/ (e do município de exemplo, sorteado deles): os que a planilha
    escreve. Não lê o modelo, as páginas do painel, as conferências nem a planilha, e por isso o construtor
    da planilha roda antes de tudo isso existir."""
    d = ler()
    N = Registro()
    numeros_da_base(N, d)
    numeros_dos_dados_do_readme(N, d)
    numeros_do_exemplo(N, d)
    numeros_do_teste(N, d)
    return N


def numeros_da_base(N, d):
    mun, fato = d['mun'], d['fato']
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


def numeros_dos_dados_do_readme(N, d):
    """Os números que o README imprime, que saem dos dados e que nenhum outro bloco calcula."""
    N.add('NumAnoBase', int(d['prev'].ano.min()) - 1, 'ano dos preços dos valores em reais (o anterior ao primeiro ano previsto)')
    pib = d['fato'][d['fato'].indicador_id == 'pib_pc']
    N.add('NumAnoFinalPib', int(pib.ano.max()), 'último ano do PIB dos Municípios na base')
    niveis = sorted(int(n) for n in d['cob'].nivel.unique())
    N.add('NumNivelMenor', niveis[0], 'nível, em %, do Intervalo de previsão mais estreito', 'scripts/modelo.py')
    N.add('NumNivelMaior', niveis[-1], 'nível, em %, do Intervalo de previsão mais largo', 'scripts/modelo.py')


def numeros_do_painel_e_das_fontes(N):
    paginas = json.loads(PAGINAS_PBIR.read_text(encoding='utf-8'))['pageOrder']
    N.add('NumPaginasPainel', len(paginas), 'páginas do painel do Power BI (pageOrder do PBIR)', 'scripts/gerar_relatorio_pbi.py')
    N.add('NumDataConsultaFontes', DATA_CONSULTA_FONTES, 'data da leitura das condições de uso das fontes (constante registrada aqui)')


def numeros_do_modelo(N, modelo):
    fatos = sorted({f for f, _ in modelo.relacoes})
    dims = sorted({t for _, t in modelo.relacoes})
    N.add('NumTabelasFato', len(fatos), f'tabelas fato do modelo (lado "muitos" das relações: {", ".join(fatos)})')
    N.add('NumDimensoes', len(dims), f'dimensões do modelo (lado "um": {", ".join(dims)})')
    N.add('NumRelacoes', len(modelo.relacoes), 'relações do modelo, todas 1:N e de direção única')
    N.add('NumMedidas', len(modelo.medidas), 'medidas DAX no modelo')


def numeros_da_conferencia_do_painel(N):
    celulas = comum.ler_conferencia()
    N.add('NumCelulasConferencia', len(celulas), 'células de powerbi/conferencia.md (valor esperado de uma medida)', 'scripts/conferir_powerbi.py')
    N.add('NumMunicipiosConferencia', len({c['municipio'] for c in celulas}), 'municípios sorteados para a conferência', 'scripts/gerar_conferencia.py')
    r = ler_resultado(RESULTADO_PBI)
    N.add('NumCelulasBatem', sum(int(x['bate']) for x in r) if r is not None else PENDENTE,
          'células em que a medida DAX devolveu o valor esperado', 'scripts/conferir_powerbi.py')
    r = ler_resultado(RESULTADO_PBI_COMPLETO)
    if r is not None:
        N.add('NumCelulasCompletas', fmt_int(sum(int(x['celulas']) for x in r)), 'células da conferência completa (3 medidas × município × ano × Indicador)', 'scripts/conferir_powerbi.py')
        N.add('NumDivergenciasCompletas', sum(int(x['divergentes']) for x in r), 'divergências entre DAX e SQLite na conferência completa', 'scripts/conferir_powerbi.py')
    else:
        N.add('NumCelulasCompletas', PENDENTE, 'células da conferência completa', 'scripts/conferir_powerbi.py')
        N.add('NumDivergenciasCompletas', PENDENTE, 'divergências entre DAX e SQLite na conferência completa', 'scripts/conferir_powerbi.py')


def numeros_do_exemplo(N, d):
    """O município de exemplo e os números das Figuras 1 a 3, que o mostram."""
    mun, fato = d['mun'], d['fato']
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
    dif = {i: ult[i]['valor'] / ult[i]['mediana'] - 1 for i in comum.INDICADORES_RESUMO}
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


def numeros_do_teste(N, d):
    """Figura 4 e texto: o Teste contra o passado, por método, horizonte e nível do Intervalo de previsão."""
    met = d['met'].set_index(['metodo', 'horizonte'])
    ultimo = max(comum.MACRO_HORIZONTE)
    for metodo, nome in comum.macros_dos_metodos().items():
        for h, hn in comum.MACRO_HORIZONTE.items():
            N.add(f'NumErro{nome}{hn}', fmt(met.erro_medio_abs_pct[(metodo, h)], 1),
                  f'erro médio absoluto, em %, do método {metodo} a {h} ano(s)', 'scripts/modelo.py')
        vies = met.vies_pct[(metodo, ultimo)]
        N.add(f'NumVies{nome}{comum.MACRO_HORIZONTE[ultimo]}', ('+' if vies > 0 else '−') + fmt(abs(vies), 1),
              f'viés médio, em %, do método {metodo} a {ultimo} anos', 'scripts/modelo.py')
    cob = d['cob']
    N.add('NumOrigensTeste', cob.origem_fora.nunique(), 'anos de origem do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumOrigemInicial', int(cob.origem_fora.min()), 'primeira origem do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumOrigemFinal', int(cob.origem_fora.max()), 'última origem do Teste contra o passado', 'scripts/modelo.py')
    for nivel in sorted(int(n) for n in cob.nivel.unique()):
        nn = comum.MACRO_NIVEL[nivel]
        g = cob[cob.nivel == nivel]
        N.add(f'NumCob{nn}Sem', fmt(ponderada(g, 'cobertura_sem_ajuste'), 0), f'cobertura do intervalo de {nivel}% sem ajuste, em %', 'scripts/modelo.py')
        N.add(f'NumCob{nn}Com', fmt(ponderada(g, 'cobertura_com_ajuste'), 0), f'cobertura do intervalo de {nivel}% depois do ajuste, em %', 'scripts/modelo.py')
        por_origem = comum.cobertura_por_origem(nivel)
        pior = min(por_origem, key=por_origem.get)
        N.add(f'NumCob{nn}Pior', fmt(por_origem[pior], 0), f'cobertura do intervalo de {nivel}% na pior origem deixada de fora, depois do ajuste, em %', 'scripts/modelo.py')
        N.add(f'NumCob{nn}PiorOrigem', int(pior), f'a pior origem deixada de fora para o intervalo de {nivel}%', 'scripts/modelo.py')
        esc = d['quant'][d['quant'].nivel == nivel].escala.unique()
        N.add(f'NumEscala{nn}', fmt(float(esc[0]), 2), f'fator de alargamento do intervalo de {nivel}%', 'scripts/modelo.py')


def numeros_da_conferencia_da_planilha(N):
    """Lidos do resultado que scripts/conferir_excel.py grava."""
    r = json.loads(RESULTADO_EXCEL.read_text(encoding='utf-8')) if RESULTADO_EXCEL.exists() else None
    for nome, chave, desc in [('NumCelulasExcel', 'celulas', 'células da aba Painel conferidas contra o SQLite'),
                              ('NumCelulasExcelBatem', 'batem', 'células da aba Painel iguais ao SQLite'),
                              ('NumMunicipiosExcel', 'municipios', 'municípios testados na planilha')]:
        valor = PENDENTE if r is None else (r[chave] if chave == 'municipios' else fmt_int(r[chave]))
        N.add(nome, valor, desc, 'scripts/conferir_excel.py')


def numeros_do_relatorio(N, modelo):
    """Os números que só o relatório em LaTeX usa: a data da capa, a regra da declaração, as linhas de cada tabela
    do modelo, as medidas por pasta de exibição, a conferência da base e o tamanho do Teste contra o passado."""
    # A data da capa é a da conferência da planilha gravada (o último passo que traz número novo), e não a do
    # relógio: rodar o script de novo noutro mês não muda o registro.
    r = json.loads(RESULTADO_EXCEL.read_text(encoding='utf-8')) if RESULTADO_EXCEL.exists() else {}
    dia = datetime.date.fromisoformat(r['data']) if 'data' in r else None
    N.add('NumMesCapa', comum.MESES[dia.month - 1] if dia else PENDENTE,
          'mês da capa do relatório (o da conferência da planilha gravada em excel/resultado_conferencia_excel.json)',
          'scripts/conferir_excel.py')
    N.add('NumAnoCapa', dia.year if dia else PENDENTE,
          'ano da capa do relatório (o da conferência da planilha gravada em excel/resultado_conferencia_excel.json)',
          'scripts/conferir_excel.py')

    sql = (RAIZ / 'sql' / '20_indicadores.sql').read_text(encoding='utf-8')
    baixo, alto = re.search(r'rc_liq\s*/\s*rc_liq_outros\s*<\s*([\d.]+)\s*OR\s*rc_liq\s*/\s*rc_liq_outros\s*>\s*([\d.]+)',
                            sql).groups()
    if abs(float(baixo) * float(alto) - 1) > 1e-9:
        raise ValueError(f'a regra da declaração deixou de ser simétrica ({baixo} e {alto}): reescreva o texto')
    N.add('NumRegraFator', fmt_int(float(alto)), 'quantas vezes acima ou abaixo da média dos outros anos o valor sai',
          'sql/20_indicadores.sql')

    linhas = {t: len(pd.read_csv(TRATADOS / arq)) for t, _, _, arq, _ in tmdl.TABELAS_MODELO if arq}
    N.add('NumLinhasRefFaixa', fmt_int(linhas['ref_faixa']), 'linhas de ref_faixa (Faixa de porte × ano × Indicador)')
    N.add('NumLinhasPrevisao', fmt_int(linhas['previsao']), 'linhas de previsao (município × ano previsto)')
    anos_fim = max(int(N['NumAnoFinal']['valor']), int(N['NumAnoPrevFinal']['valor']))
    N.add('NumLinhasDimAno', anos_fim - int(N['NumAnoInicial']['valor']) + 1,
          'linhas de dim_ano (do primeiro ano dos dados ao último previsto)')

    pastas = modelo.pastas()
    N.add('NumPastasMedidas', len(pastas), 'pastas de exibição das medidas DAX')
    for pasta, medidas in pastas.items():
        N.add(f'NumMedidasPasta{comum.parte_de_macro(pasta)}', len(medidas), f'medidas DAX na pasta "{pasta}"')

    r = ler_resultado(RESULTADO_PBI_COMPLETO)
    N.add('NumMedidasCompletas', len(r) if r is not None else PENDENTE,
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
    metodo_de = {papel: m for m, papel in comum.macros_dos_metodos().items()}
    N.add('NumMetodos', met.metodo.nunique(), 'métodos de previsão testados contra o passado', 'scripts/modelo.py')
    N.add('NumHorizontes', int(met.horizonte.max()), 'anos à frente da Previsão da receita e do Teste contra o passado', 'scripts/modelo.py')
    N.add('NumJanelaEscolhido', janelas[metodo_de['Escolhido']], 'anos da tendência do método escolhido', 'scripts/modelo.py')
    N.add('NumJanelaReta', janelas[metodo_de['Reta']], 'anos da reta do método concorrente', 'scripts/modelo.py')


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


def main():
    N = calcular()
    relatorio_gerados.escrever()
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
