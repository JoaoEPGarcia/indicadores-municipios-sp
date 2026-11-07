"""Onde fica cada coisa na planilha: as abas e as células que scripts/montar_excel.py escreve, que
scripts/conferir_excel.py lê e que scripts/numeros.py cita no relatório. Mudar uma posição aqui muda os três;
o passo a passo escrito à mão (excel/PASSO_A_PASSO.md) cita as mesmas células e se atualiza à mão.
"""
from xlsxwriter.utility import xl_cell_to_rowcol

ARQUIVO = 'painel-municipios-sp.xlsx'        # em excel/
# Marca da planilha de referência: o construtor grava ORIGEM no nome definido NOME_ORIGEM.
ORIGEM = 'scripts/montar_excel.py'
NOME_ORIGEM = 'OrigemDaPlanilha'

PAINEL, PREVISAO, EXPLORAR = 'Painel', 'Previsão', 'Explorar'

# Painel: o município escolhido e o que as fórmulas trazem dele
MUNICIPIO = 'C4'           # escolhido na lista
CODIGO = 'C5'              # código IBGE
FAIXA = 'C6'               # Faixa de porte
MUNICIPIOS_NA_FAIXA = 'C7'
INDICADOR_GRAFICO = 'C24'  # Indicador do gráfico, escolhido na lista
ID_INDICADOR_GRAFICO = 'D24'

# Painel: a tabela dos Indicadores, uma linha por Indicador a partir de LINHA_TABELA. A coluna A guarda o
# código do Indicador, B e C o nome e a unidade; de D a H, o que o conferidor compara com o SQLite.
LINHA_TABELA = 13
COLUNAS_TABELA = {'ano': 'D', 'valor': 'E', 'mediana': 'F', 'diferenca': 'G', 'posicao': 'H'}
LINHA_DADOS_GRAFICO = 46   # anos do gráfico do Painel; as séries vêm logo abaixo

# Previsão: um ano por linha a partir de LINHA_PREVISAO. As colunas previstas têm o nome da coluna do CSV.
LINHA_PREVISAO = 8
COLUNA_ANO = 'B'
COLUNA_OBSERVADA = 'C'
COLUNAS_PREVISTAS = {'previsto': 'D', 'inferior_80': 'E', 'superior_80': 'F', 'inferior_95': 'G', 'superior_95': 'H'}
ULTIMO_OBSERVADO = 'D4'
ULTIMO_PREVISTO = 'D5'

# Explorar: o canto da tabela dinâmica; a área a partir da linha dele fica vazia
CANTO_DINAMICA = 'D8'
LINHA_DINAMICA = xl_cell_to_rowcol(CANTO_DINAMICA)[0] + 1


def celula_tabela(campo, k=0):
    """A célula do campo na linha do k-ésimo Indicador da tabela do Painel: celula_tabela('valor') → 'E13'."""
    return f'{COLUNAS_TABELA[campo]}{LINHA_TABELA + k}'


def fixa(celula, aba=None):
    """Referência absoluta, como as fórmulas a usam: fixa('C4') → '$C$4'; fixa('C5', 'Painel') → 'Painel!$C$5'."""
    letras = celula.rstrip('0123456789')
    return (f'{aba}!' if aba else '') + f'${letras}${celula[len(letras):]}'
