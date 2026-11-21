import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from database.db_manager import db_transaction

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


def _to_float(valor, default=0.0):
    if valor is None or str(valor).strip() == "":
        return default
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


class SGIHService:
    @staticmethod
    def _liberar_licencas_ativo(conn, ativo_id):
        """Desvincula licenças associadas ao ativo e devolve assentos (UC02 - FA1)."""
        vinculos = conn.execute(
            "SELECT licenca_id FROM ativo_licencas WHERE ativo_id = ?", (ativo_id,)
        ).fetchall()
        for v in vinculos:
            conn.execute(
                """UPDATE licencas
                   SET assentos_disponiveis = MIN(assentos_totais, assentos_disponiveis + 1)
                   WHERE id = ?""",
                (v["licenca_id"],),
            )
        conn.execute("DELETE FROM ativo_licencas WHERE ativo_id = ?", (ativo_id,))

    # --- UC01: Cadastros Básicos ---
    @staticmethod
    def listar_colaboradores(apenas_ativos=True):
        with db_transaction() as conn:
            sql = """
                SELECT c.*, s.nome AS setor_nome
                FROM colaboradores c
                LEFT JOIN setores s ON c.setor_id = s.id
            """
            if apenas_ativos:
                sql += " WHERE c.ativo = 1"
            return conn.execute(sql).fetchall()

    @staticmethod
    def cadastrar_colaborador(nome, matricula, email, perfil, setor_id):
        if not nome or not matricula or not email:
            raise ValueError("Nome, matrícula e e-mail são obrigatórios.")
        try:
            with db_transaction() as conn:
                conn.execute(
                    "INSERT INTO colaboradores (nome, matricula, email, perfil, setor_id) VALUES (?, ?, ?, ?, ?)",
                    (nome, matricula, email, perfil, setor_id),
                )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Matrícula ou e-mail já cadastrado: {e}")

    @staticmethod
    def inativar_colaborador(colab_id):
        with db_transaction() as conn:
            # FA1: Inativação lógica preservando histórico
            conn.execute("UPDATE colaboradores SET ativo = 0 WHERE id = ?", (colab_id,))

    @staticmethod
    def listar_auxiliares():
        with db_transaction() as conn:
            setores = conn.execute("SELECT * FROM setores WHERE ativo = 1").fetchall()
            categorias = conn.execute("SELECT * FROM categorias WHERE ativo = 1").fetchall()
            fornecedores = conn.execute("SELECT * FROM fornecedores WHERE ativo = 1").fetchall()
            return setores, categorias, fornecedores

    # --- UC02: Ativos e Licenças ---
    @staticmethod
    def listar_ativos():
        with db_transaction() as conn:
            return conn.execute("""
                SELECT a.*, c.nome AS categoria_nome, s.nome AS setor_nome, col.nome AS responsavel_nome
                FROM ativos a
                LEFT JOIN categorias c ON a.categoria_id = c.id
                LEFT JOIN setores s ON a.setor_id = s.id
                LEFT JOIN colaboradores col ON a.colaborador_id = col.id
                ORDER BY a.id DESC
            """).fetchall()

    @staticmethod
    def cadastrar_ativo(patrimonio, num_serie, modelo, fabricante, categoria_id, fornecedor_id, valor):
        if not patrimonio or not num_serie or not modelo:
            raise ValueError("Patrimônio, número de série e modelo são obrigatórios.")
        valor_float = _to_float(valor, 0.0)
        try:
            with db_transaction() as conn:
                conn.execute(
                    """INSERT INTO ativos (patrimonio, num_serie, modelo, fabricante, categoria_id, fornecedor_id, valor, data_compra, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Disponível')""",
                    (
                        patrimonio,
                        num_serie,
                        modelo,
                        fabricante,
                        categoria_id,
                        fornecedor_id,
                        valor_float,
                        datetime.now().strftime("%Y-%m-%d"),
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Patrimônio ou número de série já cadastrado: {e}")

    @staticmethod
    def baixar_ativo(ativo_id, motivo):
        if not motivo:
            raise ValueError("Informe o motivo da baixa patrimonial.")
        with db_transaction() as conn:
            ativo = conn.execute("SELECT * FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
            if not ativo:
                raise ValueError("Ativo não encontrado.")
            if ativo["status"] == "Baixado":
                raise ValueError("Este ativo já possui baixa patrimonial registrada.")
            if ativo["status"] == "Em Manutenção":
                raise ValueError("Não é possível baixar diretamente um ativo em manutenção. Encerre a OM como inviável.")

            agora = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute(
                "UPDATE ativos SET status = 'Baixado', colaborador_id = NULL, motivo_baixa = ? WHERE id = ?",
                (motivo, ativo_id),
            )
            SGIHService._liberar_licencas_ativo(conn, ativo_id)
            conn.execute(
                "INSERT INTO movimentacoes (ativo_id, tipo, data_movimentacao, observacao) VALUES (?, 'Baixa', ?, ?)",
                (ativo_id, agora, f"Baixa patrimonial: {motivo}"),
            )

    @staticmethod
    def listar_licencas():
        with db_transaction() as conn:
            return conn.execute("SELECT * FROM licencas WHERE ativo = 1").fetchall()

    @staticmethod
    def listar_licencas_ativo(ativo_id):
        with db_transaction() as conn:
            return conn.execute(
                """SELECT al.id AS vinculo_id, al.data_vinculo, l.*
                   FROM ativo_licencas al
                   JOIN licencas l ON al.licenca_id = l.id
                   WHERE al.ativo_id = ?""",
                (ativo_id,),
            ).fetchall()

    @staticmethod
    def consumir_assento_licenca(licenca_id, ativo_id=None):
        with db_transaction() as conn:
            lic = conn.execute("SELECT * FROM licencas WHERE id = ?", (licenca_id,)).fetchone()
            if not lic or lic["assentos_disponiveis"] <= 0:
                raise ValueError("Não há assentos disponíveis para esta licença.")

            if ativo_id is not None:
                ativo = conn.execute("SELECT status FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
                if not ativo:
                    raise ValueError("Ativo não encontrado.")
                if ativo["status"] == "Baixado":
                    raise ValueError("Não é possível vincular licenças a um ativo baixado.")
                try:
                    conn.execute(
                        "INSERT INTO ativo_licencas (ativo_id, licenca_id, data_vinculo) VALUES (?, ?, ?)",
                        (ativo_id, licenca_id, datetime.now().strftime("%Y-%m-%d %H:%M")),
                    )
                except sqlite3.IntegrityError:
                    raise ValueError("Esta licença já está vinculada ao ativo selecionado.")

            conn.execute(
                "UPDATE licencas SET assentos_disponiveis = assentos_disponiveis - 1 WHERE id = ?",
                (licenca_id,),
            )

    # --- UC03: Movimentar Ativo + Termo de Responsabilidade ---
    @staticmethod
    def listar_movimentacoes(ativo_id=None):
        with db_transaction() as conn:
            sql = """
                SELECT m.*, a.patrimonio, a.modelo, col.nome AS colaborador_nome
                FROM movimentacoes m
                JOIN ativos a ON m.ativo_id = a.id
                LEFT JOIN colaboradores col ON m.colaborador_id = col.id
            """
            params = ()
            if ativo_id is not None:
                sql += " WHERE m.ativo_id = ?"
                params = (ativo_id,)
            sql += " ORDER BY m.id DESC"
            return conn.execute(sql, params).fetchall()

    @staticmethod
    def movimentar_ativo(ativo_id, colaborador_id, tipo, data_prevista="", observacao="", com_avaria=False):
        with db_transaction() as conn:
            ativo = conn.execute("SELECT * FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
            if not ativo:
                raise ValueError("Ativo não encontrado.")

            agora = datetime.now().strftime("%Y-%m-%d %H:%M")
            termo_path = None

            if tipo in ("Alocação", "Empréstimo"):
                if ativo["status"] != "Disponível":
                    raise ValueError(f"Ativo indisponível (status atual: {ativo['status']}).")
                if not colaborador_id:
                    raise ValueError("Selecione um colaborador para realizar a alocação ou empréstimo.")
                novo_status = "Em Uso" if tipo == "Alocação" else "Emprestado"
                colab = conn.execute("SELECT * FROM colaboradores WHERE id = ?", (colaborador_id,)).fetchone()
                if not colab:
                    raise ValueError("Colaborador não encontrado.")

                conn.execute(
                    "UPDATE ativos SET status = ?, colaborador_id = ?, setor_id = ? WHERE id = ?",
                    (novo_status, colaborador_id, colab["setor_id"], ativo_id),
                )
                conn.execute(
                    """INSERT INTO movimentacoes (ativo_id, colaborador_id, tipo, data_movimentacao, data_prevista_devolucao, observacao)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (ativo_id, colaborador_id, tipo, agora, data_prevista, observacao),
                )

                termo_path = EXPORT_DIR / f"Termo_{ativo['patrimonio']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                termo_texto = (
                    f"=== TERMO DE RESPONSABILIDADE DE ATIVO DE TI (SGIH) ===\n"
                    f"Data/Hora: {agora}\n"
                    f"Modalidade: {tipo}\n"
                    f"Colaborador: {colab['nome']} (Matrícula: {colab['matricula']})\n"
                    f"Equipamento: {ativo['modelo']} | Patrimônio: {ativo['patrimonio']} | Série: {ativo['num_serie']}\n"
                    f"Devolução Prevista: {data_prevista or 'Indeterminada'}\n\n"
                    f"Declaro ter recebido o equipamento acima em perfeitas condições de uso, assumindo\n"
                    f"a responsabilidade pela sua guarda e conservação conforme políticas internas de TI.\n\n"
                    f"Assinatura do Colaborador: _________________________________________\n"
                )
                termo_path.write_text(termo_texto, encoding="utf-8")

            elif tipo == "Devolução":
                if ativo["status"] not in ("Em Uso", "Emprestado"):
                    raise ValueError("Este ativo não está alocado/emprestado para devolução.")
                novo_status = "Em Manutenção" if com_avaria else "Disponível"
                conn.execute(
                    "UPDATE ativos SET status = ?, colaborador_id = NULL WHERE id = ?",
                    (novo_status, ativo_id),
                )
                conn.execute(
                    "INSERT INTO movimentacoes (ativo_id, colaborador_id, tipo, data_movimentacao, observacao) VALUES (?, ?, 'Devolução', ?, ?)",
                    (ativo_id, ativo["colaborador_id"], agora, observacao),
                )
                # FA2: Se devolvido com avaria, abre Ordem de Manutenção na mesma transação
                if com_avaria:
                    conn.execute(
                        """INSERT INTO ordens_manutencao (ativo_id, tipo, local_execucao, falha, data_abertura)
                           VALUES (?, 'Corretiva', 'Interna', ?, ?)""",
                        (ativo_id, f"Avaria detectada na devolução: {observacao}", agora),
                    )

            return str(termo_path) if termo_path else None

    # --- UC04, UC05, UC06: Helpdesk ---
    @staticmethod
    def listar_chamados():
        with db_transaction() as conn:
            return conn.execute("""
                SELECT ch.*, s.nome AS solicitante_nome, t.nome AS tecnico_nome, a.patrimonio AS ativo_patrimonio
                FROM chamados ch
                LEFT JOIN colaboradores s ON ch.solicitante_id = s.id
                LEFT JOIN colaboradores t ON ch.tecnico_id = t.id
                LEFT JOIN ativos a ON ch.ativo_id = a.id
                ORDER BY ch.id DESC
            """).fetchall()

    @staticmethod
    def abrir_chamado(solicitante_id, ativo_id, categoria_id, urgencia, descricao):
        if not solicitante_id:
            raise ValueError("Selecione um colaborador solicitante.")
        if not descricao:
            raise ValueError("Descreva o problema para abrir o chamado.")
        with db_transaction() as conn:
            cat = conn.execute("SELECT sla_horas FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
            sla_horas = cat["sla_horas"] if cat else 24
            if urgencia == "Crítica":
                sla_horas = max(2, sla_horas // 2)

            agora = datetime.now()
            prazo_sla = agora + timedelta(hours=sla_horas)
            protocolo = f"CH-{agora.strftime('%Y%m%d-%H%M%S')}"

            conn.execute(
                """INSERT INTO chamados (protocolo, solicitante_id, ativo_id, categoria_id, urgencia, descricao, status, data_abertura, prazo_sla)
                   VALUES (?, ?, ?, ?, ?, ?, 'Aberto', ?, ?)""",
                (
                    protocolo,
                    solicitante_id,
                    ativo_id if ativo_id else None,
                    categoria_id,
                    urgencia,
                    descricao,
                    agora.strftime("%Y-%m-%d %H:%M"),
                    prazo_sla.strftime("%Y-%m-%d %H:%M"),
                ),
            )
            return protocolo

    @staticmethod
    def atender_resolver_chamado(chamado_id, tecnico_id, novo_status, solucao):
        if not tecnico_id:
            raise ValueError("Selecione um técnico responsável pelo atendimento.")
        with db_transaction() as conn:
            chamado = conn.execute("SELECT status FROM chamados WHERE id = ?", (chamado_id,)).fetchone()
            if not chamado:
                raise ValueError("Chamado não encontrado.")
            if chamado["status"] in ("Fechado", "Cancelado"):
                raise ValueError(f"Não é possível alterar um chamado com status '{chamado['status']}'.")

            data_res = datetime.now().strftime("%Y-%m-%d %H:%M") if novo_status == "Resolvido" else None
            conn.execute(
                """UPDATE chamados
                   SET tecnico_id = ?, status = ?, solucao = ?, data_resolucao = COALESCE(?, data_resolucao)
                   WHERE id = ?""",
                (tecnico_id, novo_status, solucao, data_res, chamado_id),
            )

    @staticmethod
    def avaliar_ou_reabrir_chamado(chamado_id, acao, nota=5, justificativa=""):
        with db_transaction() as conn:
            if acao == "Fechar":
                conn.execute(
                    "UPDATE chamados SET status = 'Fechado', nota_avaliacao = ? WHERE id = ?",
                    (int(nota), chamado_id),
                )
            elif acao == "Reabrir":
                if not justificativa:
                    raise ValueError("Justificativa obrigatória para reabrir o chamado.")
                conn.execute(
                    "UPDATE chamados SET status = 'Reaberto', solucao = COALESCE(solucao, '') || ' | [REABERTO]: ' || ? WHERE id = ?",
                    (justificativa, chamado_id),
                )

    # --- UC07: Ordem de Manutenção e Peças ---
    @staticmethod
    def listar_ordens_manutencao():
        with db_transaction() as conn:
            return conn.execute("""
                SELECT om.*, a.patrimonio, a.modelo
                FROM ordens_manutencao om
                JOIN ativos a ON om.ativo_id = a.id
                ORDER BY om.id DESC
            """).fetchall()

    @staticmethod
    def abrir_ordem_manutencao(ativo_id, tipo, local_execucao, falha):
        if not ativo_id:
            raise ValueError("Selecione um ativo para abrir a Ordem de Manutenção.")
        if not falha:
            raise ValueError("Informe a falha constatada.")
        with db_transaction() as conn:
            ativo = conn.execute("SELECT status FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
            if not ativo:
                raise ValueError("Ativo não encontrado.")
            if ativo["status"] == "Baixado":
                raise ValueError("Não é possível abrir Ordem de Manutenção para um ativo baixado.")
            if ativo["status"] == "Em Manutenção":
                raise ValueError("Este ativo já possui uma Ordem de Manutenção em andamento.")

            agora = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute(
                """INSERT INTO ordens_manutencao (ativo_id, tipo, local_execucao, falha, data_abertura)
                   VALUES (?, ?, ?, ?, ?)""",
                (ativo_id, tipo, local_execucao, falha, agora),
            )
            conn.execute("UPDATE ativos SET status = 'Em Manutenção' WHERE id = ?", (ativo_id,))

    @staticmethod
    def adicionar_peca_om(om_id, nome, quantidade, valor_unitario):
        if not nome or not str(nome).strip():
            raise ValueError("Informe o nome da peça.")
        qtd = int(quantidade)
        if qtd <= 0:
            raise ValueError("A quantidade de peças deve ser maior que zero.")
        valor_unit = _to_float(valor_unitario, 0.0)
        with db_transaction() as conn:
            om = conn.execute("SELECT status FROM ordens_manutencao WHERE id = ?", (om_id,)).fetchone()
            if not om:
                raise ValueError("Ordem de manutenção não encontrada.")
            if om["status"] != "Aberta":
                raise ValueError("Não é possível adicionar peças a uma Ordem de Manutenção já encerrada.")
            conn.execute(
                "INSERT INTO om_pecas (om_id, nome, quantidade, valor_unitario) VALUES (?, ?, ?, ?)",
                (om_id, nome.strip(), qtd, valor_unit),
            )

    @staticmethod
    def listar_pecas_om(om_id):
        with db_transaction() as conn:
            return conn.execute("SELECT * FROM om_pecas WHERE om_id = ? ORDER BY id", (om_id,)).fetchall()

    @staticmethod
    def encerrar_ordem_manutencao(om_id, custo, parecer, inviavel=False):
        custo_servico = _to_float(custo, 0.0)
        with db_transaction() as conn:
            om = conn.execute("SELECT * FROM ordens_manutencao WHERE id = ?", (om_id,)).fetchone()
            if not om:
                raise ValueError("Ordem de manutenção não encontrada.")
            if om["status"] != "Aberta":
                raise ValueError(f"Esta Ordem de Manutenção já foi encerrada (status: {om['status']}).")

            row_pecas = conn.execute(
                "SELECT COALESCE(SUM(quantidade * valor_unitario), 0) AS total FROM om_pecas WHERE om_id = ?",
                (om_id,),
            ).fetchone()
            custo_total = custo_servico + (float(row_pecas["total"]) if row_pecas else 0.0)

            agora = datetime.now().strftime("%Y-%m-%d %H:%M")
            status_om = "Inviável" if inviavel else "Concluída"
            conn.execute(
                """UPDATE ordens_manutencao
                   SET custo = ?, parecer_final = ?, status = ?, data_fechamento = ?
                   WHERE id = ?""",
                (custo_total, parecer, status_om, agora, om_id),
            )

            # FA1 (UC07): Inviabilidade aciona baixa patrimonial automática
            if inviavel:
                motivo_baixa = f"Perda total / Inviabilidade técnica (OM #{om_id})"
                conn.execute(
                    "UPDATE ativos SET status = 'Baixado', colaborador_id = NULL, motivo_baixa = ? WHERE id = ?",
                    (motivo_baixa, om["ativo_id"]),
                )
                SGIHService._liberar_licencas_ativo(conn, om["ativo_id"])
                conn.execute(
                    "INSERT INTO movimentacoes (ativo_id, tipo, data_movimentacao, observacao) VALUES (?, 'Baixa', ?, ?)",
                    (om["ativo_id"], agora, f"Baixa patrimonial automática: {motivo_baixa}"),
                )
            else:
                conn.execute("UPDATE ativos SET status = 'Disponível' WHERE id = ?", (om["ativo_id"],))

    # --- UC08: Indicadores Gerenciais, SLA e Exportação ---
    @staticmethod
    def obter_kpis():
        with db_transaction() as conn:
            total_ativos = conn.execute("SELECT COUNT(*) FROM ativos").fetchone()[0]
            ativos_disponiveis = conn.execute("SELECT COUNT(*) FROM ativos WHERE status = 'Disponível'").fetchone()[0]
            ativos_manutencao = conn.execute("SELECT COUNT(*) FROM ativos WHERE status = 'Em Manutenção'").fetchone()[0]
            chamados_abertos = conn.execute(
                "SELECT COUNT(*) FROM chamados WHERE status IN ('Aberto', 'Em Atendimento', 'Reaberto')"
            ).fetchone()[0]
            custo_manutencao = conn.execute("SELECT COALESCE(SUM(custo), 0) FROM ordens_manutencao").fetchone()[0]

            agora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            sla_violados = conn.execute(
                "SELECT COUNT(*) FROM chamados WHERE status NOT IN ('Resolvido', 'Fechado', 'Cancelado') AND prazo_sla < ?",
                (agora_str,),
            ).fetchone()[0]

            return {
                "total_ativos": total_ativos,
                "ativos_disponiveis": ativos_disponiveis,
                "ativos_manutencao": ativos_manutencao,
                "chamados_abertos": chamados_abertos,
                "sla_violados": sla_violados,
                "custo_manutencao": custo_manutencao,
            }

    @staticmethod
    def exportar_relatorio_csv():
        with db_transaction() as conn:
            chamados = conn.execute("SELECT * FROM chamados ORDER BY id").fetchall()
        arquivo = EXPORT_DIR / f"Relatorio_Chamados_SLA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Protocolo", "Urgência", "Status", "Abertura", "Prazo SLA", "Resolução", "Nota"])
            for c in chamados:
                writer.writerow([
                    c["id"], c["protocolo"], c["urgencia"], c["status"],
                    c["data_abertura"], c["prazo_sla"], c["data_resolucao"] or "-", c["nota_avaliacao"] or "-"
                ])
        return str(arquivo)