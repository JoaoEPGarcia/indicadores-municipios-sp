"""Apoio dos testes: uma cópia do repositório numa pasta temporária, para rodar por fora um script que grava
dentro do repositório (scripts/numeros.py) ou para tirar dele um arquivo, sem mexer nos arquivos versionados."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class Copia:
    """Os arquivos do repositório (versionados e novos ainda não versionados, sem os ignorados), copiados."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        arquivos = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=REPO,
                                  capture_output=True, check=True).stdout.decode('utf-8').split('\0')
        for rel in filter(None, arquivos):
            origem = REPO / rel
            if origem.is_file():
                destino = self.raiz / rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origem, destino)

    def rodar(self, script, *args):
        """Roda scripts/<script> da cópia; devolve (código de saída, saída)."""
        r = subprocess.run([sys.executable, '-X', 'utf8', str(self.raiz / 'scripts' / script), *map(str, args)],
                           cwd=self.raiz, capture_output=True, text=True, encoding='utf-8')
        return r.returncode, r.stdout + r.stderr

    def ler(self, rel):
        return (self.raiz / rel).read_text(encoding='utf-8')

    def fechar(self):
        self._tmp.cleanup()
