"""Testes do conferidor da planilha (scripts/conferir_excel.py).

    python -m unittest discover -s tests -v

O conferidor lê uma planilha já calculada pelo Excel (baixada do Excel para a web) e compara o que as fórmulas
devolveram com o SQLite. Aqui, cada planilha de teste é montada com openpyxl só com valores, como o Excel os
guarda depois de calcular. Os valores esperados saem dos CSV de dados/tratados/, por pandas, e não do SQLite
nem do código do conferidor: é uma segunda conta, independente. O conferidor roda por fora, como o dono roda.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.workbook.defined_name import DefinedName

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / 'scripts' / 'conferir_excel.py'
TRATADOS = REPO / 'dados' / 'tratados'
sys.path.insert(0, str(REPO / 'scripts'))
import comum  # noqa: E402

MUN = pd.read_csv(TRATADOS / 'dim_municipio.csv')
FATO = pd.read_csv(TRATADOS / 'indicadores_longo.csv')
REF = pd.read_csv(TRATADOS / 'referencia_faixa.csv')
PREV = pd.read_csv(TRATADOS / 'previsao_receita_total.csv')
CONFERENCIA = ['Franco da Rocha', 'Morro Agudo', 'Santa Lúcia']      # powerbi/conferencia.md
EXEMPLO = MUN.set_index('cod_ibge').municipio[comum.municipio_de_exemplo()[0]]


def linha_painel(cod, ind):
    """(ano, valor, mediana, diferença, posição) como a tabela do Painel mostra, contados em pandas."""
    f = FATO[(FATO.cod_ibge == cod) & (FATO.indicador_id == ind)]
    if f.empty:
        return ['n.d.'] * 5
    ano = int(f.ano.max())
    v = float(f[f.ano == ano].valor.iloc[0])
    faixa = MUN.set_index('cod_ibge').faixa_porte[cod]
    r = REF[(REF.faixa_porte == faixa) & (REF.ano == ano) & (REF.indicador_id == ind)].iloc[0]
    da_faixa = FATO[(FATO.faixa_porte == faixa) & (FATO.ano == ano) & (FATO.indicador_id == ind)]
    posicao = (da_faixa.valor < v).sum() / (int(r.n) - 1)
    return [ano, v, float(r.mediana), v / float(r.mediana) - 1, float(posicao)]


def planilha(destino, municipio, referencia=True, mexer=None, sem_cache=False):
    """Uma planilha como o Excel a grava depois de calcular: só os valores nas células que o conferidor lê."""
    cod = int(MUN.set_index('municipio').cod_ibge[municipio])
    wb = openpyxl.Workbook()
    painel = wb.active
    painel.title = 'Painel'
    prev = wb.create_sheet('Previsão')
    painel['C4'] = municipio
    painel['C5'] = '=XLOOKUP($C$4, tMunicipios[municipio], tMunicipios[cod_ibge])' if sem_cache else cod
    for k, ind in enumerate(comum.INDICADORES_PAINEL):
        for j, v in enumerate(linha_painel(cod, ind)):
            painel.cell(13 + k, 4 + j, '=1+1' if sem_cache else v)
    obs = FATO[(FATO.cod_ibge == cod) & (FATO.indicador_id == 'receita_total')].set_index('ano').valor
    p = PREV[PREV.cod_ibge == cod].set_index('ano')
    ultimo_obs = int(PREV.ano.min()) - 1
    for k, ano in enumerate(range(int(FATO.ano.min()), int(PREV.ano.max()) + 1)):
        r = 8 + k
        prev.cell(r, 2, ano)
        prev.cell(r, 3, float(obs[ano]) if ano in obs.index else '#N/A')
        for j, c in enumerate(['previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95']):
            if ano in p.index:
                v = float(p[c][ano])
            elif ano == ultimo_obs and ano in obs.index:
                v = float(obs[ano])
            else:
                v = '#N/A'
            prev.cell(r, 4 + j, v)
    if mexer:
        aba, celula, valor = mexer
        wb[aba][celula] = valor
    if referencia:
        wb.defined_names['OrigemDaPlanilha'] = DefinedName('OrigemDaPlanilha', attr_text='"scripts/montar_excel.py"')
    wb.save(destino)
    return destino


class Conferidor(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self._tmp.name)
        self.resultado = self.pasta / 'resultado.json'

    def tearDown(self):
        self._tmp.cleanup()

    def conferir(self, *arquivos):
        r = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--resultado', str(self.resultado),
                            '--arquivo', *map(str, arquivos)], capture_output=True, text=True, encoding='utf-8')
        return r.returncode, r.stdout + r.stderr

    def quatro(self, **opcoes):
        return [planilha(self.pasta / f'p{k}.xlsx', m, **opcoes) for k, m in enumerate(CONFERENCIA + [EXEMPLO])]

    def test_quatro_planilhas_de_referencia_iguais_ao_sqlite_passam_e_gravam_o_resultado(self):
        codigo, saida = self.conferir(*self.quatro())
        self.assertEqual(codigo, 0, saida)
        r = json.loads(self.resultado.read_text(encoding='utf-8'))
        self.assertEqual(r['municipios'], 4)
        self.assertEqual(sorted(r['lista']), sorted(CONFERENCIA + [EXEMPLO]))
        self.assertEqual(r['batem'], r['celulas'])
        self.assertIn(f"{r['celulas']} de {r['celulas']} células iguais ao SQLite", saida)

    def test_celula_diferente_do_sqlite_falha_e_diz_onde(self):
        arq = planilha(self.pasta / 'p.xlsx', 'Morro Agudo', mexer=('Painel', 'E15', 123.4))
        codigo, saida = self.conferir(arq)
        self.assertEqual(codigo, 1, saida)
        self.assertIn('Morro Agudo | Painel | saude_pc | valor', saida)

    def test_previsao_diferente_do_sqlite_falha(self):
        arq = planilha(self.pasta / 'p.xlsx', 'Santa Lúcia', mexer=('Previsão', 'G21', 1.0))
        codigo, saida = self.conferir(arq)
        self.assertEqual(codigo, 1, saida)
        self.assertIn('Santa Lúcia | Previsão |', saida)

    def test_planilha_nunca_calculada_pelo_excel_falha_com_aviso_claro(self):
        arq = planilha(self.pasta / 'p.xlsx', EXEMPLO, sem_cache=True)
        codigo, saida = self.conferir(arq)
        self.assertEqual(codigo, 2, saida)
        self.assertIn('sem valores calculados', saida)
        self.assertFalse(self.resultado.exists())

    def test_planilha_que_nao_e_a_de_referencia_nao_mexe_no_resultado(self):
        self.resultado.write_text('{"celulas": 1}\n', encoding='utf-8')
        codigo, saida = self.conferir(*self.quatro(referencia=False))
        self.assertEqual(codigo, 0, saida)
        self.assertEqual(self.resultado.read_text(encoding='utf-8'), '{"celulas": 1}\n')
        self.assertIn('não é a planilha de referência', saida)

    def test_avisa_quais_municipios_da_conferencia_faltam_e_nao_grava_resultado_parcial(self):
        arq = planilha(self.pasta / 'p.xlsx', EXEMPLO)
        codigo, saida = self.conferir(arq)
        self.assertEqual(codigo, 0, saida)
        for m in CONFERENCIA:
            self.assertIn(m, saida)
        self.assertIn('faltam', saida)
        self.assertFalse(self.resultado.exists())


if __name__ == '__main__':
    unittest.main()
