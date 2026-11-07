"""Testes dos números que só o README usa (scripts/numeros.py, bloco "README").

    python -m unittest discover -s tests -v

O registro é lido como os outros scripts o leem (numeros.calcular(), o mesmo que scripts/graficos.py chama).
Os valores esperados vêm de fora do código: o ano do último PIB municipal está em dados/tratados/validacao.txt
(a tabela de cobertura mostra PIB até 2023), a ordem das páginas está em powerbi/roteiro.md (quatro páginas) e
a data da leitura das licenças é a do README antigo (seção "Fontes e licenças").
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
import numeros  # noqa: E402


class NumerosDoReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.N = numeros.calcular()

    def valor(self, nome):
        self.assertIn(nome, self.N, f'{nome} não está no registro')
        return self.N[nome]['valor']

    def test_ano_base_dos_reais_e_o_ano_antes_da_previsao(self):
        self.assertEqual(self.valor('NumAnoBase'), '2025')

    def test_ultimo_ano_do_pib_municipal(self):
        self.assertEqual(self.valor('NumAnoFinalPib'), '2023')

    def test_paginas_do_painel(self):
        self.assertEqual(self.valor('NumPaginasPainel'), '4')

    def test_data_da_leitura_das_licencas(self):
        self.assertEqual(self.valor('NumDataConsultaFontes'), '14/10/2026')


if __name__ == '__main__':
    unittest.main()
