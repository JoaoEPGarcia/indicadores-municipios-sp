"""Testes do registro de números (scripts/numeros.py), rodado por fora numa cópia do repositório.

    python -m unittest discover -s tests -v

O script grava o README, relatorio/numeros.tex e relatorio/gerados/ dentro do repositório; por isso ele roda numa
cópia (tests/apoio.py), e os testes leem o que ele escreveu. Os valores esperados vêm de fora do código: dos CSV
de dados/tratados/, contados aqui com pandas, das páginas gravadas do PBIR e do passo a passo escrito à mão
(excel/PASSO_A_PASSO.md), que traz as fórmulas como o leitor as digita no Excel em português. A data da capa
do relatório sai de dado versionado (o dia da conferência da planilha, gravado no resultado dela), e não do
relógio: a cópia troca esse dia por outro, de propósito, e o registro tem de segui-lo.
"""
import json
import re
import unittest

import pandas as pd

from apoio import REPO, Copia

TRATADOS = REPO / 'dados' / 'tratados'
PASSO = (REPO / 'excel' / 'PASSO_A_PASSO.md').read_text(encoding='utf-8')
DIA_DA_CONFERENCIA = '2027-03-15'      # um dia que não é hoje: se a capa seguisse o relógio, o teste pegaria


def sem_espacos(f):
    return re.sub(r'\s+', '', f)


def trecho_de_codigo(tex):
    """O código entre \\begin{verbatim} e \\end{verbatim} de um arquivo gerado."""
    return re.search(r'\\begin\{verbatim\}\n(.*)\n\\end\{verbatim\}', tex, re.S).group(1)


class RegistroGerado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copia = Copia()
        resultado = cls.copia.raiz / 'excel' / 'resultado_conferencia_excel.json'
        r = json.loads(resultado.read_text(encoding='utf-8'))
        resultado.write_text(json.dumps({**r, 'data': DIA_DA_CONFERENCIA}), encoding='utf-8')
        cls.codigo, cls.saida = cls.copia.rodar('numeros.py')
        cls.readme = cls.copia.ler('README.md')

    @classmethod
    def tearDownClass(cls):
        cls.copia.fechar()

    def test_roda_sem_erro_e_sem_marcador_sobrando_no_readme(self):
        self.assertEqual(self.codigo, 0, self.saida)
        self.assertNotIn('{{', self.readme)

    def test_readme_diz_os_precos_do_ano_antes_da_previsao(self):
        ano_base = int(pd.read_csv(TRATADOS / 'previsao_receita_total.csv').ano.min()) - 1
        self.assertIn(f'(a preços de {ano_base})', self.readme)

    def test_readme_diz_o_ultimo_ano_do_pib_municipal(self):
        fato = pd.read_csv(TRATADOS / 'indicadores_longo.csv')
        self.assertIn(f'O PIB dos Municípios termina em {int(fato[fato.indicador_id == "pib_pc"].ano.max())}.', self.readme)

    def test_readme_conta_as_paginas_gravadas_do_painel(self):
        pastas = [p for p in (REPO / 'powerbi' / 'painel-municipios-sp.Report' / 'definition' / 'pages').iterdir() if p.is_dir()]
        self.assertIn(f'Painel de Power BI (PBIP) de {len(pastas)} páginas', self.readme)

    def test_readme_usa_os_dois_niveis_do_intervalo_de_previsao(self):
        menor, maior = sorted(pd.read_csv(TRATADOS / 'backtest_cobertura.csv').nivel.unique())
        self.assertIn(f'com os Intervalos de previsão de {menor}% e de {maior}%', self.readme)

    def test_capa_do_relatorio_tem_o_mes_e_o_ano_da_conferencia_gravada(self):
        registro = self.copia.ler('relatorio/numeros.tex')
        self.assertIn(r'\newcommand{\NumMesCapa}{Março}', registro)
        self.assertIn(r'\newcommand{\NumAnoCapa}{2027}', registro)

    def test_procx_do_relatorio_e_a_do_passo_a_passo(self):
        esperado = re.search(r'^\| E13 \| `(=[^`]+)`', PASSO, re.M).group(1)
        obtido = trecho_de_codigo(self.copia.ler('relatorio/gerados/excel_procx.tex'))
        self.assertEqual(sem_espacos(obtido), sem_espacos(esperado))

    def test_let_do_relatorio_e_o_do_passo_a_passo(self):
        esperado = re.search(r'^\| D13 \| `(=[^`]+)`', PASSO, re.M).group(1)
        obtido = trecho_de_codigo(self.copia.ler('relatorio/gerados/excel_let.tex'))
        self.assertEqual(sem_espacos(obtido), sem_espacos(esperado))


if __name__ == '__main__':
    unittest.main()
