from base64 import b64encode
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"
COLUNAS = [
    "Matrícula", "Nome do servidor", "Local de trabalho", "Função",
    "Situação no IndexPonto", "Recadastramento no RHOnline", "Lotação na Index",
]


def gerar_base_ficticia() -> pd.DataFrame:
    unidades = ["Hospital do Dirceu II", "Hospital da Primavera"]
    funcoes = ["Enfermeiro", "Técnico em enfermagem plantonista",
               "Auxiliar de administração", "Clínico urgentista"]
    registros = []
    for i in range(18):
        unidade = unidades[i >= 11]
        ativo = i % 3 != 0
        registros.append((
            f"DEMO-{i + 1:03}", f"Servidor de exemplo {i + 1:02}", unidade,
            funcoes[i % len(funcoes)], "Ativo confirmado" if ativo else "Sem confirmação",
            "Recadastramento confirmado" if i % 4 else "Sem confirmação",
            unidade if ativo else "—",
        ))
    return pd.DataFrame(registros, columns=COLUNAS)


def cor_da_situacao(valor: str) -> str:
    if valor == "Sem confirmação":
        return "background-color: #fcebd9; color: #713209; font-weight: 600"
    return "background-color: #ddf2e6; color: #14563c; font-weight: 600"


def limpar_filtros() -> None:
    for campo in ("Local de trabalho", "Função", "Situação no IndexPonto"):
        st.session_state.pop(campo, None)


def cabecalho(titulo: str, descricao: str) -> None:
    assinatura = b64encode((ASSETS / "assinatura.png").read_bytes()).decode("ascii")
    html = preencher("executiva_header.html", assinatura=f"data:image/png;base64,{assinatura}")
    html = html.replace("Servidores · Visão Executiva", escape(titulo))
    html = html.replace("Acompanhamento de servidores no IndexPonto", escape(descricao))
    st.html(html)


def por_unidade() -> None:
    cabecalho("Servidores · Por Unidade", "Acompanhamento por local de trabalho")
    base = gerar_base_ficticia()
    campos = ("Local de trabalho", "Função", "Situação no IndexPonto")
    filtrados = base
    colunas = st.columns([2, 2.5, 2, 1.4], vertical_alignment="bottom")
    for coluna, campo in zip(colunas, campos):
        opcoes = sorted(base[campo].unique())
        escolha = coluna.selectbox(campo, ["Todos", *opcoes], key=campo)
        if escolha != "Todos":
            filtrados = filtrados.loc[filtrados[campo] == escolha]
    colunas[-1].button("Limpar filtros", on_click=limpar_filtros)

    st.subheader("Acompanhamento por unidade")
    st.caption(f"{len(filtrados)} de {len(base)} vínculos de exemplo")
    if filtrados.empty:
        st.info("Nenhum vínculo corresponde aos filtros selecionados.")
        return

    estilo = filtrados.style.map(
        cor_da_situacao, subset=["Situação no IndexPonto", "Recadastramento no RHOnline"]
    )
    larguras = [110, 200, 195, 260, 190, 240, 195]
    st.dataframe(
        estilo,
        hide_index=True,
        width="stretch",
        height=510,
        row_height=40,
        column_config={
            campo: st.column_config.TextColumn(width=largura)
            for campo, largura in zip(COLUNAS, larguras)
        },
    )


TEMPLATES = ASSETS.parent / "templates"


def preencher(arquivo: str, **campos) -> str:
    conteudo = (TEMPLATES / arquivo).read_text(encoding="utf-8")
    for campo, valor in campos.items():
        conteudo = conteudo.replace("{{" + campo + "}}", str(valor))
    return conteudo


def numeros(base: pd.DataFrame) -> dict:
    total = len(base)
    ativos = int(base["Situação no IndexPonto"].eq("Ativo confirmado").sum())
    rh = int(base["Recadastramento no RHOnline"].ne("Sem confirmação").sum())
    taxa = 100 * ativos / total if total else 0
    return dict(total=total, ativos=ativos, pendentes=total - ativos, rh=rh,
                rh_pendente=total - rh, percentual=f"{taxa:.0f}%" if total else "—",
                percentual_barra=taxa, restante=100 - taxa if total else 0,
                percentual_restante=f"{100 - taxa:.0f}%" if total else "—")


def linhas_do_resumo(base: pd.DataFrame, campo: str, arquivo: str) -> str:
    grupos = [(nome, numeros(grupo)) for nome, grupo in base.groupby(campo)]
    if not grupos:
        return '<p style="padding:0 16px">Nenhum vínculo para os filtros selecionados.</p>'
    grupos.sort(key=lambda grupo: grupo[1]["pendentes"], reverse=True)
    maior = grupos[0][1]["pendentes"] or 1
    return "".join(
        preencher(arquivo, nome=escape(nome), peso=100 * dados["pendentes"] / maior, **dados)
        for nome, dados in grupos
    )


def painel_resumo(pagina: str) -> None:
    assinatura = b64encode((ASSETS / "assinatura.png").read_bytes()).decode("ascii")
    st.html(preencher(f"{pagina}_header.html", assinatura=f"data:image/png;base64,{assinatura}"))
    base = gerar_base_ficticia()
    campos = ["Local de trabalho"]
    if pagina == "geral":
        campos.extend(["Função", "Situação no IndexPonto"])
    colunas = st.columns([2.3, 2.3, 2.3, 1.4] if pagina == "geral" else [2.3, 2.3, 1.4, 3],
                         vertical_alignment="bottom")
    chaves = [f"{pagina}-{campo}" for campo in campos]
    filtrados = base
    for coluna, campo, chave in zip(colunas, campos, chaves):
        escolha = coluna.selectbox(campo, ["Todos", *sorted(base[campo].unique())], key=chave)
        if escolha != "Todos":
            filtrados = filtrados.loc[filtrados[campo] == escolha]
    if pagina == "executiva":
        colunas[1].date_input("Período do histórico", value=None, disabled=True,
                              help="Disponível ao conectar o histórico diário.")

    def limpar() -> None:
        for chave in chaves:
            st.session_state.pop(chave, None)

    colunas[3 if pagina == "geral" else 2].button(
        "Limpar filtros", on_click=limpar, key=f"{pagina}-limpar"
    )
    dados = numeros(filtrados)
    if pagina == "geral":
        dados["funcoes"] = linhas_do_resumo(filtrados, "Função", "geral_linha0.html")
    linha_unidade = "geral_linha1.html" if pagina == "geral" else "executiva_linha0.html"
    dados["unidades"] = linhas_do_resumo(filtrados, "Local de trabalho", linha_unidade)
    st.html(preencher(f"{pagina}.html", **dados))


def visao_geral() -> None:
    painel_resumo("geral")


def visao_executiva() -> None:
    painel_resumo("executiva")


def main() -> None:
    st.set_page_config(page_title="IndexPonto | FMS Teresina", layout="wide",
                       initial_sidebar_state="expanded")
    st.html(ASSETS.parent / "templates" / "site.css")
    st.html("""
    <style>
        [data-testid="stMainBlockContainer"] { padding: 4.25rem 1.5rem 1.5rem; }
        [data-testid="stSidebar"] { border-right: 1px solid #DDE3EB; }
        [data-testid="stSidebar"][aria-expanded="true"],
        [data-testid="stSidebar"][data-collapsed="false"] {
            width: 225px !important;
            min-width: 225px !important;
            max-width: 225px !important;
        }
        [data-testid="stSidebarResizeHandle"],
        [data-testid="stSidebar"] div:has(> [data-testid="stSidebarResizeHandle"]) {
            display: none !important;
        }
        [data-testid="stAppDeployButton"] { display: none; }
        .st-key-menu-ativo a {
            background: #0F2A47 !important;
            border-radius: 8px;
            padding: .5rem .75rem !important;
        }
        .st-key-menu-ativo a, .st-key-menu-ativo a * {
            color: #FFFFFF !important;
            font-weight: 700;
        }
        .indexponto-menu-reservado {
            display: grid;
            gap: 14px;
            padding: 0 .75rem;
            color: #5A6B82;
            font: 13px/1.4 Roboto, Arial, sans-serif;
        }
    </style>
    """)
    geral = st.Page(visao_geral, title="Visão Geral", default=True)
    executivo = st.Page(visao_executiva, title="Visão Executiva", url_path="visao-executiva")
    unidade = st.Page(por_unidade, title="Por Unidade", url_path="por-unidade")
    pagina = st.navigation([geral, executivo, unidade], position="hidden")
    with st.sidebar:
        st.image(str(ASSETS / "fms.png"), width=155)
        for item in (geral, executivo, unidade):
            if item is executivo:
                st.caption("SERVIDORES")
            if item.url_path == pagina.url_path:
                with st.container(key="menu-ativo"):
                    st.page_link(item)
            else:
                st.page_link(item)
        st.caption("TERMINAIS")
        st.html("""
            <div class="indexponto-menu-reservado">
                <span>Visão Executiva</span>
                <span>Por Unidade</span>
                <span>Cronograma</span>
            </div>
        """)
    pagina.run()


if __name__ == "__main__":
    main()
