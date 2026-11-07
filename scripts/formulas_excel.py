"""A gramática das fórmulas da planilha: como o arquivo .xlsx as guarda e como o Excel em português as mostra.

O arquivo guarda as fórmulas em inglês (XLOOKUP, LET, SEQUENCE), com prefixos que o Excel não mostra (_xlfn. nas
funções novas, _xlpm. nos nomes do LET): `fx` os põe, para scripts/montar_excel.py gravar. O Excel em português
mostra PROCX, LET e SEQUÊNCIA, com ponto e vírgula entre os argumentos: `em_portugues` faz essa tradução, para o
relatório (scripts/numeros.py) mostrar a fórmula como o leitor a vê. As duas leem a fórmula pelo mesmo
fatiador, que separa o texto entre aspas (com aspas dobradas dentro) e os nomes de coluna entre colchetes.
"""
import re

import openpyxl

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


# Funções da planilha como o Excel em português as mostra.
FUNCOES_PT = {'XLOOKUP': 'PROCX', 'IF': 'SE', 'AND': 'E', 'ISNUMBER': 'ÉNÚM', 'SUMPRODUCT': 'SOMARPRODUTO',
              'MAXIFS': 'MÁXIMOSES', 'NA': 'NÃO.DISP', 'SEQUENCE': 'SEQUÊNCIA', 'MATCH': 'CORRESP', 'LET': 'LET'}


def em_portugues(f):
    """A fórmula como o Excel em português a mostra: PROCX no lugar de XLOOKUP, ponto e vírgula entre os
    argumentos, sem os prefixos _xlfn. e _xlpm. do arquivo. Texto entre aspas e nome de coluna não mudam."""
    f = f.replace('_xlfn.', '').replace('_xlpm.', '')
    saida = []
    for tipo, t in _fatiar(f):
        if tipo == 'codigo':
            t = re.sub(r'(?<![\w.])[A-Z][A-Z.]*(?=\()', lambda m: FUNCOES_PT.get(m.group(0), m.group(0)), t)
            t = t.replace(',', ';')
        saida.append(t)
    return ''.join(saida)


def ler_formula(arquivo, aba, celula):
    """A fórmula de uma célula de um .xlsx, como o arquivo a guarda."""
    wb = openpyxl.load_workbook(arquivo)
    try:
        v = wb[aba][celula].value
    finally:
        wb.close()
    return getattr(v, 'text', v)      # fórmula de matriz dinâmica: openpyxl devolve um objeto
