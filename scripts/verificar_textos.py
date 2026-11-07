"""Verificador dos textos entregues: diz se o README, o relatório e o PDF estão prontos para mostrar.

    python scripts/verificar_textos.py

Roda na raiz do repositório. Sai com código 0 quando tudo passa e 1 quando algo falha; cada falha
aponta o arquivo, a linha e o trecho. Quando o modelo do README, o relatório ou o PDF ainda não
existem, a verificação correspondente é pulada e o comando diz isso.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

MODELO_README = 'docs/README.modelo.md'
RELATORIO_TEX = 'relatorio/relatorio.tex'
RELATORIO_PDF = 'relatorio/relatorio.pdf'
REGISTRO = 'relatorio/numeros.tex'      # a saída do registro de números (scripts/numeros.py)
USADOS = ['graficos/numeros_usados.json', 'excel/numeros_usados.json']  # números impressos em figura e planilha
PENDENTE = 'PENDENTE'


class Verificacao:
    """Junta o resultado de cada conferência, no formato de scripts/validar.py."""

    def __init__(self):
        self.linhas, self.falhas = [], 0

    def ok(self, nome):
        self.linhas.append(f'[OK] {nome}')

    def pulada(self, nome, motivo):
        self.linhas.append(f'[PULADA] {nome}: {motivo}')

    def falha(self, nome, problemas):
        self.falhas += len(problemas)
        self.linhas.append(f'[FALHA] {nome}')
        self.linhas += [f'    {p}' for p in problemas]


# ── número digitado ─────────────────────────────────────────────────────
def apagar(texto, padrao, flags=0):
    """Troca cada trecho que casa com o padrão por espaços do mesmo tamanho, mantendo as quebras de
    linha: assim a posição de cada caractere que sobra, e a linha dele, não mudam."""
    return re.sub(padrao, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), texto, flags=flags)


def linha_de(texto, pos):
    return texto.count('\n', 0, pos) + 1


# As exceções à regra do número digitado (GUIA_ESTILO.md, "A regra dos números"). Lista única e curta:
# cada entrada é um número que faz parte de um NOME, e não um resultado do estudo. Antes de pôr uma
# entrada aqui, veja se o número não deveria sair de scripts/numeros.py.
EXCECOES = [
    # ano no nome de uma fonte: o "Censo 2022" é a pesquisa, e não um recorte escolhido pelo estudo
    r'\bCenso(?: Demográfico| Escolar)? \d{4}\b',
    # número de ato normativo: "Portaria STN nº 642/2019", "Lei 12.527/2011"
    r'\b(?:Lei|Portaria|Decreto|Resolução)\b[^\d\n]{0,20}[\d./]+',
    # nome de arquivo: "01-painel-municipio.png", "backtest_2015.csv"
    r'[\w.-]*\d[\w.-]*\.(?:csv|png|pdf|tex|md|py|json|sqlite|xlsx|tmdl|pbip|sql)\b',
    # data da capa do relatório: metadado do documento, e não número do estudo
    r'\\newcommand\{\\DataCapa\}\{[^}]*\}',
]

# O que, no Markdown, não é texto corrido: o leitor não vê ali um número do estudo.
SINTAXE_MARKDOWN = [
    (r'<!--.*?-->', re.S),               # comentário (scripts/numeros.py o tira do README)
    (r'^\s*```.*?^\s*```', re.S | re.M),  # bloco de código: comandos
    (r'`[^`\n]*`', 0),                    # código na linha: comando, caminho, nome de coluna
    (r'https?://[^\s)>]+', 0),            # endereço
    (r'\]\([^)\n]*\)', 0),                # destino de link e de imagem
    (r'^\s*\d+[.)](?=\s)', re.M),         # marca de lista numerada
]

# O que, no LaTeX, não é texto corrido. O modelo do kit tem medidas, coordenadas e cores que não são
# números do estudo; o preâmbulo do kit nem se edita (GUIA_ESTILO.md), então nem se lê.
COMANDOS_TECNICOS = ('label|ref|eqref|pageref|autoref|cite|input|include|includegraphics|imagemplena|'
                     'linhasde|graphicspath|url|setcounter|addtocounter|cmidrule|fontsize|vspace|hspace|rule|'
                     'color|rowcolor|cellcolor')
COMANDOS_PRIMEIRO_ARG = 'multicolumn|multirow|scalebox|subfig|href|textcolor|colorbox'
DIMENSOES = 'textwidth|linewidth|figwidth|columnwidth|paperwidth|textheight|baselineskip'
SINTAXE_LATEX = [
    (r'^% PREÂMBULO DO KIT.*?^% FIM DO PREÂMBULO DO KIT[^\n]*', re.S | re.M),  # o bloco do kit
    (r'(?<!\\)%[^\n]*', 0),                                                  # comentário
    (r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', re.S),                # desenho: coordenadas
    # rótulo, arquivo, medida: todos os argumentos do comando
    (r'\\(?:' + COMANDOS_TECNICOS + r')\*?(?:\s*\[[^\]]*\]|\s*\([^)]*\)|\s*\{[^{}]*\})+', 0),
    # colunas, escala, arquivo, endereço, cor: só o primeiro argumento (o resto é texto)
    (r'\\(?:' + COMANDOS_PRIMEIRO_ARG + r')\*?(?:\s*\[[^\]]*\])?\s*\{[^{}]*\}', 0),
    (r'[-+]?\d*\.?\d+(?:pt|cm|mm|em|ex|in|bp|pc|sp)\b', 0),                  # medida: 0.5cm, 1.5pt
    (r'[-+]?\d*\.?\d+\s*\\(?:' + DIMENSOES + r')\b', 0),                     # medida: 0.94\textwidth
    (r'https?://[^\s}]+', 0),                                                # endereço
]

MARCADOR = r'\{\{[^}]*\}\}'      # {{NumX}} no modelo do README
MACRO = r'\\Num[A-Za-z]+'        # \NumX no LaTeX


def numeros_digitados(texto, sintaxe, marcador):
    """(linha, número, trecho) de cada número que sobra fora de marcador, de sintaxe e das exceções."""
    limpo = texto
    for padrao, flags in sintaxe:
        limpo = apagar(limpo, padrao, flags)
    limpo = apagar(limpo, marcador)
    for padrao in EXCECOES:
        limpo = apagar(limpo, padrao)
    linhas = texto.splitlines()
    achados = []
    for m in re.finditer(r'\d+(?:[.,]\d+)*', limpo):
        n = linha_de(limpo, m.start())
        achados.append((n, m.group(0), linhas[n - 1].strip()))
    return achados


def conferir_digitados(v, raiz, caminho):
    texto = (raiz / caminho).read_text(encoding='utf-8')
    if caminho.endswith('.tex'):
        achados, uso = numeros_digitados(texto, SINTAXE_LATEX, MACRO), r'uma macro \Num...'
    else:
        achados, uso = numeros_digitados(texto, SINTAXE_MARKDOWN, MARCADOR), 'um marcador {{Num...}}'
    nome = f'nenhum número digitado em {caminho}'
    if achados:
        v.falha(nome, [f'{caminho}:{n}: número digitado "{num}" (use {uso}): {trecho}'
                       for n, num, trecho in achados])
    else:
        v.ok(nome)


# ── marcadores, macros e PENDENTE ───────────────────────────────────────
def ler_registro(raiz):
    """{nome: valor} da saída do registro de números (relatorio/numeros.tex), ou None se ela não existe."""
    arq = raiz / REGISTRO
    if not arq.exists():
        return None
    texto = arq.read_text(encoding='utf-8')
    return dict(re.findall(r'^\\newcommand\{\\(Num[A-Za-z]+)\}\{(.*)\}\s*$', texto, flags=re.M))


def usos_no_modelo(raiz):
    """(onde, nome) de cada marcador {{...}} do modelo do README, fora de comentário."""
    texto = apagar((raiz / MODELO_README).read_text(encoding='utf-8'), r'<!--.*?-->', re.S)
    return [(f'{MODELO_README}:{linha_de(texto, m.start())}', m.group(1).strip())
            for m in re.finditer(r'\{\{([^}]*)\}\}', texto)]


def usos_no_latex(raiz, caminho):
    r"""(onde, nome) de cada macro \Num... de um .tex do relatório, fora de comentário."""
    texto = apagar((raiz / caminho).read_text(encoding='utf-8'), r'(?<!\\)%[^\n]*')
    return [(f'{caminho}:{linha_de(texto, m.start())}', m.group(0)[1:]) for m in re.finditer(MACRO, texto)]


def textos_latex(raiz):
    """Os .tex do relatório escritos à mão. Os gerados por script (primeira linha "% GERADO", como
    relatorio/numeros.tex e as linhas de tabela) têm números por construção e ficam de fora."""
    pasta = raiz / 'relatorio'
    if not pasta.exists():
        return []
    return [p.relative_to(raiz).as_posix() for p in sorted(pasta.rglob('*.tex'))
            if not p.read_text(encoding='utf-8').startswith('% GERADO')]


def usos_nas_figuras(raiz):
    """(onde, nome) de cada número que figuras e planilha registram como impresso."""
    usos = []
    for arq in USADOS:
        if (raiz / arq).exists():
            for alvo, nomes in json.loads((raiz / arq).read_text(encoding='utf-8')).items():
                usos += [(f'{arq} ({alvo})', nome) for nome in nomes]
    return usos


def conferir_registro(v, raiz, usos):
    nome = 'todo número usado existe no registro e não está PENDENTE'
    if not usos:
        v.pulada(nome, 'nenhum texto usa número do registro ainda')
        return
    registro = ler_registro(raiz)
    if registro is None:
        v.falha(nome, [f'{REGISTRO} não existe: rode python scripts/numeros.py'])
        return
    problemas = []
    for onde, num in usos:
        if num not in registro:
            problemas.append(f'{onde}: {num} não existe no registro ({REGISTRO})')
        elif registro[num] == PENDENTE:
            problemas.append(f'{onde}: {num} está {PENDENTE}')
    if problemas:
        v.falha(nome, problemas)
    else:
        v.ok(nome)


# ── a verificação ───────────────────────────────────────────────────────
def verificar(raiz):
    v = Verificacao()
    usos = usos_nas_figuras(raiz)
    if (raiz / MODELO_README).exists():
        conferir_digitados(v, raiz, MODELO_README)
        usos += usos_no_modelo(raiz)
    else:
        v.pulada('modelo do README', f'{MODELO_README} ainda não existe')
    for caminho in textos_latex(raiz):
        conferir_digitados(v, raiz, caminho)
        usos += usos_no_latex(raiz, caminho)
    conferir_registro(v, raiz, usos)
    if not (raiz / RELATORIO_TEX).exists():
        v.pulada('compilação do relatório', f'{RELATORIO_TEX} ainda não existe')
    if not (raiz / RELATORIO_PDF).exists():
        v.pulada('texto do PDF', f'{RELATORIO_PDF} ainda não existe')
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--raiz', type=Path, default=RAIZ, help='raiz do repositório (padrão: a deste script)')
    raiz = ap.parse_args().raiz.resolve()
    v = verificar(raiz)
    print('\n'.join(v.linhas))
    if v.falhas:
        print(f'\n{v.falhas} problema(s). Os textos não estão prontos.')
        sys.exit(1)
    print('\nTudo certo.')


if __name__ == '__main__':
    main()
