"""Leitor do modelo semântico em TMDL (powerbi/painel-municipios-sp.SemanticModel/definition/).

Um leitor só para o que os scripts tiram do modelo: as tabelas, as relações, as medidas (com a pasta de
exibição e a expressão DAX) e os nomes dos métodos de previsão. scripts/numeros.py conta e cita; o gerador
das páginas (scripts/gerar_relatorio_pbi.py) usa os nomes dos métodos.
"""
import re
from dataclasses import dataclass

import comum

PASTA = comum.RAIZ / 'powerbi' / 'painel-municipios-sp.SemanticModel' / 'definition'

# Papel e grão de cada tabela do modelo estrela, o CSV que ela lê (dim_ano é calculada no modelo) e a macro do
# registro com o número de linhas dela. scripts/relatorio_gerados.py confere os papéis contra as relações do TMDL.
TABELAS_MODELO = [
    ('fato_indicador', 'fato', 'município, ano e Indicador', 'indicadores_longo.csv', 'NumLinhasFato'),
    ('ref_faixa', 'fato', 'Faixa de porte, ano e Indicador', 'referencia_faixa.csv', 'NumLinhasRefFaixa'),
    ('previsao', 'fato', 'município e ano previsto', 'previsao_receita_total.csv', 'NumLinhasPrevisao'),
    ('dim_municipio', 'dimensão', 'município', 'dim_municipio.csv', 'NumMunicipios'),
    ('dim_indicador', 'dimensão', 'Indicador', 'dim_indicador.csv', 'NumIndicadores'),
    ('dim_ano', 'dimensão', 'ano', None, 'NumLinhasDimAno'),
]


@dataclass
class Medida:
    nome: str
    tabela: str
    pasta: str | None       # pasta de exibição, sem o número de ordem ("2. Faixa" → "Faixa")
    inicio: str             # o que vem depois do "=" na linha da medida (vazio se a expressão começa embaixo)
    linhas: list            # as linhas da expressão abaixo da primeira, sem o recuo do TMDL

    def dax(self):
        """A expressão como o relatório a mostra: sem os comentários de linha e com dois espaços de recuo."""
        corpo = [l.replace('\t', '  ') for l in self.linhas if l.strip() and not l.strip().startswith('--')]
        return '\n'.join([f'{self.nome} ={self.inicio}'.rstrip()] + ['  ' + l for l in corpo])


@dataclass
class Modelo:
    tabelas: dict           # {nome do arquivo sem .tmdl: texto}
    relacoes: list          # [(tabela do lado "muitos", tabela do lado "um")]
    medidas: list           # [Medida], na ordem dos arquivos

    def medida(self, nome):
        return next(m for m in self.medidas if m.nome == nome)

    def pastas(self):
        """{pasta de exibição: [nomes das medidas]}, na ordem do TMDL."""
        pastas = {}
        for m in self.medidas:
            if m.pasta:
                pastas.setdefault(m.pasta, []).append(m.nome)
        return pastas

    def nomes_dos_metodos(self):
        """{código do método: nome legível}, da coluna metodo_nome que o Power Query de backtest_metodos cria."""
        return dict(re.findall(r'\[metodo\] = "(\w+)" then "([^"]+)"', self.tabelas['backtest_metodos']))


def _medidas(tabela, texto):
    medidas = []
    for bloco in re.split(r'(?=^\tmeasure )', texto, flags=re.M)[1:]:
        cab = re.match(r"\tmeasure (?:'([^']+)'|(\S+)) =(.*)\n((?:\t\t\t.*\n|[ \t]*\n)*)", bloco)
        pasta = re.search(r'^\t\tdisplayFolder: (?:\d+\.\s*)?(.+)$', bloco, re.M)
        medidas.append(Medida(nome=cab.group(1) or cab.group(2), tabela=tabela,
                              pasta=pasta.group(1).strip() if pasta else None, inicio=cab.group(3),
                              linhas=[l[3:] for l in cab.group(4).splitlines()]))
    return medidas


def ler(pasta=PASTA):
    tabelas = {p.stem: p.read_text(encoding='utf-8') for p in sorted((pasta / 'tables').glob('*.tmdl'))}
    rel = (pasta / 'relationships.tmdl').read_text(encoding='utf-8')
    relacoes = re.findall(r'fromColumn: (\w+)\.\w+\s+toColumn: (\w+)\.\w+', rel)
    medidas = [m for nome, texto in tabelas.items() for m in _medidas(nome, texto)]
    return Modelo(tabelas, relacoes, medidas)
