"""Portal da Guarda Civil Municipal de Niterói — Flet 1.x + SQLite.

Execução local:
    python main.py

Produção (GitHub + Render ou outro host ASGI):
    uvicorn main:app --host 0.0.0.0 --port $PORT

O app é servido como uma aplicação web Flet, portanto pode ser aberto
por celular em qualquer rede pela URL pública do provedor de hospedagem.
"""
import hashlib
import hmac
import os
import secrets
import socket
import sqlite3
import time
from contextlib import contextmanager

import flet as ft

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
COLOR_BLUE_GCM = "#0B1B4F"
COLOR_GOLD_GCM = "#F5B800"
COLOR_ORANGE_NIT = "#EB6014"
COLOR_BG = "#F4F6F9"
COLOR_WHITE = "#FFFFFF"
COLOR_BORDER = "#E0E0E0"

DEMO_MODE = os.getenv("GCM_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
# Senha inicial dos novos servidores. Em produção, prefira deixar vazia para
# gerar uma senha aleatória por cadastro.
DEFAULT_PASSWORD = os.getenv("GCM_DEFAULT_PASSWORD", "").strip()
PERFIL_SERVIDOR = "Servidor"
PERFIL_ADMIN = "Administrador"

# Banco configurável por variável de ambiente.
# Em Render com Persistent Disk, recomendamos /var/data/gcm_database.db.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_DIR = "/var/data" if os.path.isdir("/var/data") else BASE_DIR
DB_PATH = os.getenv("GCM_DB_PATH") or os.path.join(DEFAULT_DB_DIR, "gcm_database.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

# Bootstrap seguro: não deixe credenciais administrativas hard-coded no GitHub.
BOOTSTRAP_ADMIN_MATRICULA = os.getenv("GCM_BOOTSTRAP_ADMIN_MATRICULA", "").strip()
BOOTSTRAP_ADMIN_NOME = os.getenv("GCM_BOOTSTRAP_ADMIN_NOME", "Administrador Inicial").strip()
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("GCM_BOOTSTRAP_ADMIN_PASSWORD", "").strip()

STATUS_COLORS = {
    "Pendente": COLOR_ORANGE_NIT,
    "Aprovado": "green",
    "Recusado": "red",
    "Aberto": COLOR_ORANGE_NIT,
    "Em atendimento": COLOR_BLUE_GCM,
    "Concluído": "green",
}

# Fluxo de aprovação de cada tabela: (título, [(rótulo do botão, novo status, cor)])
WORKFLOWS = {
    "ferias": ("Férias e Licenças", [("Aprovar", "Aprovado", "green"), ("Recusar", "Recusado", "red")]),
    "qualificacoes": ("Qualificações", [("Validar", "Aprovado", "green"), ("Recusar", "Recusado", "red")]),
    "chamados_ti": ("Chamados de TI", [("Atender", "Em atendimento", COLOR_BLUE_GCM), ("Concluir", "Concluído", "green")]),
}

_SQL_LISTA = {
    "ferias": """SELECT f.id, s.nome, f.tipo || ' — ' || f.periodo AS resumo, f.status
                 FROM ferias f JOIN servidores s ON s.id = f.servidor_id""",
    "qualificacoes": """SELECT q.id, s.nome, q.curso || ' — ' || q.instituicao AS resumo, q.status
                        FROM qualificacoes q JOIN servidores s ON s.id = q.servidor_id""",
    "chamados_ti": """SELECT c.id, s.nome, c.descricao AS resumo, c.status
                      FROM chamados_ti c JOIN servidores s ON s.id = c.servidor_id""",
}
_ALIAS = {"ferias": "f", "qualificacoes": "q", "chamados_ti": "c"}


# ==============================================================================
# BANCO DE DADOS
# ==============================================================================
@contextmanager
def db():
    """Abre uma conexão SQLite curta, com timeout e busy_timeout para concorrência."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA synchronous = NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
    except ValueError:
        return False
    return hmac.compare_digest(candidate, digest)


def _enable_wal():
    """Tenta ativar WAL sem derrubar o app caso outro processo esteja usando o banco."""
    for attempt in range(5):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                conn.execute("PRAGMA busy_timeout = 30000")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
            return True
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                print(f"[aviso] WAL não ativado: {exc}")
                return False
            if attempt < 4:
                time.sleep(0.5 * (attempt + 1))
    print("[aviso] WAL não ativado: banco ocupado. O app continuará com SQLite normal.")
    return False

def init_db():
    """Cria/migra o banco. Tolerante a outra instância estar terminando uma escrita."""
    last_error = None
    for attempt in range(6):
        try:
            with db() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS servidores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        matricula TEXT UNIQUE NOT NULL,
                        nome TEXT NOT NULL,
                        perfil TEXT NOT NULL,
                        senha TEXT NOT NULL,
                        endereco TEXT
                    );

                    CREATE TABLE IF NOT EXISTS ferias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        servidor_id INTEGER NOT NULL,
                        tipo TEXT,
                        periodo TEXT,
                        status TEXT DEFAULT 'Pendente',
                        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
                    );

                    CREATE TABLE IF NOT EXISTS qualificacoes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        servidor_id INTEGER NOT NULL,
                        curso TEXT,
                        instituicao TEXT,
                        comprovante TEXT,
                        status TEXT DEFAULT 'Pendente',
                        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
                    );

                    CREATE TABLE IF NOT EXISTS chamados_ti (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        servidor_id INTEGER NOT NULL,
                        descricao TEXT,
                        evidencia TEXT,
                        status TEXT DEFAULT 'Aberto',
                        FOREIGN KEY (servidor_id) REFERENCES servidores(id)
                    );
                    """
                )

                # Migração: bancos antigos com senha em texto puro.
                for row in conn.execute("SELECT id, senha FROM servidores").fetchall():
                    if "$" not in row["senha"]:
                        conn.execute(
                            "UPDATE servidores SET senha=? WHERE id=?",
                            (hash_password(row["senha"]), row["id"]),
                        )

                # Bootstrap opcional. Nada sensível fica hard-coded no repositório.
                total = conn.execute("SELECT COUNT(*) FROM servidores").fetchone()[0]
                if total == 0 and not BOOTSTRAP_ADMIN_PASSWORD:
                    print(
                        "[config] Banco sem usuários. Defina "
                        "GCM_BOOTSTRAP_ADMIN_PASSWORD para criar o primeiro administrador."
                    )
                if total == 0 and BOOTSTRAP_ADMIN_PASSWORD:
                    conn.execute(
                        "INSERT INTO servidores (matricula, nome, perfil, senha, endereco) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            BOOTSTRAP_ADMIN_MATRICULA or "9001",
                            BOOTSTRAP_ADMIN_NOME,
                            PERFIL_ADMIN,
                            hash_password(BOOTSTRAP_ADMIN_PASSWORD),
                            "",
                        ),
                    )
            break
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "locked" not in str(exc).lower() or attempt >= 5:
                raise
            time.sleep(0.5 * (attempt + 1))

    # Não é requisito funcional; falha aqui não impede o servidor de subir.
    if last_error is None:
        _enable_wal()


init_db()

def listar(tabela: str, servidor_id=None):
    """Lista registros de uma das tabelas de workflow (nome validado pelo dicionário)."""
    sql = _SQL_LISTA[tabela]
    params = ()
    if servidor_id is not None:
        sql += f" WHERE {_ALIAS[tabela]}.servidor_id = ?"
        params = (servidor_id,)
    sql += f" ORDER BY {_ALIAS[tabela]}.id DESC"
    with db() as conn:
        return conn.execute(sql, params).fetchall()



# ==============================================================================
# COMPONENTES VISUAIS REUTILIZÁVEIS
# ==============================================================================
def primary_button(text, on_click, bg=COLOR_BLUE_GCM, fg=COLOR_WHITE, **kwargs):
    return ft.Button(content=text, on_click=on_click, style=ft.ButtonStyle(bgcolor=bg, color=fg), **kwargs)


def section_title(text):
    return ft.Text(text, size=16, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM)


def empty_note(text):
    return ft.Text(text, italic=True, color="grey")


def status_chip(status):
    return ft.Container(
        content=ft.Text(status, size=11, color=COLOR_WHITE, weight=ft.FontWeight.BOLD),
        bgcolor=STATUS_COLORS.get(status, "grey"),
        padding=ft.Padding(left=8, right=8, top=2, bottom=2),
        border_radius=10,
    )


def request_card(titulo, subtitulo, status, botoes=None):
    topo = ft.Row(
        [
            ft.Column(
                [
                    ft.Text(titulo, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                    ft.Text(subtitulo, size=12, color="grey"),
                ],
                spacing=2,
                expand=True,
            ),
            status_chip(status),
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    corpo = [topo]
    if botoes:
        corpo.append(ft.Row(botoes, wrap=True, spacing=8))
    return ft.Container(
        content=ft.Column(corpo, spacing=8),
        bgcolor=COLOR_WHITE,
        padding=12,
        border_radius=8,
        border=ft.Border.all(1, COLOR_BORDER),
    )


def module_card(icon, icon_color, titulo, descricao, botao):
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, color=icon_color, size=32),
                ft.Text(titulo, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                ft.Text(descricao, size=11, color="grey", text_align=ft.TextAlign.CENTER),
                botao,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        padding=15,
        bgcolor=COLOR_WHITE,
        border_radius=10,
        col={"xs": 12, "md": 4},
        border=ft.Border.all(1, COLOR_BORDER),
    )


# ==============================================================================
# APLICAÇÃO PRINCIPAL
# ==============================================================================
def main(page: ft.Page):
    page.title = "Portal da Guarda Civil Municipal de Niterói"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLOR_BG
    page.padding = 0
    page.spacing = 0

    # Estado por sessão (cada aba/celular tem o seu)
    session = {"user": None, "tab": 0}

    def field_width(margin=130):
        """Largura dos campos: 300px no desktop, encolhe em telas estreitas de celular."""
        largura = getattr(page, "width", None) or 400
        return int(min(300, max(220, largura - margin)))

    def notify(message, color=COLOR_BLUE_GCM):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=COLOR_WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=color,
                behavior=ft.SnackBarBehavior.FLOATING,
            )
        )

    def show_form(title, fields, submit_label, submit_bg, on_submit, success_msg):
        """Diálogo genérico. `on_submit` devolve uma mensagem de erro (str) ou None se salvou."""
        err = ft.Text("", color="red", size=12)

        def submit(e):
            problema = on_submit()
            if problema:
                err.value = problema
                err.update()
                return
            page.pop_dialog()
            notify(success_msg, "green")
            render_app()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title, color=COLOR_BLUE_GCM, weight=ft.FontWeight.BOLD),
                content=ft.Column([*fields, err], tight=True, spacing=10, width=field_width()),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                    primary_button(submit_label, submit, bg=submit_bg),
                ],
            )
        )

    # --------------------------------------------------------------------------
    # AÇÕES DE NEGÓCIO
    # --------------------------------------------------------------------------
    def logout(e=None):
        session["user"] = None
        session["tab"] = 0
        render_app()

    def set_status(tabela, item_id, novo_status):
        if tabela not in WORKFLOWS:  # nunca interpola nome de tabela vindo de fora da lista
            return
        with db() as conn:
            conn.execute(f"UPDATE {tabela} SET status=? WHERE id=?", (novo_status, item_id))
        notify(f"Solicitação #{item_id} atualizada para {novo_status}.", "green")
        render_app()

    def acao(tabela, item_id, novo_status):
        def handler(e):
            set_status(tabela, item_id, novo_status)
        return handler

    # --------------------------------------------------------------------------
    # MODAIS DO SERVIDOR
    # --------------------------------------------------------------------------
    def show_modal_ferias():
        w = field_width()
        tipo = ft.Dropdown(
            label="Tipo de Férias",
            width=w,
            options=[ft.DropdownOption(key=t, text=t) for t in ("Anual Regulamentar", "Licença Prêmio")],
        )
        periodo = ft.TextField(label="Período desejado", hint_text="Ex: 15 dias em novembro", width=w)

        def salvar():
            if not tipo.value or not (periodo.value or "").strip():
                return "Preencha todos os campos."
            with db() as conn:
                conn.execute(
                    "INSERT INTO ferias (servidor_id, tipo, periodo, status) VALUES (?, ?, ?, 'Pendente')",
                    (session["user"]["id"], tipo.value, periodo.value.strip()),
                )
            return None

        show_form("Solicitar Férias / 1/3", [tipo, periodo], "Enviar", COLOR_BLUE_GCM, salvar,
                  "Solicitação de férias enviada para análise do DP!")

    def show_modal_qualificacao():
        w = field_width()
        curso = ft.TextField(label="Curso / Graduação", width=w)
        inst = ft.TextField(label="Instituição de ensino", width=w)
        anexo = {"nome": None}
        lbl_anexo = ft.Text("Nenhum arquivo anexado", size=11, color="grey")

        def anexar(e):  # DEMO: simula o anexo (upload real exige FilePicker + upload_dir)
            anexo["nome"] = "certificado_demo.pdf"
            lbl_anexo.value = "Anexado: certificado_demo.pdf (simulado)"
            lbl_anexo.update()

        def salvar():
            if not (curso.value or "").strip() or not (inst.value or "").strip():
                return "Preencha o curso e a instituição."
            with db() as conn:
                conn.execute(
                    "INSERT INTO qualificacoes (servidor_id, curso, instituicao, comprovante, status) "
                    "VALUES (?, ?, ?, ?, 'Pendente')",
                    (session["user"]["id"], curso.value.strip(), inst.value.strip(), anexo["nome"]),
                )
            return None

        show_form(
            "Cadastrar Qualificação",
            [curso, inst, ft.OutlinedButton(content="Anexar certificado (demo)", icon=ft.Icons.ATTACH_FILE, on_click=anexar), lbl_anexo],
            "Enviar ao DP", COLOR_ORANGE_NIT, salvar,
            "Qualificação registrada! Aguardando validação funcional.",
        )

    def show_modal_ti():
        w = field_width()
        desc = ft.TextField(label="Descrição do problema", multiline=True, min_lines=3, max_lines=5, width=w)
        anexo = {"nome": None}
        lbl_anexo = ft.Text("Nenhuma evidência anexada", size=11, color="grey")

        def anexar(e):  # DEMO
            anexo["nome"] = "captura_tela_demo.png"
            lbl_anexo.value = "Anexado: captura_tela_demo.png (simulado)"
            lbl_anexo.update()

        def salvar():
            if not (desc.value or "").strip():
                return "Descreva o problema de TI."
            with db() as conn:
                conn.execute(
                    "INSERT INTO chamados_ti (servidor_id, descricao, evidencia, status) VALUES (?, ?, ?, 'Aberto')",
                    (session["user"]["id"], desc.value.strip(), anexo["nome"]),
                )
            return None

        show_form(
            "Abertura de Chamado (TI)",
            [desc, ft.OutlinedButton(content="Anexar print (demo)", icon=ft.Icons.IMAGE, on_click=anexar), lbl_anexo],
            "Abrir chamado", COLOR_BLUE_GCM, salvar, "Chamado de TI aberto com sucesso!",
        )

    # --------------------------------------------------------------------------
    # TELAS
    # --------------------------------------------------------------------------
    def build_header():
        user = session["user"]
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SECURITY, color=COLOR_GOLD_GCM, size=32),
                            ft.Column(
                                [
                                    ft.Text("GUARDA CIVIL MUNICIPAL", size=13, weight=ft.FontWeight.BOLD,
                                            color=COLOR_WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text("PREFEITURA DE NITERÓI", size=10, color=COLOR_GOLD_GCM,
                                            weight=ft.FontWeight.W_500),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                        expand=True,
                    ),
                    ft.Chip(
                        label=ft.Text(user["perfil"], color=COLOR_BLUE_GCM, size=11, weight=ft.FontWeight.BOLD),
                        bgcolor=COLOR_GOLD_GCM,
                    ),
                    ft.IconButton(icon=ft.Icons.LOGOUT, icon_color=COLOR_WHITE, tooltip="Sair", on_click=logout),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=COLOR_BLUE_GCM,
            padding=ft.Padding(left=16, right=8, top=10, bottom=10),
        )

    def build_login_view():
        w = field_width(margin=100)
        input_matricula = ft.TextField(label="Matrícula", width=w, autofocus=True)
        input_senha = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=w)

        def attempt_login(e):
            mat = (input_matricula.value or "").strip()
            pwd = (input_senha.value or "").strip()
            if not mat or not pwd:
                notify("Preencha a matrícula e a senha.", COLOR_ORANGE_NIT)
                return

            with db() as conn:
                row = conn.execute(
                    "SELECT id, matricula, nome, perfil, senha FROM servidores WHERE matricula=?", (mat,)
                ).fetchone()

            if row and verify_password(pwd, row["senha"]):
                session["user"] = {"id": row["id"], "matricula": row["matricula"],
                                   "nome": row["nome"], "perfil": row["perfil"]}
                session["tab"] = 0
                render_app()
                notify(f"Bem-vindo(a), {row['nome']}!", "green")
            else:
                notify("Matrícula ou senha inválidas.", "red")

        input_senha.on_submit = attempt_login

        demo_box = []
        if DEMO_MODE:
            demo_box = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Acessos de teste:", size=11, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                            ft.Text("Servidor: 1001 / 1234", size=10, color="grey"),
                            ft.Text("Admin/DP: 9001 / admin123", size=10, color="grey"),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=10,
                    bgcolor=COLOR_BG,
                    border_radius=6,
                )
            ]

        card = ft.Card(
            content=ft.Container(
                padding=30,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SECURITY, color=COLOR_BLUE_GCM, size=60),
                        ft.Text("PORTAL GCM NITERÓI", size=20, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                        ft.Text("Acesso restrito ao servidor", size=12, color="grey"),
                        ft.Divider(height=10, color="transparent"),
                        input_matricula,
                        input_senha,
                        primary_button("ENTRAR NO SISTEMA", attempt_login, width=w, height=45),
                        *demo_box,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    tight=True,
                ),
            )
        )
        return ft.Column(
            [card],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def link_tile(icon, color, titulo, subtitulo):
        return ft.Container(
            content=ft.ListTile(
                leading=ft.Icon(icon, color=color),
                title=ft.Text(titulo),
                subtitle=ft.Text(subtitulo),
                on_click=lambda e: notify("Módulo em desenvolvimento (demo).", COLOR_ORANGE_NIT),
            ),
            bgcolor=COLOR_WHITE,
            border_radius=6,
        )

    def build_servidor_view():
        user = session["user"]
        uid = user["id"]

        def cards(tabela, vazio):
            itens = [request_card(r["resumo"], f"Solicitação #{r['id']}", r["status"]) for r in listar(tabela, uid)]
            return itens or [empty_note(vazio)]

        return ft.ListView(
            padding=20,
            spacing=12,
            expand=True,
            controls=[
                ft.Text(f"Painel do Servidor — {user['nome']}", size=20, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                ft.Text("Acesse rapidamente os serviços administrativos:", size=13, color="grey"),
                ft.ResponsiveRow(
                    [
                        module_card(ft.Icons.BEACH_ACCESS, COLOR_BLUE_GCM, "DP - Férias & 1/3",
                                    "Solicite férias ou adiantamento.",
                                    primary_button("Solicitar", lambda e: show_modal_ferias())),
                        module_card(ft.Icons.SCHOOL, COLOR_ORANGE_NIT, "Qualificações",
                                    "Cadastre diplomas, cursos e certificados.",
                                    primary_button("Enviar curso", lambda e: show_modal_qualificacao(), bg=COLOR_ORANGE_NIT)),
                        module_card(ft.Icons.COMPUTER, COLOR_BLUE_GCM, "Chamados TI",
                                    "Abra chamados para problemas nos sistemas.",
                                    primary_button("Abrir chamado", lambda e: show_modal_ti())),
                    ],
                    run_spacing=10,
                ),
                ft.Divider(height=10, color=COLOR_BORDER),
                section_title("Minhas solicitações de férias"),
                *cards("ferias", "Nenhuma solicitação de férias registrada."),
                section_title("Minhas qualificações"),
                *cards("qualificacoes", "Nenhuma qualificação cadastrada."),
                section_title("Meus chamados de TI"),
                *cards("chamados_ti", "Nenhum chamado aberto."),
                ft.Divider(height=10, color=COLOR_BORDER),
                section_title("Serviços operacionais e comunicação"),
                link_tile(ft.Icons.CALENDAR_MONTH, COLOR_BLUE_GCM, "Minha escala / troca de turno",
                          "Consulte a escala mensal aprovada"),
                link_tile(ft.Icons.ATTACH_MONEY, COLOR_ORANGE_NIT, "Contra-cheque online",
                          "Download do demonstrativo de pagamento"),
            ],
        )

    def build_admin_view():
        if session["user"]["perfil"] != PERFIL_ADMIN:
            return ft.Container(content=empty_note("Acesso negado."), padding=20)

        blocos = []
        pendentes = {}
        for tabela, (titulo, botoes_def) in WORKFLOWS.items():
            registros = listar(tabela)
            pendentes[titulo] = sum(1 for r in registros if r["status"] in ("Pendente", "Aberto"))
            cards = []
            for r in registros:
                botoes = []
                for rotulo, novo, cor in botoes_def:
                    if r["status"] == novo:
                        continue  # não mostra a ação que já foi aplicada
                    if cor == "red":
                        botoes.append(ft.OutlinedButton(content=rotulo, style=ft.ButtonStyle(color=cor),
                                                        on_click=acao(tabela, r["id"], novo)))
                    else:
                        botoes.append(primary_button(rotulo, acao(tabela, r["id"], novo), bg=cor))
                cards.append(request_card(f"{r['nome']} — {r['resumo']}", f"Solicitação #{r['id']}", r["status"], botoes))
            blocos += [section_title(titulo), *(cards or [empty_note("Nada por aqui ainda.")])]

        # --- Cadastro de servidor -------------------------------------------------
        input_mat = ft.TextField(label="Matrícula")
        input_nome = ft.TextField(label="Nome do servidor")
        input_end = ft.TextField(label="Endereço / lotação")
        input_perfil = ft.Dropdown(
            label="Perfil",
            value=PERFIL_SERVIDOR,
            options=[ft.DropdownOption(key=p, text=p) for p in (PERFIL_SERVIDOR, PERFIL_ADMIN)],
        )

        def cadastrar_servidor(e):
            mat = (input_mat.value or "").strip()
            nome = (input_nome.value or "").strip()
            if not mat or not nome or not input_perfil.value:
                notify("Preencha matrícula, nome e perfil.", COLOR_ORANGE_NIT)
                return
            senha_inicial = DEFAULT_PASSWORD or secrets.token_urlsafe(10)
            try:
                with db() as conn:
                    conn.execute(
                        "INSERT INTO servidores (matricula, nome, perfil, senha, endereco) VALUES (?, ?, ?, ?, ?)",
                        (mat, nome, input_perfil.value, hash_password(senha_inicial), (input_end.value or "").strip()),
                    )
            except sqlite3.IntegrityError:
                notify("Erro: matrícula já cadastrada no sistema.", "red")
                return
            notify(f"Servidor {nome} cadastrado! Senha inicial: {senha_inicial}", "green")
            render_app()

        with db() as conn:
            servidores = conn.execute(
                "SELECT matricula, nome, perfil, endereco FROM servidores ORDER BY nome"
            ).fetchall()

        lista_servidores = [
            ft.Container(
                content=ft.ListTile(
                    leading=ft.Icon(ft.Icons.BADGE, color=COLOR_BLUE_GCM),
                    title=ft.Text(f"{s['nome']} — {s['matricula']}"),
                    subtitle=ft.Text(f"{s['perfil']} • {s['endereco'] or 'sem endereço'}"),
                ),
                bgcolor=COLOR_WHITE,
                border_radius=6,
            )
            for s in servidores
        ]

        resumo = "  •  ".join(f"{k}: {v}" for k, v in pendentes.items())
        return ft.ListView(
            padding=20,
            spacing=12,
            expand=True,
            controls=[
                ft.Text("Painel de Gestão e Aprovações (ADM/DP)", size=20, weight=ft.FontWeight.BOLD, color=COLOR_BLUE_GCM),
                ft.Text(f"Pendências — {resumo}", size=12, color=COLOR_ORANGE_NIT, weight=ft.FontWeight.W_500),
                *blocos,
                ft.Divider(height=10, color=COLOR_BORDER),
                section_title("Cadastrar novo servidor"),
                ft.Container(
                    content=ft.Column(
                        [input_mat, input_nome, input_end, input_perfil,
                         primary_button("Salvar servidor", cadastrar_servidor, bg=COLOR_GOLD_GCM, fg=COLOR_BLUE_GCM)],
                        spacing=10,
                    ),
                    bgcolor=COLOR_WHITE, padding=15, border_radius=8, border=ft.Border.all(1, COLOR_BORDER),
                ),
                section_title("Servidores cadastrados"),
                *lista_servidores,
            ],
        )

    # --------------------------------------------------------------------------
    # RENDERIZAÇÃO / NAVEGAÇÃO
    # --------------------------------------------------------------------------
    def render_app():
        page.controls.clear()
        user = session["user"]

        if user is None:
            page.add(build_login_view())
        else:
            is_admin = user["perfil"] == PERFIL_ADMIN
            tab = session["tab"] if is_admin else 0
            conteudo = build_admin_view() if tab == 1 else build_servidor_view()
            controles = [build_header(), ft.Container(content=conteudo, expand=True)]

            # NavigationBar exige no mínimo 2 destinos: só existe para o administrador
            if is_admin:
                def switch_tab(e):
                    session["tab"] = e.control.selected_index
                    render_app()

                controles.append(
                    ft.NavigationBar(
                        selected_index=tab,
                        on_change=switch_tab,
                        bgcolor=COLOR_WHITE,
                        destinations=[
                            ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME,
                                                        label="Portal Servidor"),
                            ft.NavigationBarDestination(icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                                                        selected_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                                        label="Painel ADM/DP"),
                        ],
                    )
                )
            page.add(*controles)

        page.update()

    render_app()


# ==============================================================================
# EXECUÇÃO (web, acessível na rede local)
# ==============================================================================
def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # não envia pacote; só descobre a interface ativa
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


# Exporta a aplicação ASGI para Uvicorn/Render/etc.
# Em produção, o processo HTTP deve ser iniciado pelo servidor ASGI.
app = ft.run(main, export_asgi_app=True)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8550"))
    print("=" * 72)
    print(" Portal GCM Niterói")
    print(f" PC:         http://127.0.0.1:{port}")
    print(f" Rede local: http://{_local_ip()}:{port}")
    print("=" * 72)
    print(" Produção: uvicorn main:app --host 0.0.0.0 --port $PORT")
    print("=" * 72)
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
