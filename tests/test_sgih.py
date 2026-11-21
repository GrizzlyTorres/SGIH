import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import database.db_manager as db_manager
import services.sgih_service as sgih_service
from services.sgih_service import SGIHService
from ui.app_window import SGIHApp


class TestSGIH(unittest.TestCase):
    def setUp(self):
        """Isola banco de dados e pasta de exportação em diretório temporário para cada teste."""
        self.temp_dir = tempfile.TemporaryDirectory()
        base_path = Path(self.temp_dir.name)

        self.db_patch = patch.object(db_manager, "DB_PATH", base_path / "test_sgih.db")
        self.export_patch = patch.object(sgih_service, "EXPORT_DIR", base_path)

        self.db_patch.start()
        self.export_patch.start()
        db_manager.init_db()

    def tearDown(self):
        self.export_patch.stop()
        self.db_patch.stop()
        # No Windows, o cleanup valida também que nenhuma conexão SQLite ficou aberta
        self.temp_dir.cleanup()

    # ==================== UC01: Cadastros Básicos ====================
    def test_uc01_cadastrar_e_inativar_colaborador(self):
        SGIHService.cadastrar_colaborador("Lucas Pereira", "MAT900", "lucas@empresa.com", "Tecnico", 1)
        ativos = SGIHService.listar_colaboradores(apenas_ativos=True)
        novo = next((c for c in ativos if c["matricula"] == "MAT900"), None)
        self.assertIsNotNone(novo)
        self.assertEqual(novo["setor_nome"], "Tecnologia da Informação")

        # Duplicidade de matrícula/e-mail deve falhar
        with self.assertRaises(ValueError):
            SGIHService.cadastrar_colaborador("Outro Nome", "MAT900", "outro@empresa.com", "Colaborador", 1)

        # Inativação lógica (FA1)
        SGIHService.inativar_colaborador(novo["id"])
        ativos_pos = SGIHService.listar_colaboradores(apenas_ativos=True)
        self.assertFalse(any(c["id"] == novo["id"] for c in ativos_pos))

        todos = SGIHService.listar_colaboradores(apenas_ativos=False)
        self.assertTrue(any(c["id"] == novo["id"] and c["ativo"] == 0 for c in todos))

    # ==================== UC02: Ativos e Licenças ====================
    def test_uc02_cadastrar_ativo_com_virgula_e_vincular_licenca(self):
        SGIHService.cadastrar_ativo("PAT-2001", "SN-9999", "ThinkPad T14", "Lenovo", 1, 1, "4.599,90")
        ativos = SGIHService.listar_ativos()
        ativo = next(a for a in ativos if a["patrimonio"] == "PAT-2001")
        self.assertEqual(ativo["status"], "Disponível")
        self.assertAlmostEqual(ativo["valor"], 4599.90)

        # Associa licença ao ativo (FA2)
        lic_antes = SGIHService.listar_licencas()[0]
        SGIHService.consumir_assento_licenca(lic_antes["id"], ativo_id=ativo["id"])

        lic_depois = SGIHService.listar_licencas()[0]
        self.assertEqual(lic_depois["assentos_disponiveis"], lic_antes["assentos_disponiveis"] - 1)
        self.assertEqual(len(SGIHService.listar_licencas_ativo(ativo["id"])), 1)

        # Baixa patrimonial deve liberar o assento da licença vinculada (FA1)
        SGIHService.baixar_ativo(ativo["id"], "Obsolescência")
        ativo_baixado = next(a for a in SGIHService.listar_ativos() if a["id"] == ativo["id"])
        self.assertEqual(ativo_baixado["status"], "Baixado")

        lic_final = SGIHService.listar_licencas()[0]
        self.assertEqual(lic_final["assentos_disponiveis"], lic_antes["assentos_disponiveis"])
        self.assertEqual(len(SGIHService.listar_licencas_ativo(ativo["id"])), 0)

    # ==================== UC03: Movimentação e Termo ====================
    def test_uc03_alocacao_termo_e_devolucao_normal(self):
        # Ativo 1 (PAT-1001) inicia Disponível; Colaborador 3 (Mariana)
        termo = SGIHService.movimentar_ativo(1, 3, "Alocação", observacao="Entrega inicial")
        self.assertIsNotNone(termo)
        self.assertTrue(Path(termo).exists())
        self.assertIn("PAT-1001", Path(termo).read_text(encoding="utf-8"))

        ativo = next(a for a in SGIHService.listar_ativos() if a["id"] == 1)
        self.assertEqual(ativo["status"], "Em Uso")
        self.assertEqual(ativo["colaborador_id"], 3)

        # Bloqueia alocação de ativo já em uso (FE1)
        with self.assertRaises(ValueError):
            SGIHService.movimentar_ativo(1, 2, "Alocação")

        # Devolução sem avaria retorna para Disponível (FA1)
        SGIHService.movimentar_ativo(1, None, "Devolução", observacao="Sem avarias")
        ativo_dev = next(a for a in SGIHService.listar_ativos() if a["id"] == 1)
        self.assertEqual(ativo_dev["status"], "Disponível")
        self.assertIsNone(ativo_dev["colaborador_id"])

    def test_uc03_devolucao_com_avaria_abre_om_automatica(self):
        SGIHService.movimentar_ativo(1, 3, "Empréstimo", data_prevista="2026-12-01")
        SGIHService.movimentar_ativo(1, None, "Devolução", observacao="Tela trincada", com_avaria=True)

        ativo = next(a for a in SGIHService.listar_ativos() if a["id"] == 1)
        self.assertEqual(ativo["status"], "Em Manutenção")

        oms = SGIHService.listar_ordens_manutencao()
        self.assertEqual(len(oms), 1)
        self.assertIn("Tela trincada", oms[0]["falha"])

    # ==================== UC04, UC05, UC06: Helpdesk ====================
    def test_uc04_05_06_ciclo_completo_chamado(self):
        # Abertura com vínculo de ativo e urgência Crítica (UC04)
        protocolo = SGIHService.abrir_chamado(3, 1, 3, "Crítica", "Sistema travando ao abrir planilhas")
        self.assertTrue(protocolo.startswith("CH-"))

        chamado = next(c for c in SGIHService.listar_chamados() if c["protocolo"] == protocolo)
        self.assertEqual(chamado["status"], "Aberto")
        self.assertEqual(chamado["ativo_id"], 1)

        # Atendimento e Resolução (UC05)
        SGIHService.atender_resolver_chamado(chamado["id"], 2, "Em Atendimento", "Analisando logs")
        SGIHService.atender_resolver_chamado(chamado["id"], 2, "Resolvido", "Memória RAM substituída")

        # Reabertura sem justificativa deve falhar (UC06 - FA1)
        with self.assertRaises(ValueError):
            SGIHService.avaliar_ou_reabrir_chamado(chamado["id"], "Reabrir", justificativa="")

        # Reabertura com justificativa e posterior fechamento com nota
        SGIHService.avaliar_ou_reabrir_chamado(chamado["id"], "Reabrir", justificativa="Voltou a travar")
        reaberto = next(c for c in SGIHService.listar_chamados() if c["id"] == chamado["id"])
        self.assertEqual(reaberto["status"], "Reaberto")

        SGIHService.avaliar_ou_reabrir_chamado(chamado["id"], "Fechar", nota=5)
        fechado = next(c for c in SGIHService.listar_chamados() if c["id"] == chamado["id"])
        self.assertEqual(fechado["status"], "Fechado")
        self.assertEqual(fechado["nota_avaliacao"], 5)

        # Chamado fechado não pode ser alterado
        with self.assertRaises(ValueError):
            SGIHService.atender_resolver_chamado(chamado["id"], 2, "Em Atendimento", "Tentativa inválida")

    # ==================== UC07: Ordem de Manutenção ====================
    def test_uc07_ordem_manutencao_pecas_e_inviabilidade(self):
        SGIHService.abrir_ordem_manutencao(2, "Corretiva", "Externa", "Fonte queimada")
        om = SGIHService.listar_ordens_manutencao()[0]
        self.assertEqual(om["status"], "Aberta")

        # Adiciona peça e encerra com perda total / inviabilidade (FA1)
        SGIHService.adicionar_peca_om(om["id"], "Placa lógica", 1, "350,00")
        SGIHService.encerrar_ordem_manutencao(om["id"], "100,00", "Reparo inviável", inviavel=True)

        om_enc = SGIHService.listar_ordens_manutencao()[0]
        self.assertEqual(om_enc["status"], "Inviável")
        self.assertAlmostEqual(om_enc["custo"], 450.00)

        ativo = next(a for a in SGIHService.listar_ativos() if a["id"] == 2)
        self.assertEqual(ativo["status"], "Baixado")

        # Não deve permitir encerrar novamente a mesma OM
        with self.assertRaises(ValueError):
            SGIHService.encerrar_ordem_manutencao(om["id"], 0, "Novo parecer", inviavel=False)

    # ==================== UC08: KPIs e Exportação CSV ====================
    def test_uc08_kpis_e_exportacao_csv(self):
        kpis = SGIHService.obter_kpis()
        self.assertEqual(kpis["total_ativos"], 2)
        self.assertEqual(kpis["ativos_disponiveis"], 2)
        self.assertEqual(kpis["chamados_abertos"], 1)

        csv_path = Path(SGIHService.exportar_relatorio_csv())
        self.assertTrue(csv_path.exists())
        conteudo = csv_path.read_text(encoding="utf-8-sig")
        self.assertIn("Protocolo;Urgência;Status", conteudo)

    # ==================== UI: Smoke Test ====================
    def test_ui_inicializacao_e_helpers(self):
        try:
            app = SGIHApp()
        except tk.TclError:
            self.skipTest("Ambiente sem servidor gráfico disponível para Tkinter.")

        try:
            app.withdraw()
            app.update_idletasks()
            self.assertEqual(len(app.notebook.tabs()), 6)
            self.assertAlmostEqual(app._parse_numero("1.250,75"), 1250.75)
            self.assertIsNone(app._parse_numero("abc"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()