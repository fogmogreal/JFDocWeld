import gc
import os
import shutil
from shutil import which
import subprocess
import sys
import tempfile
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
from pypdf import PdfWriter

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_DISPONIVEL = True
except ImportError:
    DND_DISPONIVEL = False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BaseClass = (
    (ctk.CTk, TkinterDnD.DnDWrapper) if DND_DISPONIVEL else (ctk.CTk,)
)


class JFDocWeldApp(*BaseClass):

    def __init__(self):
        super().__init__()
        if DND_DISPONIVEL:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title("JF DocWeld — Conversor & Mesclador de Arquivos")
        self.geometry("780x685")
        self.resizable(False, False)

        # Controle de estado e threads
        self.fila_conversao = []
        self.fila_pdf = []
        self.pasta_saida = os.path.join(os.path.expanduser("~"), "Downloads")
        self.inicio_fila = 0.0
        self._ultimo_update_ui = 0.0
        self.cancelar_evento = threading.Event()

        # Sistema de Abas
        self.tabview = ctk.CTkTabview(self, width=740, height=605)
        self.tabview.pack(padx=20, pady=(12, 4))

        self.tab_converter = self.tabview.add("Conversor Universal (Fila)")
        self.tab_mesclar = self.tabview.add("Mesclar PDFs (Ordem)")

        self._construir_aba_conversao()
        self._construir_aba_mesclagem()

        # Rodapé com versão dinâmica
        versao_atual = self._obter_versao()
        self.lbl_rodape = ctk.CTkLabel(
            self,
            text=f"JF DocWeld • {versao_atual}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.lbl_rodape.pack(side="bottom", anchor="e", padx=25, pady=(0, 8))

        self._aplicar_icone()

    def _obter_versao(self):
        local_app = os.getenv("LOCALAPPDATA")
        if local_app:
            caminho_prod = os.path.join(local_app, "JFDocWeld", "version.txt")
            if os.path.exists(caminho_prod):
                with open(caminho_prod, "r", encoding="utf-8") as f:
                    return f"v{f.read().strip()}"

        if "__file__" in globals():
            caminho_dev = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "version.txt"
            )
            if os.path.exists(caminho_dev):
                with open(caminho_dev, "r", encoding="utf-8") as f:
                    return f"v{f.read().strip()}"
        return "v1.0.0"

    def _aplicar_icone(self):
        candidatos = [
            os.path.join(getattr(sys, "_MEIPASS", ""), "jfdocweld.ico"),
            os.path.abspath("jfdocweld.ico"),
        ]
        if "__file__" in globals():
            candidatos.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..",
                    "jfdocweld.ico",
                )
            )

        for caminho in candidatos:
            if caminho and os.path.exists(caminho):
                self.after(200, lambda c=caminho: self.iconbitmap(c))
                break

    def _encontrar_libreoffice(self):
        if which("soffice") is not None:
            return "soffice"
        if os.name == "nt":
            caminhos_win = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for caminho in caminhos_win:
                if os.path.exists(caminho):
                    return caminho
        return None

    def abrir_pasta_saida(self):
        caminho = os.path.normpath(self.pasta_saida)
        if not os.path.exists(caminho):
            os.makedirs(caminho, exist_ok=True)

        if os.name == "nt":
            os.startfile(caminho)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])

    # =========================================================================
    # ABA 1: CONVERSOR UNIVERSAL COM ETA, ETAPAS E CANCELAMENTO SEGURO
    # =========================================================================
    def _construir_aba_conversao(self):
        frame_top = ctk.CTkFrame(self.tab_converter)
        frame_top.pack(fill="x", padx=10, pady=8)

        ctk.CTkButton(
            frame_top,
            text="+ Adicionar Arquivos",
            command=self.adicionar_arquivos_conversao,
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkButton(
            frame_top,
            text="Limpar Fila",
            fg_color="#D9534F",
            hover_color="#C9302C",
            command=self.limpar_fila_conversao,
        ).pack(side="left", padx=5, pady=8)

        # Lista visual da fila
        self.textbox_fila = ctk.CTkTextbox(
            self.tab_converter, height=150, state="disabled"
        )
        self.textbox_fila.pack(fill="x", padx=10, pady=5)
        self._atualizar_lista_conversao()

        if DND_DISPONIVEL:
            self.textbox_fila.drop_target_register(DND_FILES)
            self.textbox_fila.dnd_bind("<<Drop>>", self._ao_soltar_conversao)

        # Configurações (Formato e Pasta de Saída)
        frame_config = ctk.CTkFrame(self.tab_converter)
        frame_config.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frame_config, text="Converter para:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )

        self.formatos_disponiveis = [
            "PDF (de DOCX, XLSX, PPTX, Imagem)",
            "DOCX (de PDF)",
            "PNG (de Imagem ou PDF)",
            "JPG (de Imagem ou PDF)",
            "WEBP (de Imagem ou PDF)",
            "MP3 (de Vídeo ou Áudio)",
            "MP4 (de Vídeo ou GIF)",
            "GIF (de Vídeo MP4)",
        ]
        self.combo_formato = ctk.CTkComboBox(
            frame_config, values=self.formatos_disponiveis, width=280
        )
        self.combo_formato.grid(row=0, column=1, padx=10, pady=8, sticky="w")
        self.combo_formato.set(self.formatos_disponiveis[0])

        ctk.CTkLabel(frame_config, text="Pasta de Saída:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        self.lbl_saida = ctk.CTkLabel(
            frame_config, text=self.pasta_saida, text_color="gray"
        )
        self.lbl_saida.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkButton(
            frame_config,
            text="Alterar Pasta",
            width=120,
            command=self.escolher_pasta_saida,
        ).grid(row=1, column=2, padx=10, pady=8)

        # Painel de Progresso Duplo + Previsão de Tempo (ETA)
        frame_prog = ctk.CTkFrame(self.tab_converter)
        frame_prog.pack(fill="x", padx=10, pady=6)

        frame_info_prog = ctk.CTkFrame(frame_prog, fg_color="transparent")
        frame_info_prog.pack(fill="x", padx=12, pady=(8, 2))

        self.lbl_etapa_arquivo = ctk.CTkLabel(
            frame_info_prog,
            text="Etapa: Aguardando arquivos...",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_etapa_arquivo.pack(side="left")

        self.lbl_eta = ctk.CTkLabel(
            frame_info_prog,
            text="Tempo estimado: --",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38BDF8",
        )
        self.lbl_eta.pack(side="right")

        self.progress_arquivo = ctk.CTkProgressBar(frame_prog, width=685)
        self.progress_arquivo.pack(padx=12, pady=(2, 8))
        self.progress_arquivo.set(0)

        self.lbl_status_conv = ctk.CTkLabel(
            frame_prog,
            text="Fila geral: 0 de 0 concluídos",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.lbl_status_conv.pack(anchor="w", padx=12, pady=(0, 2))

        self.progress_conv = ctk.CTkProgressBar(
            frame_prog, width=685, progress_color="#28A745"
        )
        self.progress_conv.pack(padx=12, pady=(0, 10))
        self.progress_conv.set(0)

        # Botões de Ação (Iniciar, Cancelar e Abrir Pasta)
        frame_acoes = ctk.CTkFrame(self.tab_converter, fg_color="transparent")
        frame_acoes.pack(pady=8)

        self.btn_iniciar_conv = ctk.CTkButton(
            frame_acoes,
            text="INICIAR CONVERSÃO EM LOTE",
            width=250,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#28A745",
            hover_color="#218838",
            command=self.iniciar_thread_conversao,
        )
        self.btn_iniciar_conv.pack(side="left", padx=6)

        self.btn_cancelar_conv = ctk.CTkButton(
            frame_acoes,
            text="CANCELAR",
            width=130,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#D9534F",
            hover_color="#C9302C",
            state="disabled",
            command=self.cancelar_conversao,
        )
        self.btn_cancelar_conv.pack(side="left", padx=6)

        self.btn_abrir_pasta = ctk.CTkButton(
            frame_acoes,
            text="Abrir Pasta de Saída",
            width=175,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1F6AA5",
            hover_color="#144870",
            command=self.abrir_pasta_saida,
        )

    def _ao_soltar_conversao(self, event):
        arquivos = self.tk.splitlist(event.data)
        adicionados = 0
        for arq in arquivos:
            if os.path.isfile(arq) and arq not in self.fila_conversao:
                self.fila_conversao.append(arq)
                adicionados += 1
        if adicionados > 0:
            self._atualizar_lista_conversao()

    def adicionar_arquivos_conversao(self):
        arquivos = filedialog.askopenfilenames(
            title="Selecione os arquivos para converter"
        )
        if arquivos:
            for arq in arquivos:
                if arq not in self.fila_conversao:
                    self.fila_conversao.append(arq)
            self._atualizar_lista_conversao()

    def limpar_fila_conversao(self):
        self.fila_conversao.clear()
        self._atualizar_lista_conversao()
        self.progress_arquivo.set(0)
        self.progress_conv.set(0)
        self.lbl_etapa_arquivo.configure(text="Etapa: Fila limpa.")
        self.lbl_eta.configure(text="Tempo estimado: --")
        self.btn_abrir_pasta.pack_forget()

    def _atualizar_lista_conversao(self):
        self.textbox_fila.configure(state="normal")
        self.textbox_fila.delete("1.0", "end")
        if not self.fila_conversao:
            self.textbox_fila.insert(
                "end",
                "Arraste e solte seus arquivos aqui ou clique em '+ Adicionar Arquivos'...",
            )
        else:
            for idx, arq in enumerate(self.fila_conversao, 1):
                self.textbox_fila.insert(
                    "end", f"{idx}. {os.path.basename(arq)}\n"
                )
        self.textbox_fila.configure(state="disabled")
        if hasattr(self, "lbl_status_conv"):
            self.lbl_status_conv.configure(
                text=f"Fila geral: 0 de {len(self.fila_conversao)} arquivo(s) na fila."
            )

    def escolher_pasta_saida(self):
        pasta = filedialog.askdirectory(title="Escolha onde salvar os arquivos")
        if pasta:
            self.pasta_saida = pasta
            self.lbl_saida.configure(text=self.pasta_saida)

    def iniciar_thread_conversao(self):
        if not self.fila_conversao:
            messagebox.showwarning(
                "Aviso", "Adicione pelo menos um arquivo na fila!"
            )
            return
        self.cancelar_evento.clear()
        self.btn_abrir_pasta.pack_forget()
        self.btn_iniciar_conv.configure(state="disabled")
        self.btn_cancelar_conv.configure(state="normal", text="CANCELAR")
        self.inicio_fila = time.time()
        self._ultimo_update_ui = 0.0
        threading.Thread(target=self.processar_conversoes, daemon=True).start()

    def cancelar_conversao(self):
        self.cancelar_evento.set()
        self.btn_cancelar_conv.configure(
            state="disabled", text="Cancelando..."
        )
        self.lbl_etapa_arquivo.configure(
            text="Interrompendo e limpando arquivo atual..."
        )

    def _formatar_tempo(self, segundos):
        segundos = int(max(0, segundos))
        if segundos < 60:
            return f"~{segundos}s restantes"
        minutos, seg = divmod(segundos, 60)
        if minutos < 60:
            return f"~{minutos}m {seg:02d}s restantes"
        horas, minutos = divmod(minutos, 60)
        return f"~{horas}h {minutos:02d}m restantes"

    def _reportar_etapa(
        self, idx_arquivo, total_arquivos, pct_arquivo, texto_etapa, nome_arq
    ):
        agora = time.time()
        if pct_arquivo < 1.0 and (agora - self._ultimo_update_ui) < 0.25:
            return
        self._ultimo_update_ui = agora

        pct_fila = (idx_arquivo + pct_arquivo) / total_arquivos
        decorrido = agora - self.inicio_fila

        if pct_fila >= 0.04 and decorrido >= 1.5:
            total_estimado = decorrido / pct_fila
            restante = total_estimado - decorrido
            texto_eta = self._formatar_tempo(restante)
        else:
            texto_eta = "Calculando tempo..."

        nome_curto = (
            nome_arq if len(nome_arq) <= 28 else nome_arq[:25] + "..."
        )

        def _atualizar_ui():
            self.lbl_etapa_arquivo.configure(
                text=f"{nome_curto} → {texto_etapa}"
            )
            self.lbl_eta.configure(text=texto_eta)
            self.progress_arquivo.set(pct_arquivo)
            self.lbl_status_conv.configure(
                text=f"Fila geral: Arquivo {idx_arquivo + 1} de {total_arquivos} ({int(pct_fila * 100)}%)"
            )
            self.progress_conv.set(pct_fila)

        self.after(0, _atualizar_ui)

    def _remover_arquivos_incompletos(self, caminhos):
        for caminho in caminhos:
            if caminho and os.path.exists(caminho):
                try:
                    os.remove(caminho)
                except OSError:
                    pass

    def processar_conversoes(self):
        total = len(self.fila_conversao)
        formato_escolhido = self.combo_formato.get().split(" ")[0]
        erros = []
        avisos = []
        cancelado = False

        for i, caminho_entrada in enumerate(self.fila_conversao):
            if self.cancelar_evento.is_set():
                cancelado = True
                break

            nome_arq = os.path.basename(caminho_entrada)
            nome_base = os.path.splitext(nome_arq)[0]
            ext_origem = os.path.splitext(caminho_entrada)[1].lower()

            def reportar(pct, etapa, idx=i, nome=nome_arq):
                if self.cancelar_evento.is_set():
                    raise InterruptedError("Cancelado pelo usuário.")
                self._reportar_etapa(idx, total, pct, etapa, nome)

            try:
                reportar(0.05, "Preparando arquivo...")
                self._executar_conversao_individual(
                    caminho_entrada,
                    nome_arq,
                    nome_base,
                    ext_origem,
                    formato_escolhido,
                    reportar,
                    avisos,
                )
                reportar(1.0, "Concluído!")
            except InterruptedError:
                cancelado = True
                break
            except Exception as e:
                erros.append(f"{nome_arq}: {str(e)}")
            finally:
                gc.collect()

        tempo_total_gasto = int(time.time() - self.inicio_fila)

        def _finalizar_ui():
            self.btn_iniciar_conv.configure(state="normal")
            self.btn_cancelar_conv.configure(state="disabled", text="CANCELAR")

            if cancelado:
                self.lbl_etapa_arquivo.configure(
                    text="Etapa: Conversão cancelada pelo usuário."
                )
                self.lbl_eta.configure(text="Cancelado")
                messagebox.showinfo(
                    "Cancelado",
                    "A fila foi interrompida com segurança e os arquivos incompletos foram removidos.",
                )
                return

            self.btn_abrir_pasta.pack(side="left", padx=6)
            self.lbl_etapa_arquivo.configure(
                text="Etapa: Processamento finalizado!"
            )
            self.lbl_eta.configure(text=f"Concluído em {tempo_total_gasto}s")
            self.lbl_status_conv.configure(
                text=f"Fila geral: {total} de {total} arquivo(s) concluído(s)."
            )

            if erros:
                messagebox.showwarning(
                    "Concluído com avisos",
                    "Alguns arquivos falharam:\n\n" + "\n".join(erros),
                )
            elif avisos:
                messagebox.showinfo(
                    "Concluído com observações",
                    f"Conversão finalizada em {tempo_total_gasto}s!\n\nObservações:\n"
                    + "\n".join(avisos),
                )
            else:
                messagebox.showinfo(
                    "Sucesso!",
                    f"Todos os {total} arquivos foram convertidos em {tempo_total_gasto}s!\nSalvos em: {self.pasta_saida}",
                )

        self.after(0, _finalizar_ui)

    def _converter_pdf_para_docx(
        self, entrada, saida, nome_arq, reportar, avisos
    ):
        import fitz

        doc_check = fitz.open(entrada)
        try:
            total_pags = len(doc_check)
            if total_pags == 0:
                raise RuntimeError("O arquivo PDF está vazio.")
            texto_amostra = ""
            for p in range(min(3, total_pags)):
                texto_amostra += doc_check[p].get_text().strip()
        finally:
            doc_check.close()

        if not texto_amostra:
            avisos.append(
                f"• {nome_arq}: PDF escaneado (sem texto selecionável); páginas inseridas como imagem no Word."
            )

        reportar(0.25, f"Convertendo {total_pags} página(s) para Word...")

        # Nível 1: pdf2docx padrão (sem parâmetro 'ocr' inválido)
        try:
            from pdf2docx import Converter

            cv = Converter(entrada)
            try:
                cv.convert(saida, multi_processing=False)
            finally:
                cv.close()
            if os.path.exists(saida) and os.path.getsize(saida) > 0:
                return
        except Exception:
            pass

        # Nível 2: LibreOffice (se estiver instalado no PC)
        soffice_bin = self._encontrar_libreoffice()
        if soffice_bin:
            reportar(0.55, "Usando motor alternativo (LibreOffice)...")
            pasta_temp_lo = tempfile.mkdtemp(prefix="jfdocweld_lo_")
            try:
                cmd = [
                    soffice_bin,
                    "--headless",
                    "--infilter=writer_pdf_import",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    pasta_temp_lo,
                    entrada,
                ]
                creation_flags = (
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                proc = subprocess.run(cmd, creationflags=creation_flags)
                gerado_lo = os.path.join(
                    pasta_temp_lo,
                    os.path.splitext(os.path.basename(entrada))[0] + ".docx",
                )
                if (
                    proc.returncode == 0
                    and os.path.exists(gerado_lo)
                    and os.path.getsize(gerado_lo) > 0
                ):
                    shutil.move(gerado_lo, saida)
                    return
            finally:
                shutil.rmtree(pasta_temp_lo, ignore_errors=True)

        # Nível 3: Motor nativo embutido (PyMuPDF + python-docx preservando estilos e imagens)
        reportar(0.70, "Montando documento Word (motor nativo)...")
        import docx
        from docx.shared import Inches, Pt, RGBColor

        documento = docx.Document()
        secao = documento.sections[0]
        secao.top_margin = Inches(0.6)
        secao.bottom_margin = Inches(0.6)
        secao.left_margin = Inches(0.6)
        secao.right_margin = Inches(0.6)

        largura_util = (
            secao.page_width - secao.left_margin - secao.right_margin
        ) / 914400
        altura_util = (
            secao.page_height - secao.top_margin - secao.bottom_margin
        ) / 914400

        doc_pdf = fitz.open(entrada)
        try:
            matriz = fitz.Matrix(200 / 72, 200 / 72)
            for idx_pag in range(total_pags):
                pct = 0.70 + (0.25 * (idx_pag + 1) / total_pags)
                reportar(
                    pct,
                    f"Montando página {idx_pag + 1} de {total_pags} no Word...",
                )
                pagina = doc_pdf.load_page(idx_pag)
                dados_pag = pagina.get_text("dict")
                blocos = sorted(
                    dados_pag.get("blocks", []),
                    key=lambda b: (
                        round(b.get("bbox", [0, 0, 0, 0])[1], 1),
                        round(b.get("bbox", [0, 0, 0, 0])[0], 1),
                    ),
                )

                tem_conteudo = False
                for bloco in blocos:
                    if bloco.get("type") == 0:  # Bloco de texto estruturado
                        linhas_validas = [
                            ln
                            for ln in bloco.get("lines", [])
                            if "".join(
                                str(sp.get("text", ""))
                                for sp in ln.get("spans", [])
                            ).strip()
                        ]
                        if not linhas_validas:
                            continue

                        tem_conteudo = True
                        p = documento.add_paragraph()
                        p.paragraph_format.space_after = Pt(6)

                        for idx_ln, linha in enumerate(linhas_validas):
                            if idx_ln > 0:
                                p.add_run(" ")
                            for span in linha.get("spans", []):
                                txt = str(span.get("text", ""))
                                if not txt:
                                    continue
                                run = p.add_run(txt)
                                tam = span.get("size", 11)
                                if isinstance(tam, (int, float)) and 6 <= tam <= 72:
                                    run.font.size = Pt(round(float(tam), 1))
                                flags = span.get("flags", 0) or 0
                                run.bold = bool(flags & 16)
                                run.italic = bool(flags & 2)
                                cor_int = span.get("color", 0)
                                if isinstance(cor_int, int) and cor_int > 0:
                                    r = (cor_int >> 16) & 255
                                    g = (cor_int >> 8) & 255
                                    b_col = cor_int & 255
                                    if (r, g, b_col) != (255, 255, 255):
                                        run.font.color.rgb = RGBColor(
                                            r, g, b_col
                                        )

                    elif bloco.get("type") == 1 and bloco.get("image"):
                        tem_conteudo = True
                        ext_img = str(bloco.get("ext") or "png").strip(".")
                        fd, caminho_tmp = tempfile.mkstemp(
                            suffix=f".{ext_img}"
                        )
                        os.close(fd)
                        try:
                            with open(caminho_tmp, "wb") as f_img:
                                f_img.write(bloco["image"])
                            bbox = bloco.get("bbox", [0, 0, 200, 200])
                            largura_pt = max(20.0, float(bbox[2]) - float(bbox[0]))
                            largura_pol = min(largura_util, largura_pt / 72.0)
                            documento.add_picture(
                                caminho_tmp, width=Inches(largura_pol)
                            )
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(caminho_tmp):
                                try:
                                    os.remove(caminho_tmp)
                                except OSError:
                                    pass

                # Página escaneada ou sem blocos de texto/imagem reconhecidos
                if not tem_conteudo:
                    pix = pagina.get_pixmap(matrix=matriz, alpha=False)
                    fd, caminho_tmp = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    try:
                        pix.save(caminho_tmp)
                        proporcao_img = pix.height / max(1, pix.width)
                        proporcao_pag = altura_util / max(0.1, largura_util)
                        if proporcao_img > proporcao_pag:
                            documento.add_picture(
                                caminho_tmp, height=Inches(altura_util)
                            )
                        else:
                            documento.add_picture(
                                caminho_tmp, width=Inches(largura_util)
                            )
                    finally:
                        pix = None
                        if os.path.exists(caminho_tmp):
                            try:
                                os.remove(caminho_tmp)
                            except OSError:
                                pass

                if idx_pag < total_pags - 1:
                    documento.add_page_break()
        finally:
            doc_pdf.close()

        documento.save(saida)

    def _executar_conversao_individual(
        self, entrada, nome_arq, nome_base, ext_origem, destino, reportar, avisos
    ):
        arquivos_gerados = []
        try:
            # 1. PDF -> IMAGEM (PNG, JPG, WEBP via PyMuPDF em 200 DPI)
            if ext_origem == ".pdf" and destino in ["PNG", "JPG", "WEBP"]:
                import fitz

                doc = fitz.open(entrada)
                try:
                    total_pags = len(doc)
                    if total_pags == 0:
                        raise RuntimeError("O arquivo PDF está vazio.")

                    ext_final = "jpg" if destino == "JPG" else destino.lower()
                    matriz = fitz.Matrix(200 / 72, 200 / 72)

                    for num_pag in range(total_pags):
                        pct = (num_pag + 0.5) / total_pags
                        reportar(
                            pct,
                            f"Renderizando página {num_pag + 1} de {total_pags}...",
                        )

                        pagina = doc.load_page(num_pag)
                        pix = pagina.get_pixmap(matrix=matriz, alpha=False)

                        if total_pags == 1:
                            nome_saida = f"{nome_base}.{ext_final}"
                        else:
                            nome_saida = (
                                f"{nome_base}_pag_{num_pag + 1:02d}.{ext_final}"
                            )

                        caminho_pag = os.path.join(self.pasta_saida, nome_saida)
                        arquivos_gerados.append(caminho_pag)

                        if destino == "JPG":
                            img_temp = Image.frombytes(
                                "RGB", [pix.width, pix.height], pix.samples
                            )
                            img_temp.save(
                                caminho_pag, quality=95, subsampling=0
                            )
                            img_temp.close()
                        elif destino == "WEBP":
                            img_temp = Image.frombytes(
                                "RGB", [pix.width, pix.height], pix.samples
                            )
                            img_temp.save(caminho_pag, quality=92)
                            img_temp.close()
                        else:
                            pix.save(caminho_pag)

                        pix = None
                finally:
                    doc.close()

            # 2. PDF -> DOCX (Pipeline resiliente de 3 níveis)
            elif destino == "DOCX" and ext_origem == ".pdf":
                saida = os.path.join(self.pasta_saida, f"{nome_base}.docx")
                arquivos_gerados.append(saida)
                self._converter_pdf_para_docx(
                    entrada, saida, nome_arq, reportar, avisos
                )
                reportar(0.96, "Finalizando DOCX...")

            # 3. IMAGENS -> PNG, JPG, WEBP, PDF
            elif ext_origem in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
                reportar(0.25, "Etapa 1/3: Lendo imagem...")
                with Image.open(entrada) as img:
                    if destino in ["JPG", "PDF"] and img.mode in ("RGBA", "P"):
                        reportar(0.55, "Etapa 2/3: Ajustando perfil de cores...")
                        img_final = img.convert("RGB")
                    else:
                        reportar(
                            0.55, "Etapa 2/3: Preparando qualidade máxima..."
                        )
                        img_final = img.copy()

                    ext_final = "jpg" if destino == "JPG" else destino.lower()
                    saida = os.path.join(
                        self.pasta_saida, f"{nome_base}.{ext_final}"
                    )
                    arquivos_gerados.append(saida)

                    reportar(0.85, f"Etapa 3/3: Gravando {destino}...")
                    if destino == "JPG":
                        img_final.save(saida, quality=98, subsampling=0)
                    elif destino == "PDF":
                        img_final.save(saida, resolution=300.0)
                    else:
                        img_final.save(saida)

            # 4. OFFICE -> PDF (LibreOffice Headless)
            elif destino == "PDF" and ext_origem in [
                ".docx",
                ".doc",
                ".xlsx",
                ".xls",
                ".pptx",
                ".ppt",
            ]:
                reportar(0.20, "Etapa 1/3: Iniciando LibreOffice...")
                saida = os.path.join(self.pasta_saida, f"{nome_base}.pdf")
                arquivos_gerados.append(saida)

                soffice_bin = self._encontrar_libreoffice()
                if not soffice_bin:
                    raise RuntimeError(
                        "LibreOffice não encontrado no computador."
                    )

                cmd = [
                    soffice_bin,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    self.pasta_saida,
                    entrada,
                ]

                reportar(0.55, "Etapa 2/3: Convertendo páginas...")
                creation_flags = (
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                proc = subprocess.Popen(cmd, creationflags=creation_flags)
                while proc.poll() is None:
                    if self.cancelar_evento.is_set():
                        proc.terminate()
                        proc.wait(timeout=3)
                        raise InterruptedError("Cancelado pelo usuário.")
                    time.sleep(0.2)

                if proc.returncode != 0:
                    raise RuntimeError("Falha ao converter documento Office.")
                reportar(0.95, "Etapa 3/3: Finalizando PDF...")

            # 5. ÁUDIO E VÍDEO -> MP3, MP4, GIF
            elif ext_origem in [
                ".mp4",
                ".mkv",
                ".avi",
                ".mov",
                ".gif",
                ".mp3",
                ".wav",
            ]:
                from moviepy import AudioFileClip, VideoFileClip
                from proglog import ProgressBarLogger

                class LoggerLeve(ProgressBarLogger):

                    def bars_callback(self, bar, attr, value, old_value=None):
                        total = self.bars[bar].get("total", 0)
                        if total > 0:
                            pct = min(value / total, 1.0)
                            etapa = (
                                "Codificando áudio"
                                if bar == "chunk"
                                else "Renderizando quadros"
                            )
                            reportar(pct, f"{etapa} ({int(pct * 100)}%)")

                saida = os.path.join(
                    self.pasta_saida, f"{nome_base}.{destino.lower()}"
                )
                arquivos_gerados.append(saida)
                logger_real = LoggerLeve()

                if destino == "MP3":
                    if ext_origem in [".mp3", ".wav"]:
                        clip = AudioFileClip(entrada)
                        try:
                            clip.write_audiofile(
                                saida, bitrate="320k", logger=logger_real
                            )
                        finally:
                            clip.close()
                    else:
                        video = VideoFileClip(entrada)
                        try:
                            video.audio.write_audiofile(
                                saida, bitrate="320k", logger=logger_real
                            )
                        finally:
                            video.close()
                elif destino == "GIF":
                    video = VideoFileClip(entrada)
                    try:
                        video.write_gif(saida, fps=15, logger=logger_real)
                    finally:
                        video.close()
                elif destino == "MP4":
                    video = VideoFileClip(entrada)
                    try:
                        video.write_videofile(
                            saida,
                            codec="libx264",
                            audio_codec="aac",
                            preset="faster",
                            logger=logger_real,
                        )
                    finally:
                        video.close()
            else:
                raise ValueError(
                    f"Conversão de {ext_origem} para {destino} não suportada."
                )

        except InterruptedError:
            self._remover_arquivos_incompletos(arquivos_gerados)
            raise

    # =========================================================================
    # ABA 2: MESCLAGEM DE PDF COM ORDEM DE PRIORIDADE
    # =========================================================================
    def _construir_aba_mesclagem(self):
        frame_top = ctk.CTkFrame(self.tab_mesclar)
        frame_top.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            frame_top,
            text="+ Adicionar PDFs",
            command=self.adicionar_pdfs_mesclagem,
        ).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(
            frame_top,
            text="Limpar Lista",
            fg_color="#D9534F",
            hover_color="#C9302C",
            command=self.limpar_lista_pdf,
        ).pack(side="left", padx=5, pady=10)

        frame_meio = ctk.CTkFrame(self.tab_mesclar)
        frame_meio.pack(fill="both", expand=True, padx=10, pady=5)

        self.listbox_pdf = ctk.CTkScrollableFrame(
            frame_meio,
            width=520,
            height=265,
            label_text="Ordem de Colagem (Arraste PDFs ou use + Adicionar)",
        )
        self.listbox_pdf.pack(
            side="left", fill="both", expand=True, padx=10, pady=10
        )

        if DND_DISPONIVEL:
            for alvo in (self.listbox_pdf, self.listbox_pdf._parent_canvas):
                alvo.drop_target_register(DND_FILES)
                alvo.dnd_bind("<<Drop>>", self._ao_soltar_pdf)

        self.selecionado_idx = None

        frame_ordem = ctk.CTkFrame(frame_meio)
        frame_ordem.pack(side="right", fill="y", padx=10, pady=10)

        ctk.CTkLabel(
            frame_ordem, text="Prioridade", font=ctk.CTkFont(weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(
            frame_ordem, text="▲ Subir", width=110, command=self.mover_pdf_cima
        ).pack(pady=5, padx=10)
        ctk.CTkButton(
            frame_ordem,
            text="▼ Descer",
            width=110,
            command=self.mover_pdf_baixo,
        ).pack(pady=5, padx=10)
        ctk.CTkButton(
            frame_ordem,
            text="✕ Remover",
            width=110,
            fg_color="#D9534F",
            command=self.remover_pdf_selecionado,
        ).pack(pady=20, padx=10)

        frame_bot = ctk.CTkFrame(self.tab_mesclar)
        frame_bot.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_bot, text="Nome do PDF Final:").pack(
            side="left", padx=10, pady=15
        )
        self.entry_nome_mesclado = ctk.CTkEntry(
            frame_bot, placeholder_text="Ex: Documento_Completo", width=230
        )
        self.entry_nome_mesclado.pack(side="left", padx=5, pady=15)

        ctk.CTkButton(
            frame_bot,
            text="MESCLAR PDFs AGORA",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#28A745",
            hover_color="#218838",
            command=self.mesclar_pdfs,
        ).pack(side="right", padx=15, pady=15)

    def _ao_soltar_pdf(self, event):
        arquivos = self.tk.splitlist(event.data)
        adicionados = 0
        for arq in arquivos:
            if os.path.isfile(arq) and arq.lower().endswith(".pdf"):
                self.fila_pdf.append(arq)
                adicionados += 1
        if adicionados > 0:
            self._renderizar_lista_pdf()
        else:
            messagebox.showwarning(
                "Formato inválido",
                "Solte apenas arquivos PDF na aba de mesclagem.",
            )

    def adicionar_pdfs_mesclagem(self):
        arquivos = filedialog.askopenfilenames(
            title="Selecione os PDFs", filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if arquivos:
            for arq in arquivos:
                self.fila_pdf.append(arq)
            self._renderizar_lista_pdf()

    def _renderizar_lista_pdf(self):
        for widget in self.listbox_pdf.winfo_children():
            widget.destroy()

        for idx, caminho in enumerate(self.fila_pdf):
            cor = (
                "#1F6AA5" if idx == self.selecionado_idx else "transparent"
            )
            btn = ctk.CTkButton(
                self.listbox_pdf,
                text=f"{idx + 1}º  |  {os.path.basename(caminho)}",
                anchor="w",
                fg_color=cor,
                text_color=("black", "white"),
                command=lambda i=idx: self._selecionar_item_pdf(i),
            )
            btn.pack(fill="x", pady=2)

    def _selecionar_item_pdf(self, idx):
        self.selecionado_idx = idx
        self._renderizar_lista_pdf()

    def mover_pdf_cima(self):
        idx = self.selecionado_idx
        if idx is not None and idx > 0:
            self.fila_pdf[idx], self.fila_pdf[idx - 1] = (
                self.fila_pdf[idx - 1],
                self.fila_pdf[idx],
            )
            self.selecionado_idx -= 1
            self._renderizar_lista_pdf()

    def mover_pdf_baixo(self):
        idx = self.selecionado_idx
        if idx is not None and idx < len(self.fila_pdf) - 1:
            self.fila_pdf[idx], self.fila_pdf[idx + 1] = (
                self.fila_pdf[idx + 1],
                self.fila_pdf[idx],
            )
            self.selecionado_idx += 1
            self._renderizar_lista_pdf()

    def remover_pdf_selecionado(self):
        idx = self.selecionado_idx
        if idx is not None:
            self.fila_pdf.pop(idx)
            self.selecionado_idx = None
            self._renderizar_lista_pdf()

    def limpar_lista_pdf(self):
        self.fila_pdf.clear()
        self.selecionado_idx = None
        self._renderizar_lista_pdf()

    def mesclar_pdfs(self):
        if len(self.fila_pdf) < 2:
            messagebox.showwarning(
                "Aviso", "Adicione pelo menos 2 arquivos PDF para mesclar!"
            )
            return

        nome_saida = self.entry_nome_mesclado.get().strip() or "PDF_Mesclado"
        if not nome_saida.lower().endswith(".pdf"):
            nome_saida += ".pdf"

        caminho_final = os.path.join(self.pasta_saida, nome_saida)

        try:
            merger = PdfWriter()
            for pdf in self.fila_pdf:
                merger.append(pdf)
            merger.write(caminho_final)
            merger.close()
            gc.collect()
            if messagebox.askyesno(
                "Mesclagem Concluída!",
                f"Os {len(self.fila_pdf)} PDFs foram unidos na ordem exata!\n\nSalvo em:\n{caminho_final}\n\nDeseja abrir a pasta agora?",
            ):
                self.abrir_pasta_saida()
        except Exception as e:
            messagebox.showerror("Erro ao mesclar", f"Ocorreu um erro: {str(e)}")


if __name__ == "__main__":
    app = JFDocWeldApp()
    app.mainloop()