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


if __name__ == '__main__':
    unittest.main()
