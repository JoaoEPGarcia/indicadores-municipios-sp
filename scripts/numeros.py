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

TRATADOS = RAIZ / 'dados' / 'tratados'
TMDL = RAIZ / 'powerbi' / 'painel-municipios-sp.SemanticModel' / 'definition'
PENDENTE = 'PENDENTE'

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
        if not re.fullmatch(r'Num[A-Za-z]+', nome):
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
    return N


# ── saídas ──────────────────────────────────────────────────────────────
def onde_aparece(N):
    """Procura cada número nos textos e no registro das figuras."""
    fontes = {}
    for caminho in [RAIZ / 'docs' / 'README.modelo.md', *sorted((RAIZ / 'relatorio').glob('**/*.tex'))]:
        if caminho.exists() and caminho.name != 'numeros.tex':
            fontes[caminho.relative_to(RAIZ).as_posix()] = caminho.read_text(encoding='utf-8')
    registros = {}      # figuras e planilha: cada gerador grava os números que imprime
    for pasta in ('graficos', 'excel'):
        arq = RAIZ / pasta / 'numeros_usados.json'
        if arq.exists():
            for alvo, nomes in json.loads(arq.read_text(encoding='utf-8')).items():
                registros[f'{pasta}/{alvo}'] = nomes
    onde = {}
    for nome in N:
        lugares = [f for f, t in fontes.items() if re.search(r'\{\{' + nome + r'\}\}|\\' + nome + r'(?![A-Za-z])', t)]
        lugares += [alvo for alvo, nomes in registros.items() if nome in nomes]
        onde[nome] = lugares
    return onde


def escrever_tex(N):
    linhas = ['% GERADO por scripts/numeros.py. Não edite à mão: rode o script de novo.',
              '% Registro de cada número em NUMEROS_CANONICOS.md.']
    for k, v in N.items():
        valor = v['valor'].replace('%', r'\%').replace('−', '$-$')
        linhas.append(f'\\newcommand{{\\{k}}}{{{valor}}}')
    destino = RAIZ / 'relatorio' / 'numeros.tex'
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
    modelo = RAIZ / 'docs' / 'README.modelo.md'
    if not modelo.exists():
        return
    texto = modelo.read_text(encoding='utf-8')
    texto = re.sub(r'<!--.*?-->\n?', '', texto, flags=re.S)
    faltam = sorted(set(re.findall(r'\{\{(Num[A-Za-z]+)\}\}', texto)) - set(N))
    if faltam:
        sys.exit(f'README.modelo.md usa números que não existem: {faltam}')
    texto = re.sub(r'\{\{(Num[A-Za-z]+)\}\}', lambda mm: N[mm.group(1)]['valor'], texto)
    (RAIZ / 'README.md').write_text(texto, encoding='utf-8')


def main():
    N = calcular()
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
