"""Confere as medidas DAX do painel contra powerbi/conferencia.md, rodando-as no modelo aberto no Power BI Desktop.

    python scripts/conferir_powerbi.py              # as células de conferencia.md
    python scripts/conferir_powerbi.py --completo   # e também Valor, Mediana e Posição de todos os municípios, contra o SQLite

Antes: abra powerbi/painel-municipios-sp.pbip no Power BI Desktop e espere a atualização dos dados terminar.
O Desktop sobe um Analysis Services local numa porta que muda a cada abertura; o script acha a porta no
arquivo msmdsrv.port.txt da pasta de workspaces e manda as consultas DAX para lá.

Para falar com esse servidor o script usa a biblioteca ADOMD.NET, pelo pythonnet. Ela vem dentro do
Power BI Desktop (Microsoft.PowerBI.AdomdClient.dll, na pasta bin); no Desktop da Microsoft Store o script
pede ao Windows a pasta do pacote. Se mesmo assim não achar, instale o ADOMD.NET (pacote
"Microsoft.AnalysisServices.AdomdClient") e aponte a variável de ambiente ADOMD_DLL para a DLL. Sem ADOMD, o script tenta o provedor OLE DB MSOLAP (pywin32).

Saídas (versionadas, porque os números do README e do relatório saem delas):
  powerbi/resultado_conferencia.csv           uma linha por célula conferida
  powerbi/resultado_conferencia_completa.csv  com --completo: uma linha por medida, com o total e as divergências
Sai com código 1 se alguma célula não bater.
"""
import argparse
import csv
import glob
import math
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFERENCIA = RAIZ / 'powerbi' / 'conferencia.md'
SAIDA = RAIZ / 'powerbi' / 'resultado_conferencia.csv'
SAIDA_COMPLETA = RAIZ / 'powerbi' / 'resultado_conferencia_completa.csv'
SQLITE = RAIZ / 'dados' / 'tratados' / 'amostra.sqlite'

# Colunas da tabela de cada município em conferencia.md → medida DAX
COLUNAS_INDICADOR = {
    '`[Valor]` 2023': 'Valor',
    '`[Mediana da faixa]`': 'Mediana da faixa',
    '`[1º quartil da faixa]`': '1º quartil da faixa',
    '`[3º quartil da faixa]`': '3º quartil da faixa',
    '`[Diferença para a mediana]`': 'Diferença para a mediana',
    '`[Posição na faixa]`': 'Posição na faixa',
    'Municípios na faixa com dado': 'Municípios com dado na faixa',
}
COLUNAS_PREVISAO = {
    '`[Receita prevista]`': 'Receita prevista',
    '`[Limite inferior 80%]`': 'Limite inferior 80%',
    '`[Limite superior 80%]`': 'Limite superior 80%',
}


# ── leitura de conferencia.md ────────────────────────────────────────────
def numero_br(texto):
    """'−22,42%' → (-0.2242, 4 casas); '5176,4883' → (5176.4883, 4); '123' → (123.0, 0)."""
    t = texto.strip().replace('−', '-').replace('.', '')
    pct = t.endswith('%')
    t = t.rstrip('%').replace(',', '.')
    casas = len(t.split('.')[1]) if '.' in t else 0
    v = float(t)
    if pct:
        return v / 100, casas + 2
    return v, casas


def linhas_tabela(bloco):
    return [[c.strip() for c in l.strip().strip('|').split('|')] for l in bloco if l.strip().startswith('|')]


def ler_conferencia():
    """Devolve a lista de células: dict(municipio, indicador, ano, medida, esperado, casas)."""
    texto = CONFERENCIA.read_text(encoding='utf-8')
    ano_ref = int(re.search(r'\[Valor\]` (\d{4})', texto).group(1))
    celulas = []
    for secao in re.split(r'^## ', texto, flags=re.M)[1:]:
        municipio = secao.splitlines()[0].strip()
        tabelas = re.split(r'\n\s*\n', secao)
        for t in tabelas:
            linhas = linhas_tabela(t.splitlines())
            if len(linhas) < 3:
                continue
            cab, corpo = linhas[0], linhas[2:]
            if cab[0] == 'Indicador':
                for l in corpo:
                    for col, valor in zip(cab[1:], l[1:]):
                        if col in COLUNAS_INDICADOR:
                            v, casas = numero_br(valor)
                            celulas.append(dict(municipio=municipio, indicador=l[0], ano=ano_ref,
                                                medida=COLUNAS_INDICADOR[col], esperado=v, casas=casas))
            elif cab[0] == 'Ano':
                for l in corpo:
                    for col, valor in zip(cab[1:], l[1:]):
                        if col in COLUNAS_PREVISAO:
                            v, casas = numero_br(valor)
                            celulas.append(dict(municipio=municipio, indicador='receita_total', ano=int(l[0]),
                                                medida=COLUNAS_PREVISAO[col], esperado=v, casas=casas))
    return celulas


# ── conexão com o Analysis Services do Power BI Desktop ──────────────────
def achar_porta():
    padroes = [
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt'),
        os.path.expandvars(r'%USERPROFILE%\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt'),
    ]
    arquivos = [a for p in padroes for a in glob.glob(p)]
    if not arquivos:
        sys.exit('Nenhum Power BI Desktop aberto: abra powerbi/painel-municipios-sp.pbip e rode de novo.')
    mais_novo = max(arquivos, key=os.path.getmtime)
    if len(arquivos) > 1:
        print(f'  [aviso] {len(arquivos)} instâncias do Desktop abertas; usando a mais recente ({mais_novo}).')
    bruto = Path(mais_novo).read_bytes()
    texto = bruto.decode('utf-16') if bruto[:2] in (b'\xff\xfe', b'\xfe\xff') or b'\x00' in bruto else bruto.decode()
    return int(texto.strip().strip('\ufeff'))


def pasta_desktop_da_store():
    """Pasta de instalação do Desktop da Microsoft Store. A pasta WindowsApps não deixa listar o conteúdo
    (então o glob não a acha), mas a pasta do pacote se lê quando se sabe o nome, que o Windows informa."""
    try:
        saida = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '(Get-AppxPackage -Name Microsoft.MicrosoftPowerBIDesktop).InstallLocation'],
            capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return saida.splitlines()[0] if saida else None


def achar_adomd():
    candidatos = [os.environ.get('ADOMD_DLL', '')]
    candidatos += glob.glob(r'C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll')
    store = pasta_desktop_da_store()
    if store:
        candidatos.append(os.path.join(store, 'bin', 'Microsoft.PowerBI.AdomdClient.dll'))
    candidatos += glob.glob(r'C:\Windows\Microsoft.NET\assembly\GAC_MSIL\Microsoft.AnalysisServices.AdomdClient\*\Microsoft.AnalysisServices.AdomdClient.dll')
    return next((c for c in candidatos if c and os.path.exists(c)), None)


class Servidor:
    def __init__(self, porta):
        self.fonte = f'localhost:{porta}'
        dll = achar_adomd()
        if dll:
            import clr  # pythonnet
            clr.AddReference(dll)
            import System
            from Microsoft.AnalysisServices.AdomdClient import AdomdConnection
            self._System = System
            self.con = AdomdConnection(f'Data Source={self.fonte}')
            self.con.Open()
            self.modo = f'ADOMD ({os.path.basename(dll)})'
        else:
            import win32com.client
            self.con = win32com.client.Dispatch('ADODB.Connection')
            self.con.Open(f'Provider=MSOLAP;Data Source={self.fonte};')
            self.modo = 'OLE DB (MSOLAP)'

    def _num(self, v):
        if v is None:
            return None
        if hasattr(self, '_System'):
            if isinstance(v, self._System.DBNull):
                return None
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                return v
            return float(self._System.Convert.ToDouble(v))
        return float(v) if isinstance(v, (int, float)) else v

    def consultar(self, dax):
        """Devolve (colunas, linhas) de uma consulta DAX."""
        if self.modo.startswith('ADOMD'):
            cmd = self.con.CreateCommand()
            cmd.CommandText = dax
            leitor = cmd.ExecuteReader()
            cols = [leitor.GetName(i) for i in range(leitor.FieldCount)]
            linhas = []
            while leitor.Read():
                linhas.append([self._num(leitor.GetValue(i)) for i in range(leitor.FieldCount)])
            leitor.Close()
            return cols, linhas
        import win32com.client
        rs = win32com.client.Dispatch('ADODB.Recordset')
        rs.Open(dax, self.con)
        cols = [rs.Fields.Item(i).Name for i in range(rs.Fields.Count)]
        linhas = []
        while not rs.EOF:
            linhas.append([self._num(rs.Fields.Item(i).Value) for i in range(rs.Fields.Count)])
            rs.MoveNext()
        rs.Close()
        return cols, linhas


def texto_dax(s):
    return '"' + s.replace('"', '""') + '"'


def medir(srv, municipio, indicador, ano, medidas):
    colunas = ', '.join(f'{texto_dax(m)}, [{m}]' for m in medidas)
    dax = (f'EVALUATE CALCULATETABLE ( ROW ( {colunas} ), '
           f'dim_municipio[municipio] = {texto_dax(municipio)}, dim_ano[ano] = {ano}, '
           f'dim_indicador[indicador_id] = {texto_dax(indicador)} )')
    _, linhas = srv.consultar(dax)
    return dict(zip(medidas, linhas[0])) if linhas else {}


def bate(esperado, obtido, casas):
    if obtido is None or isinstance(obtido, str):
        return False
    return abs(obtido - esperado) <= 0.5 * 10 ** (-casas) + 1e-9


# ── conferência ampla, contra o SQLite ───────────────────────────────────
def conferir_completo(srv):
    con = sqlite3.connect(SQLITE)
    esperado = {}
    for cod, ano, ind, v, med, pos in con.execute(
            'SELECT f.cod_ibge, f.ano, f.indicador_id, f.valor, r.mediana, p.posicao_na_faixa / 100.0 '
            'FROM fato_indicador f JOIN dim_municipio d ON d.cod_ibge = f.cod_ibge '
            'JOIN ref_faixa r ON r.faixa_porte = d.faixa_porte AND r.ano = f.ano AND r.indicador_id = f.indicador_id '
            'JOIN v_posicao p ON p.cod_ibge = f.cod_ibge AND p.ano = f.ano AND p.indicador_id = f.indicador_id'):
        esperado[(cod, ano, ind)] = (v, med, pos)
    dax = ('EVALUATE FILTER ( ADDCOLUMNS ( CROSSJOIN ( VALUES ( dim_municipio[cod_ibge] ), VALUES ( dim_ano[ano] ), '
           'VALUES ( dim_indicador[indicador_id] ) ), "v", [Valor], "m", [Mediana da faixa], "p", [Posição na faixa] ), '
           'NOT ISBLANK ( [v] ) )')
    _, linhas = srv.consultar(dax)
    obtido = {(int(c), int(a), i): (v, m, p) for c, a, i, v, m, p in linhas}
    resumo = []
    for k, nome in enumerate(['Valor', 'Mediana da faixa', 'Posição na faixa']):
        chaves = set(esperado) | set(obtido)
        diverg = []
        for ch in chaves:
            e = esperado.get(ch, (None,) * 3)[k]
            o = obtido.get(ch, (None,) * 3)[k]
            if e is None or o is None:
                if e is not o:
                    diverg.append(ch)
            elif not math.isclose(e, o, rel_tol=1e-9, abs_tol=1e-9):
                diverg.append(ch)
        resumo.append(dict(medida=nome, celulas=len(chaves), divergentes=len(diverg),
                           exemplo_divergente=' '.join(map(str, sorted(diverg)[0])) if diverg else ''))
        print(f'  [{"OK" if not diverg else "ERRO"}] {nome}: {len(chaves) - len(diverg)} de {len(chaves)} células iguais ao SQLite')
    with open(SAIDA_COMPLETA, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(resumo[0]))
        w.writeheader()
        w.writerows(resumo)
    return all(r['divergentes'] == 0 for r in resumo)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--completo', action='store_true', help='confere também todos os municípios e anos contra o SQLite')
    args = ap.parse_args()

    celulas = ler_conferencia()
    srv = Servidor(achar_porta())
    print(f'Conectado a {srv.fonte} por {srv.modo}. {len(celulas)} células em conferencia.md.')

    grupos = {}
    for c in celulas:
        grupos.setdefault((c['municipio'], c['indicador'], c['ano']), []).append(c)
    for (mun, ind, ano), cs in grupos.items():
        res = medir(srv, mun, ind, ano, sorted({c['medida'] for c in cs}))
        for c in cs:
            c['obtido'] = res.get(c['medida'])
            c['bate'] = bate(c['esperado'], c['obtido'], c['casas'])

    erradas = [c for c in celulas if not c['bate']]
    for c in erradas:
        print(f"  [ERRO] {c['municipio']} | {c['indicador']} | {c['ano']} | [{c['medida']}]: "
              f"esperado {c['esperado']}, obtido {c['obtido']}")
    with open(SAIDA, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['municipio', 'indicador', 'ano', 'medida', 'esperado', 'obtido', 'casas', 'bate'])
        w.writeheader()
        for c in celulas:
            w.writerow({**c, 'bate': int(c['bate'])})
    print(f'{len(celulas) - len(erradas)} de {len(celulas)} células batem. Gravado {SAIDA.relative_to(RAIZ)}.')

    ok = not erradas
    if args.completo:
        ok = conferir_completo(srv) and ok
        print(f'Gravado {SAIDA_COMPLETA.relative_to(RAIZ)}.')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
