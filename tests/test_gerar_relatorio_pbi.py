"""Testes do gerador das páginas do Power BI (scripts/gerar_relatorio_pbi.py).

    python -m unittest discover -s tests -v

O gerador roda por fora, como o dono roda, numa pasta temporária. Os testes leem só o que ele grava
(a pasta .Report em formato PBIR) e conferem contra fontes independentes dele: o modelo semântico em
TMDL (todo campo usado existe), o registro de números (o município de exemplo) e o roteiro (páginas,
ordem de tabulação, sincronia das segmentações). Abrir no Power BI Desktop fica para o dono.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / 'scripts' / 'gerar_relatorio_pbi.py'
TMDL = REPO / 'powerbi' / 'painel-municipios-sp.SemanticModel' / 'definition' / 'tables'
REGISTRO = REPO / 'relatorio' / 'numeros.tex'
ESQUEMA = re.compile(r'^https://developer\.microsoft\.com/json-schemas/fabric/item/report/'
                     r'(definition/[A-Za-z]+|definitionProperties)/\d+\.\d+\.\d+/schema\.json$')

PAGINAS = ['Município', 'Comparação na faixa', 'Previsão da receita', 'Como ler, fontes e limites']


def gerar(saida):
    r = subprocess.run([sys.executable, str(SCRIPT), '--saida', str(saida)], capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode('utf-8', errors='replace')


def ler(arq):
    return json.loads(Path(arq).read_text(encoding='utf-8'))


def nome_tmdl(texto):
    texto = texto.strip()
    return texto[1:-1].replace("''", "'") if texto.startswith("'") else texto


def campos_do_modelo():
    """{(tabela, nome): 'column' | 'measure'} lido do TMDL, a fonte única do modelo."""
    campos = {}
    for arq in TMDL.glob('*.tmdl'):
        tabela = None
        for linha in arq.read_text(encoding='utf-8').splitlines():
            m = re.match(r"^table\s+(.+)$", linha)
            if m:
                tabela = nome_tmdl(m.group(1))
            m = re.match(r"^\t(column|measure)\s+('(?:[^']|'')+'|[^\s=]+)", linha)
            if m:
                campos[(tabela, nome_tmdl(m.group(2)))] = m.group(1)
    return campos


def percorrer(no):
    """Todo dicionário dentro de um JSON."""
    if isinstance(no, dict):
        yield no
        for v in no.values():
            yield from percorrer(v)
    elif isinstance(no, list):
        for v in no:
            yield from percorrer(v)


class TesteRelatorioGerado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.saida = Path(cls._tmp.name) / 'painel.Report'
        cls.codigo, cls.mensagem = gerar(cls.saida)
        cls.definicao = cls.saida / 'definition'
        cls.visuais = {}   # {(página, visual): json}
        for arq in sorted(cls.definicao.glob('pages/*/visuals/*/visual.json')):
            cls.visuais[(arq.parts[-4], arq.parts[-2])] = ler(arq)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_gera_sem_erro(self):
        self.assertEqual(self.codigo, 0, self.mensagem)

    def test_quatro_paginas_na_ordem_do_roteiro(self):
        meta = ler(self.definicao / 'pages' / 'pages.json')
        nomes = [ler(self.definicao / 'pages' / p / 'page.json')['displayName'] for p in meta['pageOrder']]
        self.assertEqual(nomes, PAGINAS)
        self.assertEqual(meta['activePageName'], meta['pageOrder'][0])
        pastas = sorted(p.name for p in (self.definicao / 'pages').iterdir() if p.is_dir())
        self.assertEqual(pastas, sorted(meta['pageOrder']))

    def test_todo_campo_usado_existe_no_modelo(self):
        campos = campos_do_modelo()
        self.assertIn(('Medidas', '1º quartil da faixa'), campos)   # o leitor de TMDL acha nome com aspas
        usados = 0
        for arq in self.definicao.rglob('*.json'):
            apelidos = {}
            for no in percorrer(ler(arq)):
                if 'From' in no and isinstance(no['From'], list):
                    apelidos.update({f['Name']: f['Entity'] for f in no['From']})
            for no in percorrer(ler(arq)):
                for tipo, esperado in (('Column', 'column'), ('Measure', 'measure')):
                    if tipo in no and isinstance(no[tipo], dict) and 'Property' in no[tipo]:
                        fonte = no[tipo]['Expression']['SourceRef']
                        tabela = fonte.get('Entity') or apelidos[fonte['Source']]
                        chave = (tabela, no[tipo]['Property'])
                        self.assertEqual(campos.get(chave), esperado, f'{arq.relative_to(self.saida)}: {chave}')
                        usados += 1
        self.assertGreater(usados, 50)

    # ── o que vale para todo visual ──
    def test_todo_arquivo_declara_o_esquema_oficial(self):
        for arq in [self.saida / 'definition.pbir', *self.definicao.rglob('*.json')]:
            self.assertRegex(ler(arq)['$schema'], ESQUEMA, arq)

    def test_todo_visual_tem_texto_alternativo(self):
        for chave, v in self.visuais.items():
            alt = v['visual']['visualContainerObjects']['general'][0]['properties']['altText']
            self.assertGreater(len(alt['expr']['Literal']['Value'].strip("'")), 15, chave)

    def test_ordem_de_tabulacao_unica_por_pagina(self):
        for pagina in {p for p, _ in self.visuais}:
            ordens = [v['position']['tabOrder'] for (p, _), v in self.visuais.items() if p == pagina]
            self.assertEqual(len(ordens), len(set(ordens)), pagina)

    def test_ordem_de_tabulacao_segue_o_roteiro(self):
        # município, Indicador, visual principal, cartões, tabela (powerbi/roteiro.md, "Ordem de tabulação")
        def papel(v):
            tipo = v['visual']['visualType']
            if tipo == 'slicer':
                campo = v['visual']['query']['queryState']['Values']['projections'][0]['field']['Column']
                return {'municipio': 0, 'nome': 1}.get(campo['Property'], 2)
            return {'lineChart': 3, 'scatterChart': 3, 'card': 4, 'multiRowCard': 4, 'tableEx': 5}.get(tipo)

        for pagina in ('municipio', 'comparacao', 'previsao'):
            visuais = sorted((v for (p, _), v in self.visuais.items() if p == pagina),
                             key=lambda v: v['position']['tabOrder'])
            papeis = [papel(v) for v in visuais if papel(v) is not None]
            self.assertEqual(papeis, sorted(papeis), pagina)
            self.assertEqual(visuais[0]['visual']['visualType'], 'textbox', f'{pagina}: o título vem primeiro')

    def test_titulo_da_evolucao_vem_da_medida(self):
        titulo = self.visuais[('municipio', 'p1_evolucao')]['visual']['visualContainerObjects']['title'][0]
        self.assertEqual(titulo['properties']['text']['expr']['Measure']['Property'], 'Título da evolução')

    # ── segmentações ──
    def segmentacoes(self, coluna):
        """{página: visual} das segmentações sobre (tabela, coluna)."""
        achadas = {}
        for (pagina, _), v in self.visuais.items():
            if v['visual']['visualType'] == 'slicer':
                campo = v['visual']['query']['queryState']['Values']['projections'][0]['field']['Column']
                if (campo['Expression']['SourceRef']['Entity'], campo['Property']) == coluna:
                    achadas[pagina] = v
        return achadas

    @staticmethod
    def escolhido(segmentacao):
        selecao = segmentacao['visual']['objects']['general'][0]['properties']['filter']['filter']
        valores = selecao['Where'][0]['Condition']['In']['Values']
        return [v[0]['Literal']['Value'] for v in valores]

    def test_segmentacao_de_indicador_sincronizada_nas_paginas_1_e_2(self):
        seg = self.segmentacoes(('dim_indicador', 'nome'))
        self.assertEqual(sorted(seg), ['comparacao', 'municipio'])
        grupos = {v['visual']['syncGroup']['groupName'] for v in seg.values()}
        self.assertEqual(len(grupos), 1)
        for v in seg.values():
            self.assertEqual(self.escolhido(v), ["'Despesa com saúde por habitante'"])

    def test_municipio_de_exemplo_escolhido_em_toda_pagina_com_municipio(self):
        exemplo = re.search(r'\\newcommand\{\\NumExemplo\}\{(.+)\}',REGISTRO.read_text(encoding='utf-8')).group(1)
        dim = self.segmentacoes(('dim_municipio', 'municipio'))
        solta = self.segmentacoes(('sel_municipio', 'municipio'))
        self.assertEqual(sorted(dim), ['municipio', 'previsao'])
        self.assertEqual(sorted(solta), ['comparacao'])   # a página 2 usa a cópia solta (roteiro, página 2)
        self.assertEqual(len({v['visual']['syncGroup']['groupName'] for v in dim.values()}), 1)
        for v in [*dim.values(), *solta.values()]:
            self.assertEqual(self.escolhido(v), [f"'{exemplo}'"])
            self.assertEqual(v['visual']['objects']['selection'][0]['properties']['strictSingleSelect'],
                             {'expr': {'Literal': {'Value': 'true'}}})

    # ── o que o painel não faz ──
    def test_nenhum_ranking_de_municipios_por_nome(self):
        for chave, v in self.visuais.items():
            consulta = v['visual'].get('query', {})
            ordem = [s['field'] for s in consulta.get('sortDefinition', {}).get('sort', [])]
            self.assertNotIn('municipio', [f.get('Column', {}).get('Property') for f in ordem], chave)
            nomes = [p['field'] for papel in consulta.get('queryState', {}).values() for p in papel['projections']
                     if p['field'].get('Column', {}).get('Property') == 'municipio']
            if not nomes:
                continue
            # o nome do município só entra numa segmentação ou como ponto da dispersão, e nada ordena por ele
            self.assertIn(v['visual']['visualType'], ('slicer', 'scatterChart'), chave)
            self.assertNotIn('sortDefinition', v['visual']['query'], chave)

    def tema(self):
        return ler(self.saida / 'StaticResources' / 'RegisteredResources' / 'tema-portfolio.json')

    def cor(self, no):
        """A cor que o Desktop desenha. No ThemeDataColor, os ids 0 e 1 são o fundo e a cor de texto do tema,
        e o id i + 2 é dataColors[i] (a primeira tela do Desktop mostrou isso: id 0 saía branco)."""
        tema = self.tema()
        cor = no['solid']['color']['expr']
        if 'ThemeDataColor' in cor:
            ident, clarear = cor['ThemeDataColor']['ColorId'], cor['ThemeDataColor']['Percent']
            base = [tema['background'], tema['foreground'], *tema['dataColors']][ident]
            return base, clarear
        return cor['Literal']['Value'].strip("'").upper(), 0

    def cor_da_serie(self, chave, objeto, campo):
        regras = self.visuais[chave]['visual']['objects'][objeto]
        regra = next(r for r in regras if r.get('selector', {}).get('metadata') == campo)
        return self.cor(regra['properties']['fill'])

    def test_municipio_em_vermelho_e_mediana_em_cinza(self):
        tema = self.tema()
        self.assertEqual(self.cor_da_serie(('municipio', 'p1_evolucao'), 'dataPoint', 'Medidas.Valor'),
                         (tema['dataColors'][0], 0))
        self.assertEqual(self.cor_da_serie(('municipio', 'p1_evolucao'), 'dataPoint', 'Medidas.Mediana da faixa'),
                         (tema['dataColors'][1], 0))
        self.assertEqual(self.cor_da_serie(('previsao', 'p3_previsao'), 'dataPoint', 'Medidas.Receita observada'),
                         (tema['dataColors'][0], 0))

    def test_cores_so_do_destaque_e_do_neutro(self):
        tema = self.tema()
        permitidas = {tema['dataColors'][0], tema['dataColors'][1], tema['backgroundLight'], tema['foreground']}
        for chave, v in self.visuais.items():
            for no in percorrer(v):
                if 'solid' in no and isinstance(no['solid'], dict) and 'expr' in no['solid'].get('color', {}):
                    if 'Conditional' not in no['solid']['color']['expr']:
                        self.assertIn(self.cor(no)[0], permitidas, chave)   # sem azul, verde nem "bom"
                valor = no.get('Literal', {}).get('Value', '')
                if re.fullmatch(r"'#[0-9A-Fa-f]{6}'", valor):
                    self.assertIn(valor.strip("'").upper(), permitidas, chave)

    def test_caixas_de_texto_na_fonte_do_tema(self):
        fontes = {c['fontFace'] for c in self.tema()['textClasses'].values()}
        achadas = 0
        for chave, v in self.visuais.items():
            for no in percorrer(v):
                if 'textStyle' in no:
                    self.assertIn(no['textStyle'].get('fontFamily'), fontes, chave)
                    achadas += 1
        self.assertGreater(achadas, 8)

    # ── leitura dos números ──
    def test_cartoes_mostram_o_numero_inteiro(self):
        # "11.690", e não "12 Mil": unidade de exibição "nenhuma" em todo cartão
        for chave, v in self.visuais.items():
            if v['visual']['visualType'] == 'card':
                rotulos = v['visual']['objects']['labels'][0]['properties']
                self.assertEqual(rotulos['labelDisplayUnits'], {'expr': {'Literal': {'Value': '1D'}}}, chave)

    def test_tabela_do_municipio_com_as_mesmas_casas_e_sem_total(self):
        formatos = {}
        for arq in TMDL.glob('Medidas.tmdl'):
            atual = None
            for linha in arq.read_text(encoding='utf-8').splitlines():
                m = re.match(r"^\tmeasure\s+('(?:[^']|'')+'|[^\s=]+)", linha)
                if m:
                    atual = nome_tmdl(m.group(1))
                m = re.match(r'^\t\tformatString:\s*(.+)$', linha)
                if m and atual:
                    formatos[atual] = m.group(1).strip()
        tabela = self.visuais[('municipio', 'p1_tabela')]['visual']
        colunas = {p['displayName']: p['field'] for p in tabela['query']['queryState']['Values']['projections']}
        valor, mediana = colunas['Valor'], colunas['Mediana da faixa']
        self.assertEqual(formatos.get(valor['Measure']['Property']), formatos[mediana['Measure']['Property']])
        self.assertEqual(tabela['objects']['total'][0]['properties']['totals'], {'expr': {'Literal': {'Value': 'false'}}})

    def test_tabela_dos_indicadores_cabe_sem_rolagem_lateral(self):
        v = self.visuais[('como_ler', 'p4_indicadores')]
        projecoes = v['visual']['query']['queryState']['Values']['projections']
        larguras = {r['selector']['metadata']: float(r['properties']['value']['expr']['Literal']['Value'].rstrip('D'))
                    for r in v['visual']['objects']['columnWidth']}
        self.assertEqual(set(larguras), {p['queryRef'] for p in projecoes})
        self.assertLessEqual(sum(larguras.values()), v['position']['width'] - 24)

    def test_todo_visual_cabe_na_pagina(self):
        for chave, v in self.visuais.items():
            p = v['position']
            self.assertLessEqual(p['x'] + p['width'], 1280, chave)
            self.assertLessEqual(p['y'] + p['height'], 720, chave)

    def test_tema_do_kit_registrado(self):
        relatorio = ler(self.definicao / 'report.json')
        tema = relatorio['themeCollection']['customTheme']
        self.assertEqual(tema['type'], 'RegisteredResources')
        pacote = next(p for p in relatorio['resourcePackages'] if p['type'] == 'RegisteredResources')
        item = next(i for i in pacote['items'] if i['type'] == 'CustomTheme')
        self.assertEqual(item['name'], tema['name'])
        arquivo = self.saida / 'StaticResources' / 'RegisteredResources' / item['path']
        self.assertEqual(ler(arquivo), ler(REPO / 'powerbi' / 'tema.json'))

    def test_aponta_para_o_modelo_e_apaga_o_formato_antigo(self):
        pbir = ler(self.saida / 'definition.pbir')
        self.assertEqual(pbir['datasetReference'], {'byPath': {'path': '../painel-municipios-sp.SemanticModel'}})
        self.assertFalse((self.saida / 'report.json').exists())


class TesteRegerar(unittest.TestCase):
    def test_regerar_apaga_visual_antigo_e_o_report_json_legado(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / 'painel.Report'
            (saida / 'definition' / 'pages' / 'velha' / 'visuals' / 'v').mkdir(parents=True)
            (saida / 'report.json').write_text('{}', encoding='utf-8')
            codigo, mensagem = gerar(saida)
            self.assertEqual(codigo, 0, mensagem)
            self.assertFalse((saida / 'definition' / 'pages' / 'velha').exists())
            self.assertFalse((saida / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
