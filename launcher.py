import os
import shutil
import sys
import threading
import traceback
from tkinter import messagebox
import customtkinter as ctk
import requests

USUARIO_GITHUB = "fogmogreal"
REPOSITORIO = "JFDocWeld"
BRANCH = "main"

URL_LATEST_RELEASE = f"https://api.github.com/repos/{USUARIO_GITHUB}/{REPOSITORIO}/releases/latest"
URL_VERSION = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPOSITORIO}/{BRANCH}/app/version.txt"
URL_MAIN = f"https://raw.githubusercontent.com/{USUARIO_GITHUB}/{REPOSITORIO}/{BRANCH}/app/main.py"

PASTA_LOCAL = os.path.join(
    os.getenv("LOCALAPPDATA") or os.path.expanduser("~"), "JFDocWeld"
)
ARQUIVO_VERSION = os.path.join(PASTA_LOCAL, "version.txt")
ARQUIVO_APP = os.path.join(PASTA_LOCAL, "main.py")

HEADERS_GITHUB = {
    "User-Agent": f"{REPOSITORIO}-Launcher/1.0",
    "Accept": "application/vnd.github+json",
}


def obter_recurso_embutido(nome_arquivo, subpasta_relativa=None):
    candidatos = []
    if hasattr(sys, "_MEIPASS"):
        if subpasta_relativa:
            candidatos.append(
                os.path.join(sys._MEIPASS, subpasta_relativa, nome_arquivo)
            )
        candidatos.append(os.path.join(sys._MEIPASS, nome_arquivo))

    base_script = os.path.dirname(os.path.abspath(__file__))
    if subpasta_relativa:
        candidatos.append(
            os.path.join(base_script, subpasta_relativa, nome_arquivo)
        )
    candidatos.append(os.path.join(base_script, nome_arquivo))
    candidatos.append(os.path.abspath(nome_arquivo))

    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None


class SplashAtualizador(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.overrideredirect(True)

        largura, altura = 360, 140
        pos_x = (self.winfo_screenwidth() // 2) - (largura // 2)
        pos_y = (self.winfo_screenheight() // 2) - (altura // 2)
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")

        caminho_ico = obter_recurso_embutido("jfdocweld.ico")
        if caminho_ico and os.path.exists(caminho_ico):
            self.after(100, lambda c=caminho_ico: self.iconbitmap(c))

        self.frame = ctk.CTkFrame(
            self, corner_radius=12, border_width=1, border_color="#38BDF8"
        )
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(
            self.frame,
            text="JF DocWeld",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 4))

        self.lbl_status = ctk.CTkLabel(
            self.frame,
            text="Iniciando...",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.lbl_status.pack(pady=(0, 10))

        self.barra = ctk.CTkProgressBar(
            self.frame, width=280, mode="indeterminate"
        )
        self.barra.pack(pady=(0, 18))
        self.barra.start()

        self.status_texto = "Verificando atualizações..."
        self.concluido = False

        threading.Thread(target=self._fluxo_inicializacao, daemon=True).start()
        self._monitorar_progresso()

    def _fluxo_inicializacao(self):
        try:
            os.makedirs(PASTA_LOCAL, exist_ok=True)

            if not os.path.exists(ARQUIVO_APP):
                origem_app = obter_recurso_embutido("main.py", "app")
                if origem_app:
                    shutil.copy2(origem_app, ARQUIVO_APP)

            if not os.path.exists(ARQUIVO_VERSION):
                origem_ver = obter_recurso_embutido("version.txt", "app")
                if origem_ver:
                    shutil.copy2(origem_ver, ARQUIVO_VERSION)
                else:
                    with open(ARQUIVO_VERSION, "w", encoding="utf-8") as f:
                        f.write("1.0.0")

            versao_local = "0.0.0"
            if os.path.exists(ARQUIVO_VERSION):
                with open(ARQUIVO_VERSION, "r", encoding="utf-8") as f:
                    versao_local = f.read().strip()

            try:
                resp_v = requests.get(
                    URL_VERSION, headers=HEADERS_GITHUB, timeout=3.0
                )
                if resp_v.status_code == 200:
                    versao_remota = resp_v.text.strip()
                    if versao_remota and (
                        versao_remota != versao_local
                        or not os.path.exists(ARQUIVO_APP)
                    ):
                        self.status_texto = (
                            f"Atualizando para v{versao_remota}..."
                        )
                        resp_code = requests.get(
                            URL_MAIN, headers=HEADERS_GITHUB, timeout=8.0
                        )
                        if (
                            resp_code.status_code == 200
                            and resp_code.text.strip()
                        ):
                            with open(
                                ARQUIVO_APP, "w", encoding="utf-8"
                            ) as f:
                                f.write(resp_code.text)
                            with open(
                                ARQUIVO_VERSION, "w", encoding="utf-8"
                            ) as f:
                                f.write(versao_remota)
            except Exception:
                pass

            self.status_texto = "Abrindo JF DocWeld..."
        finally:
            self.concluido = True

    def _fechar_splash(self):
        try:
            self.barra.stop()
        except Exception:
            pass
        self.quit()
        self.destroy()

    def _monitorar_progresso(self):
        if not self.winfo_exists():
            return
        self.lbl_status.configure(text=self.status_texto)
        if self.concluido:
            self.after(200, self._fechar_splash)
        else:
            self.after(100, self._monitorar_progresso)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    splash = SplashAtualizador()
    splash.mainloop()

    if not os.path.exists(ARQUIVO_APP):
        messagebox.showerror(
            "Erro de Inicialização",
            "Não foi possível localizar o arquivo principal do JF DocWeld.",
        )
        sys.exit(1)

    if PASTA_LOCAL not in sys.path:
        sys.path.insert(0, PASTA_LOCAL)

    try:
        with open(ARQUIVO_APP, "r", encoding="utf-8") as f:
            codigo = f.read()
        exec(
            compile(codigo, ARQUIVO_APP, "exec"),
            {"__name__": "__main__", "__file__": ARQUIVO_APP},
        )
    except Exception:
        messagebox.showerror(
            "Erro no JF DocWeld",
            f"Ocorreu um erro ao executar o programa:\n\n{traceback.format_exc()}",
        )