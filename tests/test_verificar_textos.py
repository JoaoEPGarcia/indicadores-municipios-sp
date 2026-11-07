"""Testes do verificador dos textos entregues (scripts/verificar_textos.py).

    python -m unittest discover -s tests -v

Cada teste monta um repositório pequeno numa pasta temporária, com os arquivos que o leitor veria
(modelo do README, LaTeX do relatório, registro de números), roda o comando por fora, como o dono
roda, e olha só o código de saída e a mensagem.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / 'scripts' / 'verificar_textos.py'
MODELO_DO_KIT = REPO / 'estilo' / 'modelo_relatorio.tex'

# A saída do registro de números (relatorio/numeros.tex), como scripts/numeros.py a escreve.
REGISTRO = textwrap.dedent(r'''
    % GERADO por scripts/numeros.py. Não edite à mão: rode o script de novo.
    \newcommand{\NumMunicipios}{645}
    \newcommand{\NumAnoInicial}{2015}
    \newcommand{\NumAnoFinal}{2025}
    \newcommand{\NumLinhasFato}{50.413}
    \newcommand{\NumDifSaude}{$-$18,7}
    \newcommand{\NumCelulasBatem}{PENDENTE}
''').lstrip()

# O menor relatório que compila: só uma macro do registro.
RELATORIO_MINIMO = r'''
    \documentclass{article}
    \input{numeros.tex}
    \begin{document}
    São \NumMunicipios{} municípios.
    \end{document}
'''


class Repositorio:
    """Um repositório de brinquedo, com git, numa pasta temporária."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        subprocess.run(['git', 'init', '-q'], cwd=self.raiz, check=True)
        self.escrever('relatorio/numeros.tex', REGISTRO)

    def escrever(self, caminho, texto, versionar=False):
        arq = self.raiz / caminho
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(textwrap.dedent(texto).lstrip(), encoding='utf-8')
        if versionar:
            subprocess.run(['git', 'add', caminho], cwd=self.raiz, check=True)
        return arq

    def verificar(self, *opcoes, env=None):
        # Sem PYTHONIOENCODING nem PYTHONUTF8: o comando escreve os acentos sozinho, também no console
        # do Windows, cuja página de código (cp1252) não é UTF-8.
        ambiente = {k: v for k, v in os.environ.items() if k not in ('PYTHONIOENCODING', 'PYTHONUTF8')}
        ambiente.update(env or {})
        r = subprocess.run([sys.executable, str(SCRIPT), '--raiz', str(self.raiz), *opcoes],
                           capture_output=True, env=ambiente)
        return r.returncode, (r.stdout + r.stderr).decode('utf-8', errors='replace')

    def fechar(self):
        self._tmp.cleanup()


class TesteVerificador(unittest.TestCase):
    def setUp(self):
        self.repo = Repositorio()
        self.addCleanup(self.repo.fechar)

    def test_sem_modelo_e_sem_relatorio_passa_e_lista_o_que_pulou(self):
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)
        self.assertIn('[PULADA]', saida)
        self.assertIn('docs/README.modelo.md', saida)
        self.assertIn('relatorio/relatorio.tex', saida)
        self.assertIn('relatorio/relatorio.pdf', saida)

    def test_saida_escreve_os_acentos_em_utf8(self):
        codigo, saida = self.repo.verificar()
        self.assertIn('ainda não existe', saida)

    def test_numero_digitado_no_modelo_do_readme_falha_com_arquivo_e_linha(self):
        self.repo.escrever('docs/README.modelo.md', '''
            # Indicadores dos {{NumMunicipios}} municípios de SP

            Base de {{NumAnoInicial}} a {{NumAnoFinal}}, com 869 fórmulas na planilha.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('docs/README.modelo.md:3', saida)
        self.assertIn('869', saida)

    def test_modelo_no_formato_do_kit_passa(self):
        # Estrutura do README_modelo.md do kit: comentário, lista numerada (com subitens), código,
        # links, caminhos de arquivo e anos em nome de fonte, da lista de exceções.
        self.repo.escrever('docs/README.modelo.md', '''
            <!-- Modelo do README. Rode scripts/numeros.py: 1 passo só. -->
            # Indicadores dos {{NumMunicipios}} municípios de SP

            | | |
            |---|---|
            | **Dados** | {{NumLinhasFato}} linhas, de {{NumAnoInicial}} a {{NumAnoFinal}} |

            Faixas de porte do Censo 2022; ver a [Figura](graficos/01-painel-municipio.png) e o
            arquivo 03-previsao.png. Ideb sob CC BY 4.0, pela Portaria Inep nº 380/2020; o site
            do Ministério traz CC BY-ND 3.0.

            1. **Seleção.** Critérios:
               1. valor positivo;
               2. dentro de um quarto a quatro vezes a média.
            2. **Conferência.** Ver `scripts/validar.py` e `dados/tratados/backtest_2015.csv`.

            ```bash
            python scripts/coletar_siconfi_ibge.py 2015 2025
            ```

            ![Painel](graficos/02-municipio-na-faixa.png) · [LinkedIn](https://www.linkedin.com/in/x-123/)
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)

    def test_marcador_que_nao_existe_no_registro_falha(self):
        self.repo.escrever('docs/README.modelo.md', '''
            # Indicadores dos {{NumMunicipios}} municípios de SP

            Foram {{NumCidades}} cidades.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('docs/README.modelo.md:3', saida)
        self.assertIn('NumCidades', saida)

    def test_numero_pendente_usado_no_modelo_falha(self):
        self.repo.escrever('docs/README.modelo.md', '''
            # Indicadores dos {{NumMunicipios}} municípios de SP

            Batem {{NumCelulasBatem}} células.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('docs/README.modelo.md:3', saida)
        self.assertIn('NumCelulasBatem', saida)
        self.assertIn('PENDENTE', saida)

    def test_numero_pendente_usado_numa_figura_falha(self):
        self.repo.escrever('graficos/numeros_usados.json', '''
            {"01-painel-municipio.png": ["NumMunicipios", "NumCelulasBatem"]}
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('graficos/numeros_usados.json', saida)
        self.assertIn('01-painel-municipio.png', saida)
        self.assertIn('NumCelulasBatem', saida)

    def test_readme_montado_que_mostra_pendente_falha(self):
        self.repo.escrever('README.md', '''
            # Indicadores dos 645 municípios de SP

            Batem PENDENTE células.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('README.md:3', saida)
        self.assertIn('PENDENTE', saida)

    def test_numero_digitado_no_latex_falha_com_arquivo_e_linha(self):
        self.repo.escrever('relatorio/secao.tex', r'''
            \section{A base}
            São \NumMunicipios{} municípios, de \NumAnoInicial{} a \NumAnoFinal.
            A planilha tem 869 fórmulas.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/secao.tex:3', saida)
        self.assertIn('869', saida)

    def test_macro_que_nao_existe_no_registro_falha(self):
        self.repo.escrever('relatorio/secao.tex', r'''
            \section{A base}
            São \NumCidades{} cidades.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/secao.tex:2', saida)
        self.assertIn('NumCidades', saida)

    def test_modelo_de_relatorio_do_kit_nao_acusa_numero_digitado(self):
        # Preâmbulo do kit, capa com TikZ, medidas, \imagemplena[0.86], \linhasde: nada disso é
        # número do estudo. O registro de brinquedo traz as macros que o modelo usa.
        modelo = MODELO_DO_KIT.read_text(encoding='utf-8')
        macros = sorted(set(re.findall(r'\\(Num[A-Za-z]+)', modelo)))
        self.repo.escrever('relatorio/numeros.tex',
                           '% GERADO por scripts/numeros.py.\n' + ''.join(f'\\newcommand{{\\{m}}}{{1}}\n' for m in macros))
        self.repo.escrever('relatorio/secao.tex', modelo)
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)

    def test_texto_versionado_dizendo_que_o_painel_foi_publicado_na_web_falha(self):
        self.repo.escrever('powerbi/roteiro.md', '''
            # Roteiro

            Depois de montado, o painel foi publicado na web e pode ser aberto pelo link.
        ''', versionar=True)
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('powerbi/roteiro.md:3', saida)
        self.assertIn('publicado na web', saida)

    def test_publicacao_na_web_no_readme_e_acusada_uma_vez(self):
        self.repo.escrever('README.md', '''
            # Indicadores

            O painel foi publicado na web.
        ''', versionar=True)
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertEqual(saida.count('README.md:3'), 1, saida)

    def test_texto_que_nega_a_publicacao_passa(self):
        self.repo.escrever('GLOSSARY.md', '''
            # Glossário

            O painel não foi publicado na web: abre-se no Power BI Desktop.
        ''', versionar=True)
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)

    def test_outras_formas_de_dizer_que_o_painel_foi_publicado_falham(self):
        for frase in ['Publicamos o painel na web.',
                      'O painel foi publicado online.',
                      'O painel foi publicado na internet.',
                      'O painel está disponível online em painel.exemplo.org.',
                      'Abra em https://app.powerbi.com/groups/me/reports/abc.']:
            with self.subTest(frase=frase):
                self.repo.escrever('GLOSSARY.md', '# Glossário\n\n' + frase + '\n', versionar=True)
                codigo, saida = self.repo.verificar()
                self.assertEqual(codigo, 1, saida)
                self.assertIn('GLOSSARY.md:3', saida)

    def test_publicacao_em_texto_versionado_de_qualquer_extensao_falha(self):
        for caminho in ['powerbi/tabelas/Medidas.tmdl', 'scripts/gerar_tema.py', 'NOTAS']:
            with self.subTest(caminho=caminho):
                self.repo.escrever(caminho, '// o painel foi publicado na web\n', versionar=True)
                codigo, saida = self.repo.verificar()
                self.assertEqual(codigo, 1, saida)
                self.assertIn(f'{caminho}:1', saida)
                subprocess.run(['git', 'rm', '-q', '-f', caminho], cwd=self.repo.raiz, check=True)

    def test_binario_versionado_e_o_proprio_verificador_ficam_de_fora(self):
        imagem = self.repo.raiz / 'graficos' / 'captura.png'
        imagem.parent.mkdir()
        imagem.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\xff\xfe o painel foi publicado na web')
        self.repo.escrever('scripts/verificar_textos.py', "# acusa 'o painel foi publicado na web'\n")
        self.repo.escrever('tests/test_verificar_textos.py', "frase = 'o painel foi publicado na web'\n")
        subprocess.run(['git', 'add', '.'], cwd=self.repo.raiz, check=True)
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)

    def test_negacao_so_vale_quando_rege_a_publicacao(self):
        afirmam = [
            'Não é difícil: o painel foi publicado na web.',
            'O painel não usa DAX complexo; foi publicado na web.',
            'Nada de DAX complexo.\nO painel foi publicado na web.',
        ]
        negam = [
            'O painel não foi publicado na web.',
            'Nada diz que o painel foi publicado na web.',
            'O painel fica no Desktop, nem publicado na web nem no Service.',
            'O painel não foi\npublicado na web.',
        ]
        for frase, codigo_esperado in [(f, 1) for f in afirmam] + [(f, 0) for f in negam]:
            with self.subTest(frase=frase):
                self.repo.escrever('GLOSSARY.md', '# Glossário\n\n' + frase + '\n', versionar=True)
                codigo, saida = self.repo.verificar()
                self.assertEqual(codigo, codigo_esperado, saida)

    def test_sem_pdflatex_no_path_a_compilacao_falha_sem_traceback(self):
        self.repo.escrever('relatorio/relatorio.tex', RELATORIO_MINIMO)
        so_o_git = os.path.dirname(shutil.which('git'))
        codigo, saida = self.repo.verificar(env={'PATH': so_o_git})
        self.assertEqual(codigo, 1, saida)
        self.assertIn('[FALHA] relatorio/relatorio.tex compila', saida)
        self.assertIn('pdflatex', saida)
        self.assertNotIn('Traceback', saida)

    def test_sem_pymupdf_o_texto_do_pdf_falha_sem_traceback(self):
        self.repo.escrever('relatorio/relatorio.pdf', '%PDF-1.4 de um build antigo')
        with tempfile.TemporaryDirectory() as sem_pymupdf:
            Path(sem_pymupdf, 'pymupdf.py').write_text("raise ImportError('pymupdf ausente')", encoding='utf-8')
            codigo, saida = self.repo.verificar(env={'PYTHONPATH': sem_pymupdf})
        self.assertEqual(codigo, 1, saida)
        self.assertIn('[FALHA] relatorio/relatorio.pdf', saida)
        self.assertIn('pymupdf', saida)
        self.assertNotIn('Traceback', saida)


@unittest.skipUnless(shutil.which('pdflatex'), 'pdflatex não está no PATH')
class TesteCompilacao(unittest.TestCase):
    """Com um relatório presente, o comando compila o PDF (pdfLaTeX, duas passadas)."""

    def setUp(self):
        self.repo = Repositorio()
        self.addCleanup(self.repo.fechar)

    def test_relatorio_que_compila_passa_e_deixa_o_pdf(self):
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \input{numeros.tex}
            \begin{document}
            \section{A base}\label{sec:base}
            São \NumMunicipios{} municípios (Seção~\ref{sec:base}).
            \end{document}
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 0, saida)
        self.assertIn('[OK] relatorio/relatorio.tex compila', saida)
        self.assertTrue((self.repo.raiz / 'relatorio' / 'relatorio.pdf').exists())

    def test_relatorio_com_erro_de_latex_falha(self):
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \input{numeros.tex}
            \begin{document}
            São \NumMunicipios{} municípios. \comandoquenaoexiste
            \end{document}
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/relatorio.tex:4', saida)
        self.assertIn('Undefined control sequence', saida)

    def test_erro_de_latex_num_arquivo_incluido_aponta_esse_arquivo(self):
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \input{numeros.tex}
            \begin{document}
            \input{secoes/base}
            \end{document}
        ''')
        self.repo.escrever('relatorio/secoes/base.tex', r'''
            \section{A base}
            São \NumMunicipios{} municípios. \comandoquenaoexiste
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/secoes/base.tex:2', saida)
        self.assertIn('Undefined control sequence', saida)

    def test_referencia_quebrada_falha_apontando_onde_esta(self):
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \input{numeros.tex}
            \begin{document}
            \section{A base}\label{sec:base}
            São \NumMunicipios{} municípios (Seção~\ref{sec:base}).
            \input{secoes/fim}
            \end{document}
        ''')
        self.repo.escrever('relatorio/secoes/fim.tex', r'''
            Ver a Seção~\ref{sec:inexistente} e \cite{autor}.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/secoes/fim.tex:1', saida)
        self.assertIn('sec:inexistente', saida)
        self.assertIn('autor', saida)
        self.assertNotIn('sec:base', saida)

    def test_compilacao_que_passa_do_limite_de_tempo_falha_sem_traceback(self):
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \def\laco{\laco}
            \begin{document}
            \laco
            \end{document}
        ''')
        codigo, saida = self.repo.verificar('--limite-pdflatex', '3')
        self.assertEqual(codigo, 1, saida)
        self.assertIn('3 s', saida)
        self.assertNotIn('Traceback', saida)

    def test_pdf_que_imprime_pendente_falha(self):
        # Um PENDENTE que escapou para o PDF, por um caminho que não é macro (texto colado de outro lugar).
        self.repo.escrever('relatorio/relatorio.tex', r'''
            \documentclass{article}
            \input{numeros.tex}
            \begin{document}
            São \NumMunicipios{} municípios. Conferência: PENDENTE.
            \end{document}
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('relatorio/relatorio.pdf, página 1', saida)
        self.assertIn('PENDENTE', saida)


if __name__ == '__main__':
    unittest.main()
