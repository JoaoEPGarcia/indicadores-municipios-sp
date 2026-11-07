"""Testes do construtor da planilha de referência (scripts/montar_excel.py).

    python -m unittest discover -s tests -v

O construtor roda uma vez, por fora, como o dono roda, gravando numa pasta temporária. Os testes abrem o
arquivo gravado com openpyxl e olham o que quem abre a planilha encontra: as abas e a ordem delas, as tabelas
nomeadas, as listas de escolha, as fórmulas nas células que o passo a passo indica e os gráficos.
Os valores das fórmulas não são testados aqui: quem calcula é o Excel, e quem confere é scripts/conferir_excel.py.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / 'scripts' / 'montar_excel.py'
TRATADOS = REPO / 'dados' / 'tratados'
sys.path.insert(0, str(REPO / 'scripts'))
import comum  # noqa: E402
from apoio import Copia  # noqa: E402


def formula(celula):
    """Texto da fórmula de uma célula, sem os prefixos de arquivo (_xlfn., _xlpm.) que o Excel não mostra."""
    v = celula.value
    v = getattr(v, 'text', v)           # fórmula de matriz dinâmica: openpyxl devolve um objeto
    if not isinstance(v, str):
        return None
    return v.lstrip('=').replace('_xlfn.', '').replace('_xlpm.', '')


class PlanilhaGerada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.saida = Path(cls._tmp.name) / 'painel.xlsx'
        r = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), '--saida', str(cls.saida)],
                           capture_output=True, text=True, encoding='utf-8')
        if r.returncode != 0:
            raise AssertionError(f'o construtor falhou:\n{r.stdout}\n{r.stderr}')
        cls.wb = openpyxl.load_workbook(cls.saida)
        cls.cod_ex, _ = comum.municipio_de_exemplo()

    @classmethod
    def tearDownClass(cls):
        cls.wb.close()
        cls._tmp.cleanup()

    def test_abas_na_ordem_da_spec_com_as_de_dados_no_fim(self):
        self.assertEqual(self.wb.sheetnames, ['Leia-me', 'Painel', 'Explorar', 'Previsão', 'Indicadores',
                                              'Fontes e licenças', 'Municípios', 'Dados', 'Referência', 'Previsões'])

    def test_cinco_tabelas_nomeadas_com_os_dados(self):
        tabelas = {nome: (ws.title, ref) for ws in self.wb.worksheets for nome, ref in ws.tables.items()}
        self.assertEqual(set(tabelas), {'tMunicipios', 'tIndicadores', 'tFato', 'tReferencia', 'tPrevisao'})
        self.assertEqual(tabelas['tFato'][0], 'Dados')
        # a tabela Fato tem uma linha por linha do CSV, mais o cabeçalho, e o nome do Indicador mesclado
        with open(REPO / 'dados' / 'tratados' / 'indicadores_longo.csv', encoding='utf-8') as f:
            n_csv = sum(1 for _ in f)
        ws = self.wb['Dados']
        cab = [c.value for c in ws[1]]
        self.assertIn('indicador', cab)
        self.assertEqual(ws.max_row, n_csv)
        # o valor é número, e não texto (o CSV usa ponto decimal)
        self.assertIsInstance(ws.cell(2, cab.index('valor') + 1).value, float)
        # o nome mesclado é o do Indicador da linha
        linha = [c.value for c in ws[2]]
        ind = self.wb['Indicadores']
        nomes = {r[0]: r[1] for r in ind.iter_rows(min_row=2, values_only=True)}
        self.assertEqual(linha[cab.index('indicador')], nomes[linha[cab.index('indicador_id')]])

    def test_listas_de_escolha_de_municipio_e_de_indicador(self):
        ws = self.wb['Painel']
        listas = {str(v.sqref): v.formula1 for v in ws.data_validations.dataValidation if v.type == 'list'}
        self.assertEqual(listas, {'C4': 'ListaMunicipios', 'C24': 'ListaIndicadores'})
        nomes = self.wb.defined_names
        self.assertEqual(nomes['ListaMunicipios'].attr_text, 'tMunicipios[municipio]')
        self.assertEqual(nomes['ListaIndicadores'].attr_text, 'tIndicadores[nome]')

    def test_municipio_escolhido_de_saida_e_o_de_exemplo(self):
        nome = self.wb['Municípios']
        nomes = {r[0]: r[1] for r in nome.iter_rows(min_row=2, values_only=True)}
        self.assertEqual(self.wb['Painel']['C4'].value, nomes[self.cod_ex])

    def test_tabela_dos_sete_indicadores_com_procx_de_varias_condicoes_let_e_somarproduto(self):
        ws = self.wb['Painel']
        for k, ind in enumerate(comum.INDICADORES_PAINEL):
            r = 13 + k
            self.assertEqual(ws[f'A{r}'].value, ind)
            self.assertEqual(formula(ws[f'B{r}']), f'XLOOKUP($A{r}, tIndicadores[indicador_id], tIndicadores[nome])')
            self.assertTrue(formula(ws[f'D{r}']).startswith('LET(a, MAXIFS(tFato[ano]'))
            self.assertEqual(formula(ws[f'E{r}']), f'XLOOKUP(1, (tFato[cod_ibge]=$C$5)*(tFato[ano]=$D{r})'
                                                   f'*(tFato[indicador_id]=$A{r}), tFato[valor], "n.d.")')
            self.assertIn('tReferencia[mediana]', formula(ws[f'F{r}']))
            h = formula(ws[f'H{r}'])
            self.assertTrue(h.startswith(f'LET(v, E{r},'))
            self.assertIn('SUMPRODUCT((tFato[faixa_porte]=faixa)', h)

    def test_nomes_do_let_vao_com_o_prefixo_de_arquivo_e_so_fora_de_texto_e_de_coluna(self):
        h = self.wb['Painel']['H13'].value.text
        self.assertIn('_xlpm.ano, $D13', h)
        self.assertIn('tFato[ano]', h)              # o nome de coluna não leva o prefixo
        self.assertNotIn('[_xlpm.', h)
        frase = self.wb['Previsão']['B23'].value
        frase = getattr(frase, 'text', frase)
        self.assertIn('"Em "&_xlpm.a&", a receita corrente de "', frase)   # o "a" dentro do texto fica

    def test_aba_previsao_com_serie_intervalos_e_frase_com_def_num_dec(self):
        ws = self.wb['Previsão']
        self.assertTrue(formula(ws['B8']).startswith('SEQUENCE('))
        self.assertIn('"receita_total"', formula(ws['C8']))
        for col, campo in zip('DEFGH', ['previsto', 'inferior_80', 'superior_80', 'inferior_95', 'superior_95']):
            self.assertIn(f'tPrevisao[{campo}]', formula(ws[f'{col}8']))
        frase = formula(ws['B23'])
        self.assertEqual(frase.count('FIXED('), 5)

    def test_dados_dos_graficos_com_nao_disp_onde_nao_ha_dado(self):
        ws = self.wb['Painel']
        self.assertTrue(formula(ws['C46']).startswith('SEQUENCE(1, '))
        for r in range(47, 51):
            self.assertTrue(formula(ws[f'C{r}']).endswith('NA())'))

    def test_dois_graficos_de_linhas(self):
        with zipfile.ZipFile(self.saida) as z:
            graficos = [n for n in z.namelist() if re.fullmatch(r'xl/charts/chart\d+\.xml', n)]
            self.assertEqual(len(graficos), 2)
            for g in graficos:
                self.assertIn('<c:lineChart>', z.read(g).decode('utf-8'))

    def test_explorar_deixa_a_area_da_tabela_dinamica_vazia_e_diz_onde_inserir(self):
        ws = self.wb['Explorar']
        textos = ' '.join(str(c.value) for linha in ws.iter_rows() for c in linha if c.value)
        self.assertIn('D8', textos)
        self.assertIn('Segmentação', textos)
        for linha in ws.iter_rows(min_row=8):
            for c in linha:
                self.assertIsNone(c.value, f'{c.coordinate} devia ficar vazia para a tabela dinâmica')

    def test_marca_de_planilha_de_referencia(self):
        self.assertEqual(self.wb.defined_names['OrigemDaPlanilha'].attr_text, '"scripts/montar_excel.py"')

    def test_formulas_sem_valor_em_cache(self):
        """O construtor não calcula: o valor guardado fica vazio até o Excel abrir e recalcular."""
        wb = openpyxl.load_workbook(self.saida, data_only=True)
        try:
            self.assertIsNone(wb['Painel']['C5'].value)
            self.assertIsNone(wb['Painel']['E13'].value)
        finally:
            wb.close()

    def test_registro_dos_numeros_impressos_ao_lado_da_planilha(self):
        usados = json.loads((self.saida.parent / 'numeros_usados.json').read_text(encoding='utf-8'))
        self.assertIn('NumExemplo', usados[self.saida.name])
        self.assertIn('NumAnoBase', usados[self.saida.name])       # os reais do Leia-me

    def texto(self, aba):
        return ' '.join(str(c.value) for linha in self.wb[aba].iter_rows() for c in linha if isinstance(c.value, str))

    def test_leia_me_diz_o_ano_dos_precos_tirado_dos_dados(self):
        ano_base = int(pd.read_csv(TRATADOS / 'previsao_receita_total.csv').ano.min()) - 1
        self.assertIn(f'reais de {ano_base}', self.texto('Leia-me'))

    def test_leia_me_usa_o_vocabulario_do_glossario(self):
        leiame = self.texto('Leia-me')
        self.assertNotIn('projeção', leiame)       # GLOSSARY.md: Previsão da receita (evitar "projeção")
        self.assertIn('Previsão da receita', leiame)

    def test_leia_me_diz_quem_pos_a_tabela_dinamica_e_onde_esta_a_versao_final(self):
        # A planilha gerada não tem a tabela dinâmica: ela entra no Excel para a web, pelo agente de IA.
        leiame = self.texto('Leia-me')
        self.assertIn('Claude', leiame)
        self.assertNotIn('à mão, no Excel para a web', leiame)
        self.assertIn('excel/calculadas/ibira.xlsx', leiame)

    def test_previsao_chama_o_intervalo_pelo_nome_do_glossario_e_com_os_niveis_dos_dados(self):
        menor, maior = sorted(pd.read_csv(TRATADOS / 'backtest_cobertura.csv').nivel.unique())
        ws = self.wb['Previsão']
        cab = [ws.cell(7, c).value for c in range(2, 9)]
        self.assertEqual(cab[3:], [f'Limite inferior {menor}%', f'Limite superior {menor}%',
                                   f'Limite inferior {maior}%', f'Limite superior {maior}%'])
        self.assertIn(f'No Intervalo de previsão de {menor}%', formula(ws['B23']))
        self.assertIn(f'o Intervalo de previsão de {menor}% cobriu', self.texto('Previsão'))



class SoComOsDados(unittest.TestCase):
    """A planilha sai só de dados/tratados/: o construtor roda antes do painel, das conferências e da conferência
    da base existirem (numa cópia do repositório sem esses arquivos)."""

    def test_monta_sem_as_paginas_do_painel_sem_as_conferencias_e_sem_a_conferencia_da_base(self):
        copia = Copia()
        self.addCleanup(copia.fechar)
        for rel in ['powerbi/painel-municipios-sp.Report/definition/pages/pages.json', 'dados/tratados/validacao.txt',
                    'powerbi/resultado_conferencia.csv', 'powerbi/resultado_conferencia_completa.csv',
                    'excel/resultado_conferencia_excel.json', 'powerbi/conferencia.md']:
            (copia.raiz / rel).unlink()
        codigo, saida = copia.rodar('montar_excel.py', '--saida', copia.raiz / 'saida' / 'painel.xlsx')
        self.assertEqual(codigo, 0, saida)
        self.assertTrue((copia.raiz / 'saida' / 'painel.xlsx').exists())

if __name__ == '__main__':
    unittest.main()
