"""Testes do verificador dos textos entregues (scripts/verificar_textos.py).

    python -m unittest discover -s tests -v

Cada teste monta um repositório pequeno numa pasta temporária, com os arquivos que o leitor veria
(modelo do README, LaTeX do relatório, registro de números), roda o comando por fora, como o dono
roda, e olha só o código de saída e a mensagem.
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'verificar_textos.py'

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

    def verificar(self):
        r = subprocess.run([sys.executable, str(SCRIPT), '--raiz', str(self.raiz)],
                           capture_output=True, text=True, encoding='utf-8',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        return r.returncode, r.stdout + r.stderr

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

    def test_numero_digitado_no_modelo_do_readme_falha_com_arquivo_e_linha(self):
        self.repo.escrever('docs/README.modelo.md', '''
            # Indicadores dos {{NumMunicipios}} municípios de SP

            Base de {{NumAnoInicial}} a {{NumAnoFinal}}, com 869 fórmulas na planilha.
        ''')
        codigo, saida = self.repo.verificar()
        self.assertEqual(codigo, 1, saida)
        self.assertIn('docs/README.modelo.md:3', saida)
        self.assertIn('869', saida)


if __name__ == '__main__':
    unittest.main()
