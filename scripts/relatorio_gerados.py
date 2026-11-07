"""Os arquivos que o relatório em LaTeX lê de relatorio/gerados/, todos com a primeira linha "% GERADO".

Escritos por scripts/numeros.py, depois do registro: linhas de tabela (lidas com \\linhasde) e trechos de
código (lidos com \\input). As linhas de tabela usam as macros \\Num... em vez do valor, para que a coluna
"Onde aparece" de NUMEROS_CANONICOS.md as encontre. Os trechos de código saem do modelo em TMDL (as medidas
DAX) e da planilha gerada (as fórmulas, como o Excel em português as mostra).
"""
import re

import comum
import layout_planilha as L
import tmdl
from formulas_excel import em_portugues, ler_formula

GERADOS = comum.RAIZ / 'relatorio' / 'gerados'
PLANILHA = comum.EXCEL / L.ARQUIVO
CABECALHO_GERADO = '% GERADO por scripts/numeros.py. Não edite à mão: rode o script de novo.'


def _tt(nome):
    return r'\texttt{' + nome.replace('_', r'\_') + '}'


def _codigo(destino, codigo):
    destino.write_text('\n'.join([CABECALHO_GERADO, r'\begin{verbatim}', codigo, r'\end{verbatim}']) + '\n',
                       encoding='utf-8')


def _linhas(destino, linhas):
    destino.write_text('\n'.join([CABECALHO_GERADO] + [l + r' \\' for l in linhas]) + '\n', encoding='utf-8')


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


def formula_da_planilha(campo):
    """A fórmula do campo na primeira linha da tabela do Painel, como o Excel em português a mostra."""
    return em_portugues(ler_formula(PLANILHA, L.PAINEL, L.celula_tabela(campo)))


def tabela_do_modelo(modelo):
    liga = {}
    for f, d in modelo.relacoes:
        liga.setdefault(f, []).append(d)
        liga.setdefault(d, []).append(f)
    papeis = {t: p for t, p, _, _, _ in tmdl.TABELAS_MODELO}
    if set(liga) != set(papeis) or any((papeis[f], papeis[d]) != ('fato', 'dimensão') for f, d in modelo.relacoes):
        raise ValueError('as relações do TMDL não batem com tmdl.TABELAS_MODELO: atualize a lista')
    return [f'{_tt(t)} & {p} & {g} & \\{macro} & ' + ', '.join(_tt(x) for x in sorted(liga[t]))
            for t, p, g, _, macro in tmdl.TABELAS_MODELO]


def tabela_dos_metodos(modelo):
    """Uma linha por método, na ordem de backtest_metodos.csv; o escolhido em negrito. O nome vem do TMDL, com o
    número de anos trocado pela macro da janela do método."""
    nomes, macros = modelo.nomes_dos_metodos(), comum.macros_dos_metodos()
    metodos = list(dict.fromkeys(r['metodo'] for r in comum.ler_csv('backtest_metodos.csv')))
    ultimo = comum.MACRO_HORIZONTE[max(comum.MACRO_HORIZONTE)]
    linhas = []
    for metodo in metodos:
        papel = macros[metodo]
        escolhido = papel == 'Escolhido'
        rotulo = re.sub(r'\d+', lambda _: f'\\NumJanela{papel}{{}}', nomes[metodo]) + (' (escolhido)' if escolhido else '')
        celulas = ([rotulo] + [f'\\NumErro{papel}{h}\\%' for h in comum.MACRO_HORIZONTE.values()]
                   + [f'\\NumVies{papel}{ultimo}\\%'])
        linhas.append(' & '.join(f'\\textbf{{{c}}}' if escolhido else c for c in celulas))
    return linhas


def tabela_da_cobertura():
    niveis = sorted({int(r['nivel']) for r in comum.ler_csv('backtest_cobertura.csv')})
    linhas = []
    for nivel, ordem in zip(niveis, comum.ORDEM_NIVEL):
        nn = comum.MACRO_NIVEL[nivel]
        linhas.append(f'\\NumNivel{ordem}\\% & \\NumCob{nn}Sem\\% & \\NumEscala{nn} & \\NumCob{nn}Com\\% & '
                      f'\\NumCob{nn}Pior\\% (origem \\NumCob{nn}PiorOrigem)')
    return linhas


def escrever():
    GERADOS.mkdir(parents=True, exist_ok=True)
    modelo = tmdl.ler()
    _linhas(GERADOS / 'tabelas_modelo.tex', tabela_do_modelo(modelo))

    _linhas(GERADOS / 'pastas_medidas.tex', [
        f'{pasta} & \\NumMedidasPasta{comum.parte_de_macro(pasta)} & ' + '; '.join(medidas[:3])
        + ('; \\ldots' if len(medidas) > 3 else '')
        for pasta, medidas in modelo.pastas().items()])

    _linhas(GERADOS / 'conferencias.tex', [
        r'Indicadores: SQL e pandas & cada valor refeito em pandas, sem olhar o SQL & \NumValoresValidados & \NumValoresValidadosIguais',
        r'Medidas DAX e tabela de conferência & valores esperados de \NumMunicipiosConferencia{} municípios sorteados & \NumCelulasConferencia & \NumCelulasBatem',
        r'Medidas DAX e SQLite & \NumMedidasCompletas{} medidas em cada linha da fato & \NumCelulasCompletas & \NumDivergenciasCompletas{} divergências',
        r'Planilha e SQLite & abas Painel e Previsão calculadas no Excel para a web, \NumMunicipiosExcel{} municípios & \NumCelulasExcel & \NumCelulasExcelBatem',
    ])

    _linhas(GERADOS / 'teste_metodos.tex', tabela_dos_metodos(modelo))
    _linhas(GERADOS / 'cobertura.tex', tabela_da_cobertura())

    _codigo(GERADOS / 'dax_mediana.tex', modelo.medida('Mediana da faixa').dax())
    _codigo(GERADOS / 'dax_posicao.tex', modelo.medida('Posição na faixa').dax())
    _codigo(GERADOS / 'excel_procx.tex', quebrar_formula(formula_da_planilha('valor')))
    _codigo(GERADOS / 'excel_let.tex', quebrar_formula(formula_da_planilha('ano')))
