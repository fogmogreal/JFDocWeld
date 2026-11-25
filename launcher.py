import os
import re
import subprocess
import sys
import tempfile
import traceback
from tkinter import Tk, messagebox
import requests

USUARIO_GITHUB = "fogmogreal"
REPOSITORIO = "JFDocWeld"
BRANCH = "main"

URL_LATEST_RELEASE = f"https://api.github.com/repos/{USUARIO_GITHUB}/{REPOSITORIO}/releases/latest"
URL_VERSION = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPOSITORIO}/{BRANCH}/app/version.txt"
URL_MAIN = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPOSITORIO}/{BRANCH}/app/main.py"

PASTA_LOCAL = os.path.join(
    os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "JFDocWeld"
)
ARQUIVO_VERSION_LOCAL = os.path.join(PASTA_LOCAL, "version.txt")
ARQUIVO_MAIN_LOCAL = os.path.join(PASTA_LOCAL, "main.py")
ARQUIVO_RELEASE_IGNORADA = os.path.join(PASTA_LOCAL, "release_instalada.txt")

HEADERS_GITHUB = {
    "User-Agent": f"{REPOSITORIO}-Launcher/1.0",
    "Accept": "application/vnd.github+json",
}


def _normalizar_versao(texto):
    if not texto:
        return (0,)
    numeros = re.findall(r"\d+", texto.strip())
    if not numeros:
        return (0,)
    return tuple(int(n) for n in numeros)


def obter_versao_local():
    if os.path.exists(ARQUIVO_VERSION_LOCAL):
        with open(ARQUIVO_VERSION_LOCAL, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "0.0.0"


def obter_versao_release_local():
    if os.path.exists(ARQUIVO_RELEASE_IGNORADA):
        with open(ARQUIVO_RELEASE_IGNORADA, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def salvar_versao_release_local(tag):
    os.makedirs(PASTA_LOCAL, exist_ok=True)
    with open(ARQUIVO_RELEASE_IGNORADA, "w", encoding="utf-8") as f:
        f.write(tag.strip())


def _baixar_arquivo(url, destino, timeout=60):
    with requests.get(
        url, headers=HEADERS_GITHUB, stream=True, timeout=timeout
    ) as resp:
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)


def verificar_novo_instalador():
    """Consulta a última Release no GitHub e oferece baixar/executar Setup_JFDocWeld.exe."""
    try:
        resp = requests.get(
            URL_LATEST_RELEASE, headers=HEADERS_GITHUB, timeout=6
        )
        if resp.status_code != 200:
            return False

        dados = resp.json()
        tag_remota = (dados.get("tag_name") or "").strip()
        if not tag_remota:
            return False

        versao_atual_ref = obter_versao_release_local() or obter_versao_local()
        if _normalizar_versao(tag_remota) <= _normalizar_versao(
            versao_atual_ref
        ):
            return False

        # Procura o anexo Setup_JFDocWeld.exe na release
        url_setup = None
        for asset in dados.get("assets", []):
            nome_asset = (asset.get("name") or "").lower()
            if nome_asset == "setup_jfdocweld.exe" or (
                nome_asset.endswith(".exe") and "setup" in nome_asset
            ):
                url_setup = asset.get("browser_download_url")
                break

        if not url_setup:
            return False

        root = Tk()
        root.withdraw()
        try:
            quer_baixar = messagebox.askyesno(
                "Nova versão disponível — JF DocWeld",
                f"Uma nova versão ({tag_remota}) está disponível nas Releases do GitHub.\n\n"
                "Deseja baixar e executar o instalador Setup_JFDocWeld.exe agora?\n"
                "(O programa será fechado para concluir a atualização.)",
            )
            if not quer_baixar:
                salvar_versao_release_local(tag_remota)
                return False

            caminho_setup = os.path.join(
                tempfile.gettempdir(), f"Setup_JFDocWeld_{tag_remota}.exe"
            )
            _baixar_arquivo(url_setup, caminho_setup, timeout=120)

            if not os.path.exists(caminho_setup) or os.path.getsize(caminho_setup) == 0:
                messagebox.showerror(
                    "Erro no download",
                    "O arquivo Setup_JFDocWeld.exe foi baixado vazio ou incompleto.",
                )
                return False

            salvar_versao_release_local(tag_remota)
            subprocess.Popen([caminho_setup], close_fds=True)
            return True
        finally:
            root.destroy()

    except Exception:
        # Sem internet ou rate-limit da API: não bloqueia a abertura do app
        return False


def sincronizar_atualizacao():
    os.makedirs(PASTA_LOCAL, exist_ok=True)
    versao_local = obter_versao_local()

    try:
        resp_ver = requests.get(URL_VERSION, headers=HEADERS_GITHUB, timeout=5)
        if resp_ver.status_code == 200:
            versao_remota = resp_ver.text.strip()
            precisa_baixar = (
                versao_remota != versao_local
                or not os.path.exists(ARQUIVO_MAIN_LOCAL)
            )
            if precisa_baixar:
                resp_code = requests.get(
                    URL_MAIN, headers=HEADERS_GITHUB, timeout=15
                )
                if resp_code.status_code == 200 and resp_code.text.strip():
                    with open(ARQUIVO_MAIN_LOCAL, "w", encoding="utf-8") as f:
                        f.write(resp_code.text)
                    with open(
                        ARQUIVO_VERSION_LOCAL, "w", encoding="utf-8"
                    ) as f:
                        f.write(versao_remota)
    except Exception:
        pass

    if not os.path.exists(ARQUIVO_MAIN_LOCAL):
        caminho_dev = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "app", "main.py"
        )
        if os.path.exists(caminho_dev):
            return caminho_dev

    return ARQUIVO_MAIN_LOCAL


def iniciar_aplicacao():
    # 1. Verifica se há novo Setup_JFDocWeld.exe nas Releases
    if verificar_novo_instalador():
        sys.exit(0)

    # 2. Sincroniza o app/main.py mais recente
    caminho_execucao = sincronizar_atualizacao()
    if not os.path.exists(caminho_execucao):
        messagebox.showerror(
            "Erro de Inicialização",
            "Não foi possível baixar o JF DocWeld. Verifique sua conexão com a internet e tente novamente.",
        )
        sys.exit(1)

    pasta_app = os.path.dirname(caminho_execucao)
    if pasta_app not in sys.path:
        sys.path.insert(0, pasta_app)

    try:
        with open(caminho_execucao, "r", encoding="utf-8") as f:
            codigo = f.read()
        contexto_execucao = {
            "__name__": "__main__",
            "__file__": caminho_execucao,
        }
        exec(compile(codigo, caminho_execucao, "exec"), contexto_execucao)
    except Exception:
        messagebox.showerror(
            "Erro no JF DocWeld",
            f"Ocorreu um erro ao iniciar o programa:\n\n{traceback.format_exc()}",
        )


if __name__ == "__main__":
    iniciar_aplicacao()
