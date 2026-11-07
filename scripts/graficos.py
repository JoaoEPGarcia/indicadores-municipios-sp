"""Figuras do projeto, no kit de estilo do portfólio (estilo/estilo_portfolio.py).

    python scripts/graficos.py

Quatro figuras sobre o município de exemplo (sorteado com semente fixa, ver comum.municipio_de_exemplo):
  01-painel-municipio.png    o exemplo contra a mediana e os quartis da faixa, em quatro Indicadores
  02-municipio-na-faixa.png  a diferença para a mediana nos sete Indicadores, sobre a distribuição da faixa
  03-previsao.png            a Previsão da receita com os dois Intervalos de previsão
  04-teste-do-modelo.png     o Teste contra o passado: erro dos métodos e cobertura do intervalo

Regras do kit: o título afirma o achado e todo número dele vem de scripts/numeros.py; o Município
selecionado sai no vermelho de destaque e o contexto em neutro; a distribuição sai em azul; rótulo direto
em vez de legenda; fonte no rodapé. Os números usados em cada figura ficam em graficos/numeros_usados.json,
que scripts/numeros.py lê para preencher a coluna "Onde aparece" de NUMEROS_CANONICOS.md.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'estilo'))
sys.path.insert(0, str(RAIZ / 'scripts'))

from estilo_portfolio import (COR_BARRA, DESTAQUE, GRAY_10, GRAY_20, GRAY_60, GRAY_70, GRAY_90, NEUTRO,  # noqa: E402
                              PESO_TITULO, TAM_NOTA, TAM_SUBTITULO, TAM_TITULO, cor_de_texto, eixo_ano, eixo_no_zero,
                              fonte, misturar, rotular_ponta, set_sus_style, titulo)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MultipleLocator  # noqa: E402

import comum  # noqa: E402
import numeros  # noqa: E402

SAIDA = RAIZ / 'graficos'
TRATADOS = RAIZ / 'dados' / 'tratados'
FONTE_FINANCAS = ('Fonte: Siconfi/Tesouro Nacional (DCA, anexos I-C e I-E) e IBGE (população e IPCA). '
                  'Municípios parecidos: mesma faixa de população do Censo 2022.')
USADOS = {}


def usar(figura, N, *nomes):
    """Devolve os valores dos números e registra que a figura os imprime."""
    USADOS.setdefault(figura, [])
    for n in nomes:
        if n not in USADOS[figura]:
            USADOS[figura].append(n)
    vals = [N[n]['valor'] for n in nomes]
    return vals[0] if len(vals) == 1 else vals


def br(casas):
    return FuncFormatter(lambda v, _: numeros.fmt(v, casas))


def pct(v, _=None):
    return numeros.fmt(v, 0) + '%'


def separar(a, b, dist):
    """Afasta dois rótulos de ponta que ficariam um sobre o outro, mantendo o centro entre eles."""
    if abs(a - b) >= dist:
        return a, b
    meio, sinal = (a + b) / 2, (1 if a >= b else -1)
    return meio + sinal * dist / 2, meio - sinal * dist / 2


def titulo_figura(fig, texto, subtitulo):
    """Título e subtítulo da figura inteira, quando há mais de um painel (o kit faz o mesmo por eixo)."""
    fig.text(0.0, 1.0, texto, ha='left', va='bottom', fontsize=TAM_TITULO, fontweight=PESO_TITULO, color=GRAY_90)
    fig.text(0.0, 0.985, subtitulo, ha='left', va='top', fontsize=TAM_SUBTITULO, color=GRAY_70)


def fonte_figura(fig, texto, y=-0.02):
    fig.text(0.0, y, texto, ha='left', va='top', fontsize=TAM_NOTA, color=GRAY_60)


def salvar(fig, nome):
    SAIDA.mkdir(exist_ok=True)
    fig.savefig(SAIDA / nome)
    plt.close(fig)
    print('gravado graficos/' + nome)


def ler():
    return {k: pd.read_csv(TRATADOS / f) for k, f in [
        ('mun', 'dim_municipio.csv'), ('ind', 'dim_indicador.csv'), ('fato', 'indicadores_longo.csv'),
        ('ref', 'referencia_faixa.csv'), ('prev', 'previsao_receita_total.csv'), ('met', 'backtest_metodos.csv'),
        ('cob', 'backtest_cobertura.csv')]}


# ── Figura 1 ────────────────────────────────────────────────────────────
def figura_painel(d, N, cod):
    fig_nome = '01-painel-municipio.png'
    ex, faixa_txt, n_faixa = usar(fig_nome, N, 'NumExemplo', 'NumExemploFaixa', 'NumExemploNaFaixa')
    verbo, dif, sentido, objeto = usar(fig_nome, N, 'NumFigUmVerbo', 'NumFigUmDif', 'NumFigUmSentido', 'NumFigUmObjeto')
    a0, a1 = usar(fig_nome, N, 'NumAnoInicial', 'NumAnoFinal')
    faixa = d['mun'].set_index('cod_ibge').faixa_porte[cod]
    nomes = d['ind'].set_index('indicador_id')

    fig, eixos = plt.subplots(2, 2, figsize=(12, 7.4), sharex=True)
    for ax, i in zip(eixos.flat, numeros.INDICADORES_FIGURA_1):
        r = d['ref'][(d['ref'].faixa_porte == faixa) & (d['ref'].indicador_id == i)].sort_values('ano')
        s = d['fato'][(d['fato'].cod_ibge == cod) & (d['fato'].indicador_id == i)].sort_values('ano')
        ax.fill_between(r.ano, r.p25, r.p75, color=GRAY_10, linewidth=0, zorder=1)
        ax.plot(r.ano, r.mediana, color=NEUTRO, linewidth=1.6, zorder=2)
        ax.plot(s.ano, s.valor, color=DESTAQUE, linewidth=2.4, marker='o', markersize=4.5,
                markeredgecolor='white', markeredgewidth=0.8, zorder=4)
        casas = int(nomes.casas[i])
        lo, hi = min(r.p25.min(), s.valor.min()), max(r.p75.max(), s.valor.max())
        y_mun, y_med = separar(s.valor.iloc[-1], r.mediana.iloc[-1], 0.16 * (hi - lo))
        rotular_ponta(ax, s.ano.iloc[-1], y_mun, f'{ex}\n{numeros.fmt(s.valor.iloc[-1], casas)}', cor=DESTAQUE)
        rotular_ponta(ax, r.ano.iloc[-1], y_med, 'mediana', cor=GRAY_60, negrito=False)
        ax.set_title(nomes.nome[i], loc='left', fontweight='normal', color=GRAY_90, pad=16)
        ax.annotate(nomes.unidade[i], xy=(0, 1), xycoords='axes fraction', xytext=(0, 3), textcoords='offset points',
                    ha='left', va='bottom', fontsize=TAM_NOTA, color=GRAY_60)
        ax.yaxis.set_major_formatter(br(casas))
        eixo_ano(ax)
        ax.set_xlim(int(a0) - 0.3, int(a1) + 0.3)
        ax.set_ylim(lo - 0.12 * (hi - lo), hi + 0.12 * (hi - lo))
    fig.tight_layout(rect=(0, 0, 0.93, 0.90), h_pad=2.6, w_pad=5)
    titulo_figura(fig, f'{ex} {verbo} {dif}% {sentido} {objeto} que a mediana dos {n_faixa} municípios {faixa_txt} habitantes',
                  f'Valor do município (vermelho), mediana dos municípios parecidos (linha cinza) e faixa do 1º ao 3º quartil '
                  f'(sombra), {a0} a {a1}. Os eixos não começam no zero.')
    fonte_figura(fig, FONTE_FINANCAS + '\nReais de 2025 (IPCA). Os valores por habitante têm um degrau entre 2021 e 2022 '
                      '(troca da base de população para o Censo 2022).')
    salvar(fig, fig_nome)


# ── Figura 2 ────────────────────────────────────────────────────────────
def figura_faixa(d, N, cod):
    fig_nome = '02-municipio-na-faixa.png'
    ex, faixa_txt, n_faixa = usar(fig_nome, N, 'NumExemplo', 'NumExemploFaixa', 'NumExemploNaFaixa')
    acima, total = usar(fig_nome, N, 'NumFigDoisAcima', 'NumIndicadoresComparaveis')
    faixa = d['mun'].set_index('cod_ibge').faixa_porte[cod]
    nomes = d['ind'].set_index('indicador_id')
    membros = set(d['mun'][d['mun'].faixa_porte == faixa].cod_ibge)

    linhas = []
    for i in comum.INDICADORES_PAINEL:
        s = d['fato'][(d['fato'].cod_ibge == cod) & (d['fato'].indicador_id == i)]
        ano = int(s.ano.max())
        med = float(d['ref'][(d['ref'].faixa_porte == faixa) & (d['ref'].ano == ano) & (d['ref'].indicador_id == i)].mediana.iloc[0])
        grupo = d['fato'][(d['fato'].indicador_id == i) & (d['fato'].ano == ano) & d['fato'].cod_ibge.isin(membros)]
        rel = (grupo.valor / med - 1) * 100
        v = (float(s[s.ano == ano].valor.iloc[0]) / med - 1) * 100
        linhas.append((f'{nomes.nome[i]} ({ano})', rel.to_numpy(), v))
    linhas = linhas[::-1]           # o primeiro Indicador fica em cima

    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.boxplot([l[1] for l in linhas], orientation='horizontal', widths=0.5, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor=misturar(COR_BARRA, 0.70), edgecolor=COR_BARRA, linewidth=1),
               medianprops=dict(color=COR_BARRA, linewidth=1.6), whiskerprops=dict(color=COR_BARRA, linewidth=1),
               capprops=dict(color=COR_BARRA, linewidth=1))
    for k, (_, _, v) in enumerate(linhas, start=1):
        ax.scatter([v], [k], s=70, color=DESTAQUE, edgecolor='white', linewidth=1, zorder=5)
        ax.annotate(('+' if v > 0 else '−') + numeros.fmt(abs(v), 1) + '%', (v, k), xytext=(0, 13),
                    textcoords='offset points', ha='center', va='bottom', fontsize=TAM_NOTA, color=cor_de_texto(DESTAQUE),
                    bbox=dict(boxstyle='square,pad=0.1', facecolor='white', edgecolor='none'), zorder=6)
    ax.axvline(0, color=GRAY_60, linewidth=1, zorder=1)
    ax.set_yticks(range(1, len(linhas) + 1), [l[0] for l in linhas])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: ('+' if v > 0 else '−' if v < 0 else '') + pct(abs(v))))
    ax.set_xlabel('diferença para a mediana da faixa')
    ax.grid(axis='x', color=GRAY_20, linewidth=0.7, linestyle=(0, (4, 4)))
    ax.grid(axis='y', visible=False)
    titulo(ax, f'{ex} fica acima da mediana dos municípios parecidos em {acima} de {total} indicadores',
           f'Em vermelho, {ex}. A caixa vai do 1º ao 3º quartil dos {n_faixa} municípios {faixa_txt} habitantes; '
           'último ano com dado de cada indicador.')
    fonte(ax, 'Fonte: Siconfi/Tesouro Nacional, IBGE, INEP (Ideb) e DataSUS (SINASC). As hastes vão até 1,5 vez o comprimento '
              'da caixa; pontos além delas ficam fora do quadro.')
    salvar(fig, fig_nome)


# ── Figura 3 ────────────────────────────────────────────────────────────
def figura_previsao(d, N, cod):
    fig_nome = '03-previsao.png'
    ex, prev, lo9, hi9 = usar(fig_nome, N, 'NumExemplo', 'NumExemploPrevista', 'NumExemploInfNoventaCinco', 'NumExemploSupNoventaCinco')
    af, a0 = usar(fig_nome, N, 'NumAnoPrevFinal', 'NumAnoInicial')
    s = d['fato'][(d['fato'].cod_ibge == cod) & (d['fato'].indicador_id == 'receita_total')].sort_values('ano')
    p = d['prev'][d['prev'].cod_ibge == cod].sort_values('ano')
    ancora_ano, ancora_v = int(s.ano.iloc[-1]), float(s.valor.iloc[-1])
    anos = [ancora_ano] + list(p.ano)

    def com_ancora(col):
        return [ancora_v] + list(p[col])

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.fill_between(anos, com_ancora('inferior_95'), com_ancora('superior_95'), color=misturar(DESTAQUE, 0.90), linewidth=0, zorder=1)
    ax.fill_between(anos, com_ancora('inferior_80'), com_ancora('superior_80'), color=misturar(DESTAQUE, 0.78), linewidth=0, zorder=2)
    ax.plot(anos, com_ancora('previsto'), color=DESTAQUE, linewidth=2.2, linestyle=(0, (5, 3)), zorder=3)
    ax.plot(s.ano, s.valor, color=DESTAQUE, linewidth=2.6, marker='o', markersize=5, markeredgecolor='white',
            markeredgewidth=0.8, zorder=4)
    x = p.ano.iloc[-1]
    rotular_ponta(ax, x, p.previsto.iloc[-1], f'previsto: {prev}', cor=DESTAQUE)
    rotular_ponta(ax, x, (p.superior_80.iloc[-1] + p.superior_95.iloc[-1]) / 2, 'intervalo de 95%', cor=GRAY_60, negrito=False)
    rotular_ponta(ax, x, (p.superior_80.iloc[-1] + p.previsto.iloc[-1]) / 2, 'intervalo de 80%', cor=GRAY_60, negrito=False)
    ax.axvline(ancora_ano + 0.5, color=GRAY_60, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)
    ax.annotate('previsão', xy=(ancora_ano + 0.5, 1), xycoords=('data', 'axes fraction'), xytext=(5, -2),
                textcoords='offset points', ha='left', va='top', fontsize=TAM_NOTA, color=GRAY_70)
    ax.yaxis.set_major_formatter(br(0))
    ax.set_ylabel('R$ milhões de 2025')
    eixo_ano(ax)
    ax.set_xlim(int(a0) - 0.3, int(af) + 0.3)
    # "R\$": dois cifrões no mesmo texto abririam o modo matemático do matplotlib
    titulo(ax, f'A receita de {ex} deve chegar a R\\$ {prev} milhões em {af},\nentre R\\$ {lo9} e R\\$ {hi9} milhões no intervalo de 95%',
           f'Receita corrente total, observada até {ancora_ano} e prevista pela tendência dos 3 últimos anos. '
           'O eixo não começa no zero.')
    fonte(ax, 'Fonte: Siconfi/Tesouro Nacional (DCA, anexo I-C) e IBGE (IPCA). Intervalos tirados dos erros do método ao prever o passado.')
    salvar(fig, fig_nome)


# ── Figura 4 ────────────────────────────────────────────────────────────
def figura_teste(d, N):
    fig_nome = '04-teste-do-modelo.png'
    e3, i3 = usar(fig_nome, N, 'NumErroEscolhidoTres', 'NumErroIngenuoTres')
    pior, origem, media = usar(fig_nome, N, 'NumCobOitentaPior', 'NumCobOitentaPiorOrigem', 'NumCobOitentaCom')
    o0, o1 = usar(fig_nome, N, 'NumOrigemInicial', 'NumOrigemFinal')
    nomes = {'ingenuo': 'Repetir o último valor', 'tendencia3': 'Tendência dos 3 últimos anos', 'tendencia5': 'Reta dos 5 últimos anos'}

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
    finais = {}
    for m, g in d['met'].groupby('metodo'):
        g = g.sort_values('horizonte')
        escolhido = int(g.escolhido.iloc[0]) == 1
        cor = DESTAQUE if escolhido else NEUTRO
        a1.plot(g.horizonte, g.erro_medio_abs_pct, color=cor, linewidth=2.6 if escolhido else 1.6, marker='o',
                markersize=5, markeredgecolor='white', zorder=4 if escolhido else 2)
        finais[m] = (float(g.erro_medio_abs_pct.iloc[-1]), cor, escolhido)
    # os dois rótulos mais baixos (reta e tendência) ficam perto: afastá-los para não se tocarem
    ordem = sorted(finais, key=lambda m: finais[m][0])
    ys = {m: finais[m][0] for m in ordem}
    ys[ordem[0]], ys[ordem[1]] = separar(ys[ordem[0]], ys[ordem[1]], 1.2)
    for m in ordem:
        v, cor, escolhido = finais[m]
        rotular_ponta(a1, 3, ys[m], f'{nomes[m]}: {numeros.fmt(v, 1)}%', cor=cor, negrito=escolhido)
    a1.set_xticks([1, 2, 3], ['1 ano', '2 anos', '3 anos'])
    a1.set_xlim(0.8, 3.1)
    a1.yaxis.set_major_locator(MultipleLocator(5))
    a1.yaxis.set_major_formatter(FuncFormatter(pct))
    eixo_no_zero(a1)
    a1.set_title('Erro médio absoluto, por horizonte', loc='left', fontweight='normal', color=GRAY_90)

    cob = d['cob'][d['cob'].nivel == 80]
    por_origem = {int(o): numeros.ponderada(g, 'cobertura_com_ajuste') for o, g in cob.groupby('origem_fora')}
    cores = [DESTAQUE if o == int(origem) else NEUTRO for o in por_origem]
    a2.bar([str(o) for o in por_origem], list(por_origem.values()), color=cores, width=0.6)
    for x, (v, c) in enumerate(zip(por_origem.values(), cores)):
        a2.annotate(pct(v), (x, v), xytext=(0, 4), textcoords='offset points', ha='center',
                    va='bottom', fontsize=TAM_NOTA, color=cor_de_texto(c))
    a2.axhline(80, color=GRAY_70, linewidth=1, linestyle=(0, (4, 3)))
    a2.annotate('80% prometidos', xy=(1, 80), xycoords=('axes fraction', 'data'), xytext=(0, 4),
                textcoords='offset points', ha='right', va='bottom', fontsize=TAM_NOTA, color=GRAY_70)
    a2.yaxis.set_major_formatter(FuncFormatter(pct))
    eixo_no_zero(a2, topo=100)
    a2.set_title('Cobertura do intervalo de 80%, por origem deixada de fora', loc='left', fontweight='normal', color=GRAY_90)

    fig.tight_layout(rect=(0, 0, 0.97, 0.88), w_pad=14)
    titulo_figura(fig, f'A tendência dos 3 últimos anos erra {e3}% a três anos, contra {i3}% de repetir o último valor',
                  f'Previsões feitas a partir de {o0} a {o1} e comparadas ao que veio depois. Na média, o intervalo de 80% '
                  f'cobriu {media}%;\ncom {origem} deixado de fora, cobriu {pior}%.')
    fonte_figura(fig, 'Fonte: Siconfi/Tesouro Nacional (DCA, anexo I-C), receita corrente total dos municípios de SP. '
                      'Cobertura ponderada pelo número de previsões testadas.')
    salvar(fig, fig_nome)


def main():
    set_sus_style()
    N = numeros.calcular()
    cod, _ = comum.municipio_de_exemplo()
    d = ler()
    figura_painel(d, N, cod)
    figura_faixa(d, N, cod)
    figura_previsao(d, N, cod)
    figura_teste(d, N)
    (SAIDA / 'numeros_usados.json').write_text(json.dumps(USADOS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('gravado graficos/numeros_usados.json')


if __name__ == '__main__':
    main()
