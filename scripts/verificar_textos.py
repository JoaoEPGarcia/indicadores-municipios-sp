"""Verificador dos textos entregues: diz se o README, o relatório e o PDF estão prontos para mostrar.

    python scripts/verificar_textos.py

Roda na raiz do repositório. Sai com código 0 quando tudo passa e 1 quando algo falha; cada falha
aponta o arquivo, a linha e o trecho. Quando o modelo do README, o relatório ou o PDF ainda não
existem, a verificação correspondente é pulada e o comando diz isso.
"""
import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

MODELO_README = 'docs/README.modelo.md'
RELATORIO_TEX = 'relatorio/relatorio.tex'
RELATORIO_PDF = 'relatorio/relatorio.pdf'


class Verificacao:
    """Junta o resultado de cada conferência, no formato de scripts/validar.py."""

    def __init__(self):
        self.linhas, self.falhas = [], 0

    def ok(self, nome):
        self.linhas.append(f'[OK] {nome}')

    def pulada(self, nome, motivo):
        self.linhas.append(f'[PULADA] {nome}: {motivo}')

    def falha(self, nome, problemas):
        self.falhas += len(problemas)
        self.linhas.append(f'[FALHA] {nome}')
        self.linhas += [f'    {p}' for p in problemas]


# ── número digitado ─────────────────────────────────────────────────────
def apagar(texto, padrao, flags=0):
    """Troca cada trecho que casa com o padrão por espaços do mesmo tamanho, mantendo as quebras de
    linha: assim a posição de cada caractere que sobra, e a linha dele, não mudam."""
    return re.sub(padrao, lambda m: re.sub(r'[^\n]', ' ', m.group(0)), texto, flags=flags)


def linha_de(texto, pos):
    return texto.count('\n', 0, pos) + 1


def numeros_digitados(texto):
    """(linha, trecho) de cada número que sobra fora de marcador."""
    limpo = apagar(texto, r'\{\{[^}]*\}\}')
    achados = []
    for m in re.finditer(r'\d+(?:[.,]\d+)*', limpo):
        n = linha_de(limpo, m.start())
        achados.append((n, texto.splitlines()[n - 1].strip()))
    return achados


def conferir_digitados(v, raiz, caminho):
    texto = (raiz / caminho).read_text(encoding='utf-8')
    achados = numeros_digitados(texto)
    nome = f'nenhum número digitado em {caminho}'
    if achados:
        v.falha(nome, [f'{caminho}:{n}: número digitado fora de marcador: {trecho}' for n, trecho in achados])
    else:
        v.ok(nome)


# ── a verificação ───────────────────────────────────────────────────────
def verificar(raiz):
    v = Verificacao()
    if (raiz / MODELO_README).exists():
        conferir_digitados(v, raiz, MODELO_README)
    else:
        v.pulada('modelo do README', f'{MODELO_README} ainda não existe')
    if not (raiz / RELATORIO_TEX).exists():
        v.pulada('compilação do relatório', f'{RELATORIO_TEX} ainda não existe')
    if not (raiz / RELATORIO_PDF).exists():
        v.pulada('texto do PDF', f'{RELATORIO_PDF} ainda não existe')
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--raiz', type=Path, default=RAIZ, help='raiz do repositório (padrão: a deste script)')
    raiz = ap.parse_args().raiz.resolve()
    v = verificar(raiz)
    print('\n'.join(v.linhas))
    if v.falhas:
        print(f'\n{v.falhas} problema(s). Os textos não estão prontos.')
        sys.exit(1)
    print('\nTudo certo.')


if __name__ == '__main__':
    main()
