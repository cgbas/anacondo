"""
Dashboard Interativo — Prestações de Contas
Condomínio | P7

Uso:
    streamlit run scripts/dashboard.py
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="ANACONDO — Prestações",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Caminhos ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CSV_DIR = ROOT / "exports" / "csv"

PRESTACOES_CSV = CSV_DIR / "prestacoes.csv"
ANOMALIAS_CSV = CSV_DIR / "anomalias_prestacoes.csv"

CATEGORIA_CORES = {
    "Pessoal": "#2E86C1",
    "Utilidades": "#1ABC9C",
    "Manutenção": "#F39C12",
    "Taxas e Impostos": "#8E44AD",
    "Administração": "#E74C3C",
    "Receitas Condominiais": "#27AE60",
    "Fundos": "#16A085",
    "Retiradas/Acerto": "#95A5A6",
    "Outros": "#BDC3C7",
}


# ── Carregamento de dados ─────────────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando dados…")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(PRESTACOES_CSV)
    df["evento"] = df["evento"].str.strip()
    df["macro_categoria"] = df["macro_categoria"].str.strip()

    anom = pd.read_csv(ANOMALIAS_CSV)
    anom["evento"] = anom["evento"].str.strip()
    # Severidade IQR por categoria
    q75 = df.groupby("macro_categoria")["valor"].quantile(0.75)
    q90 = df.groupby("macro_categoria")["valor"].quantile(0.90)
    q99 = df.groupby("macro_categoria")["valor"].quantile(0.99)

    def _sev(row: pd.Series) -> str:
        cat = row["macro_categoria"]
        v = row["valor"]
        if v >= q99.get(cat, float("inf")):
            return "Crítica"
        if v >= q90.get(cat, float("inf")):
            return "Alta"
        if v >= q75.get(cat, float("inf")):
            return "Média"
        return "Baixa"

    anom["severidade"] = anom.apply(_sev, axis=1)
    return df, anom


def sort_mes(series: pd.Series) -> pd.Series:
    return pd.Categorical(series, categories=sorted(series.unique()), ordered=True)


# ── Sidebar — filtros ─────────────────────────────────────────────────────────
def sidebar_filters(df: pd.DataFrame, anom: pd.DataFrame):
    st.sidebar.header("🔍 Filtros")

    meses = sorted(df["mes_ano"].unique())
    col1, col2 = st.sidebar.columns(2)
    mes_inicio = col1.selectbox("De", meses, index=0, key="mes_inicio")
    mes_fim = col2.selectbox("Até", meses, index=len(meses) - 1, key="mes_fim")

    categorias = ["Todas"] + sorted(df["macro_categoria"].unique())
    categoria = st.sidebar.selectbox("Categoria", categorias)

    tipo = st.sidebar.radio("Tipo", ["Todos", "RECEITA", "DESPESA"], horizontal=True)

    sev_opts = ["Todas", "Crítica", "Alta", "Média", "Baixa"]
    severidade = st.sidebar.selectbox("Severidade (anomalias)", sev_opts)

    return mes_inicio, mes_fim, categoria, tipo, severidade


def apply_filters(
    df: pd.DataFrame,
    anom: pd.DataFrame,
    mes_inicio: str,
    mes_fim: str,
    categoria: str,
    tipo: str,
    severidade: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mask = (df["mes_ano"] >= mes_inicio) & (df["mes_ano"] <= mes_fim)
    if categoria != "Todas":
        mask &= df["macro_categoria"] == categoria
    if tipo != "Todos":
        mask &= df["tipo"] == tipo
    df_f = df[mask].copy()

    mask_a = (anom["mes_ano"] >= mes_inicio) & (anom["mes_ano"] <= mes_fim)
    if categoria != "Todas":
        mask_a &= anom["macro_categoria"] == categoria
    if severidade != "Todas":
        mask_a &= anom["severidade"] == severidade
    anom_f = anom[mask_a].copy()

    return df_f, anom_f


# ── KPIs ──────────────────────────────────────────────────────────────────────
def render_kpis(df_f: pd.DataFrame, anom_f: pd.DataFrame):
    receitas = df_f[df_f["tipo"] == "RECEITA"]["valor"].sum()
    despesas = df_f[df_f["tipo"] == "DESPESA"]["valor"].sum()
    saldo = receitas - despesas
    n_anom = len(anom_f)
    pct_anom = n_anom / len(df_f) * 100 if len(df_f) else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Receitas", f"R$ {receitas:,.0f}".replace(",", "."))
    c2.metric("Total Despesas", f"R$ {despesas:,.0f}".replace(",", "."))
    delta_color = "normal" if saldo >= 0 else "inverse"
    c3.metric("Saldo", f"R$ {saldo:,.0f}".replace(",", "."), delta_color=delta_color)
    c4.metric("Registros", f"{len(df_f):,}")
    c5.metric("Anomalias", f"{n_anom}", f"{pct_anom:.1f}% do total")


# ── Gráficos ──────────────────────────────────────────────────────────────────
def chart_pl_mensal(df_f: pd.DataFrame):
    grp = (
        df_f.groupby(["mes_ano", "tipo"], as_index=False)["valor"]
        .sum()
        .rename(columns={"valor": "total"})
    )
    grp["mes_cat"] = sort_mes(grp["mes_ano"])
    grp = grp.sort_values("mes_cat")

    fig = px.bar(
        grp,
        x="mes_ano",
        y="total",
        color="tipo",
        barmode="group",
        color_discrete_map={"RECEITA": "#27AE60", "DESPESA": "#C0392B"},
        labels={"mes_ano": "Mês", "total": "R$", "tipo": ""},
        title="Receitas vs Despesas por Mês",
        text_auto=".2s",
    )
    fig.update_layout(xaxis_tickangle=-45, plot_bgcolor="white", height=380)
    return fig


def chart_categorias(df_f: pd.DataFrame):
    despesas = df_f[df_f["tipo"] == "DESPESA"]
    grp = despesas.groupby("macro_categoria", as_index=False)["valor"].sum()
    grp = grp.sort_values("valor", ascending=False)

    fig = px.pie(
        grp,
        names="macro_categoria",
        values="valor",
        color="macro_categoria",
        color_discrete_map=CATEGORIA_CORES,
        title="Despesas por Categoria",
        hole=0.35,
    )
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>R$ %{value:,.2f}")
    fig.update_layout(height=380, showlegend=False)
    return fig


def chart_top_eventos(df_f: pd.DataFrame):
    top = (
        df_f[df_f["tipo"] == "DESPESA"]
        .groupby("evento", as_index=False)["valor"]
        .sum()
        .sort_values("valor", ascending=True)
        .tail(15)
    )
    fig = px.bar(
        top,
        x="valor",
        y="evento",
        orientation="h",
        color="valor",
        color_continuous_scale="Reds",
        labels={"valor": "R$", "evento": ""},
        title="Top 15 Despesas por Evento (total período)",
        text_auto=".2s",
    )
    fig.update_layout(
        coloraxis_showscale=False, plot_bgcolor="white", height=440, yaxis={"tickfont": {"size": 11}}
    )
    return fig


def chart_evolucao_categoria(df_f: pd.DataFrame):
    despesas = df_f[df_f["tipo"] == "DESPESA"]
    grp = despesas.groupby(["mes_ano", "macro_categoria"], as_index=False)["valor"].sum()
    grp["mes_cat"] = sort_mes(grp["mes_ano"])
    grp = grp.sort_values("mes_cat")

    fig = px.area(
        grp,
        x="mes_ano",
        y="valor",
        color="macro_categoria",
        color_discrete_map=CATEGORIA_CORES,
        labels={"mes_ano": "Mês", "valor": "R$", "macro_categoria": ""},
        title="Evolução de Despesas por Categoria",
    )
    fig.update_layout(xaxis_tickangle=-45, plot_bgcolor="white", height=400)
    return fig


def chart_inadimplencia(df_f: pd.DataFrame):
    """Receitas condominiais vs multas por mês (proxy de inadimplência)."""
    rec_cond = df_f[
        df_f["evento"].str.contains(r"(?i)rec\.?\s*condom", na=False, regex=True)
        & df_f["tipo"].eq("RECEITA")
    ]
    multas = df_f[
        df_f["evento"].str.contains(r"(?i)multa|jrs\.", na=False, regex=True)
        & df_f["tipo"].eq("RECEITA")
    ]

    if rec_cond.empty and multas.empty:
        return None

    rec_mes = rec_cond.groupby("mes_ano", as_index=False)["valor"].sum().rename(columns={"valor": "Receita condominial"})
    mul_mes = multas.groupby("mes_ano", as_index=False)["valor"].sum().rename(columns={"valor": "Multas/Atraso"})

    merged = rec_mes.merge(mul_mes, on="mes_ano", how="outer").fillna(0)
    merged = merged.sort_values("mes_ano")
    merged["% atraso"] = (merged["Multas/Atraso"] / (merged["Receita condominial"] + merged["Multas/Atraso"]) * 100).round(2)

    fig = go.Figure()
    fig.add_bar(x=merged["mes_ano"], y=merged["Receita condominial"], name="Receita condominial", marker_color="#27AE60")
    fig.add_bar(x=merged["mes_ano"], y=merged["Multas/Atraso"], name="Multas/Atraso", marker_color="#E74C3C")
    fig.add_scatter(
        x=merged["mes_ano"],
        y=merged["% atraso"],
        name="% atraso",
        yaxis="y2",
        mode="lines+markers",
        marker_color="#F39C12",
        line_dash="dot",
    )
    fig.update_layout(
        barmode="stack",
        title="Inadimplência — Receita Condominial vs Multas",
        xaxis_tickangle=-45,
        yaxis={"title": "R$"},
        yaxis2={"title": "% atraso", "overlaying": "y", "side": "right", "ticksuffix": "%"},
        plot_bgcolor="white",
        height=400,
        legend={"orientation": "h", "y": -0.3},
    )
    return fig


def chart_anomalias(anom_f: pd.DataFrame):
    if anom_f.empty:
        return None

    grp = anom_f.groupby(["mes_ano", "severidade"], as_index=False).agg(
        qtd=("valor", "count"),
        total=("valor", "sum"),
    )
    grp = grp.sort_values("mes_ano")

    sev_order = ["Crítica", "Alta", "Média", "Baixa"]
    sev_cores = {"Crítica": "#C0392B", "Alta": "#E67E22", "Média": "#F1C40F", "Baixa": "#3498DB"}

    fig = px.bar(
        grp,
        x="mes_ano",
        y="qtd",
        color="severidade",
        category_orders={"severidade": sev_order},
        color_discrete_map=sev_cores,
        labels={"mes_ano": "Mês", "qtd": "Nº Anomalias", "severidade": "Severidade"},
        title="Anomalias por Mês e Severidade",
        text_auto=True,
    )
    fig.update_layout(xaxis_tickangle=-45, plot_bgcolor="white", height=360)
    return fig


# ── Export ────────────────────────────────────────────────────────────────────
def export_csv(df_f: pd.DataFrame, label: str) -> bytes:
    buf = io.StringIO()
    df_f.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue().encode("utf-8-sig")


# ── Layout principal ──────────────────────────────────────────────────────────
def main():
    st.title("📊 ANACONDO — Prestações de Contas")
    st.caption("Condomínio · mai/2022–jun/2026 · Fonte: prestacoes.csv + anomalias_prestacoes.csv")

    if not PRESTACOES_CSV.exists():
        st.error(f"Arquivo não encontrado: {PRESTACOES_CSV}\nExecute `prestacao_de_contas.ipynb` primeiro.")
        st.stop()

    df, anom = load_data()

    mes_inicio, mes_fim, categoria, tipo, severidade = sidebar_filters(df, anom)

    if mes_inicio > mes_fim:
        st.sidebar.error("'De' deve ser anterior a 'Até'.")
        st.stop()

    df_f, anom_f = apply_filters(df, anom, mes_inicio, mes_fim, categoria, tipo, severidade)

    if df_f.empty:
        st.warning("Nenhum registro encontrado para os filtros selecionados.")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    render_kpis(df_f, anom_f)
    st.divider()

    # ── Aba 1: Visão Geral ─────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Geral", "🔴 Anomalias", "📋 Tabela", "📤 Exportar"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(chart_pl_mensal(df_f), use_container_width=True)
        with col_b:
            st.plotly_chart(chart_categorias(df_f), use_container_width=True)

        st.plotly_chart(chart_evolucao_categoria(df_f), use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            st.plotly_chart(chart_top_eventos(df_f), use_container_width=True)
        with col_d:
            fig_inad = chart_inadimplencia(df_f)
            if fig_inad:
                st.plotly_chart(fig_inad, use_container_width=True)
            else:
                st.info("Sem dados de multa/inadimplência no período selecionado.")

    # ── Aba 2: Anomalias ───────────────────────────────────────────────────────
    with tab2:
        if anom_f.empty:
            st.info("Sem anomalias para os filtros selecionados.")
        else:
            fig_anom = chart_anomalias(anom_f)
            if fig_anom:
                st.plotly_chart(fig_anom, use_container_width=True)

            st.subheader(f"Detalhamento ({len(anom_f)} registros)")
            sev_order_map = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}
            anom_disp = anom_f.copy()
            anom_disp["_ord"] = anom_disp["severidade"].map(sev_order_map)
            anom_disp = anom_disp.sort_values(["_ord", "valor"], ascending=[True, False]).drop(columns="_ord")
            anom_disp["valor"] = anom_disp["valor"].map("R$ {:,.2f}".format)

            def _sev_color(val: str) -> str:
                return {
                    "Crítica": "background-color:#f5c6cb",
                    "Alta": "background-color:#ffd6a5",
                    "Média": "background-color:#fff3cd",
                    "Baixa": "background-color:#d1ecf1",
                }.get(val, "")

            st.dataframe(
                anom_disp[["mes_ano", "evento", "tipo", "valor", "macro_categoria", "motivo_anomalia", "severidade"]]
                .style.applymap(_sev_color, subset=["severidade"]),
                use_container_width=True,
                height=400,
            )

    # ── Aba 3: Tabela ──────────────────────────────────────────────────────────
    with tab3:
        st.subheader(f"Lançamentos filtrados ({len(df_f):,} registros)")
        df_disp = df_f.copy()
        df_disp["valor_fmt"] = df_disp["valor"].map("R$ {:,.2f}".format)
        st.dataframe(
            df_disp[["mes_ano", "evento", "tipo", "valor_fmt", "macro_categoria"]].rename(
                columns={"valor_fmt": "valor"}
            ),
            use_container_width=True,
            height=500,
        )

    # ── Aba 4: Exportar ────────────────────────────────────────────────────────
    with tab4:
        st.subheader("Exportar dados filtrados")
        col_e1, col_e2, col_e3 = st.columns(3)

        with col_e1:
            st.download_button(
                "⬇ Lançamentos (CSV)",
                data=export_csv(df_f, "lancamentos"),
                file_name=f"prestacoes_{mes_inicio}_{mes_fim}.csv",
                mime="text/csv",
            )

        with col_e2:
            st.download_button(
                "⬇ Anomalias (CSV)",
                data=export_csv(anom_f, "anomalias"),
                file_name=f"anomalias_{mes_inicio}_{mes_fim}.csv",
                mime="text/csv",
            )

        with col_e3:
            # Resumo mensal para Excel/BI
            resumo = (
                df_f.groupby(["mes_ano", "macro_categoria", "tipo"], as_index=False)["valor"]
                .sum()
                .round(2)
            )
            st.download_button(
                "⬇ Resumo Mensal (CSV)",
                data=export_csv(resumo, "resumo"),
                file_name=f"resumo_mensal_{mes_inicio}_{mes_fim}.csv",
                mime="text/csv",
            )

        st.info(
            "💡 Dica: os CSVs exportados respeitam os filtros aplicados na sidebar. "
            "Para exportar tudo, remova os filtros antes de baixar."
        )


if __name__ == "__main__":
    main()
