"""Confere a planilha excel/painel-municipios-sp.xlsx contra o SQLite, com o próprio Excel calculando.

    python scripts/conferir_excel.py                 # os três municípios de powerbi/conferencia.md e o de exemplo
    python scripts/conferir_excel.py "Santos" ...    # outros municípios
    python scripts/conferir_excel.py --arquivo excel/minha-versao.xlsx   # a versão que você refez à mão

Para cada município, o script escreve o nome na célula de escolha da aba Painel (C4), manda o Excel recalcular
e lê o que as fórmulas devolvem: na aba Painel, último ano, valor, mediana, diferença e posição dos sete
Indicadores; na aba Previsão, a receita observada e os cinco valores previstos de cada ano. Cada célula é
comparada com o valor calculado do SQLite (dados/tratados/amostra.sqlite), com tolerância de 1e-9.
O arquivo é aberto só para leitura e não é salvo.

Saída: excel/resultado_conferencia_excel.json (lido por scripts/numeros.py). Sai com código 1 se algo divergir.
"""
import json
import math
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))
import comum  # noqa: E402
from conferir_powerbi import ler_conferencia  # noqa: E402

PLANILHA = RAIZ / 'excel' / 'painel-municipios-sp.xlsx'
SAIDA = RAIZ / 'excel' / 'resultado_conferencia_excel.json'
SQLITE = RAIZ / 'dados' / 'tratados' / 'amostra.sqlite'
LINHA_TABELA = 13          # primeira linha da tabela de Indicadores na aba Painel
LINHA_PREVISAO = 8         # primeira linha da tabela da aba Previsão


def esperado_painel(con, cod, ind):
    r = con.execute('SELECT MAX(ano) FROM fato_indicador WHERE cod_ibge = ? AND indicador_id = ?', (cod, ind)).fetchone()
    ano = r[0]
    if ano is None:
        return dict(ano='n.d.', valor='n.d.', mediana='n.d.', diferenca='n.d.', posicao='n.d.')
    v, med, pos = con.execute(
        'SELECT f.valor, r.mediana, p.posicao_na_faixa / 100.0 FROM fato_indicador f '
        'JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge '
        'JOIN ref_faixa r ON r.faixa_porte = d.faixa_porte AND r.ano = f.ano AND r.indicador_id = f.indicador_id '
        'JOIN v_posicao p ON p.cod_ibge = f.cod_ibge AND p.ano = f.ano AND p.indicador_id = f.indicador_id '
        'WHERE f.cod_ibge = ? AND f.ano = ? AND f.indicador_id = ?', (cod, ano, ind)).fetchone()
    return dict(ano=ano, valor=v, mediana=med, diferenca=v / med - 1, posicao=pos)


def igual(esperado, obtido):
    if isinstance(esperado, str) or esperado is None:
        return obtido == esperado or (esperado is None and obtido in (None, -2146826246))   # -2146826246 = #N/D
    if not isinstance(obtido, (int, float)):
        return False
    return math.isclose(esperado, obtido, rel_tol=1e-9, abs_tol=1e-9)


def main():
    import win32com.client as win32

    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('municipios', nargs='*', help='nomes de municípios (padrão: os da conferência e o de exemplo)')
    ap.add_argument('--arquivo', default=str(PLANILHA), help='planilha a conferir (padrão: excel/painel-municipios-sp.xlsx)')
    args = ap.parse_args()
    arquivo = Path(args.arquivo).resolve()
    padrao = arquivo == PLANILHA.resolve()
    if args.municipios:
        municipios = args.municipios
    else:
        cod_ex, _ = comum.municipio_de_exemplo()
        municipios = sorted({c['municipio'] for c in ler_conferencia()})
        con0 = sqlite3.connect(SQLITE)
        municipios.append(con0.execute('SELECT municipio FROM dim_municipio WHERE cod_ibge = ?', (cod_ex,)).fetchone()[0])
    con = sqlite3.connect(SQLITE)

    xl = win32.DispatchEx('Excel.Application')
    xl.Visible = False
    xl.DisplayAlerts = False
    celulas, divergencias = 0, []
    try:
        wb = xl.Workbooks.Open(str(arquivo), ReadOnly=True)
        painel, prev = wb.Worksheets('Painel'), wb.Worksheets('Previsão')
        for nome in municipios:
            cod = con.execute('SELECT cod_ibge FROM dim_municipio WHERE municipio = ?', (nome,)).fetchone()
            if cod is None:
                sys.exit(f'município não encontrado: {nome}')
            cod = cod[0]
            painel.Range('C4').Value = nome
            xl.CalculateFull()
            for k, ind in enumerate(comum.INDICADORES_PAINEL):
                r = LINHA_TABELA + k
                e = esperado_painel(con, cod, ind)
                obtido = dict(ano=painel.Range(f'D{r}').Value, valor=painel.Range(f'E{r}').Value,
                              mediana=painel.Range(f'F{r}').Value, diferenca=painel.Range(f'G{r}').Value,
                              posicao=painel.Range(f'H{r}').Value)
                for campo in e:
                    celulas += 1
                    if not igual(e[campo], obtido[campo]):
                        divergencias.append(f'{nome} | Painel | {ind} | {campo}: esperado {e[campo]}, obtido {obtido[campo]}')
            # aba Previsão
            linha = LINHA_PREVISAO
            while prev.Range(f'B{linha}').Value not in (None, ''):
                ano = int(prev.Range(f'B{linha}').Value)
                obs = con.execute("SELECT valor FROM fato_indicador WHERE cod_ibge = ? AND ano = ? AND indicador_id = 'receita_total'",
                                  (cod, ano)).fetchone()
                p = con.execute('SELECT previsto, inferior_80, superior_80, inferior_95, superior_95 FROM previsao_receita_total '
                                'WHERE cod_ibge = ? AND ano = ?', (cod, ano)).fetchone()
                pares = [('observada', 'C', obs[0] if obs else None)]
                if p:
                    pares += [(c, col, v) for (c, col), v in zip([('prevista', 'D'), ('inf80', 'E'), ('sup80', 'F'),
                                                                   ('inf95', 'G'), ('sup95', 'H')], p)]
                for campo, col, e in pares:
                    celulas += 1
                    o = prev.Range(f'{col}{linha}').Value
                    if not igual(e, o):
                        divergencias.append(f'{nome} | Previsão | {ano} | {campo}: esperado {e}, obtido {o}')
                linha += 1
            print(f'  {nome}: conferido')
        wb.Close(False)
    finally:
        xl.Quit()

    for d in divergencias:
        print('  [ERRO]', d)
    batem = celulas - len(divergencias)
    print(f'{batem} de {celulas} células iguais ao SQLite, em {len(municipios)} municípios.')
    if padrao:      # só a planilha do repositório alimenta os números do README
        SAIDA.write_text(json.dumps(dict(celulas=celulas, batem=batem, municipios=len(municipios), lista=municipios),
                                    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('gravado', SAIDA.relative_to(RAIZ))
    sys.exit(0 if not divergencias else 1)


if __name__ == '__main__':
    main()
