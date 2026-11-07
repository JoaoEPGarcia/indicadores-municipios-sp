"""Confere a planilha contra o SQLite, lendo os valores que o Excel calculou e guardou no arquivo.

    python scripts/conferir_excel.py                                  # as planilhas de excel/calculadas/
    python scripts/conferir_excel.py --arquivo A.xlsx B.xlsx ...      # outras (por exemplo, a versão refeita à mão)

Não abre o Excel. Cada arquivo é uma cópia da planilha já calculada pelo Excel (no Excel para a web: escolha o
município em Painel!C4 e baixe uma cópia). O script lê, sem recalcular, o município escolhido em Painel!C4 e o que
as fórmulas devolveram: na aba Painel, último ano, valor, mediana, diferença e posição dos sete Indicadores
(D13:H19); na aba Previsão, a receita observada e os cinco valores previstos de cada ano (B8:H21). Cada célula é
comparada com o valor calculado do SQLite (dados/tratados/amostra.sqlite), com tolerância de 1e-9.

Um arquivo que o Excel nunca calculou (o que scripts/montar_excel.py grava, antes de abrir no Excel) não tem
valores guardados: o script para e diz isso.

Por padrão, a conferência cobre os três municípios de powerbi/conferencia.md e o município de exemplo, um por
arquivo; o script diz quais deles faltam entre os arquivos dados. Só quando todos os arquivos são a planilha de
referência (marcada pelo nome definido OrigemDaPlanilha, que o construtor grava) e os quatro municípios estão
presentes, o resultado vai para excel/resultado_conferencia_excel.json, lido por scripts/numeros.py. Conferir
outra planilha nunca muda esse arquivo.

Sai com código 1 se alguma célula divergir e 2 se um arquivo não puder ser conferido.
"""
import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scripts'))
import comum  # noqa: E402
import layout_planilha as L  # noqa: E402

CALCULADAS = comum.EXCEL / 'calculadas'
SAIDA = comum.EXCEL / 'resultado_conferencia_excel.json'
SQLITE = comum.TRATADOS / 'amostra.sqlite'
ERROS = {'#N/A', '#N/D'}   # como o arquivo guarda o NÃO.DISP() (o Excel grava em inglês)


class NaoConfere(Exception):
    """O arquivo não pode ser conferido (sem valores calculados, aba ou município faltando)."""


def esperado_painel(con, cod, ind):
    r = con.execute('SELECT MAX(ano) FROM fato_indicador WHERE cod_ibge = ? AND indicador_id = ?', (cod, ind)).fetchone()
    ano = r[0]
    if ano is None:
        return dict.fromkeys(L.COLUNAS_TABELA, 'n.d.')
    v, med, pos = con.execute(
        'SELECT f.valor, r.mediana, p.posicao_na_faixa / 100.0 FROM fato_indicador f '
        'JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge '
        'JOIN ref_faixa r ON r.faixa_porte = d.faixa_porte AND r.ano = f.ano AND r.indicador_id = f.indicador_id '
        'JOIN v_posicao p ON p.cod_ibge = f.cod_ibge AND p.ano = f.ano AND p.indicador_id = f.indicador_id '
        'WHERE f.cod_ibge = ? AND f.ano = ? AND f.indicador_id = ?', (cod, ano, ind)).fetchone()
    return dict(ano=ano, valor=v, mediana=med, diferenca=v / med - 1, posicao=pos)


def igual(esperado, obtido):
    if isinstance(esperado, str) or esperado is None:
        return obtido == esperado or (esperado is None and obtido in ERROS)
    if isinstance(obtido, bool) or not isinstance(obtido, (int, float)):
        return False
    return math.isclose(esperado, obtido, rel_tol=1e-9, abs_tol=1e-9)


def e_referencia(wb):
    nome = wb.defined_names.get(L.NOME_ORIGEM)
    if nome is not None and L.ORIGEM in (nome.attr_text or ''):
        return True
    return any(p.name == 'Origem' and p.value == L.ORIGEM for p in getattr(wb, 'custom_doc_props', []))


def conferir_arquivo(caminho, con):
    """Devolve (município, células conferidas, divergências, é a planilha de referência)."""
    try:
        wb = openpyxl.load_workbook(caminho, data_only=True)
    except Exception as e:      # arquivo que não é .xlsx, corrompido, inexistente
        raise NaoConfere(f'{caminho}: não abre como planilha ({e})')
    try:
        for aba in (L.PAINEL, L.PREVISAO):
            if aba not in wb.sheetnames:
                raise NaoConfere(f'{caminho}: falta a aba "{aba}"')
        painel, prev = wb[L.PAINEL], wb[L.PREVISAO]
        nome, codigo = painel[L.MUNICIPIO].value, painel[L.CODIGO].value
        tabela = [{campo: painel[L.celula_tabela(campo, k)].value for campo in L.COLUNAS_TABELA}
                  for k in range(len(comum.INDICADORES_PAINEL))]
        if codigo in (None, '', 0) or all(v is None for linha in tabela for v in linha.values()):
            raise NaoConfere(f'{caminho}: sem valores calculados. O arquivo nunca foi calculado pelo Excel: abra-o no Excel '
                             '(para a web), espere as fórmulas calcularem e baixe uma cópia (Arquivo → Salvar como → Baixar uma Cópia).')
        cod = con.execute('SELECT cod_ibge FROM dim_municipio WHERE municipio = ?', (nome,)).fetchone()
        if cod is None:
            raise NaoConfere(f'{caminho}: município escolhido em {L.PAINEL}!{L.MUNICIPIO} não encontrado: {nome!r}')
        cod = cod[0]
        celulas, divergencias = 0, []
        if codigo != cod:
            divergencias.append(f'{nome} | Painel | {L.CODIGO} (código IBGE): esperado {cod}, obtido {codigo}')
        for ind, obtido in zip(comum.INDICADORES_PAINEL, tabela):
            e = esperado_painel(con, cod, ind)
            for campo in e:
                celulas += 1
                if not igual(e[campo], obtido[campo]):
                    divergencias.append(f'{nome} | Painel | {ind} | {campo}: esperado {e[campo]}, obtido {obtido[campo]}')
        previstas = ', '.join(L.COLUNAS_PREVISTAS)
        linha = L.LINHA_PREVISAO
        while prev[f'{L.COLUNA_ANO}{linha}'].value not in (None, ''):
            ano = int(prev[f'{L.COLUNA_ANO}{linha}'].value)
            obs = con.execute("SELECT valor FROM fato_indicador WHERE cod_ibge = ? AND ano = ? AND indicador_id = 'receita_total'",
                              (cod, ano)).fetchone()
            p = con.execute(f'SELECT {previstas} FROM previsao_receita_total WHERE cod_ibge = ? AND ano = ?', (cod, ano)).fetchone()
            pares = [('observada', L.COLUNA_OBSERVADA, obs[0] if obs else None)]
            pares += [(c, col, v) for (c, col), v in zip(L.COLUNAS_PREVISTAS.items(), p)] if p else []
            for campo, col, e in pares:
                celulas += 1
                o = prev[f'{col}{linha}'].value
                if not igual(e, o):
                    divergencias.append(f'{nome} | Previsão | {ano} | {campo}: esperado {e}, obtido {o}')
            linha += 1
        if linha == L.LINHA_PREVISAO:
            raise NaoConfere(f'{caminho}: a aba Previsão não tem anos em {L.COLUNA_ANO}{L.LINHA_PREVISAO} (sem valores calculados?)')
        return nome, celulas, divergencias, e_referencia(wb)
    finally:
        wb.close()


def municipios_padrao(con):
    cod_ex, _ = comum.municipio_de_exemplo()
    lista = sorted({c['municipio'] for c in comum.ler_conferencia()})
    lista.append(con.execute('SELECT municipio FROM dim_municipio WHERE cod_ibge = ?', (cod_ex,)).fetchone()[0])
    return lista


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--arquivo', nargs='+', type=Path,
                    help='planilhas calculadas pelo Excel, uma por município (padrão: excel/calculadas/*.xlsx)')
    # Os testes (tests/test_conferir_excel.py) gravam o resultado numa pasta temporária, para não mexer no versionado.
    ap.add_argument('--resultado', type=Path, default=SAIDA,
                    help='onde gravar o resultado da planilha de referência (padrão: excel/resultado_conferencia_excel.json)')
    args = ap.parse_args()
    arquivos = args.arquivo or sorted(CALCULADAS.glob('*.xlsx'))
    if not arquivos:
        print(f'[ERRO] Nenhuma planilha para conferir em {CALCULADAS.relative_to(RAIZ).as_posix()}/. Baixe do Excel para a web '
              'uma cópia calculada por município, ou aponte os arquivos com --arquivo.')
        sys.exit(2)
    con = sqlite3.connect(SQLITE)

    celulas, divergencias, conferidos, referencia = 0, [], [], True
    try:
        for arq in arquivos:
            nome, n, div, ref = conferir_arquivo(arq, con)
            celulas += n
            divergencias += div
            conferidos.append(nome)
            referencia &= ref
            print(f'  {nome}: {n - len(div)} de {n} células ({arq.name}{"" if ref else ", não é a planilha de referência"})')
    except NaoConfere as e:
        print('[ERRO]', e)
        sys.exit(2)

    for d in divergencias:
        print('  [ERRO]', d)
    batem = celulas - len(divergencias)
    unicos = sorted(set(conferidos))
    print(f'{batem} de {celulas} células iguais ao SQLite, em {len(unicos)} municípios.')
    faltam = [m for m in municipios_padrao(con) if m not in unicos]
    if faltam:
        print(f'  [aviso] faltam municípios da conferência: {", ".join(faltam)} (um arquivo calculado por município).')
    if not referencia:
        print('  Algum arquivo não é a planilha de referência: o resultado da conferência não foi gravado.')
    elif faltam:
        print('  Conferência incompleta: o resultado não foi gravado.')
    else:
        args.resultado.write_text(json.dumps(dict(celulas=celulas, batem=batem, municipios=len(unicos), lista=unicos,
                                                  arquivos=[a.name for a in arquivos]),
                                             ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('gravado', args.resultado)
    sys.exit(0 if not divergencias else 1)


if __name__ == '__main__':
    main()
