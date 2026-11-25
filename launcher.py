import os
import shutil
import sys
import threading
import customtkinter as ctk
import requests

# ==============================================================================
URL_VERSAO = "https://raw.githubusercontent.com/fogmogreal/JFDocWeld/refs/heads/main/app/version.txt"
URL_CODIGO = "https://raw.githubusercontent.com/fogmogreal/JFDocWeld/refs/heads/main/app/main.py"
# ==============================================================================

PASTA_LOCAL = os.path.join(os.getenv("LOCALAPPDATA"), "JFDocWeld")
ARQUIVO_VERSAO = os.path.join(PASTA_LOCAL, "version.txt")
ARQUIVO_APP = os.path.join(PASTA_LOCAL, "main.py")


def obter_recurso_embutido(nome_arquivo):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, nome_arquivo)
    if os.path.exists(os.path.abspath(nome_arquivo)):
        return os.path.abspath(nome_arquivo)
    return os.path.join(os.path.abspath("app"), nome_arquivo)


class SplashAtualizador(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.overrideredirect(True)

        largura, altura = 360, 140
        pos_x = (self.winfo_screenwidth() // 2) - (largura // 2)
        pos_y = (self.winfo_screenheight() // 2) - (altura // 2)
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")

        caminho_ico = obter_recurso_embutido("jfdocweld.ico")
        if os.path.exists(caminho_ico):
            self.after(100, lambda: self.iconbitmap(caminho_ico))

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
        os.makedirs(PASTA_LOCAL, exist_ok=True)
        if not os.path.exists(ARQUIVO_APP):
            shutil.copy2(obter_recurso_embutido("main.py"), ARQUIVO_APP)
        if not os.path.exists(ARQUIVO_VERSAO):
            shutil.copy2(obter_recurso_embutido("version.txt"), ARQUIVO_VERSAO)

        with open(ARQUIVO_VERSAO, "r", encoding="utf-8") as f:
            versao_local = f.read().strip()

        try:
            resp_v = requests.get(URL_VERSAO, timeout=2.5)
            if resp_v.status_code == 200:
                versao_remota = resp_v.text.strip()
                if versao_remota != versao_local:
                    self.status_texto = f"Atualizando para v{versao_remota}..."
                    resp_code = requests.get(URL_CODIGO, timeout=6)
                    if resp_code.status_code == 200:
                        with open(ARQUIVO_APP, "w", encoding="utf-8") as f:
                            f.write(resp_code.text)
                        with open(ARQUIVO_VERSAO, "w", encoding="utf-8") as f:
                            f.write(versao_remota)
        except Exception:
            pass

        self.status_texto = "Abrindo JF DocWeld..."
        self.concluido = True

    def _monitorar_progresso(self):
        self.lbl_status.configure(text=self.status_texto)
        if self.concluido:
            self.barra.stop()
            self.after(200, self.destroy)
        else:
            self.after(100, self._monitorar_progresso)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    splash = SplashAtualizador()
    splash.mainloop()

    with open(ARQUIVO_APP, encoding="utf-8") as f:
        exec(f.read(), {"__name__": "__main__"})