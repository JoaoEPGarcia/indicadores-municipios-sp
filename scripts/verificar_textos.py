"""Verificador dos textos entregues: diz se o README, o relatório e o PDF estão prontos para mostrar.

    python scripts/verificar_textos.py

Roda na raiz do repositório (rode antes scripts/numeros.py, que escreve relatorio/numeros.tex). Sai com
código 0 quando tudo passa e 1 quando algo falha; cada falha aponta o arquivo, a linha e o trecho.

Falha quando:
  - um número usado (marcador {{NumX}} do modelo do README, macro \\NumX do LaTeX, número registrado
    pelas figuras e pela planilha em numeros_usados.json) está PENDENTE ou não existe no registro;
  - há número digitado, fora de marcador ou macro, em docs/README.modelo.md ou num .tex de relatorio/
    (exceções na lista EXCECOES, abaixo; o preâmbulo do kit e os .tex gerados não se leem);
  - algum texto versionado (.md, .tex, .txt), o README ou o PDF diz que o painel foi publicado na web;
  - o README montado ou o PDF mostram PENDENTE ou um marcador que sobrou;
  - relatorio/relatorio.tex não compila em pdfLaTeX, nas duas passadas, sem erro. Compilado, o PDF
    vai para relatorio/relatorio.pdf.

Quando o modelo do README, o relatório ou o PDF ainda não existem, a verificação correspondente é
pulada e o comando diz isso. Os testes ficam em tests/ (python -m unittest discover -s tests).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

MODELO_README = 'docs/README.modelo.md'
README = 'README.md'                    # montado por scripts/numeros.py a partir do modelo
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
    # versão no nome de uma licença: "CC BY 4.0", "CC BY-ND 3.0" (seção de Fontes e licenças)
    r'\bCC BY(?:-[A-Z]{2})*\s+\d\.\d\b',
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


# ── "publicado na web" ──────────────────────────────────────────────────
# O painel abre no Power BI Desktop e não foi publicado (spec, Out of Scope). Nenhum texto diz o contrário.
PUBLICACAO = re.compile('|'.join([
    r'publicad[oa]s?\s+(?:na|em)\s+(?:web|internet)',
    r'publicad[oa]s?\s+no\s+(?:Power\s+BI\s+)?Service',
    r'publish(?:ed)?\s+to\s+(?:the\s+)?web',
    r'published\s+(?:on|to)\s+(?:the\s+)?(?:internet|Power\s+BI\s+Service)',
    r'app\.powerbi\.com/view',              # link de "Publicar na Web"
]), re.I)
# Frase que nega ("o painel não foi publicado na web") não afirma a publicação. A negação só conta
# quando rege a afirmação: na mesma oração e a poucas palavras antes dela ("nada diz que o painel foi
# publicado", "nem publicado"). Um "não" de outra oração ("Não é difícil: o painel foi publicado")
# ou de outra linha da lista não vale.
NEGACAO = re.compile(r'\b(?:não|nunca|nada|nem|jamais|not|never|nothing)\b', re.I)
FIM_DE_ORACAO = re.compile(r'[.;:!?,()—]|\n\s*\n|\n\s*(?:[-*+>#|]|\d+[.)])')
ALCANCE_DA_NEGACAO = 6  # palavras antes da afirmação
EXTENSOES_DE_TEXTO = ('.md', '.tex', '.txt')


def negada(texto, inicio):
    """A afirmação que começa em inicio vem negada na própria oração?"""
    antes = texto[max(0, inicio - 300):inicio]
    fins = list(FIM_DE_ORACAO.finditer(antes))
    oracao = antes[fins[-1].end():] if fins else antes
    return bool(NEGACAO.search(' '.join(oracao.split()[-ALCANCE_DA_NEGACAO:])))


def frases_de_publicacao(texto):
    """(linha, trecho) de cada frase que afirma que o painel foi publicado na web."""
    achados = []
    linhas = texto.splitlines()
    for m in PUBLICACAO.finditer(texto):
        if negada(texto, m.start()):
            continue
        n = linha_de(texto, m.start())
        achados.append((n, linhas[n - 1].strip()))
    return achados


def textos_versionados(raiz):
    """Os arquivos de texto do repositório (git ls-files). Fora de um repositório git, todos os que não
    estão em pasta oculta (.git, .venv, .scratch)."""
    r = subprocess.run(['git', 'ls-files', '-z'], cwd=raiz, capture_output=True)
    if r.returncode == 0:
        caminhos = [c for c in r.stdout.decode('utf-8').split('\0') if c]
    else:
        caminhos = [p.relative_to(raiz).as_posix() for p in raiz.rglob('*')
                    if p.is_file() and not any(parte.startswith('.') for parte in p.relative_to(raiz).parts)]
    return sorted(c for c in caminhos if c.endswith(EXTENSOES_DE_TEXTO) and (raiz / c).exists())


def conferir_publicacao(v, raiz, caminhos):
    nome = 'nenhum texto diz que o painel foi publicado na web'
    problemas = []
    for caminho in caminhos:
        texto = (raiz / caminho).read_text(encoding='utf-8', errors='replace')
        problemas += [f'{caminho}:{n}: {trecho}' for n, trecho in frases_de_publicacao(texto)]
    if problemas:
        v.falha(nome, problemas)
    else:
        v.ok(f'{nome} ({len(caminhos)} arquivos)')


# ── compilação do relatório ─────────────────────────────────────────────
def erros_do_log(log):
    """Cada erro do pdfLaTeX ("! ...") com a linha do fonte ("l.12 ...") que vem logo depois."""
    erros = []
    linhas = log.splitlines()
    for i, linha in enumerate(linhas):
        # "!  ==> Fatal error" e "! Emergency stop" só repetem que o erro anterior parou a compilação
        if linha.startswith('! ') and not linha.startswith(('!  ==>', '! Emergency stop')):
            onde = next((m.group(1) for m in (re.match(r'l\.(\d+)', x) for x in linhas[i + 1:i + 15]) if m), '?')
            erros.append((onde, linha))
    return erros


def conferir_compilacao(v, raiz, limite):
    """Compila relatorio/relatorio.tex em duas passadas, como o kit manda. Os arquivos auxiliares ficam
    numa pasta temporária; o PDF vai para relatorio/relatorio.pdf. limite: segundos por passada."""
    nome = f'{RELATORIO_TEX} compila em pdfLaTeX, duas passadas, sem erro'
    pasta = (raiz / RELATORIO_TEX).parent
    with tempfile.TemporaryDirectory() as saida:
        for passada in (1, 2):
            try:
                r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error',
                                    f'-output-directory={saida}', Path(RELATORIO_TEX).name],
                                   cwd=pasta, capture_output=True, timeout=limite)
            except FileNotFoundError:
                v.falha(nome, ['pdflatex não está no PATH: instale o MiKTeX (ou o TeX Live) e abra outro terminal'])
                return
            except subprocess.TimeoutExpired:
                v.falha(nome, [f'pdflatex passou de {limite:g} s na passada {passada} e foi interrompido '
                               '(laço de macro? Rode pdflatex à mão para ver onde para)'])
                return
            log = Path(saida, 'relatorio.log')
            log = log.read_text(encoding='utf-8', errors='replace') if log.exists() else r.stdout.decode(errors='replace')
            erros = erros_do_log(log)
            if r.returncode != 0 or erros:
                erros = erros or [('?', f'pdflatex saiu com código {r.returncode}')]
                v.falha(nome, [f'{RELATORIO_TEX}:{onde}: {erro} (passada {passada})' for onde, erro in erros])
                return
        shutil.copyfile(Path(saida, 'relatorio.pdf'), raiz / RELATORIO_PDF)
    v.ok(nome)


# ── o texto que o leitor vê: PDF e README montado ───────────────────────
def conferir_texto_final(v, caminho, paginas, publicacao):
    """paginas: [(onde, texto)]. Falha se o leitor veria PENDENTE ou um marcador que sobrou e, com
    publicacao=True, a frase de publicação na web. O README é texto versionado, e a conferência da
    publicação já o lê; o PDF não, e só aqui se procura a frase nele."""
    nome = f'{caminho} não mostra {PENDENTE}, marcador sobrando' + (' nem publicação na web' if publicacao else '')
    problemas = []
    for onde, texto in paginas:
        linhas = texto.splitlines()
        for m in re.finditer(PENDENTE + '|' + MARCADOR, texto):
            problemas.append(f'{onde}: "{m.group(0)}" em: {linhas[linha_de(texto, m.start()) - 1].strip()}')
        if publicacao:
            problemas += [f'{onde}: publicação na web em: {trecho}' for _, trecho in frases_de_publicacao(texto)]
    if problemas:
        v.falha(nome, problemas)
    else:
        v.ok(nome)


def conferir_pdf(v, raiz):
    """Lê o texto de cada página do PDF e confere o que o leitor veria."""
    try:
        import pymupdf  # só aqui: sem PDF, o verificador roda sem a biblioteca
    except ImportError:
        v.falha(f'{RELATORIO_PDF} legível', ['pymupdf não está instalado: pip install -r requirements.txt'])
        return
    try:
        with pymupdf.open(raiz / RELATORIO_PDF) as doc:
            paginas = [(f'{RELATORIO_PDF}, página {i}', p.get_text()) for i, p in enumerate(doc, start=1)]
    except Exception as e:  # PDF corrompido ou truncado: o pymupdf tem vários tipos de erro
        v.falha(f'{RELATORIO_PDF} legível', [f'o pymupdf não abriu o PDF: {e}'])
        return
    conferir_texto_final(v, RELATORIO_PDF, paginas, publicacao=True)


# ── a verificação ───────────────────────────────────────────────────────
def verificar(raiz, limite_pdflatex=600):
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
    # os versionados e, mesmo antes do primeiro commit, os textos entregues
    entregues = [c for c in (MODELO_README, README) if (raiz / c).exists()] + textos_latex(raiz)
    conferir_publicacao(v, raiz, sorted(set(textos_versionados(raiz)) | set(entregues)))
    if (raiz / README).exists():
        linhas = (raiz / README).read_text(encoding='utf-8').splitlines()
        conferir_texto_final(v, README, [(f'{README}:{i}', t) for i, t in enumerate(linhas, start=1)],
                             publicacao=False)
    if (raiz / RELATORIO_TEX).exists():
        conferir_compilacao(v, raiz, limite_pdflatex)
    else:
        v.pulada('compilação do relatório', f'{RELATORIO_TEX} ainda não existe')
    if (raiz / RELATORIO_PDF).exists():
        conferir_pdf(v, raiz)
    else:
        v.pulada('texto do PDF', f'{RELATORIO_PDF} ainda não existe')
    return v


def main():
    # UTF-8 em qualquer saída: no console do Windows (cp1252) e em pipe, os acentos e o texto do PDF
    # saem legíveis, e um caractere fora da página de código não derruba o comando.
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--raiz', type=Path, default=RAIZ, help='raiz do repositório (padrão: a deste script)')
    ap.add_argument('--limite-pdflatex', type=float, default=600, metavar='SEGUNDOS',
                    help='tempo máximo de cada passada do pdfLaTeX (padrão: 600)')
    args = ap.parse_args()
    v = verificar(args.raiz.resolve(), args.limite_pdflatex)
    print('\n'.join(v.linhas))
    if v.falhas:
        print(f'\n{v.falhas} problema(s). Os textos não estão prontos.')
        sys.exit(1)
    print('\nTudo certo.')


if __name__ == '__main__':
    main()
