import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from services.sgih_service import SGIHService


# ---------------------------------------------------------------------------
# Paleta de cores e constantes visuais
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#eef1f6",
    "surface": "#ffffff",
    "primary": "#2563eb",
    "primary_dark": "#1e3a8a",
    "success": "#15803d",
    "danger": "#b91c1c",
    "warning": "#b45309",
    "muted": "#64748b",
    "border": "#d8dee8",
    "header_bg": "#111827",
    "row_even": "#f3f6fb",
    "row_odd": "#ffffff",
}
FONTE = "Segoe UI"


def formatar_moeda(valor):
    """Formata um número no padrão monetário brasileiro: R$ 1.234,56"""
    try:
        texto = f"R$ {float(valor):,.2f}"
    except (TypeError, ValueError):
        return f"R$ {valor}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


class SGIHApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SGIH - Sistema de Gestão de Inventário e Helpdesk de Ativos de TI")
        self.geometry("1200x720")
        self.minsize(1040, 640)
        self.configure(bg=COLORS["bg"])

        # Caches locais usados pelos filtros de busca e combos dependentes
        self._dados_colab = []
        self._dados_ativos = []
        self._lista_ativos_raw = []
        self._dados_licencas = []
        self._dados_chamados = []
        self._dados_om = []

        self.map_setores = {}
        self.map_cat_ativo = {}
        self.map_fornecedores = {}
        self.map_ativos = {}
        self.map_colabs = {}
        self.map_sol = {}
        self.map_cat_chamado = {}
        self.map_ativos_chamado = {}
        self.map_tec = {}
        self.map_om_ativos = {}

        self._configurar_estilo()
        self._construir_menu()
        self._construir_cabecalho()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(10, 0))

        self._build_tab_dashboard()
        self._build_tab_cadastros()
        self._build_tab_inventario()
        self._build_tab_movimentacao()
        self._build_tab_helpdesk()
        self._build_tab_manutencao()

        self._construir_barra_status()

        self.bind_all("<Control-r>", lambda e: self.atualizar_tudo())
        self._centralizar()

        self.atualizar_tudo()

    # ------------------------------------------------------------------
    # Infraestrutura visual
    # ------------------------------------------------------------------
    def _centralizar(self):
        self.update_idletasks()
        largura, altura = 1200, 720
        tela_l, tela_a = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (tela_l - largura) // 2, max((tela_a - altura) // 3, 0)
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def _configurar_estilo(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", font=(FONTE, 10), background=COLORS["bg"])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground="#1f2937")
        style.configure("TLabelframe", background=COLORS["bg"], bordercolor=COLORS["border"])
        style.configure("TLabelframe.Label", background=COLORS["bg"], font=(FONTE, 10, "bold"),
                        foreground=COLORS["primary_dark"])

        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", font=(FONTE, 10, "bold"), padding=(14, 9))
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["surface"])],
                  foreground=[("selected", COLORS["primary_dark"])])

        style.configure("TButton", font=(FONTE, 9, "bold"), padding=(10, 6))
        style.configure("Primary.TButton", foreground="white", background=COLORS["primary"])
        style.map("Primary.TButton", background=[("active", COLORS["primary_dark"])])
        style.configure("Danger.TButton", foreground="white", background=COLORS["danger"])
        style.map("Danger.TButton", background=[("active", "#7f1d1d")])

        style.configure("Treeview", font=(FONTE, 9), rowheight=25,
                        background=COLORS["surface"], fieldbackground=COLORS["surface"])
        style.configure("Treeview.Heading", font=(FONTE, 9, "bold"),
                        background=COLORS["header_bg"], foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[("active", COLORS["primary_dark"])])
        style.map("Treeview", background=[("selected", COLORS["primary"])],
                  foreground=[("selected", "white")])

    def _construir_menu(self):
        menubar = tk.Menu(self)

        arquivo = tk.Menu(menubar, tearoff=0)
        arquivo.add_command(label="Atualizar Tudo        Ctrl+R", command=self.atualizar_tudo)
        arquivo.add_command(label="Exportar Relatório CSV", command=self.exportar_csv)
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.destroy)
        menubar.add_cascade(label="Arquivo", menu=arquivo)

        ajuda = tk.Menu(menubar, tearoff=0)
        ajuda.add_command(label="Sobre o SGIH", command=self._sobre)
        menubar.add_cascade(label="Ajuda", menu=ajuda)

        self.config(menu=menubar)

    def _sobre(self):
        messagebox.showinfo(
            "Sobre o SGIH",
            "SGIH — Sistema de Gestão de Inventário e Helpdesk de Ativos de TI\n\n"
            "Controle centralizado de colaboradores, ativos, licenças, "
            "chamados de suporte e ordens de manutenção.",
        )

    def _construir_cabecalho(self):
        header = tk.Frame(self, bg=COLORS["header_bg"], height=54)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="🖥  SGIH", bg=COLORS["header_bg"], fg="white",
                 font=(FONTE, 15, "bold")).pack(side="left", padx=(18, 8))
        tk.Label(header, text="Sistema de Gestão de Inventário e Helpdesk de Ativos de TI",
                 bg=COLORS["header_bg"], fg="#9ca3af", font=(FONTE, 10)).pack(side="left")

    def _construir_barra_status(self):
        barra = tk.Frame(self, bg=COLORS["header_bg"], height=26)
        barra.pack(fill="x", side="bottom")
        self.lbl_status = tk.Label(barra, text="Pronto.", bg=COLORS["header_bg"], fg="white",
                                   font=(FONTE, 8), anchor="w")
        self.lbl_status.pack(side="left", padx=10)
        self.lbl_hora = tk.Label(barra, text="", bg=COLORS["header_bg"], fg="#9ca3af", font=(FONTE, 8))
        self.lbl_hora.pack(side="right", padx=10)

    def definir_status(self, mensagem, tipo="info"):
        cores = {"info": "white", "ok": "#4ade80", "erro": "#f87171"}
        self.lbl_status.config(text=mensagem, fg=cores.get(tipo, "white"))
        self.lbl_hora.config(text=datetime.now().strftime("Atualizado às %H:%M:%S"))

    # ------------------------------------------------------------------
    # Auxiliares genéricos (tabelas, combos, validação)
    # ------------------------------------------------------------------
    def _criar_tree(self, parent, colunas, larguras, altura=10):
        """Cria um Treeview com scrollbar vertical e cabeçalhos ordenáveis por clique."""
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=colunas, show="headings", height=altura)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        for i, col in enumerate(colunas):
            tree.heading(col, text=col, command=lambda c=col, t=tree: self._ordenar_coluna(t, c, False))
            tree.column(col, width=larguras[i] if i < len(larguras) else 120, anchor="w")
        tree.tag_configure("par", background=COLORS["row_even"])
        tree.tag_configure("impar", background=COLORS["row_odd"])
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return frame, tree

    def _ordenar_coluna(self, tree, coluna, decrescente):
        dados = [(tree.set(item, coluna), item) for item in tree.get_children("")]

        def chave(par):
            texto = par[0].replace("R$", "").strip()
            texto_num = texto.replace(".", "").replace(",", ".")
            try:
                return (0, float(texto_num))
            except ValueError:
                return (1, par[0].lower())

        dados.sort(key=chave, reverse=decrescente)
        for indice, (_, item) in enumerate(dados):
            tree.move(item, "", indice)
            tags = [t for t in tree.item(item, "tags") if t not in ("par", "impar")]
            tags.insert(0, "par" if indice % 2 else "impar")
            tree.item(item, tags=tuple(tags))
        tree.heading(coluna, command=lambda: self._ordenar_coluna(tree, coluna, not decrescente))

    def _preencher_tree(self, tree, linhas, tags_extra=None):
        tree.delete(*tree.get_children())
        for idx, valores in enumerate(linhas):
            tags = ["par" if idx % 2 else "impar"]
            if tags_extra:
                extra = tags_extra(valores)
                if extra:
                    tags.append(extra)
            tree.insert("", "end", values=valores, tags=tuple(tags))

    def _criar_busca(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="🔍 Buscar:").pack(side="left", padx=(0, 6))
        var = tk.StringVar()
        ttk.Entry(frame, textvariable=var, width=34).pack(side="left")
        ttk.Button(frame, text="Limpar", command=lambda: var.set("")).pack(side="left", padx=6)
        return frame, var

    def _repopular_combo(self, combo, valores, manter_selecao=True, selecionar_primeiro=False):
        """Atualiza os valores de um combobox sem perder a seleção atual, quando possível."""
        atual = combo.get()
        combo["values"] = valores
        if manter_selecao and atual in valores:
            combo.set(atual)
        elif selecionar_primeiro and valores:
            combo.current(0)
        else:
            combo.set("")

    def _validar_obrigatorios(self, campos):
        """campos: lista de tuplas (valor, rótulo, widget_opcional_para_foco)."""
        faltando, primeiro_widget = [], None
        for item in campos:
            valor, rotulo = item[0], item[1]
            widget = item[2] if len(item) > 2 else None
            if not str(valor).strip():
                faltando.append(rotulo)
                if primeiro_widget is None:
                    primeiro_widget = widget
        if faltando:
            messagebox.showwarning("Campos obrigatórios",
                                   "Preencha os campos obrigatórios: " + ", ".join(faltando) + ".")
            if primeiro_widget is not None:
                primeiro_widget.focus_set()
            return False
        return True

    def _parse_numero(self, texto):
        """Valida um número aceitando separador decimal com vírgula (pt-BR) ou ponto."""
        t = str(texto).strip()
        if not t:
            return None
        if "," in t and "." in t:
            t = t.replace(".", "").replace(",", ".")
        elif "," in t:
            t = t.replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return None

    def atualizar_tudo(self):
        self.atualizar_dashboard()
        self.atualizar_colaboradores()
        self.atualizar_ativos_licencas()
        self.atualizar_combos_movimentacao()
        self.atualizar_chamados()
        self.atualizar_manutencoes()

    # ==================== ABA 1: DASHBOARD & SLA (UC08) ====================
    def _build_tab_dashboard(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="1. Dashboard & SLA")

        ttk.Label(tab, text="Painel Executivo e Monitoramento de SLA",
                  font=(FONTE, 14, "bold")).pack(pady=12)

        self.kpi_frame = ttk.Frame(tab)
        self.kpi_frame.pack(pady=10, padx=20, fill="x")

        cartoes = [
            ("total_ativos", "Total de Ativos", "🖥", COLORS["primary"]),
            ("ativos_disponiveis", "Ativos Disponíveis", "✅", COLORS["success"]),
            ("ativos_manutencao", "Em Manutenção", "🔧", COLORS["warning"]),
            ("chamados_abertos", "Chamados Ativos", "🎫", COLORS["primary"]),
            ("sla_violados", "SLAs Estourados", "⏰", COLORS["danger"]),
            ("custo_manutencao", "Custo Manutenção (R$)", "💰", COLORS["muted"]),
        ]
        self.lbl_kpis = {}
        self.lbl_kpis_sub = {}
        for idx, (chave, titulo, icone, cor) in enumerate(cartoes):
            cartao = tk.Frame(self.kpi_frame, bg=COLORS["surface"],
                              highlightbackground=COLORS["border"], highlightthickness=1)
            cartao.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
            self.kpi_frame.columnconfigure(idx % 3, weight=1)

            tk.Frame(cartao, bg=cor, width=6).pack(side="left", fill="y")
            conteudo = tk.Frame(cartao, bg=COLORS["surface"])
            conteudo.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            tk.Label(conteudo, text=f"{icone}  {titulo}", bg=COLORS["surface"],
                     fg=COLORS["muted"], font=(FONTE, 9, "bold")).pack(anchor="w")
            lbl = tk.Label(conteudo, text="0", bg=COLORS["surface"], fg=cor, font=(FONTE, 22, "bold"))
            lbl.pack(anchor="w", pady=(2, 0))
            sub = tk.Label(conteudo, text="", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONTE, 8))
            sub.pack(anchor="w")

            self.lbl_kpis[chave] = lbl
            self.lbl_kpis_sub[chave] = sub

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=18)
        ttk.Button(btn_frame, text="🔄 Atualizar Indicadores", style="Primary.TButton",
                   command=self.atualizar_tudo).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="📄 Exportar Relatório CSV",
                   command=self.exportar_csv).pack(side="left", padx=8)

    def atualizar_dashboard(self):
        kpis = SGIHService.obter_kpis()
        for chave, valor in kpis.items():
            if chave not in self.lbl_kpis:
                continue
            texto = formatar_moeda(valor) if chave == "custo_manutencao" else str(valor)
            self.lbl_kpis[chave].config(text=texto)

        total = kpis.get("total_ativos") or 0
        disponiveis = kpis.get("ativos_disponiveis") or 0
        if total and "ativos_disponiveis" in self.lbl_kpis_sub:
            self.lbl_kpis_sub["ativos_disponiveis"].config(text=f"{disponiveis / total * 100:.0f}% do total")

        sla = kpis.get("sla_violados") or 0
        if "sla_violados" in self.lbl_kpis:
            cor = COLORS["danger"] if sla > 0 else COLORS["success"]
            self.lbl_kpis["sla_violados"].config(fg=cor)

        self.definir_status("Indicadores atualizados.", "ok")

    def exportar_csv(self):
        try:
            caminho = SGIHService.exportar_relatorio_csv()
            self.definir_status(f"Relatório exportado para: {caminho}", "ok")
            messagebox.showinfo("Relatório Gerado", f"Relatório exportado com sucesso em:\n{caminho}")
        except Exception as e:
            self.definir_status(f"Erro ao exportar relatório: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 2: CADASTROS BÁSICOS (UC01) ====================
    def _build_tab_cadastros(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="2. Cadastros")

        ttk.Label(tab, text="Cadastro de Colaboradores e Técnicos",
                  font=(FONTE, 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        form = ttk.LabelFrame(tab, text="Novo Colaborador / Técnico", padding=10)
        form.pack(fill="x", padx=10, pady=8)

        ttk.Label(form, text="Nome:*").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        self.ent_col_nome = ttk.Entry(form, width=28)
        self.ent_col_nome.grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Matrícula:*").grid(row=0, column=2, padx=5, sticky="w")
        self.ent_col_mat = ttk.Entry(form, width=15)
        self.ent_col_mat.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="E-mail:*").grid(row=0, column=4, padx=5, sticky="w")
        self.ent_col_email = ttk.Entry(form, width=25)
        self.ent_col_email.grid(row=0, column=5, padx=5)

        ttk.Label(form, text="Perfil:").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        self.cb_col_perfil = ttk.Combobox(form, values=["Colaborador", "Tecnico", "Administrador"],
                                          state="readonly", width=25)
        self.cb_col_perfil.set("Colaborador")
        self.cb_col_perfil.grid(row=1, column=1, padx=5)

        ttk.Label(form, text="Setor:*").grid(row=1, column=2, padx=5, sticky="w")
        self.cb_col_setor = ttk.Combobox(form, state="readonly", width=25)
        self.cb_col_setor.grid(row=1, column=3, columnspan=2, padx=5, sticky="w")

        botoes = ttk.Frame(form)
        botoes.grid(row=1, column=5, padx=5, sticky="e")
        ttk.Button(botoes, text="Limpar", command=self._limpar_form_colaborador).pack(side="left", padx=4)
        ttk.Button(botoes, text="Salvar Colaborador", style="Primary.TButton",
                   command=self.salvar_colaborador).pack(side="left")

        ttk.Label(form, text="* campos obrigatórios", font=(FONTE, 8), foreground=COLORS["muted"]) \
            .grid(row=2, column=0, columnspan=6, sticky="w", padx=5, pady=(6, 0))

        for campo in (self.ent_col_nome, self.ent_col_mat, self.ent_col_email):
            campo.bind("<Return>", lambda e: self.salvar_colaborador())

        busca_frame, self.var_busca_colab = self._criar_busca(tab)
        busca_frame.pack(anchor="w", padx=12, pady=(6, 2))
        self.var_busca_colab.trace_add("write", lambda *_: self._filtrar_colaboradores())

        cols = ("ID", "Nome", "Matrícula", "E-mail", "Perfil", "Setor")
        larguras = (45, 170, 100, 190, 110, 150)
        frame_tree, self.tree_colab = self._criar_tree(tab, cols, larguras, altura=13)
        frame_tree.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Button(tab, text="Inativar Selecionado (Exclusão Lógica)", style="Danger.TButton",
                   command=self.inativar_colaborador).pack(pady=6)

    def _limpar_form_colaborador(self):
        self.ent_col_nome.delete(0, "end")
        self.ent_col_mat.delete(0, "end")
        self.ent_col_email.delete(0, "end")
        self.cb_col_perfil.set("Colaborador")

    def atualizar_colaboradores(self):
        setores, _, _ = SGIHService.listar_auxiliares()
        self.map_setores = {f"{s['id']} - {s['nome']}": s["id"] for s in setores}
        self._repopular_combo(self.cb_col_setor, list(self.map_setores.keys()), selecionar_primeiro=True)

        self._dados_colab = [
            (c["id"], c["nome"], c["matricula"], c["email"], c["perfil"], c["setor_nome"])
            for c in SGIHService.listar_colaboradores()
        ]
        self._filtrar_colaboradores()

    def _filtrar_colaboradores(self):
        termo = self.var_busca_colab.get().lower().strip()
        dados = self._dados_colab
        if termo:
            dados = [d for d in dados if termo in " ".join(str(v) for v in d).lower()]
        self._preencher_tree(self.tree_colab, dados)

    def salvar_colaborador(self):
        nome = self.ent_col_nome.get().strip()
        matricula = self.ent_col_mat.get().strip()
        email = self.ent_col_email.get().strip()
        if not self._validar_obrigatorios([
            (nome, "Nome", self.ent_col_nome),
            (matricula, "Matrícula", self.ent_col_mat),
            (email, "E-mail", self.ent_col_email),
        ]):
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            messagebox.showwarning("E-mail inválido", "Informe um e-mail válido, ex: nome@empresa.com")
            self.ent_col_email.focus_set()
            return
        setor_id = self.map_setores.get(self.cb_col_setor.get())
        if self.map_setores and setor_id is None:
            messagebox.showwarning("Campo obrigatório", "Selecione um setor.")
            return
        try:
            SGIHService.cadastrar_colaborador(nome, matricula, email, self.cb_col_perfil.get(), setor_id)
            self._limpar_form_colaborador()
            self.atualizar_tudo()
            self.definir_status(f"Colaborador '{nome}' cadastrado com sucesso.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao cadastrar colaborador: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def inativar_colaborador(self):
        sel = self.tree_colab.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um colaborador na tabela primeiro.")
            return
        valores = self.tree_colab.item(sel[0])["values"]
        colab_id, nome = valores[0], valores[1]
        if not messagebox.askyesno("Confirmar Inativação",
                                   f"Inativar o colaborador '{nome}'?\nO histórico será preservado."):
            return
        try:
            SGIHService.inativar_colaborador(colab_id)
            self.atualizar_tudo()
            self.definir_status(f"Colaborador '{nome}' inativado.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao inativar colaborador: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 3: ATIVOS E LICENÇAS (UC02) ====================
    def _build_tab_inventario(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="3. Ativos & Licenças")

        ttk.Label(tab, text="Inventário de Hardware e Licenças de Software",
                  font=(FONTE, 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        form = ttk.LabelFrame(tab, text="Cadastrar Novo Hardware", padding=10)
        form.pack(fill="x", padx=10, pady=6)

        ttk.Label(form, text="Patrimônio:*").grid(row=0, column=0, padx=4, sticky="w")
        self.ent_pat = ttk.Entry(form, width=14)
        self.ent_pat.grid(row=0, column=1, padx=4)

        ttk.Label(form, text="Nº Série:*").grid(row=0, column=2, padx=4, sticky="w")
        self.ent_serie = ttk.Entry(form, width=16)
        self.ent_serie.grid(row=0, column=3, padx=4)

        ttk.Label(form, text="Modelo:*").grid(row=0, column=4, padx=4, sticky="w")
        self.ent_modelo = ttk.Entry(form, width=20)
        self.ent_modelo.grid(row=0, column=5, padx=4)

        ttk.Label(form, text="Fabricante:*").grid(row=0, column=6, padx=4, sticky="w")
        self.ent_fab = ttk.Entry(form, width=16)
        self.ent_fab.grid(row=0, column=7, padx=4)

        ttk.Label(form, text="Valor (R$):*").grid(row=1, column=0, padx=4, pady=5, sticky="w")
        self.ent_valor = ttk.Entry(form, width=14)
        self.ent_valor.grid(row=1, column=1, padx=4)

        ttk.Label(form, text="Categoria:*").grid(row=1, column=2, padx=4, pady=5, sticky="w")
        self.cb_at_cat = ttk.Combobox(form, state="readonly", width=18)
        self.cb_at_cat.grid(row=1, column=3, padx=4)

        ttk.Label(form, text="Fornecedor:*").grid(row=1, column=4, padx=4, pady=5, sticky="w")
        self.cb_at_forn = ttk.Combobox(form, state="readonly", width=22)
        self.cb_at_forn.grid(row=1, column=5, padx=4)

        ttk.Button(form, text="Cadastrar Hardware", style="Primary.TButton",
                   command=self.cadastrar_ativo).grid(row=1, column=7, padx=4, sticky="e")

        for campo in (self.ent_pat, self.ent_serie, self.ent_modelo, self.ent_fab, self.ent_valor):
            campo.bind("<Return>", lambda e: self.cadastrar_ativo())

        busca_ativos, self.var_busca_ativos = self._criar_busca(tab)
        busca_ativos.pack(anchor="w", padx=12, pady=(6, 2))
        self.var_busca_ativos.trace_add("write", lambda *_: self._filtrar_ativos())

        cols = ("ID", "Patrimônio", "Série", "Modelo", "Fabricante", "Status", "Responsável")
        larguras = (40, 110, 120, 140, 120, 110, 140)
        frame_ativos, self.tree_ativos = self._criar_tree(tab, cols, larguras, altura=8)
        frame_ativos.pack(fill="x", padx=10, pady=4)
        self.tree_ativos.tag_configure("status_disp", foreground=COLORS["success"])

        baixa_frame = ttk.Frame(tab)
        baixa_frame.pack(fill="x", padx=10, pady=4)
        ttk.Label(baixa_frame, text="Motivo da Baixa:*").pack(side="left", padx=4)  # FA1
        self.ent_motivo_baixa = ttk.Entry(baixa_frame, width=40)
        self.ent_motivo_baixa.pack(side="left", padx=4)
        ttk.Button(baixa_frame, text="Registrar Baixa Patrimonial", style="Danger.TButton",
                   command=self.baixar_ativo).pack(side="left", padx=4)

        ttk.Label(tab, text="Licenças de Software", font=(FONTE, 10, "bold")) \
            .pack(anchor="w", padx=12, pady=(10, 2))

        busca_lic, self.var_busca_lic = self._criar_busca(tab)
        busca_lic.pack(anchor="w", padx=12, pady=(0, 2))
        self.var_busca_lic.trace_add("write", lambda *_: self._filtrar_licencas())

        cols_lic = ("ID", "Software", "Chave", "Tipo", "Assentos Totais", "Disponíveis", "Validade")
        larguras_lic = (40, 140, 140, 90, 110, 90, 100)
        frame_lic, self.tree_lic = self._criar_tree(tab, cols_lic, larguras_lic, altura=5)
        frame_lic.pack(fill="x", padx=10, pady=4)
        self.tree_lic.tag_configure("sem_assento", foreground=COLORS["danger"])

        ttk.Button(tab, text="Vincular 1 Assento da Licença Selecionada",  # FA2
                   command=self.consumir_licenca).pack(pady=4)

    @staticmethod
    def _tag_ativo(valores):
        return "status_disp" if valores[5] == "Disponível" else None

    @staticmethod
    def _tag_licenca(valores):
        try:
            return "sem_assento" if int(valores[5]) <= 0 else None
        except (ValueError, TypeError):
            return None

    def atualizar_ativos_licencas(self):
        _, categorias, fornecedores = SGIHService.listar_auxiliares()
        cats_ativo = [c for c in categorias if c["tipo"] == "Ativo"] or categorias
        self.map_cat_ativo = {f"{c['id']} - {c['nome']}": c["id"] for c in cats_ativo}
        self._repopular_combo(self.cb_at_cat, list(self.map_cat_ativo.keys()), selecionar_primeiro=True)

        self.map_fornecedores = {f"{f['id']} - {f['razao_social']}": f["id"] for f in fornecedores}
        self._repopular_combo(self.cb_at_forn, list(self.map_fornecedores.keys()), selecionar_primeiro=True)

        self._lista_ativos_raw = SGIHService.listar_ativos()
        self._dados_ativos = [
            (a["id"], a["patrimonio"], a["num_serie"], a["modelo"], a["fabricante"],
             a["status"], a["responsavel_nome"] or "-")
            for a in self._lista_ativos_raw
        ]
        self._filtrar_ativos()

        self._dados_licencas = [
            (l["id"], l["software"], l["chave_produto"], l["tipo"],
             l["assentos_totais"], l["assentos_disponiveis"], l["validade"])
            for l in SGIHService.listar_licencas()
        ]
        self._filtrar_licencas()

    def _filtrar_ativos(self):
        termo = self.var_busca_ativos.get().lower().strip()
        dados = self._dados_ativos
        if termo:
            dados = [d for d in dados if termo in " ".join(str(v) for v in d).lower()]
        self._preencher_tree(self.tree_ativos, dados, tags_extra=self._tag_ativo)

    def _filtrar_licencas(self):
        termo = self.var_busca_lic.get().lower().strip()
        dados = self._dados_licencas
        if termo:
            dados = [d for d in dados if termo in " ".join(str(v) for v in d).lower()]
        self._preencher_tree(self.tree_lic, dados, tags_extra=self._tag_licenca)

    def cadastrar_ativo(self):
        patrimonio = self.ent_pat.get().strip()
        serie = self.ent_serie.get().strip()
        modelo = self.ent_modelo.get().strip()
        fabricante = self.ent_fab.get().strip()
        if not self._validar_obrigatorios([
            (patrimonio, "Patrimônio", self.ent_pat),
            (serie, "Nº Série", self.ent_serie),
            (modelo, "Modelo", self.ent_modelo),
            (fabricante, "Fabricante", self.ent_fab),
        ]):
            return
        valor_num = self._parse_numero(self.ent_valor.get())
        if valor_num is None:
            messagebox.showwarning("Valor inválido", "Informe um valor numérico válido, ex: 1500,00")
            self.ent_valor.focus_set()
            return
        categoria_id = self.map_cat_ativo.get(self.cb_at_cat.get())
        if self.map_cat_ativo and categoria_id is None:
            messagebox.showwarning("Campo obrigatório", "Selecione uma categoria de ativo.")
            return
        fornecedor_id = self.map_fornecedores.get(self.cb_at_forn.get())
        if self.map_fornecedores and fornecedor_id is None:
            messagebox.showwarning("Campo obrigatório", "Selecione um fornecedor.")
            return
        try:
            SGIHService.cadastrar_ativo(
                patrimonio, serie, modelo, fabricante, categoria_id, fornecedor_id, valor_num
            )
            for campo in (self.ent_pat, self.ent_serie, self.ent_modelo, self.ent_fab, self.ent_valor):
                campo.delete(0, "end")
            self.atualizar_tudo()
            self.definir_status(f"Ativo '{patrimonio}' cadastrado com status 'Disponível'.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao cadastrar ativo: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def baixar_ativo(self):
        sel = self.tree_ativos.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um ativo na tabela primeiro.")
            return
        valores = self.tree_ativos.item(sel[0])["values"]
        ativo_id, patrimonio = valores[0], valores[1]
        motivo = self.ent_motivo_baixa.get().strip()
        if not motivo:
            messagebox.showwarning("Campo obrigatório", "Informe o motivo da baixa patrimonial.")
            self.ent_motivo_baixa.focus_set()
            return
        if not messagebox.askyesno(
            "Confirmar Baixa Patrimonial",
            f"Confirma a baixa do ativo '{patrimonio}'?\nEsta ação não pode ser desfeita.\n\nMotivo: {motivo}",
        ):
            return
        try:
            SGIHService.baixar_ativo(ativo_id, motivo)
            self.ent_motivo_baixa.delete(0, "end")
            self.atualizar_tudo()
            self.definir_status(f"Ativo '{patrimonio}' baixado com sucesso.", "ok")
            messagebox.showinfo("Baixa Efetuada", "Ativo baixado com sucesso.")
        except Exception as e:
            self.definir_status(f"Erro ao baixar ativo: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def consumir_licenca(self):
        sel = self.tree_lic.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma licença na tabela primeiro.")
            return
        valores = self.tree_lic.item(sel[0])["values"]
        lic_id, software, disponiveis = valores[0], valores[1], valores[5]
        try:
            if int(disponiveis) <= 0 and not messagebox.askyesno(
                "Sem assentos disponíveis",
                f"A licença '{software}' não possui assentos disponíveis.\nTentar mesmo assim?",
            ):
                return
        except (ValueError, TypeError):
            pass
        try:
            SGIHService.consumir_assento_licenca(lic_id)
            self.atualizar_tudo()
            self.definir_status(f"Assento de '{software}' vinculado com sucesso.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao vincular assento: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 4: MOVIMENTAÇÃO & TERMO (UC03) ====================
    def _build_tab_movimentacao(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="4. Movimentar Ativo")

        ttk.Label(tab, text="Movimentação e Termo de Responsabilidade",
                  font=(FONTE, 12, "bold")).pack(anchor="w", padx=22, pady=(14, 0))

        box = ttk.LabelFrame(tab, text="Alocação, Empréstimo ou Devolução de Ativos", padding=15)
        box.pack(fill="x", padx=20, pady=20)

        ttk.Label(box, text="Ativo:*").grid(row=0, column=0, sticky="w", pady=6)
        self.cb_mov_ativo = ttk.Combobox(box, state="readonly", width=48)
        self.cb_mov_ativo.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(box, text="Operação:").grid(row=1, column=0, sticky="w", pady=6)
        self.cb_mov_tipo = ttk.Combobox(box, values=["Alocação", "Empréstimo", "Devolução"],
                                        state="readonly", width=48)
        self.cb_mov_tipo.set("Alocação")
        self.cb_mov_tipo.grid(row=1, column=1, padx=8, pady=6)
        self.cb_mov_tipo.bind("<<ComboboxSelected>>", self._ao_mudar_tipo_movimentacao)

        self.lbl_mov_colab = ttk.Label(box, text="Colaborador:*")
        self.lbl_mov_colab.grid(row=2, column=0, sticky="w", pady=6)
        self.cb_mov_colab = ttk.Combobox(box, state="readonly", width=48)
        self.cb_mov_colab.grid(row=2, column=1, padx=8, pady=6)

        ttk.Label(box, text="Observação / Inspeção:").grid(row=3, column=0, sticky="w", pady=6)
        self.ent_mov_obs = ttk.Entry(box, width=51)
        self.ent_mov_obs.grid(row=3, column=1, padx=8, pady=6)

        self.var_avaria = tk.BooleanVar(value=False)
        self.chk_avaria = ttk.Checkbutton(
            box, text="Devolução com Avaria (encaminha automaticamente para Ordem de Manutenção)",  # FA2
            variable=self.var_avaria, state="disabled",
        )
        self.chk_avaria.grid(row=4, column=1, sticky="w", pady=6)

        ttk.Button(box, text="Confirmar Movimentação e Gerar Termo", style="Primary.TButton",
                   command=self.executar_movimentacao).grid(row=5, column=1, sticky="e", pady=12)

    def _ao_mudar_tipo_movimentacao(self, event=None):
        if self.cb_mov_tipo.get() == "Devolução":
            self.cb_mov_colab.configure(state="disabled")
            self.cb_mov_colab.set("")
            self.lbl_mov_colab.configure(text="Colaborador:")
            self.chk_avaria.configure(state="normal")
        else:
            self.cb_mov_colab.configure(state="readonly")
            self.lbl_mov_colab.configure(text="Colaborador:*")
            self.chk_avaria.configure(state="disabled")
            self.var_avaria.set(False)

    def atualizar_combos_movimentacao(self):
        ativos = self._lista_ativos_raw or SGIHService.listar_ativos()
        self.map_ativos = {
            f"{a['id']} - {a['patrimonio']} ({a['modelo']}) [{a['status']}]": a["id"] for a in ativos
        }
        self._repopular_combo(self.cb_mov_ativo, list(self.map_ativos.keys()))

        colabs = SGIHService.listar_colaboradores()
        self.map_colabs = {f"{c['id']} - {c['nome']}": c["id"] for c in colabs}
        self._repopular_combo(self.cb_mov_colab, list(self.map_colabs.keys()))
        self._ao_mudar_tipo_movimentacao()

    def executar_movimentacao(self):
        ativo_sel = self.cb_mov_ativo.get()
        if not ativo_sel:
            messagebox.showwarning("Campo obrigatório", "Selecione um ativo.")
            return
        tipo = self.cb_mov_tipo.get()
        ativo_id = self.map_ativos.get(ativo_sel)
        colab_id = None
        if tipo in ("Alocação", "Empréstimo"):
            colab_sel = self.cb_mov_colab.get()
            if not colab_sel:
                messagebox.showwarning("Campo obrigatório", f"Selecione um colaborador para {tipo.lower()}.")
                return
            colab_id = self.map_colabs.get(colab_sel)

        if tipo == "Devolução" and self.var_avaria.get():
            if not messagebox.askyesno(
                "Confirmar Devolução com Avaria",
                "O ativo será encaminhado automaticamente para uma Ordem de Manutenção. Confirma?",
            ):
                return
        try:
            termo = SGIHService.movimentar_ativo(
                ativo_id, colab_id, tipo, observacao=self.ent_mov_obs.get(), com_avaria=self.var_avaria.get()
            )
            self.ent_mov_obs.delete(0, "end")
            self.var_avaria.set(False)
            self.atualizar_tudo()
            if termo:
                self.definir_status(f"Movimentação ({tipo}) registrada. Termo gerado.", "ok")
                messagebox.showinfo("Sucesso", f"Movimentação registrada com sucesso!\n\n"
                                                 f"Termo de Responsabilidade gerado em:\n{termo}")
            else:
                self.definir_status(f"Movimentação ({tipo}) registrada com sucesso.", "ok")
        except Exception as e:
            self.definir_status(f"Erro na movimentação: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 5: HELPDESK (UC04, UC05, UC06) ====================
    def _build_tab_helpdesk(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="5. Helpdesk")

        ttk.Label(tab, text="Central de Atendimento (Helpdesk)",
                  font=(FONTE, 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        top = ttk.LabelFrame(tab, text="Abrir Novo Chamado", padding=8)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(top, text="Solicitante:*").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.cb_ch_sol = ttk.Combobox(top, state="readonly", width=26)
        self.cb_ch_sol.grid(row=0, column=1, padx=4, pady=3, sticky="w")
        self.cb_ch_sol.bind("<<ComboboxSelected>>", self._ao_mudar_solicitante_chamado)

        ttk.Label(top, text="Categoria:*").grid(row=0, column=2, padx=4, pady=3, sticky="w")
        self.cb_ch_cat = ttk.Combobox(top, state="readonly", width=26)
        self.cb_ch_cat.grid(row=0, column=3, padx=4, pady=3, sticky="w")

        ttk.Label(top, text="Urgência:").grid(row=0, column=4, padx=4, pady=3, sticky="w")
        self.cb_ch_urg = ttk.Combobox(top, values=["Baixa", "Média", "Alta", "Crítica"],
                                      state="readonly", width=12)
        self.cb_ch_urg.set("Média")
        self.cb_ch_urg.grid(row=0, column=5, padx=4, pady=3, sticky="w")

        ttk.Label(top, text="Ativo (opcional):").grid(row=1, column=0, padx=4, pady=3, sticky="w")
        self.cb_ch_ativo = ttk.Combobox(top, state="readonly", width=26)
        self.cb_ch_ativo.grid(row=1, column=1, padx=4, pady=3, sticky="w")

        ttk.Label(top, text="Descrição:*").grid(row=1, column=2, padx=4, pady=3, sticky="w")
        self.ent_ch_desc = ttk.Entry(top, width=46)
        self.ent_ch_desc.grid(row=1, column=3, columnspan=3, padx=4, pady=3, sticky="we")
        self.ent_ch_desc.bind("<Return>", lambda e: self.abrir_chamado())

        ttk.Button(top, text="Registrar Chamado", style="Primary.TButton",
                   command=self.abrir_chamado).grid(row=1, column=6, padx=6, pady=3)

        busca_ch, self.var_busca_chamados = self._criar_busca(tab)
        busca_ch.pack(anchor="w", padx=12, pady=(2, 2))
        self.var_busca_chamados.trace_add("write", lambda *_: self._filtrar_chamados())

        cols = ("ID", "Protocolo", "Solicitante", "Ativo", "Urgência", "Status", "Prazo SLA", "Solução", "Nota")
        larguras = (40, 110, 130, 85, 75, 110, 115, 200, 45)
        frame_ch, self.tree_chamados = self._criar_tree(tab, cols, larguras, altura=9)
        frame_ch.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree_chamados.tag_configure("urgencia_alta", foreground=COLORS["danger"])
        self.tree_chamados.tag_configure("status_resolvido", foreground=COLORS["success"])
        self.tree_chamados.bind("<<TreeviewSelect>>", self._ao_selecionar_chamado)

        bottom = ttk.LabelFrame(tab, text="Atendimento Técnico e Avaliação/Reabertura", padding=8)
        bottom.pack(fill="x", padx=10, pady=6)

        ttk.Label(bottom, text="Técnico:*").grid(row=0, column=0, padx=4, sticky="w")
        self.cb_ch_tec = ttk.Combobox(bottom, state="readonly", width=24)
        self.cb_ch_tec.grid(row=0, column=1, padx=4, sticky="w")

        ttk.Label(bottom, text="Parecer / Solução:").grid(row=0, column=2, padx=4, sticky="w")
        self.ent_ch_solucao = ttk.Entry(bottom, width=36)
        self.ent_ch_solucao.grid(row=0, column=3, padx=4)

        ttk.Button(bottom, text="Colocar Em Atendimento",
                   command=lambda: self.atualizar_chamado("Em Atendimento")).grid(row=0, column=4, padx=4)
        ttk.Button(bottom, text="Marcar como Resolvido", style="Primary.TButton",
                   command=lambda: self.atualizar_chamado("Resolvido")).grid(row=0, column=5, padx=4)

        ttk.Label(bottom, text="Nota (1-5):").grid(row=1, column=0, padx=4, pady=6, sticky="w")
        self.cb_ch_nota = ttk.Combobox(bottom, values=[5, 4, 3, 2, 1], state="readonly", width=5)
        self.cb_ch_nota.set(5)
        self.cb_ch_nota.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(bottom, text="Avaliar e Fechar",
                   command=lambda: self.avaliar_chamado("Fechar")).grid(row=1, column=4, padx=4)
        ttk.Button(bottom, text="Reabrir Chamado", style="Danger.TButton",  # FA1
                   command=lambda: self.avaliar_chamado("Reabrir")).grid(row=1, column=5, padx=4)

    @staticmethod
    def _tag_chamado(valores):
        urgencia, status = valores[4], valores[5]
        if status in ("Resolvido", "Fechado"):
            return "status_resolvido"
        if urgencia in ("Alta", "Crítica"):
            return "urgencia_alta"
        return None

    def _ao_mudar_solicitante_chamado(self, event=None):
        """Exibe no combo os ativos sob custódia do solicitante selecionado (UC04 / R9)."""
        sol_id = self.map_sol.get(self.cb_ch_sol.get())
        ativos = self._lista_ativos_raw or SGIHService.listar_ativos()
        self.map_ativos_chamado = {"Nenhum (sem ativo vinculado)": None}
        for a in ativos:
            if sol_id is not None and a["colaborador_id"] == sol_id and a["status"] != "Baixado":
                self.map_ativos_chamado[f"{a['id']} - {a['patrimonio']} ({a['modelo']})"] = a["id"]
        self._repopular_combo(self.cb_ch_ativo, list(self.map_ativos_chamado.keys()), selecionar_primeiro=True)

    def atualizar_chamados(self):
        colabs = SGIHService.listar_colaboradores()
        self.map_sol = {f"{c['id']} - {c['nome']}": c["id"] for c in colabs}
        self._repopular_combo(self.cb_ch_sol, list(self.map_sol.keys()), selecionar_primeiro=True)

        _, categorias, _ = SGIHService.listar_auxiliares()
        cats_chamado = [c for c in categorias if c["tipo"] == "Chamado"] or categorias
        self.map_cat_chamado = {
            f"{c['id']} - {c['nome']} (SLA: {c['sla_horas']}h)": c["id"] for c in cats_chamado
        }
        self._repopular_combo(self.cb_ch_cat, list(self.map_cat_chamado.keys()), selecionar_primeiro=True)

        tecnicos = [c for c in colabs if c["perfil"] in ("Tecnico", "Administrador")] or colabs
        self.map_tec = {f"{c['id']} - {c['nome']}": c["id"] for c in tecnicos}
        self._repopular_combo(self.cb_ch_tec, list(self.map_tec.keys()), selecionar_primeiro=True)

        self._ao_mudar_solicitante_chamado()

        self._dados_chamados = [
            (ch["id"], ch["protocolo"], ch["solicitante_nome"], ch["ativo_patrimonio"] or "-",
             ch["urgencia"], ch["status"], ch["prazo_sla"], ch["solucao"] or "-",
             ch["nota_avaliacao"] if ch["nota_avaliacao"] is not None else "-")
            for ch in SGIHService.listar_chamados()
        ]
        self._filtrar_chamados()

    def _filtrar_chamados(self):
        termo = self.var_busca_chamados.get().lower().strip()
        dados = self._dados_chamados
        if termo:
            dados = [d for d in dados if termo in " ".join(str(v) for v in d).lower()]
        self._preencher_tree(self.tree_chamados, dados, tags_extra=self._tag_chamado)

    def _ao_selecionar_chamado(self, event=None):
        """Ao clicar em um chamado, carrega a solução/nota já registradas para facilitar a edição."""
        sel = self.tree_chamados.selection()
        if not sel:
            return
        valores = self.tree_chamados.item(sel[0])["values"]
        solucao, nota = valores[7], valores[8]
        self.ent_ch_solucao.delete(0, "end")
        if solucao and solucao != "-":
            self.ent_ch_solucao.insert(0, solucao)
        if nota not in ("-", "", None):
            try:
                self.cb_ch_nota.set(int(float(nota)))
            except (ValueError, TypeError):
                pass

    def abrir_chamado(self):
        sol_sel = self.cb_ch_sol.get()
        if not sol_sel:
            messagebox.showwarning("Atenção",
                                   "Cadastre e selecione um colaborador solicitante antes de abrir um chamado.")
            return
        cat_id = self.map_cat_chamado.get(self.cb_ch_cat.get())
        if self.map_cat_chamado and cat_id is None:
            messagebox.showwarning("Campo obrigatório", "Selecione uma categoria para o chamado.")
            return
        descricao = self.ent_ch_desc.get().strip()
        if not descricao:
            messagebox.showwarning("Campo obrigatório", "Descreva o problema antes de registrar o chamado.")
            self.ent_ch_desc.focus_set()
            return
        sol_id = self.map_sol.get(sol_sel)
        ativo_id = self.map_ativos_chamado.get(self.cb_ch_ativo.get())
        try:
            prot = SGIHService.abrir_chamado(sol_id, ativo_id, cat_id, self.cb_ch_urg.get(), descricao)
            self.ent_ch_desc.delete(0, "end")
            self.atualizar_tudo()
            self.definir_status(f"Chamado {prot} aberto.", "ok")
            messagebox.showinfo("Chamado Aberto", f"Protocolo gerado: {prot}")
        except Exception as e:
            self.definir_status(f"Erro ao abrir chamado: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def atualizar_chamado(self, status):
        sel = self.tree_chamados.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um chamado na tabela primeiro.")
            return
        tec_id = self.map_tec.get(self.cb_ch_tec.get())
        if tec_id is None:
            messagebox.showwarning("Campo obrigatório", "Selecione um técnico responsável pelo atendimento.")
            return
        if status == "Resolvido" and not self.ent_ch_solucao.get().strip():
            messagebox.showwarning("Campo obrigatório", "Descreva a solução antes de marcar como resolvido.")
            self.ent_ch_solucao.focus_set()
            return
        ch_id = self.tree_chamados.item(sel[0])["values"][0]
        try:
            SGIHService.atender_resolver_chamado(ch_id, tec_id, status, self.ent_ch_solucao.get().strip())
            self.atualizar_tudo()
            self.definir_status(f"Chamado #{ch_id} atualizado para '{status}'.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao atualizar chamado: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def avaliar_chamado(self, acao):
        sel = self.tree_chamados.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um chamado na tabela primeiro.")
            return
        ch_id = self.tree_chamados.item(sel[0])["values"][0]
        if acao == "Reabrir" and not messagebox.askyesno(
            "Confirmar Reabertura", "Deseja realmente reabrir este chamado?"
        ):
            return
        try:
            SGIHService.avaliar_ou_reabrir_chamado(ch_id, acao, self.cb_ch_nota.get(), self.ent_ch_solucao.get().strip())
            self.atualizar_tudo()
            verbo = "fechado" if acao == "Fechar" else "reaberto"
            self.definir_status(f"Chamado #{ch_id} {verbo}.", "ok")
        except Exception as e:
            self.definir_status(f"Erro: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 6: MANUTENÇÃO (UC07) ====================
    def _build_tab_manutencao(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="6. Manutenção")

        ttk.Label(tab, text="Ordens de Manutenção",
                  font=(FONTE, 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        top = ttk.LabelFrame(tab, text="Abrir Ordem de Manutenção", padding=8)
        top.pack(fill="x", padx=10, pady=6)

        ttk.Label(top, text="Ativo:*").grid(row=0, column=0, padx=4)
        self.cb_om_ativo = ttk.Combobox(top, state="readonly", width=35)
        self.cb_om_ativo.grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Falha:*").grid(row=0, column=2, padx=4)
        self.ent_om_falha = ttk.Entry(top, width=35)
        self.ent_om_falha.grid(row=0, column=3, padx=4)
        self.ent_om_falha.bind("<Return>", lambda e: self.abrir_om())

        ttk.Button(top, text="Abrir OM", style="Primary.TButton",
                   command=self.abrir_om).grid(row=0, column=4, padx=6)

        busca_om, self.var_busca_om = self._criar_busca(tab)
        busca_om.pack(anchor="w", padx=12, pady=(2, 2))
        self.var_busca_om.trace_add("write", lambda *_: self._filtrar_om())

        cols = ("ID", "Patrimônio", "Modelo", "Tipo", "Falha", "Custo (R$)", "Status")
        larguras = (40, 110, 130, 90, 180, 100, 120)
        frame_om, self.tree_om = self._criar_tree(tab, cols, larguras, altura=10)
        frame_om.pack(fill="both", expand=True, padx=10, pady=5)

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=10, pady=8)
        ttk.Label(bottom, text="Custo Reparo (R$):*").pack(side="left", padx=4)
        self.ent_om_custo = ttk.Entry(bottom, width=12)
        self.ent_om_custo.pack(side="left", padx=4)

        ttk.Label(bottom, text="Parecer Técnico:*").pack(side="left", padx=4)
        self.ent_om_parecer = ttk.Entry(bottom, width=35)
        self.ent_om_parecer.pack(side="left", padx=4)

        self.var_inviavel = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Perda Total / Inviável (Baixa Automática)",
                        variable=self.var_inviavel).pack(side="left", padx=6)
        ttk.Button(bottom, text="Encerrar OM", style="Primary.TButton",
                   command=self.encerrar_om).pack(side="left", padx=6)

    def atualizar_manutencoes(self):
        ativos = self._lista_ativos_raw or SGIHService.listar_ativos()
        self.map_om_ativos = {f"{a['id']} - {a['patrimonio']} ({a['modelo']})": a["id"] for a in ativos}
        self._repopular_combo(self.cb_om_ativo, list(self.map_om_ativos.keys()))

        self._dados_om = [
            (om["id"], om["patrimonio"], om["modelo"], om["tipo"], om["falha"],
             f"{om['custo']:.2f}", om["status"])
            for om in SGIHService.listar_ordens_manutencao()
        ]
        self._filtrar_om()

    def _filtrar_om(self):
        termo = self.var_busca_om.get().lower().strip()
        dados = self._dados_om
        if termo:
            dados = [d for d in dados if termo in " ".join(str(v) for v in d).lower()]
        self._preencher_tree(self.tree_om, dados)

    def abrir_om(self):
        ativo_sel = self.cb_om_ativo.get()
        if not ativo_sel:
            messagebox.showwarning("Campo obrigatório", "Selecione o ativo com falha.")
            return
        falha = self.ent_om_falha.get().strip()
        if not falha:
            messagebox.showwarning("Campo obrigatório", "Descreva a falha relatada.")
            self.ent_om_falha.focus_set()
            return
        ativo_id = self.map_om_ativos.get(ativo_sel)
        try:
            SGIHService.abrir_ordem_manutencao(ativo_id, "Corretiva", "Interna", falha)
            self.ent_om_falha.delete(0, "end")
            self.atualizar_tudo()
            self.definir_status("Ordem de Manutenção aberta.", "ok")
        except Exception as e:
            self.definir_status(f"Erro ao abrir OM: {e}", "erro")
            messagebox.showerror("Erro", str(e))

    def encerrar_om(self):
        sel = self.tree_om.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma Ordem de Manutenção na tabela primeiro.")
            return
        custo_num = self._parse_numero(self.ent_om_custo.get())
        if custo_num is None:
            messagebox.showwarning("Valor inválido", "Informe um custo de reparo numérico válido, ex: 250,00")
            self.ent_om_custo.focus_set()
            return
        parecer = self.ent_om_parecer.get().strip()
        if not parecer:
            messagebox.showwarning("Campo obrigatório", "Informe o parecer técnico antes de encerrar a OM.")
            self.ent_om_parecer.focus_set()
            return
        if self.var_inviavel.get() and not messagebox.askyesno(
            "Confirmar Perda Total", "O ativo será baixado automaticamente do inventário. Confirma?"
        ):
            return
        om_id = self.tree_om.item(sel[0])["values"][0]
        try:
            SGIHService.encerrar_ordem_manutencao(om_id, custo_num, parecer, self.var_inviavel.get())
            self.ent_om_custo.delete(0, "end")
            self.ent_om_parecer.delete(0, "end")
            self.var_inviavel.set(False)
            self.atualizar_tudo()
            self.definir_status(f"OM #{om_id} encerrada.", "ok")
            messagebox.showinfo("OM Encerrada", "Ordem de Manutenção finalizada e status do ativo atualizado!")
        except Exception as e:
            self.definir_status(f"Erro ao encerrar OM: {e}", "erro")
            messagebox.showerror("Erro", str(e))


if __name__ == "__main__":
    app = SGIHApp()
    app.mainloop()