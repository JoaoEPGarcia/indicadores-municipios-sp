"""Testes do que scripts/numeros.py escreve para o relatório em LaTeX.

    python -m unittest discover -s tests -v

O relatório mostra as fórmulas da planilha como o Excel em português as mostra (PROCX, ponto e vírgula),
lidas do arquivo gerado, que as guarda em inglês. A fonte independente do que o leitor tem de ver é o
passo a passo escrito à mão (excel/PASSO_A_PASSO.md): a fórmula do relatório tem de ser a mesma.
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'scripts'))
import numeros  # noqa: E402

PASSO = (REPO / 'excel' / 'PASSO_A_PASSO.md').read_text(encoding='utf-8')


def sem_espacos(f):
    return re.sub(r'\s+', '', f)


class FormulasDaPlanilhaNoRelatorio(unittest.TestCase):
    def test_procx_com_varias_condicoes_e_a_do_passo_a_passo(self):
        esperado = re.search(r'^\| E13 \| `(=[^`]+)`', PASSO, re.M).group(1)
        self.assertEqual(sem_espacos(numeros.formula_da_planilha('Painel', 'E13')), sem_espacos(esperado))

    def test_posicao_na_faixa_com_let_e_a_do_passo_a_passo(self):
        bloco = re.search(r'\*\*Posição na faixa \(H13\):\*\*\s*```\s*(=.*?)```', PASSO, re.S).group(1)
        self.assertEqual(sem_espacos(numeros.formula_da_planilha('Painel', 'H13')), sem_espacos(bloco))


if __name__ == '__main__':
    unittest.main()
