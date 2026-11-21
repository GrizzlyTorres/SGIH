import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "sgih.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_transaction():
    """Garante commit/rollback automático e fechamento seguro da conexão SQLite."""
    with closing(get_connection()) as conn:
        with conn:
            yield conn


def init_db():
    with db_transaction() as conn:
        cur = conn.cursor()

        # UC01 - Cadastros Básicos
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS setores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            localizacao TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL, -- 'Ativo' ou 'Chamado'
            sla_horas INTEGER DEFAULT 24,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            contato TEXT,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            perfil TEXT DEFAULT 'Colaborador', -- 'Administrador', 'Tecnico', 'Colaborador'
            setor_id INTEGER,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (setor_id) REFERENCES setores(id)
        );

        -- UC02 - Ativos e Licenças
        CREATE TABLE IF NOT EXISTS ativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio TEXT UNIQUE NOT NULL,
            num_serie TEXT UNIQUE NOT NULL,
            modelo TEXT NOT NULL,
            fabricante TEXT,
            categoria_id INTEGER,
            fornecedor_id INTEGER,
            setor_id INTEGER,
            colaborador_id INTEGER,
            valor REAL DEFAULT 0.0,
            data_compra TEXT,
            garantia_meses INTEGER DEFAULT 12,
            status TEXT DEFAULT 'Disponível', -- 'Disponível', 'Em Uso', 'Emprestado', 'Em Manutenção', 'Baixado'
            motivo_baixa TEXT,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
            FOREIGN KEY (setor_id) REFERENCES setores(id),
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        );

        CREATE TABLE IF NOT EXISTS licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            software TEXT NOT NULL,
            chave_produto TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL, -- 'Assinatura' ou 'Perpétua'
            assentos_totais INTEGER DEFAULT 1,
            assentos_disponiveis INTEGER DEFAULT 1,
            validade TEXT,
            ativo INTEGER DEFAULT 1
        );

        -- Relacionamento Ativo 1..* LicencaSoftware (UC02 - FA1 e FA2)
        CREATE TABLE IF NOT EXISTS ativo_licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id INTEGER NOT NULL,
            licenca_id INTEGER NOT NULL,
            data_vinculo TEXT NOT NULL,
            UNIQUE(ativo_id, licenca_id),
            FOREIGN KEY (ativo_id) REFERENCES ativos(id) ON DELETE CASCADE,
            FOREIGN KEY (licenca_id) REFERENCES licencas(id)
        );

        -- UC03 - Movimentações (Histórico Imutável)
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id INTEGER NOT NULL,
            colaborador_id INTEGER,
            tipo TEXT NOT NULL, -- 'Alocação', 'Empréstimo', 'Devolução', 'Baixa'
            data_movimentacao TEXT NOT NULL,
            data_prevista_devolucao TEXT,
            observacao TEXT,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id),
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        );

        -- UC04, UC05, UC06 - Helpdesk e SLA
        CREATE TABLE IF NOT EXISTS chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE NOT NULL,
            solicitante_id INTEGER NOT NULL,
            tecnico_id INTEGER,
            ativo_id INTEGER,
            categoria_id INTEGER,
            urgencia TEXT NOT NULL, -- 'Baixa', 'Média', 'Alta', 'Crítica'
            descricao TEXT NOT NULL,
            status TEXT DEFAULT 'Aberto', -- 'Aberto', 'Em Atendimento', 'Aguardando Usuário', 'Resolvido', 'Fechado', 'Reaberto', 'Cancelado'
            data_abertura TEXT NOT NULL,
            prazo_sla TEXT NOT NULL,
            data_resolucao TEXT,
            solucao TEXT,
            nota_avaliacao INTEGER,
            FOREIGN KEY (solicitante_id) REFERENCES colaboradores(id),
            FOREIGN KEY (tecnico_id) REFERENCES colaboradores(id),
            FOREIGN KEY (ativo_id) REFERENCES ativos(id),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        );

        -- UC07 - Ordens de Manutenção e Peças (Diagrama de Classes)
        CREATE TABLE IF NOT EXISTS ordens_manutencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id INTEGER NOT NULL,
            tipo TEXT NOT NULL, -- 'Corretiva' ou 'Preventiva'
            local_execucao TEXT NOT NULL, -- 'Interna' ou 'Externa'
            falha TEXT NOT NULL,
            custo REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Aberta', -- 'Aberta', 'Concluída', 'Inviável'
            parecer_final TEXT,
            data_abertura TEXT NOT NULL,
            data_fechamento TEXT,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        );

        CREATE TABLE IF NOT EXISTS om_pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            om_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            valor_unitario REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (om_id) REFERENCES ordens_manutencao(id) ON DELETE CASCADE
        );
        """)

        # Popula dados iniciais se o banco estiver vazio
        cur.execute("SELECT COUNT(*) FROM setores")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO setores (nome, localizacao) VALUES (?, ?)",
                [
                    ("Tecnologia da Informação", "Bloco A - 2º Andar"),
                    ("Recursos Humanos", "Bloco B - 1º Andar"),
                    ("Financeiro", "Bloco B - 3º Andar"),
                ],
            )
            cur.executemany(
                "INSERT INTO categorias (nome, tipo, sla_horas) VALUES (?, ?, ?)",
                [
                    ("Notebook", "Ativo", 24),
                    ("Monitor", "Ativo", 48),
                    ("Hardware / Periféricos", "Chamado", 8),
                    ("Sistemas e Acessos", "Chamado", 4),
                ],
            )
            cur.executemany(
                "INSERT INTO fornecedores (razao_social, cnpj, contato) VALUES (?, ?, ?)",
                [
                    ("Dell Computadores Ltda", "72.381.189/0001-10", "suporte@dell.com"),
                    ("TechRepair Assistência", "12.345.678/0001-99", "contato@techrepair.com.br"),
                ],
            )
            cur.executemany(
                "INSERT INTO colaboradores (nome, matricula, email, perfil, setor_id) VALUES (?, ?, ?, ?, ?)",
                [
                    ("Ana Silva (Gestora TI)", "MAT001", "ana.silva@empresa.com", "Administrador", 1),
                    ("Carlos Souza (Técnico)", "MAT002", "carlos.souza@empresa.com", "Tecnico", 1),
                    ("Mariana Costa (Analista RH)", "MAT003", "mariana.costa@empresa.com", "Colaborador", 2),
                ],
            )
            cur.executemany(
                """INSERT INTO ativos (patrimonio, num_serie, modelo, fabricante, categoria_id, fornecedor_id, setor_id, valor, data_compra, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    ("PAT-1001", "SN-DELL-9981", "Latitude 5440", "Dell", 1, 1, 1, 5800.00, "2026-01-15", "Disponível"),
                    ("PAT-1002", "SN-LG-4420", "UltraWide 29''", "LG", 2, 1, 2, 1450.00, "2026-02-10", "Disponível"),
                ],
            )
            cur.execute(
                """INSERT INTO licencas (software, chave_produto, tipo, assentos_totais, assentos_disponiveis, validade)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("Microsoft 365 Business", "XXXXX-YYYYY-ZZZZZ-12345", "Assinatura", 10, 9, "2027-01-01"),
            )

            agora = datetime.now()
            cur.execute(
                """INSERT INTO chamados (protocolo, solicitante_id, tecnico_id, ativo_id, categoria_id, urgencia, descricao, status, data_abertura, prazo_sla)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"CH-{agora.strftime('%Y%m%d')}-001",
                    3,
                    2,
                    1,
                    3,
                    "Alta",
                    "Notebook não reconhece segundo monitor via HDMI.",
                    "Em Atendimento",
                    agora.strftime("%Y-%m-%d %H:%M"),
                    (agora + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
                ),
            )