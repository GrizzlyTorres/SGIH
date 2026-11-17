import tkinter as tk
from tkinter import ttk, messagebox
from services.sgih_service import SGIHService


class SGIHApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SGIH - Sistema de Gestão de Inventário e Helpdesk de Ativos de TI")
        self.geometry("1120x680")

        style = ttk.Style(self)
        style.theme_use("clam")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_tab_dashboard()
        self._build_tab_cadastros()
        self._build_tab_inventario()
        self._build_tab_movimentacao()
        self._build_tab_helpdesk()
        self._build_tab_manutencao()

        self.atualizar_tudo()

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
        self.notebook.add(tab, text="1. Dashboard & SLA (UC08)")

        ttk.Label(tab, text="Painel Executivo e Monitoramento de SLA", font=("Segoe UI", 14, "bold")).pack(pady=12)

        self.kpi_frame = ttk.Frame(tab)
        self.kpi_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_kpis = {}
        cards = [
            ("total_ativos", "Total de Ativos"),
            ("ativos_disponiveis", "Ativos Disponíveis"),
            ("ativos_manutencao", "Em Manutenção"),
            ("chamados_abertos", "Chamados Ativos"),
            ("sla_violados", "SLAs Estourados"),
            ("custo_manutencao", "Custo Manutenção (R$)"),
        ]
        for idx, (key, titulo) in enumerate(cards):
            box = ttk.LabelFrame(self.kpi_frame, text=titulo, padding=15)
            box.grid(row=idx // 3, column=idx % 3, padx=10, pady=10, sticky="nsew")
            self.kpi_frame.columnconfigure(idx % 3, weight=1)
            lbl = ttk.Label(box, text="0", font=("Segoe UI", 18, "bold"))
            lbl.pack()
            self.lbl_kpis[key] = lbl

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Atualizar Indicadores", command=self.atualizar_tudo).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Exportar Relatório CSV (UC08)", command=self.exportar_csv).pack(side="left", padx=8)

    def atualizar_dashboard(self):
        kpis = SGIHService.obter_kpis()
        for k, val in kpis.items():
            texto = f"R$ {val:,.2f}" if k == "custo_manutencao" else str(val)
            self.lbl_kpis[k].config(text=texto)

    def exportar_csv(self):
        caminho = SGIHService.exportar_relatorio_csv()
        messagebox.showinfo("Relatório Gerado", f"Relatório exportado com sucesso em:\n{caminho}")

    # ==================== ABA 2: CADASTROS BÁSICOS (UC01) ====================
    def _build_tab_cadastros(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="2. Cadastros (UC01)")

        form = ttk.LabelFrame(tab, text="Novo Colaborador / Técnico", padding=10)
        form.pack(fill="x", padx=10, pady=8)

        ttk.Label(form, text="Nome:").grid(row=0, column=0, padx=5, pady=4)
        self.ent_col_nome = ttk.Entry(form, width=28)
        self.ent_col_nome.grid(row=0, column=1, padx=5)

        ttk.Label(form, text="Matrícula:").grid(row=0, column=2, padx=5)
        self.ent_col_mat = ttk.Entry(form, width=15)
        self.ent_col_mat.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="E-mail:").grid(row=0, column=4, padx=5)
        self.ent_col_email = ttk.Entry(form, width=25)
        self.ent_col_email.grid(row=0, column=5, padx=5)

        ttk.Label(form, text="Perfil:").grid(row=1, column=0, padx=5, pady=4)
        self.cb_col_perfil = ttk.Combobox(form, values=["Colaborador", "Tecnico", "Administrador"], state="readonly", width=25)
        self.cb_col_perfil.set("Colaborador")
        self.cb_col_perfil.grid(row=1, column=1, padx=5)

        ttk.Label(form, text="Setor:").grid(row=1, column=2, padx=5)
        self.cb_col_setor = ttk.Combobox(form, state="readonly", width=25)
        self.cb_col_setor.grid(row=1, column=3, columnspan=2, padx=5, sticky="w")

        ttk.Button(form, text="Salvar Colaborador", command=self.salvar_colaborador).grid(row=1, column=5, padx=5, sticky="e")

        cols = ("ID", "Nome", "Matrícula", "E-mail", "Perfil", "Setor")
        self.tree_colab = ttk.Treeview(tab, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree_colab.heading(c, text=c)
            self.tree_colab.column(c, width=160 if c != "ID" else 50)
        self.tree_colab.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Button(tab, text="Inativar Selecionado (FA1 - Exclusão Lógica)", command=self.inativar_colaborador).pack(pady=6)

    def atualizar_colaboradores(self):
        setores, _, _ = SGIHService.listar_auxiliares()
        self.map_setores = {f"{s['id']} - {s['nome']}": s["id"] for s in setores}
        self.cb_col_setor["values"] = list(self.map_setores.keys())
        if self.map_setores:
            self.cb_col_setor.current(0)

        for item in self.tree_colab.get_children():
            self.tree_colab.delete(item)
        for c in SGIHService.listar_colaboradores():
            self.tree_colab.insert("", "end", values=(c["id"], c["nome"], c["matricula"], c["email"], c["perfil"], c["setor_nome"]))

    def salvar_colaborador(self):
        try:
            setor_id = self.map_setores.get(self.cb_col_setor.get())
            SGIHService.cadastrar_colaborador(
                self.ent_col_nome.get(), self.ent_col_mat.get(), self.ent_col_email.get(), self.cb_col_perfil.get(), setor_id
            )
            self.ent_col_nome.delete(0, "end")
            self.ent_col_mat.delete(0, "end")
            self.ent_col_email.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Sucesso", "Colaborador cadastrado!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def inativar_colaborador(self):
        sel = self.tree_colab.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um colaborador na tabela primeiro.")
            return
        colab_id = self.tree_colab.item(sel[0])["values"][0]
        SGIHService.inativar_colaborador(colab_id)
        self.atualizar_tudo()
        messagebox.showinfo("Inativado", "Registro inativado logicamente (histórico preservado).")

    # ==================== ABA 3: ATIVOS E LICENÇAS (UC02) ====================
    def _build_tab_inventario(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="3. Ativos & Licenças (UC02)")

        form = ttk.LabelFrame(tab, text="Cadastrar Novo Hardware", padding=10)
        form.pack(fill="x", padx=10, pady=6)

        ttk.Label(form, text="Patrimônio:").grid(row=0, column=0, padx=4)
        self.ent_pat = ttk.Entry(form, width=14)
        self.ent_pat.grid(row=0, column=1, padx=4)

        ttk.Label(form, text="Nº Série:").grid(row=0, column=2, padx=4)
        self.ent_serie = ttk.Entry(form, width=16)
        self.ent_serie.grid(row=0, column=3, padx=4)

        ttk.Label(form, text="Modelo:").grid(row=0, column=4, padx=4)
        self.ent_modelo = ttk.Entry(form, width=20)
        self.ent_modelo.grid(row=0, column=5, padx=4)

        ttk.Label(form, text="Fabricante:").grid(row=0, column=6, padx=4)
        self.ent_fab = ttk.Entry(form, width=15)
        self.ent_fab.grid(row=0, column=7, padx=4)

        ttk.Label(form, text="Valor (R$):").grid(row=1, column=0, padx=4, pady=5)
        self.ent_valor = ttk.Entry(form, width=14)
        self.ent_valor.grid(row=1, column=1, padx=4)

        ttk.Button(form, text="Cadastrar Hardware", command=self.cadastrar_ativo).grid(row=1, column=7, padx=4, sticky="e")

        cols = ("ID", "Patrimônio", "Série", "Modelo", "Fabricante", "Status", "Responsável")
        self.tree_ativos = ttk.Treeview(tab, columns=cols, show="headings", height=9)
        for c in cols:
            self.tree_ativos.heading(c, text=c)
            self.tree_ativos.column(c, width=145 if c != "ID" else 45)
        self.tree_ativos.pack(fill="x", padx=10, pady=4)

        baixa_frame = ttk.Frame(tab)
        baixa_frame.pack(fill="x", padx=10, pady=4)
        ttk.Label(baixa_frame, text="Motivo da Baixa (FA1):").pack(side="left", padx=4)
        self.ent_motivo_baixa = ttk.Entry(baixa_frame, width=40)
        self.ent_motivo_baixa.pack(side="left", padx=4)
        ttk.Button(baixa_frame, text="Registrar Baixa Patrimonial", command=self.baixar_ativo).pack(side="left", padx=4)

        # Licenças
        ttk.Label(tab, text="Licenças de Software", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        cols_lic = ("ID", "Software", "Chave", "Tipo", "Assentos Totais", "Disponíveis", "Validade")
        self.tree_lic = ttk.Treeview(tab, columns=cols_lic, show="headings", height=5)
        for c in cols_lic:
            self.tree_lic.heading(c, text=c)
            self.tree_lic.column(c, width=145 if c != "ID" else 45)
        self.tree_lic.pack(fill="x", padx=10, pady=4)
        ttk.Button(tab, text="Vincular 1 Assento da Licença Selecionada (FA2)", command=self.consumir_licenca).pack(pady=4)

    def atualizar_ativos_licencas(self):
        for item in self.tree_ativos.get_children():
            self.tree_ativos.delete(item)
        for a in SGIHService.listar_ativos():
            self.tree_ativos.insert(
                "", "end",
                values=(a["id"], a["patrimonio"], a["num_serie"], a["modelo"], a["fabricante"], a["status"], a["responsavel_nome"] or "-")
            )

        for item in self.tree_lic.get_children():
            self.tree_lic.delete(item)
        for l in SGIHService.listar_licencas():
            self.tree_lic.insert(
                "", "end",
                values=(l["id"], l["software"], l["chave_produto"], l["tipo"], l["assentos_totais"], l["assentos_disponiveis"], l["validade"])
            )

    def cadastrar_ativo(self):
        try:
            SGIHService.cadastrar_ativo(
                self.ent_pat.get(), self.ent_serie.get(), self.ent_modelo.get(), self.ent_fab.get(), 1, 1, self.ent_valor.get()
            )
            self.ent_pat.delete(0, "end")
            self.ent_serie.delete(0, "end")
            self.ent_modelo.delete(0, "end")
            self.ent_fab.delete(0, "end")
            self.ent_valor.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Sucesso", "Ativo cadastrado com status 'Disponível'!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def baixar_ativo(self):
        sel = self.tree_ativos.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um ativo na tabela primeiro.")
            return
        ativo_id = self.tree_ativos.item(sel[0])["values"][0]
        try:
            SGIHService.baixar_ativo(ativo_id, self.ent_motivo_baixa.get())
            self.ent_motivo_baixa.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Baixa Efetuada", "Ativo baixado com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def consumir_licenca(self):
        sel = self.tree_lic.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma licença na tabela primeiro.")
            return
        lic_id = self.tree_lic.item(sel[0])["values"][0]
        try:
            SGIHService.consumir_assento_licenca(lic_id)
            self.atualizar_tudo()
            messagebox.showinfo("Sucesso", "Assento de licença associado!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 4: MOVIMENTAÇÃO & TERMO (UC03) ====================
    def _build_tab_movimentacao(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="4. Movimentar Ativo (UC03)")

        box = ttk.LabelFrame(tab, text="Alocação, Empréstimo ou Devolução de Ativos", padding=15)
        box.pack(fill="x", padx=20, pady=20)

        ttk.Label(box, text="Ativo:").grid(row=0, column=0, sticky="w", pady=6)
        self.cb_mov_ativo = ttk.Combobox(box, state="readonly", width=45)
        self.cb_mov_ativo.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(box, text="Operação:").grid(row=1, column=0, sticky="w", pady=6)
        self.cb_mov_tipo = ttk.Combobox(box, values=["Alocação", "Empréstimo", "Devolução"], state="readonly", width=45)
        self.cb_mov_tipo.set("Alocação")
        self.cb_mov_tipo.grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(box, text="Colaborador (para Alocação/Empréstimo):").grid(row=2, column=0, sticky="w", pady=6)
        self.cb_mov_colab = ttk.Combobox(box, state="readonly", width=45)
        self.cb_mov_colab.grid(row=2, column=1, padx=8, pady=6)

        ttk.Label(box, text="Observação / Inspeção:").grid(row=3, column=0, sticky="w", pady=6)
        self.ent_mov_obs = ttk.Entry(box, width=48)
        self.ent_mov_obs.grid(row=3, column=1, padx=8, pady=6)

        self.var_avaria = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            box, text="Devolução com Avaria (FA2: encaminha automaticamente para Ordem de Manutenção)", variable=self.var_avaria
        ).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Button(box, text="Confirmar Movimentação e Gerar Termo", command=self.executar_movimentacao).grid(row=5, column=1, sticky="e", pady=12)

    def atualizar_combos_movimentacao(self):
        ativos = SGIHService.listar_ativos()
        self.map_ativos = {f"{a['id']} - {a['patrimonio']} ({a['modelo']}) [{a['status']}]": a["id"] for a in ativos}
        self.cb_mov_ativo["values"] = list(self.map_ativos.keys())

        colabs = SGIHService.listar_colaboradores()
        self.map_colabs = {f"{c['id']} - {c['nome']}": c["id"] for c in colabs}
        self.cb_mov_colab["values"] = list(self.map_colabs.keys())

    def executar_movimentacao(self):
        try:
            ativo_id = self.map_ativos.get(self.cb_mov_ativo.get())
            colab_id = self.map_colabs.get(self.cb_mov_colab.get())
            termo = SGIHService.movimentar_ativo(
                ativo_id, colab_id, self.cb_mov_tipo.get(), observacao=self.ent_mov_obs.get(), com_avaria=self.var_avaria.get()
            )
            self.ent_mov_obs.delete(0, "end")
            self.var_avaria.set(False)
            self.atualizar_tudo()
            msg = "Movimentação registrada com sucesso!"
            if termo:
                msg += f"\n\nTermo de Responsabilidade gerado em:\n{termo}"
            messagebox.showinfo("Sucesso", msg)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 5: HELPDESK (UC04, UC05, UC06) ====================
    def _build_tab_helpdesk(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="5. Helpdesk (UC04-06)")

        # UC04 - Abrir Chamado
        top = ttk.LabelFrame(tab, text="Abrir Novo Chamado (UC04)", padding=8)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(top, text="Solicitante:").grid(row=0, column=0, padx=4)
        self.cb_ch_sol = ttk.Combobox(top, state="readonly", width=25)
        self.cb_ch_sol.grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Urgência:").grid(row=0, column=2, padx=4)
        self.cb_ch_urg = ttk.Combobox(top, values=["Baixa", "Média", "Alta", "Crítica"], state="readonly", width=12)
        self.cb_ch_urg.set("Média")
        self.cb_ch_urg.grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Descrição:").grid(row=0, column=4, padx=4)
        self.ent_ch_desc = ttk.Entry(top, width=38)
        self.ent_ch_desc.grid(row=0, column=5, padx=4)

        ttk.Button(top, text="Registrar Chamado", command=self.abrir_chamado).grid(row=0, column=6, padx=6)

        # Lista de Chamados
        cols = ("ID", "Protocolo", "Solicitante", "Urgência", "Status", "Prazo SLA", "Solução / Avaliação")
        self.tree_chamados = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree_chamados.heading(c, text=c)
            self.tree_chamados.column(c, width=150 if c != "ID" else 40)
        self.tree_chamados.pack(fill="both", expand=True, padx=10, pady=5)

        # UC05 e UC06 - Atender / Resolver / Avaliar
        bottom = ttk.LabelFrame(tab, text="Atendimento Técnico (UC05) e Avaliação/Reabertura (UC06)", padding=8)
        bottom.pack(fill="x", padx=10, pady=6)

        ttk.Label(bottom, text="Parecer / Solução:").grid(row=0, column=0, padx=4)
        self.ent_ch_solucao = ttk.Entry(bottom, width=42)
        self.ent_ch_solucao.grid(row=0, column=1, padx=4)

        ttk.Button(bottom, text="Colocar Em Atendimento", command=lambda: self.atualizar_chamado("Em Atendimento")).grid(row=0, column=2, padx=4)
        ttk.Button(bottom, text="Marcar como Resolvido", command=lambda: self.atualizar_chamado("Resolvido")).grid(row=0, column=3, padx=4)

        ttk.Label(bottom, text="Nota (1-5):").grid(row=1, column=0, padx=4, pady=6)
        self.cb_ch_nota = ttk.Combobox(bottom, values=[5, 4, 3, 2, 1], state="readonly", width=5)
        self.cb_ch_nota.set(5)
        self.cb_ch_nota.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(bottom, text="Avaliar e Fechar (UC06)", command=lambda: self.avaliar_chamado("Fechar")).grid(row=1, column=2, padx=4)
        ttk.Button(bottom, text="Reabrir Chamado (FA1)", command=lambda: self.avaliar_chamado("Reabrir")).grid(row=1, column=3, padx=4)

    def atualizar_chamados(self):
        colabs = SGIHService.listar_colaboradores()
        self.map_sol = {f"{c['id']} - {c['nome']}": c["id"] for c in colabs}
        self.cb_ch_sol["values"] = list(self.map_sol.keys())
        if self.map_sol:
            self.cb_ch_sol.current(0)

        for item in self.tree_chamados.get_children():
            self.tree_chamados.delete(item)
        for ch in SGIHService.listar_chamados():
            resumo = f"{ch['solucao'] or ''} (Nota: {ch['nota_avaliacao'] or '-'})"
            self.tree_chamados.insert(
                "", "end",
                values=(ch["id"], ch["protocolo"], ch["solicitante_nome"], ch["urgencia"], ch["status"], ch["prazo_sla"], resumo)
            )

    def abrir_chamado(self):
        try:
            sol_id = self.map_sol.get(self.cb_ch_sol.get())
            prot = SGIHService.abrir_chamado(sol_id, None, 3, self.cb_ch_urg.get(), self.ent_ch_desc.get())
            self.ent_ch_desc.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Chamado Aberto", f"Protocolo gerado: {prot}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def atualizar_chamado(self, status):
        sel = self.tree_chamados.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um chamado na tabela primeiro.")
            return
        ch_id = self.tree_chamados.item(sel[0])["values"][0]
        SGIHService.atender_resolver_chamado(ch_id, 2, status, self.ent_ch_solucao.get())
        self.atualizar_tudo()

    def avaliar_chamado(self, acao):
        sel = self.tree_chamados.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um chamado na tabela primeiro.")
            return
        ch_id = self.tree_chamados.item(sel[0])["values"][0]
        try:
            SGIHService.avaliar_ou_reabrir_chamado(ch_id, acao, self.cb_ch_nota.get(), self.ent_ch_solucao.get())
            self.atualizar_tudo()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ==================== ABA 6: MANUTENÇÃO (UC07) ====================
    def _build_tab_manutencao(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="6. Manutenção (UC07)")

        top = ttk.LabelFrame(tab, text="Abrir Ordem de Manutenção", padding=8)
        top.pack(fill="x", padx=10, pady=6)

        ttk.Label(top, text="Ativo:").grid(row=0, column=0, padx=4)
        self.cb_om_ativo = ttk.Combobox(top, state="readonly", width=35)
        self.cb_om_ativo.grid(row=0, column=1, padx=4)

        ttk.Label(top, text="Falha:").grid(row=0, column=2, padx=4)
        self.ent_om_falha = ttk.Entry(top, width=35)
        self.ent_om_falha.grid(row=0, column=3, padx=4)

        ttk.Button(top, text="Abrir OM", command=self.abrir_om).grid(row=0, column=4, padx=6)

        cols = ("ID", "Patrimônio", "Modelo", "Tipo", "Falha", "Custo (R$)", "Status")
        self.tree_om = ttk.Treeview(tab, columns=cols, show="headings", height=11)
        for c in cols:
            self.tree_om.heading(c, text=c)
            self.tree_om.column(c, width=145 if c != "ID" else 40)
        self.tree_om.pack(fill="both", expand=True, padx=10, pady=5)

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=10, pady=8)
        ttk.Label(bottom, text="Custo Reparo (R$):").pack(side="left", padx=4)
        self.ent_om_custo = ttk.Entry(bottom, width=12)
        self.ent_om_custo.pack(side="left", padx=4)

        ttk.Label(bottom, text="Parecer Técnico:").pack(side="left", padx=4)
        self.ent_om_parecer = ttk.Entry(bottom, width=35)
        self.ent_om_parecer.pack(side="left", padx=4)

        self.var_inviavel = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Perda Total / Inviável (Baixa Automática)", variable=self.var_inviavel).pack(side="left", padx=6)
        ttk.Button(bottom, text="Encerrar OM", command=self.encerrar_om).pack(side="left", padx=6)

    def atualizar_manutencoes(self):
        ativos = SGIHService.listar_ativos()
        self.map_om_ativos = {f"{a['id']} - {a['patrimonio']} ({a['modelo']})": a["id"] for a in ativos}
        self.cb_om_ativo["values"] = list(self.map_om_ativos.keys())

        for item in self.tree_om.get_children():
            self.tree_om.delete(item)
        for om in SGIHService.listar_ordens_manutencao():
            self.tree_om.insert(
                "", "end",
                values=(om["id"], om["patrimonio"], om["modelo"], om["tipo"], om["falha"], f"{om['custo']:.2f}", om["status"])
            )

    def abrir_om(self):
        try:
            ativo_id = self.map_om_ativos.get(self.cb_om_ativo.get())
            SGIHService.abrir_ordem_manutencao(ativo_id, "Corretiva", "Interna", self.ent_om_falha.get())
            self.ent_om_falha.delete(0, "end")
            self.atualizar_tudo()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def encerrar_om(self):
        sel = self.tree_om.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma Ordem de Manutenção na tabela primeiro.")
            return
        om_id = self.tree_om.item(sel[0])["values"][0]
        try:
            SGIHService.encerrar_ordem_manutencao(om_id, self.ent_om_custo.get(), self.ent_om_parecer.get(), self.var_inviavel.get())
            self.ent_om_custo.delete(0, "end")
            self.ent_om_parecer.delete(0, "end")
            self.var_inviavel.set(False)
            self.atualizar_tudo()
            messagebox.showinfo("OM Encerrada", "Ordem de Manutenção finalizada e status do ativo atualizado!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))