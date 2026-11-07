"""Partes comuns dos scripts: caminhos, o registro de números, o município de exemplo, a leitura da tabela
de conferência do Power BI e a cobertura do Teste contra o passado. As cores vêm do kit, em estilo/."""
import csv
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRATADOS = RAIZ / 'dados' / 'tratados'
GRAFICOS = RAIZ / 'graficos'
EXCEL = RAIZ / 'excel'
CONFERENCIA = RAIZ / 'powerbi' / 'conferencia.md'

# O registro de números e os textos que o usam: scripts/numeros.py escreve, scripts/verificar_textos.py
# confere. Caminhos relativos à raiz do repositório.
MODELO_README = 'docs/README.modelo.md'
REGISTRO_TEX = 'relatorio/numeros.tex'     # cada número como macro LaTeX
NUMEROS_USADOS = ('graficos/numeros_usados.json', 'excel/numeros_usados.json')  # impressos em figura e planilha
PENDENTE = 'PENDENTE'                      # valor de um número que depende de um passo ainda não feito
NOME_NUMERO = r'Num[A-Za-z]+'              # vira nome de macro LaTeX, que só aceita letras
MARCADOR = re.compile(r'\{\{(' + NOME_NUMERO + r')\}\}')     # {{NumX}} no modelo do README, exato
MACRO = re.compile(r'\\(' + NOME_NUMERO + r')(?![A-Za-z])')  # \NumX no LaTeX
DEFINICAO = re.compile(r'^\\newcommand\{\\(' + NOME_NUMERO + r')\}\{(.*)\}\s*$', re.M)  # linha de REGISTRO_TEX

# Partes de nome de macro do Teste contra o passado, as mesmas no registro e nas tabelas geradas do relatório.
# O método que os dados marcam como escolhido (coluna escolhido de backtest_metodos.csv) é sempre "Escolhido";
# os outros têm a parte fixa daqui.
MACRO_METODO = {'ingenuo': 'Ingenuo', 'tendencia5': 'Reta'}
MACRO_HORIZONTE = {1: 'Um', 2: 'Dois', 3: 'Tres'}
MACRO_NIVEL = {80: 'Oitenta', 95: 'NoventaCinco'}
ORDEM_NIVEL = ('Menor', 'Maior')        # NumNivelMenor, NumNivelMaior: o intervalo mais estreito e o mais largo


def parte_de_macro(texto):
    """'Comparação na faixa' → 'ComparacaoNaFaixa': parte de nome de macro (só letras)."""
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return ''.join(p[:1].upper() + p[1:] for p in re.findall(r'[A-Za-z]+', sem_acento))


def macros_dos_metodos():
    """{método: parte do nome da macro}, com o escolhido primeiro e os outros na ordem de MACRO_METODO."""
    escolhido = {r['metodo'] for r in ler_csv('backtest_metodos.csv') if int(r['escolhido']) == 1}
    if len(escolhido) != 1:
        raise ValueError(f'backtest_metodos.csv devia marcar um método escolhido, e marca {sorted(escolhido)}')
    escolhido = escolhido.pop()
    return {escolhido: 'Escolhido', **{m: nome for m, nome in MACRO_METODO.items() if m != escolhido}}

# Sorteio do município de exemplo: semente fixa (a data da sessão), entre os que têm série completa.
SEMENTE = 20261014
INDICADORES_PAINEL = ['receita_pc', 'dependencia_transf', 'saude_pc', 'educacao_pc', 'pib_pc', 'ideb', 'pre_natal_7mais']
# Os quatro do resumo: os cartões da página Município do painel e a Figura 1.
INDICADORES_RESUMO = ['receita_pc', 'saude_pc', 'educacao_pc', 'dependencia_transf']
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
         'Outubro', 'Novembro', 'Dezembro']
ANOS = list(range(2015, 2026))


def ler_csv(arquivo):
    with open(TRATADOS / arquivo, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def municipio_de_exemplo():
    """Sorteia, com semente fixa, um município com receita, saúde, educação, dependência, pré-natal e
    PIB de 2015 a 2022 e Ideb nos cinco anos: um exemplo sem escolha nossa do que ele mostra."""
    dados = {}
    for r in ler_csv('indicadores_longo.csv'):
        dados.setdefault(int(r['cod_ibge']), {}).setdefault(r['indicador_id'], set()).add(int(r['ano']))
    exigencias = {'receita_pc': set(ANOS), 'dependencia_transf': set(ANOS), 'saude_pc': set(ANOS),
                  'educacao_pc': set(ANOS), 'pre_natal_7mais': set(range(2015, 2025)),
                  'ideb': {2015, 2017, 2019, 2021, 2023}, 'pib_pc': set(range(2015, 2024))}
    candidatos = sorted(c for c, d in dados.items()
                        if all(ind in d and anos <= d[ind] for ind, anos in exigencias.items()))
    return random.Random(SEMENTE).choice(candidatos), len(candidatos)


def cobertura_por_origem(nivel):
    """{origem deixada de fora: cobertura com ajuste, em %} do Intervalo de previsão do nível dado, no Teste
    contra o passado: a média das coberturas dos grupos, ponderada pelo número de casos de cada um."""
    soma, peso = defaultdict(float), defaultdict(int)
    for r in ler_csv('backtest_cobertura.csv'):
        if int(r['nivel']) == nivel:
            soma[int(r['origem_fora'])] += float(r['cobertura_com_ajuste']) * int(r['n_teste'])
            peso[int(r['origem_fora'])] += int(r['n_teste'])
    return {o: soma[o] / peso[o] for o in soma}


# ── tabela de conferência do Power BI (powerbi/conferencia.md) ───────────
# Colunas da tabela de cada município em conferencia.md → medida DAX
COLUNAS_INDICADOR = {
    '`[Valor]` 2023': 'Valor',
    '`[Mediana da faixa]`': 'Mediana da faixa',
    '`[1º quartil da faixa]`': '1º quartil da faixa',
    '`[3º quartil da faixa]`': '3º quartil da faixa',
    '`[Diferença para a mediana]`': 'Diferença para a mediana',
    '`[Posição na faixa]`': 'Posição na faixa',
    'Municípios na faixa com dado': 'Municípios com dado na faixa',
}
COLUNAS_PREVISAO = {
    '`[Receita prevista]`': 'Receita prevista',
    '`[Limite inferior 80%]`': 'Limite inferior 80%',
    '`[Limite superior 80%]`': 'Limite superior 80%',
}


def numero_br(texto):
    """'−22,42%' → (-0.2242, 4 casas); '5176,4883' → (5176.4883, 4); '123' → (123.0, 0)."""
    t = texto.strip().replace('−', '-').replace('.', '')
    pct = t.endswith('%')
    t = t.rstrip('%').replace(',', '.')
    casas = len(t.split('.')[1]) if '.' in t else 0
    v = float(t)
    if pct:
        return v / 100, casas + 2
    return v, casas


def linhas_tabela(bloco):
    return [[c.strip() for c in l.strip().strip('|').split('|')] for l in bloco if l.strip().startswith('|')]


def ler_conferencia():
    """Devolve a lista de células: dict(municipio, indicador, ano, medida, esperado, casas)."""
    texto = CONFERENCIA.read_text(encoding='utf-8')
    ano_ref = int(re.search(r'\[Valor\]` (\d{4})', texto).group(1))
    celulas = []
    for secao in re.split(r'^## ', texto, flags=re.M)[1:]:
        municipio = secao.splitlines()[0].strip()
        tabelas = re.split(r'\n\s*\n', secao)
        for t in tabelas:
            linhas = linhas_tabela(t.splitlines())
            if len(linhas) < 3:
                continue
            cab, corpo = linhas[0], linhas[2:]
            if cab[0] == 'Indicador':
                for l in corpo:
                    for col, valor in zip(cab[1:], l[1:]):
                        if col in COLUNAS_INDICADOR:
                            v, casas = numero_br(valor)
                            celulas.append(dict(municipio=municipio, indicador=l[0], ano=ano_ref,
                                                medida=COLUNAS_INDICADOR[col], esperado=v, casas=casas))
            elif cab[0] == 'Ano':
                for l in corpo:
                    for col, valor in zip(cab[1:], l[1:]):
                        if col in COLUNAS_PREVISAO:
                            v, casas = numero_br(valor)
                            celulas.append(dict(municipio=municipio, indicador='receita_total', ano=int(l[0]),
                                                medida=COLUNAS_PREVISAO[col], esperado=v, casas=casas))
    return celulas


# ── conexão com o Analysis Services do Power BI Desktop ──────────────────
