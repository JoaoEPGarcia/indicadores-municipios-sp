"""Verificador dos textos entregues: diz se o README, o relatório e o PDF estão prontos para mostrar.

    python scripts/verificar_textos.py [--limite-pdflatex SEGUNDOS]

Roda na raiz do repositório, que tem de ser um repositório git (rode antes scripts/numeros.py, que
escreve relatorio/numeros.tex). Sai com código 0 quando tudo passa e 1 quando algo falha; cada falha
aponta o arquivo, a linha e o trecho.

Falha quando:
  - um número usado (marcador {{NumX}} do modelo do README, macro \\NumX de qualquer .tex de relatorio/,
    gerado ou não, número registrado pelas figuras e pela planilha em numeros_usados.json) está
    PENDENTE, não existe no registro ou é um marcador fora da forma {{NumX}} exata;
  - há número digitado, fora de marcador ou macro, em docs/README.modelo.md ou num .tex de relatorio/
    escrito à mão (exceções na lista EXCECOES, abaixo, e no ADR 0002; o preâmbulo do kit não se lê);
  - algum arquivo de texto versionado, de qualquer extensão, ou o PDF diz que o painel foi publicado
    na web;
  - o README montado ou o PDF mostram PENDENTE ou um marcador que sobrou;
  - relatorio/relatorio.tex não compila em pdfLaTeX, nas duas passadas, sem erro e sem referência ou
    citação quebrada. O PDF e os .aux antigos se apagam antes; compilado, o PDF vai para
    relatorio/relatorio.pdf.

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

# O registro de números e os marcadores são os mesmos de scripts/numeros.py, que monta o README.
from comum import DEFINICAO, MACRO, MARCADOR, MODELO_README, NOME_NUMERO, NUMEROS_USADOS, PENDENTE, REGISTRO_TEX

RAIZ = Path(__file__).resolve().parent.parent

README = 'README.md'                    # montado por scripts/numeros.py a partir do modelo
RELATORIO_TEX = 'relatorio/relatorio.tex'
RELATORIO_PDF = 'relatorio/relatorio.pdf'
# Tudo o que tem cara de marcador: o que não for {{NumX}} exato, scripts/numeros.py não troca.
QUALQUER_MARCADOR = re.compile(r'\{\{[^{}\n]*\}\}')


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

    def resultado(self, nome, problemas):
        """[OK] sem problema; [FALHA], com a lista, com algum."""
        if problemas:
            self.falha(nome, problemas)
        else:
            self.ok(nome)


# ── número digitado ─────────────────────────────────────────────────────
def apagar(texto, padrao, flags=0):
    """Troca cada trecho que casa com o padrão por espaços do mesmo tamanho, mantendo as quebras de
    linha: assim a posição de cada caractere que sobra, e a linha dele, não mudam."""
    return re.sub(padrao, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), texto, flags=flags)


def linha_de(texto, pos):
    return texto.count('\n', 0, pos) + 1


# As exceções à regra do número digitado (GUIA_ESTILO.md, "A regra dos números"), decididas em
# docs/adr/0002-excecoes-ao-numero-digitado.md. Esta é a lista única, e curta: cada entrada é um número
# que faz parte de um NOME, de um comando ou da estrutura do texto, e não um resultado do estudo. Antes
# de pôr uma entrada aqui, veja se o número não deveria sair de scripts/numeros.py. A seção de Fontes do
# README não pediu nenhuma (ADR 0002).
EXCECOES = [re.compile(p, f) for p, f in [
    # código no README: comando, nome de arquivo, versão num comando. Bloco cercado por ``` e trecho
    # entre crases, nesta ordem
    (r'^\s*```.*?^\s*```', re.S | re.M),
    (r'`[^`\n]*`', 0),
    # estrutura: título numerado ("## 2. Como foi feito") e passo de lista numerada ("1. Instale"); até
    # dois algarismos, para que um ano no começo de uma linha quebrada continue acusado
    (r'^\s*(?:#{1,6}\s+)?\d{1,2}[.)](?=\s)', re.M),
    # versão de ferramenta: "Python 3.12", "Excel 365"
    (r'\b(?:Python|R|Excel)\s+\d+(?:\.\d+)*\b', 0),
    # ano no nome de uma fonte: o "Censo 2022" é a pesquisa, e não um recorte escolhido pelo estudo
    (r'\bCenso(?: Demográfico| Escolar)? \d{4}\b', 0),
    # o número do próprio ato normativo, logo depois do nome (com o órgão e "nº" no meio, se houver):
    # "Lei 8.080/1990", "Portaria STN nº 642/2019", "Lei Complementar nº 101/2000". Outro número na
    # mesma frase ("Segundo a Portaria, 45 municípios") continua acusado.
    (r'\b(?:Lei|Portaria|Decreto|Resolução)(?:[ -](?:[A-Z][A-Za-z]*(?:/[A-Z]+)?)){0,2}'
     r'\s+(?:n\.?\s?[º°o]\.?\s*)?\d[\d.]*(?:/\d{2,4})?', 0),
    # versão no nome de uma licença: "CC BY 4.0", "CC BY-ND 3.0" (seção de Fontes e licenças)
    (r'\bCC BY(?:-[A-Z]{2})*\s+\d\.\d\b', 0),
    # nome de arquivo: "01-painel-municipio.png", "backtest_2015.csv"
    (r'[\w.-]*\d[\w.-]*\.(?:csv|png|pdf|tex|md|py|json|sqlite|xlsx|tmdl|pbip|sql)\b', 0),
]]

# O que, no Markdown, não é texto: o leitor não vê ali número nenhum.
SINTAXE_MARKDOWN = [
    (r'<!--.*?-->', re.S),               # comentário (scripts/numeros.py o tira do README)
    (r'https?://[^\s)>]+', 0),            # endereço
    (r'\]\([^)\n]*\)', 0),                # destino de link e de imagem
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


def numeros_digitados(texto, sintaxe, marcador):
    """(linha, número, trecho) de cada número que sobra fora de marcador, de sintaxe e das exceções."""
    limpo = texto
    for padrao, flags in sintaxe:
        limpo = apagar(limpo, padrao, flags)
    limpo = apagar(limpo, marcador)
    for excecao in EXCECOES:
        limpo = apagar(limpo, excecao)
    linhas = texto.splitlines()
    achados = []
    for m in re.finditer(r'\d+(?:[.,]\d+)*', limpo):
        n = linha_de(limpo, m.start())
        achados.append((n, m.group(0), linhas[n - 1].strip()))
    return achados


def conferir_digitados(v, caminho, texto):
    if caminho.endswith('.tex'):
        achados, uso = numeros_digitados(texto, SINTAXE_LATEX, MACRO), r'uma macro \Num...'
    else:
        achados, uso = numeros_digitados(texto, SINTAXE_MARKDOWN, QUALQUER_MARCADOR), 'um marcador {{Num...}}'
    v.resultado(f'nenhum número digitado em {caminho}',
                [f'{caminho}:{n}: número digitado "{num}" (use {uso}): {trecho}' for n, num, trecho in achados])


# ── marcadores, macros e PENDENTE ───────────────────────────────────────
def ler_registro(raiz):
    """{nome: valor} da saída do registro de números (relatorio/numeros.tex), ou None se ela não existe."""
    arq = raiz / REGISTRO_TEX
    if not arq.exists():
        return None
    return dict(DEFINICAO.findall(arq.read_text(encoding='utf-8')))


def usos_no_modelo(texto):
    """(onde, nome) de cada marcador do modelo do README, fora de comentário. Um marcador fora da forma
    {{NumX}} exata ("{{ NumX }}", "{{Num1}}") entra inteiro, para ser acusado."""
    texto = apagar(texto, r'<!--.*?-->', re.S)
    usos = []
    for m in QUALQUER_MARCADOR.finditer(texto):
        certo = MARCADOR.fullmatch(m.group(0))
        usos.append((f'{MODELO_README}:{linha_de(texto, m.start())}', certo.group(1) if certo else m.group(0)))
    return usos


def usos_no_latex(caminho, texto):
    r"""(onde, nome) de cada macro \Num... de um .tex do relatório, fora de comentário."""
    texto = apagar(texto, r'(?<!\\)%[^\n]*')
    return [(f'{caminho}:{linha_de(texto, m.start())}', m.group(1)) for m in MACRO.finditer(texto)]


def ler_tex(raiz):
    """{caminho: texto} de cada .tex de relatorio/, lidos uma vez só."""
    pasta = raiz / 'relatorio'
    if not pasta.exists():
        return {}
    return {p.relative_to(raiz).as_posix(): p.read_text(encoding='utf-8') for p in sorted(pasta.rglob('*.tex'))}


def gerado(texto):
    """Um .tex gerado por script (primeira linha "% GERADO", como as linhas de tabela) tem os números
    por construção: não se confere número digitado nele, só as macros que usa."""
    return texto.startswith('% GERADO')


def usos_nas_figuras(raiz):
    """(onde, nome) de cada número que figuras e planilha registram como impresso."""
    usos = []
    for arq in NUMEROS_USADOS:
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
        v.falha(nome, [f'{REGISTRO_TEX} não existe: rode python scripts/numeros.py'])
        return
    problemas = []
    for onde, num in usos:
        if not re.fullmatch(NOME_NUMERO, num):
            problemas.append(f'{onde}: "{num}" fora da forma {{{{NumX}}}} ("Num" e só letras, sem espaço): '
                             'scripts/numeros.py não o troca pelo valor')
        elif num not in registro:
            problemas.append(f'{onde}: {num} não existe no registro ({REGISTRO_TEX})')
        elif registro[num] == PENDENTE:
            problemas.append(f'{onde}: {num} está {PENDENTE}')
    v.resultado(nome, problemas)


# ── "publicado na web" ──────────────────────────────────────────────────
# O painel abre no Power BI Desktop e não foi publicado (spec, Out of Scope). Nenhum texto diz o contrário.
PUBLICADO = r'\b(?:publicad[oa]s?|publicamos|publiquei|publicou|publicaram)\b'
NA_WEB = r'(?:n[ao]\s+(?:web|internet|(?:Power\s+BI\s+)?Service)|em\s+(?:web|internet)|on-?line)\b'
PUBLICACAO = re.compile('|'.join([
    # "publicado na web", "publicamos o painel na web", "publicado online", "publicado no Service":
    # até quatro palavras entre o verbo e o lugar, sem atravessar pontuação
    PUBLICADO + r'(?:\s+[^\s.;:!?]+){0,4}?\s+' + NA_WEB,
    r'\bdisponíve(?:l|is)\s+(?:on-?line|n[ao]\s+(?:web|internet))\b',
    r'\bpublish(?:ed)?\s+to\s+(?:the\s+)?web',
    r'\bpublished\s+(?:online|(?:on|to)\s+(?:the\s+)?(?:internet|web|Power\s+BI\s+Service))',
    r'app\.powerbi\.com',                   # link de relatório publicado ("Publicar na Web" ou Service)
]), re.I)
# Frase que nega ("o painel não foi publicado na web") não afirma a publicação. A negação só conta
# quando rege a afirmação: na mesma oração e a poucas palavras antes dela ("nada diz que o painel foi
# publicado", "nem publicado"). Um "não" de outra oração ("Não é difícil: o painel foi publicado")
# ou de outra linha da lista não vale.
NEGACAO = re.compile(r'\b(?:não|nunca|nada|nem|jamais|not|never|nothing)\b', re.I)
FIM_DE_ORACAO = re.compile(r'[.;:!?,()—]|\n\s*\n|\n\s*(?:[-*+>#|]|\d+[.)])')
ALCANCE_DA_NEGACAO = 6  # palavras antes da afirmação
# Os únicos textos versionados que não se leem: o verificador e os testes dele trazem as frases de
# propósito, para acusá-las.
FORA_DA_PUBLICACAO = ('scripts/verificar_textos.py', 'tests/test_verificar_textos.py')


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


def arquivos_versionados(raiz):
    """Os arquivos do repositório (git ls-files), ou None fora de um repositório git."""
    try:
        r = subprocess.run(['git', 'ls-files', '-z'], cwd=raiz, capture_output=True)
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        return None
    return [c for c in r.stdout.decode('utf-8').split('\0') if c]


def ler_se_for_texto(arq):
    """O conteúdo do arquivo, se for texto em UTF-8; None se for binário (imagem, SQLite)."""
    dados = arq.read_bytes()
    if b'\0' in dados:
        return None
    try:
        return dados.decode('utf-8')
    except UnicodeDecodeError:
        return None


def conferir_publicacao(v, raiz, entregues):
    """Lê todo arquivo versionado que seja texto, de qualquer extensão, e os textos entregues ainda não
    versionados."""
    nome = 'nenhum texto diz que o painel foi publicado na web'
    versionados = arquivos_versionados(raiz)
    if versionados is None:
        v.falha(nome, [f'git ls-files não rodou em {raiz}: a pasta tem de ser um repositório git'])
        return
    problemas, lidos = [], 0
    for caminho in sorted(set(versionados) | set(entregues)):
        if caminho in FORA_DA_PUBLICACAO or not (raiz / caminho).is_file():
            continue
        texto = ler_se_for_texto(raiz / caminho)
        if texto is None:
            continue
        lidos += 1
        problemas += [f'{caminho}:{n}: {trecho}' for n, trecho in frases_de_publicacao(texto)]
    v.resultado(f'{nome} ({lidos} arquivos de texto)', problemas)


# ── compilação do relatório ─────────────────────────────────────────────
# Com -file-line-error, o pdfLaTeX escreve o erro como "secoes/base.tex:2: Undefined control sequence.",
# com o arquivo em que ele está, também dentro de \input e \include.
ERRO_COM_ARQUIVO = re.compile(r'^(.+?\.(?:tex|sty|cls|def|cfg|ltx|aux)):(\d+): (.*)$')


def caminho_no_repositorio(arquivo, pasta, raiz):
    """O arquivo citado no log (relativo à pasta do relatório) como caminho do repositório."""
    p = (pasta / arquivo).resolve()
    return p.relative_to(raiz).as_posix() if p.is_relative_to(raiz) else arquivo


def erros_do_log(log, pasta, raiz):
    """(onde, mensagem) de cada erro do pdfLaTeX. O erro sem arquivo ("! ...") fica com a linha do fonte
    ("l.12 ...") que vem logo depois, no relatório principal."""
    erros = []
    linhas = log.splitlines()
    for i, linha in enumerate(linhas):
        m = ERRO_COM_ARQUIVO.match(linha)
        if m:
            arquivo, n, mensagem = m.groups()
            # "==> Fatal error" e "Emergency stop" só repetem que o erro anterior parou a compilação
            if not mensagem.lstrip().startswith(('==>', 'Emergency stop')):
                erros.append((f'{caminho_no_repositorio(arquivo, pasta, raiz)}:{n}', mensagem))
        elif linha.startswith('! ') and not linha.startswith(('!  ==>', '! Emergency stop')):
            n = next((m.group(1) for m in (re.match(r'l\.(\d+)', x) for x in linhas[i + 1:i + 15]) if m), '?')
            erros.append((f'{RELATORIO_TEX}:{n}', linha))
    return erros


# Referência e citação quebradas ("sem referência quebrada", ticket 07), no log da última passada.
REFERENCIA_QUEBRADA = re.compile(r"LaTeX Warning: (Reference|Citation) `([^']+)' on page \S+ undefined"
                                 r"(?: on input line (\d+))?")


def referencias_quebradas(log, textos):
    """(onde, mensagem) de cada \\ref e \\cite sem destino. onde: o \\ref no fonte, procurado nos .tex do
    relatório (o aviso do log só dá a linha, sem o arquivo)."""
    quebradas = []
    for tipo, nome, linha_log in dict.fromkeys(REFERENCIA_QUEBRADA.findall(log)):
        uso = re.compile(r'\\[A-Za-z]*(?:ref|cite)[A-Za-z]*\*?(?:\[[^\]]*\])*\{[^}]*(?<![^{,\s])'
                         + re.escape(nome) + r'(?![^},\s])')
        lugares = [f'{caminho}:{n}' for caminho, texto in textos.items()
                   for n, linha in enumerate(texto.splitlines(), start=1) if uso.search(linha)]
        o_que = 'referência' if tipo == 'Reference' else 'citação'
        for onde in lugares or [f'{RELATORIO_TEX}:{linha_log or "?"}']:
            quebradas.append((onde, f'{o_que} "{nome}" sem destino'))
    return list(dict.fromkeys(quebradas))


def conferir_compilacao(v, raiz, limite, textos):
    v.resultado(f'{RELATORIO_TEX} compila em pdfLaTeX, duas passadas, sem erro',
                problemas_da_compilacao(raiz, limite, textos))


def problemas_da_compilacao(raiz, limite, textos):
    """Compila relatorio/relatorio.tex em duas passadas, como o kit manda, e devolve os problemas. Os
    arquivos auxiliares ficam numa pasta temporária; sem problema, o PDF vai para relatorio/relatorio.pdf.
    limite: segundos por passada. textos: os .tex do relatório, para achar o \\ref quebrado."""
    pasta = (raiz / RELATORIO_TEX).parent
    # Saídas de uma compilação anterior: o PDF antigo seria conferido se esta falhar, e um .aux na pasta
    # do relatório é lido no lugar do novo, escondendo referência quebrada.
    for antigo in [raiz / RELATORIO_PDF, *pasta.rglob('*.aux'),
                   *(pasta / f'relatorio.{ext}' for ext in ('log', 'out', 'toc', 'lof', 'lot', 'bbl', 'blg'))]:
        antigo.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as saida:
        for passada in (1, 2):
            try:
                r = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', '-file-line-error',
                                    f'-output-directory={saida}', Path(RELATORIO_TEX).name],
                                   cwd=pasta, capture_output=True, timeout=limite)
            except FileNotFoundError:
                return ['pdflatex não está no PATH: instale o MiKTeX (ou o TeX Live) e abra outro terminal']
            except subprocess.TimeoutExpired:
                return [f'pdflatex passou de {limite:g} s na passada {passada} e foi interrompido '
                        '(laço de macro? Rode pdflatex à mão para ver onde para)']
            log = Path(saida, 'relatorio.log')
            log = log.read_text(encoding='utf-8', errors='replace') if log.exists() else r.stdout.decode(errors='replace')
            erros = erros_do_log(log, pasta, raiz)
            if r.returncode != 0 or erros:
                erros = erros or [(RELATORIO_TEX, f'pdflatex saiu com código {r.returncode}')]
                return [f'{onde}: {erro} (passada {passada})' for onde, erro in erros]
        quebradas = referencias_quebradas(log, textos)
        if quebradas:
            return [f'{onde}: {erro} (depois da passada 2)' for onde, erro in quebradas]
        shutil.copyfile(Path(saida, 'relatorio.pdf'), raiz / RELATORIO_PDF)
    return []


# ── o texto que o leitor vê: PDF e README montado ───────────────────────
def conferir_texto_final(v, caminho, trechos, publicacao):
    """trechos: [(onde, texto)], as linhas do README ou as páginas do PDF. Falha se o leitor veria
    PENDENTE ou um marcador que sobrou e, com publicacao=True, a frase de publicação na web. O README é
    texto versionado, e a conferência da publicação já o lê; o PDF não, e só aqui se procura a frase nele."""
    nome = f'{caminho} não mostra {PENDENTE}, marcador sobrando' + (' nem publicação na web' if publicacao else '')
    problemas = []
    for onde, texto in trechos:
        linhas = texto.splitlines()
        for m in re.finditer(PENDENTE + '|' + QUALQUER_MARCADOR.pattern, texto):
            problemas.append(f'{onde}: "{m.group(0)}" em: {linhas[linha_de(texto, m.start()) - 1].strip()}')
        if publicacao:
            problemas += [f'{onde}: publicação na web em: {trecho}' for _, trecho in frases_de_publicacao(texto)]
    v.resultado(nome, problemas)


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
        modelo = (raiz / MODELO_README).read_text(encoding='utf-8')
        conferir_digitados(v, MODELO_README, modelo)
        usos += usos_no_modelo(modelo)
    else:
        v.pulada('modelo do README', f'{MODELO_README} ainda não existe')
    tex = ler_tex(raiz)
    for caminho, texto in tex.items():
        if caminho == REGISTRO_TEX:   # o registro define as macros; não as usa
            continue
        if not gerado(texto):
            conferir_digitados(v, caminho, texto)
        usos += usos_no_latex(caminho, texto)
    conferir_registro(v, raiz, usos)
    # os versionados e, mesmo antes do primeiro commit, os textos entregues
    entregues = [c for c in (MODELO_README, README) if (raiz / c).exists()] + list(tex)
    conferir_publicacao(v, raiz, entregues)
    if (raiz / README).exists():
        linhas = (raiz / README).read_text(encoding='utf-8').splitlines()
        conferir_texto_final(v, README, [(f'{README}:{i}', t) for i, t in enumerate(linhas, start=1)],
                             publicacao=False)
    if (raiz / RELATORIO_TEX).exists():
        conferir_compilacao(v, raiz, limite_pdflatex, tex)
    else:
        v.pulada('compilação do relatório', f'{RELATORIO_TEX} ainda não existe')
    if (raiz / RELATORIO_PDF).exists():
        conferir_pdf(v, raiz)
    elif (raiz / RELATORIO_TEX).exists():
        v.pulada('texto do PDF', f'a compilação falhou e não deixou {RELATORIO_PDF}')
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
