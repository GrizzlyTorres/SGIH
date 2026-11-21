🖥️ SGIH — Sistema de Gestão de Inventário e Helpdesk de Ativos de TI

Aplicação desktop desenvolvida em Python para integrar o controle do ciclo de vida de ativos de hardware e software ao gerenciamento de chamados de suporte técnico e monitoramento de SLA.

📋 Sobre o Projeto

O SGIH tem como objetivo centralizar a gestão patrimonial de TI e o atendimento de suporte técnico em uma única plataforma. Na dimensão de Inventário, o sistema controla o cadastro de equipamentos, licenças de software, alocações, devoluções, emissão de termos de responsabilidade e baixas patrimoniais. Na dimensão de Helpdesk, permite a abertura, acompanhamento, resolução e avaliação de chamados, além do controle de ordens de manutenção e indicadores gerenciais de Acordo de Nível de Serviço (SLA).

🎓 Contexto Acadêmico

Instituição: FAETERJ-Rio — Faculdade de Educação Tecnológica do Estado do Rio de Janeiro

Curso: Análise e Desenvolvimento de Sistemas (2026)

Autores:

Pablo Camilo de Oliveira Torres

Thiago Farias de Souza

🚀 Funcionalidades e Casos de Uso

O sistema foi estruturado com base nos seguintes casos de uso:

UC01 — Gerenciar Cadastros Básicos: Cadastro de colaboradores e técnicos vinculados a setores e perfis de acesso, com suporte a inativação lógica para preservação do histórico.

UC02 — Gerenciar Ativos e Licenças: Registro de equipamentos de hardware (patrimônio, número de série, modelo, fabricante e valor), baixa patrimonial com justificativa e controle de assentos disponíveis em licenças de software.

UC03 — Movimentar Ativo: Fluxo unificado de alocação, empréstimo e devolução de equipamentos, com bloqueio de ativos indisponíveis, geração automática do Termo de Responsabilidade e abertura automática de Ordem de Manutenção em casos de devolução com avaria.

UC04 — Registrar e Acompanhar Chamado: Abertura de solicitações de suporte com geração automática de protocolo único (CH-AAAAMMDD-HHMMSS) e cálculo dinâmico do prazo de SLA conforme categoria e urgência.

UC05 — Atender e Resolver Chamado: Triagem, atualização de status para Em Atendimento ou Resolvido e registro de parecer técnico/solução.

UC06 — Avaliar ou Reabrir Chamado: Encerramento do ticket com atribuição de nota de satisfação (1 a 5) ou reabertura fundamentada mediante justificativa obrigatória.

UC07 — Gerenciar Ordem de Manutenção (OM): Controle de reparos corretivos em hardware, registro de custos e parecer técnico final, além de baixa patrimonial automática em caso de perda total/inviabilidade.

UC08 — Gestão Gerencial e SLA: Dashboard executivo com KPIs em tempo real (total de ativos, disponibilidade, equipamentos em manutenção, chamados ativos, SLAs estourados e custos de manutenção) e exportação de relatórios em CSV.

🛠️ Tecnologias Utilizadas

O projeto utiliza exclusivamente a biblioteca padrão do Python, dispensando a instalação de dependências externas:

Linguagem: Python 3.8+

Interface Gráfica (UI): tkinter e tkinter.ttk (tema clam customizado)

Banco de Dados: sqlite3 (banco relacional embutido com chaves estrangeiras habilitadas)

Manipulação de Arquivos e Datas: pathlib, csv e datetime

🏗️ Arquitetura de Pastas

O código-fonte segue uma arquitetura em camadas (Apresentação, Serviços e Persistência):

SGIH/
├── database/
│   ├── __init__.py
│   └── db_manager.py       # Conexão SQLite, criação das tabelas (DDL) e carga inicial (seed)
├── exports/                # Diretório de saída para relatórios CSV e Termos de Responsabilidade
├── services/
│   ├── __init__.py
│   └── sgih_service.py     # Regras de negócio, validações dos casos de uso e exportações
├── ui/
│   ├── __init__.py
│   └── app_window.py       # Interface gráfica desktop organizada em 6 abas funcionais
├── .gitignore              # Arquivos e diretórios ignorados pelo Git
├── main.py                 # Ponto de entrada da aplicação
└── README.md               # Documentação do repositório


⚙️ Como Executar o Projeto

1. Pré-requisitos

Certifique-se de ter o Python 3.8 ou superior instalado em sua máquina.

Nota para usuários Linux (Ubuntu/Debian): Caso o módulo tkinter não esteja instalado por padrão, instale-o com:

sudo apt-get install python3-tk


2. Clonar o Repositório

git clone <URL_DO_REPOSITORIO>
cd SGIH


3. Executar a Aplicação

python main.py


Na primeira execução, o sistema criará automaticamente o arquivo de banco de dados sgih.db na raiz do projeto e o populará com dados iniciais de demonstração (setores, categorias, fornecedores, colaboradores, ativos, licença e chamado).

💡 Recursos e Atalhos da Interface

Ctrl + R: Atualiza imediatamente os indicadores do Dashboard e todas as tabelas do sistema.

Ordenação por Coluna: Clique no cabeçalho de qualquer coluna nas tabelas para ordenar os registros de forma crescente ou decrescente (com suporte a valores monetários).

Busca Dinâmica: Todas as listagens contam com campo de filtro instantâneo em tempo real.

Submissão Rápida: Pressione Enter nos campos de formulário para salvar registros rapidamente.

📌 Roadmap de Evolução

[ ] Adicionar telas de CRUD completo para Setores, Localizações, Categorias e Fornecedores (UC01).

[ ] Permitir a seleção explícita de ativo vinculado e categoria na abertura de chamados pela interface (UC04 / R9).

[ ] Implementar autenticação de usuários com controle de acesso por perfil.

[ ] Exportar Termos de Responsabilidade e relatórios gerenciais também em formato PDF (UC03 / UC08).

[ ] Exibir aba/painel de consulta ao histórico imutável de movimentações por ativo.