"""Portal GCM Niterói - máscara institucional para apresentação.

Esta versão é propositalmente visual: não depende de SQLite, login ou backend.
Ela reproduz a ideia do protótipo enviado: navegação principal no topo e
subopções expandidas ao clicar em cada aba.

Local:
    python main.py

Deploy (Render / outro host ASGI):
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import os

import flet as ft

# -----------------------------------------------------------------------------
# Identidade visual
# -----------------------------------------------------------------------------
ORANGE = "#E85D04"
ORANGE_DARK = "#C94D00"
ORANGE_LIGHT = "#FFF1E7"
ORANGE_SOFT = "#FFF7F1"
WHITE = "#FFFFFF"
TEXT = "#303030"
TEXT_MUTED = "#6F6F6F"
NAVY = "#172447"
BG = "#F6F6F4"
BORDER = "#E6E1DC"
SUCCESS = "#2F7D4A"

# Texto e organização baseados no protótipo manuscrito enviado pelo usuário.
MENU = {
    "PORTAL": [
        ("Página inicial", "Visão geral do portal e comunicados"),
        ("Serviços", "Acesso rápido aos principais serviços"),
        ("Comunicados", "Avisos, novidades e informações internas"),
    ],
    "PERFIL": [
        ("Meus dados", "Dados cadastrais e informações funcionais"),
        ("Documentos", "Documentos, certificados e registros"),
        ("Projetos", "Participação e acompanhamento de projetos"),
        ("Minha ficha", "Resumo funcional do servidor"),
    ],
    "DP": [
        ("Férias", "Solicitação e acompanhamento de férias"),
        ("Contra-cheque", "Demonstrativo mensal de pagamento"),
        ("1/3 salário", "Consulta do adicional constitucional"),
        ("Escala", "Consulta de escala e troca de turno"),
    ],
    "INAS": [
        ("Solicitações", "Abertura e acompanhamento de solicitações"),
        ("Atendimento", "Canais e orientações de atendimento"),
        ("Acompanhamento", "Consulte o andamento das demandas"),
    ],
    "INSTITUCIONAL": [
        ("Boletim interno", "Informações e comunicados institucionais"),
        ("Instruções", "Normas, procedimentos e orientações"),
        ("Relatórios", "Documentos e indicadores institucionais"),
        ("Contratos", "Contratos e informações administrativas"),
    ],
    "PROJETOS": [
        ("Projetos", "Projetos estratégicos e iniciativas"),
        ("Ações", "Programas, ações e entregas"),
        ("Sobre", "Apresentação dos projetos institucionais"),
    ],
}


def app_card(title: str, subtitle: str, icon, accent: str = ORANGE):
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4},
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=12,
        padding=18,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=10,
                            bgcolor=ORANGE_LIGHT if accent == ORANGE else "#F0F2F7",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, color=accent, size=23),
                        ),
                        ft.Column(
                            [
                                ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                                ft.Text(subtitle, size=11, color=TEXT_MUTED),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text("Acessar módulo  ›", size=11, color=ORANGE, weight=ft.FontWeight.BOLD),
            ],
            spacing=13,
        ),
    )


def quick_item(icon, title, subtitle):
    return ft.Container(
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        border_radius=10,
        padding=14,
        content=ft.Row(
            [
                ft.Icon(icon, color=ORANGE, size=22),
                ft.Column(
                    [
                        ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        ft.Text(subtitle, size=11, color=TEXT_MUTED),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Text("›", size=20, color=ORANGE_DARK, weight=ft.FontWeight.BOLD),
            ],
        ),
    )


def menu_option(title: str, subtitle: str):
    return ft.Container(
        width=260,
        padding=10,
        border_radius=8,
        bgcolor=WHITE,
        border=ft.Border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=NAVY),
                ft.Text(subtitle, size=10, color=TEXT_MUTED, max_lines=2),
            ],
            spacing=3,
        ),
    )


def main(page: ft.Page):
    page.title = "Portal GCM Niterói"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 0
    page.spacing = 0

    state = {"tab": "PORTAL"}

    nav_host = ft.Container()
    submenu_host = ft.Container()
    body_host = ft.Container(expand=True)

    def select_tab(tab_name: str):
        state["tab"] = tab_name
        render_nav()
        render_submenu()
        render_body()
        page.update()

    def nav_item(label: str):
        selected = state["tab"] == label
        return ft.Container(
            padding=ft.Padding(left=14, right=14, top=10, bottom=7),
            border_radius=0,
            on_click=lambda e, x=label: select_tab(x),
            content=ft.Column(
                [
                    ft.Text(
                        label,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=ORANGE if selected else NAVY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(
                        height=3,
                        bgcolor=ORANGE if selected else "transparent",
                        border_radius=2,
                    ),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def render_nav():
        nav_host.content = ft.Row(
            [nav_item(item) for item in MENU.keys()],
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=2,
        )

    def render_submenu():
        current = state["tab"]
        submenu_host.content = ft.Container(
            bgcolor=ORANGE_SOFT,
            border=ft.Border.all(1, "#F1D5C2"),
            border_radius=0,
            padding=ft.Padding(left=20, right=20, top=14, bottom=14),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(current, size=12, weight=ft.FontWeight.BOLD, color=ORANGE_DARK),
                            ft.Text("• opções do módulo", size=11, color=TEXT_MUTED),
                        ],
                        spacing=6,
                    ),
                    ft.Row(
                        [menu_option(title, subtitle) for title, subtitle in MENU[current]],
                        wrap=True,
                        spacing=10,
                        run_spacing=10,
                    ),
                ],
                spacing=10,
            ),
        )

    def render_body():
        current = state["tab"]
        if current == "PORTAL":
            body_host.content = ft.ListView(
                padding=20,
                spacing=18,
                expand=True,
                controls=[
                    ft.Container(
                        bgcolor=WHITE,
                        border=ft.Border.all(1, BORDER),
                        border_radius=14,
                        padding=26,
                        content=ft.ResponsiveRow(
                            [
                                ft.Container(
                                    col={"xs": 12, "md": 8},
                                    content=ft.Column(
                                        [
                                            ft.Text("PORTAL GCM NITERÓI", size=26, weight=ft.FontWeight.BOLD, color=NAVY),
                                            ft.Text(
                                                "Ambiente institucional para serviços, comunicação e informações do servidor.",
                                                size=13,
                                                color=TEXT_MUTED,
                                            ),
                                            ft.Row(
                                                [
                                                    ft.Container(
                                                        bgcolor=ORANGE,
                                                        border_radius=20,
                                                        padding=ft.Padding(left=14, right=14, top=7, bottom=7),
                                                        content=ft.Text("AMBIENTE INTERNO", size=10, color=WHITE, weight=ft.FontWeight.BOLD),
                                                    ),
                                                    ft.Text("Guarda Civil Municipal de Niterói", size=11, color=NAVY, weight=ft.FontWeight.BOLD),
                                                ],
                                                spacing=8,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                ),
                                ft.Container(
                                    col={"xs": 12, "md": 4},
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Container(
                                        width=110,
                                        height=110,
                                        border_radius=55,
                                        bgcolor=ORANGE_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(ft.Icons.SECURITY, size=58, color=ORANGE),
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ft.Text("Serviços em destaque", size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.ResponsiveRow(
                        [
                            app_card("DP - Férias", "Solicitações e acompanhamento", ft.Icons.BEACH_ACCESS),
                            app_card("Contra-cheque", "Demonstrativo de pagamento", ft.Icons.ATTACH_MONEY),
                            app_card("Minha escala", "Escala e troca de turno", ft.Icons.CALENDAR_MONTH, accent=NAVY),
                            app_card("Qualificações", "Cursos e certificados", ft.Icons.SCHOOL),
                            app_card("Chamados TI", "Suporte e atendimento", ft.Icons.COMPUTER, accent=NAVY),
                            app_card("Solicitações", "Demandas administrativas", ft.Icons.DESCRIPTION),
                        ],
                        run_spacing=12,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                col={"xs": 12, "md": 7},
                                content=ft.Column(
                                    [
                                        ft.Text("Acesso rápido", size=17, weight=ft.FontWeight.BOLD, color=NAVY),
                                        quick_item(ft.Icons.PERSON_OUTLINE, "Meu perfil", "Dados e informações funcionais"),
                                        quick_item(ft.Icons.DESCRIPTION, "Documentos", "Certificados e registros"),
                                        quick_item(ft.Icons.DESCRIPTION, "Comunicados", "Avisos institucionais"),
                                    ],
                                    spacing=9,
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 5},
                                content=ft.Container(
                                    bgcolor=ORANGE,
                                    border_radius=12,
                                    padding=20,
                                    content=ft.Column(
                                        [
                                            ft.Text("Comunicado", size=11, color=WHITE, weight=ft.FontWeight.BOLD),
                                            ft.Text("Portal em apresentação", size=18, color=WHITE, weight=ft.FontWeight.BOLD),
                                            ft.Text(
                                                "A navegação superior organiza os módulos e concentra os atalhos por área.",
                                                size=11,
                                                color="#FFEDE1",
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                ),
                            ),
                        ],
                        spacing=14,
                    ),
                ],
            )
        else:
            current_title = current.title()
            body_host.content = ft.ListView(
                padding=20,
                spacing=16,
                expand=True,
                controls=[
                    ft.Text(f"{current_title}", size=24, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text(
                        "Área demonstrativa do portal. Os componentes abaixo representam a máscara visual do módulo.",
                        size=12,
                        color=TEXT_MUTED,
                    ),
                    ft.ResponsiveRow(
                        [
                            app_card(title, subtitle, ft.Icons.CHEVRON_RIGHT, accent=ORANGE if i % 2 == 0 else NAVY)
                            for i, (title, subtitle) in enumerate(MENU[current])
                        ],
                        run_spacing=12,
                    ),
                    ft.Container(
                        bgcolor=WHITE,
                        border=ft.Border.all(1, BORDER),
                        border_radius=12,
                        padding=18,
                        content=ft.Column(
                            [
                                ft.Text("Área institucional", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                                ft.Text(
                                    "Espaço reservado para tabelas, documentos, indicadores, atalhos ou comunicados do módulo.",
                                    size=11,
                                    color=TEXT_MUTED,
                                ),
                                ft.Row(
                                    [
                                        ft.Container(
                                            bgcolor=ORANGE_LIGHT,
                                            padding=10,
                                            border_radius=8,
                                            content=ft.Text("EXEMPLO DE CARD", size=10, color=ORANGE_DARK, weight=ft.FontWeight.BOLD),
                                        ),
                                        ft.Text("Layout preparado para apresentação", size=11, color=NAVY),
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=9,
                        ),
                    ),
                ],
            )

    def header():
        return ft.Container(
            bgcolor=ORANGE,
            padding=ft.Padding(left=18, right=18, top=10, bottom=10),
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=42,
                                height=42,
                                bgcolor=WHITE,
                                border_radius=10,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.SECURITY, color=ORANGE, size=25),
                            ),
                            ft.Column(
                                [
                                    ft.Text("GUARDA CIVIL MUNICIPAL", size=14, weight=ft.FontWeight.BOLD, color=WHITE),
                                    ft.Text("PREFEITURA DE NITERÓI", size=10, color="#FFE9D8", weight=ft.FontWeight.BOLD),
                                ],
                                spacing=1,
                            ),
                        ],
                        spacing=10,
                        expand=True,
                    ),
                    ft.Container(
                        bgcolor=WHITE,
                        border_radius=18,
                        padding=ft.Padding(left=12, right=12, top=7, bottom=7),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.PERSON_OUTLINE, color=ORANGE_DARK, size=18),
                                ft.Text("Administrador Inicial", size=11, color=NAVY, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=6,
                        ),
                    ),
                    ft.IconButton(icon=ft.Icons.LOGOUT, icon_color=WHITE, tooltip="Sair"),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    page.add(
        header(),
        ft.Container(
            bgcolor=WHITE,
            border=ft.Border(
                bottom=ft.BorderSide(1, BORDER),
            ),
            content=nav_host,
        ),
        submenu_host,
        body_host,
    )

    render_nav()
    render_submenu()
    render_body()
    page.update()


# ASGI para Render / hospedagem web.
app = ft.run(main, export_asgi_app=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8550"))
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
