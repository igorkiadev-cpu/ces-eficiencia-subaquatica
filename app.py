import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")

# =========================
# HEADER (LOGO + TÍTULO)
# =========================
col1, col2 = st.columns([1, 6])

with col1:
    import os

logo_path = None

# tenta possíveis nomes (resolve 100% dos casos)
possiveis = [
    "assets/belov.png",
    "assets/belov.jpg",
    "assets/belov.png.jpg",
    "assets/Belov.png",
    "assets/BELOV.png"
]

for p in possiveis:
    if os.path.exists(p):
        logo_path = p
        break

if logo_path:
    st.image(logo_path, width=120)
else:
    st.warning("⚠️ Logo não encontrada na pasta assets")

with col2:
    st.title("CES - Controle de Eficiência Subaquática")
    st.caption("Plataforma de Análise de Operações de Mergulho")

DATA_PATH = "data/dives.csv"

# =========================
# FUNÇÕES
# =========================
def carregar_dados():
    if os.path.exists(DATA_PATH):
        return pd.read_csv(DATA_PATH)
    else:
        return pd.DataFrame(columns=[
            "data","embarcacao","id_mergulho",
            "tempo_equipagem","tempo_mergulho","tempo_reposicionamento",
            "abortado_mergulhador","abortado_embarcacao"
        ])

def salvar_dados(df):
    df.to_csv(DATA_PATH, index=False)

df = carregar_dados()

# =========================
# MENU
# =========================
menu = st.sidebar.selectbox(
    "Menu",
    ["Registro de Mergulho", "Dashboard Quinzenal"]
)

# =========================
# TELA 1 - INPUT
# =========================
if menu == "Registro de Mergulho":

    st.header("📥 Registro de Operação")

    with st.form("formulario"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data")

            embarcacao = st.selectbox(
                "Embarcação",
                ["Amaralina", "Humaitá", "Cidade de Ouro Preto"]
            )

            id_mergulho = st.text_input("ID do Mergulho")

        with col2:
            tempo_equipagem = st.number_input("Tempo de Equipagem (min)", 0)
            tempo_mergulho = st.number_input("Tempo de Mergulho Efetivo (min)", 0)
            tempo_reposicionamento = st.number_input("Reposicionamento (min)", 0)

        submitted = st.form_submit_button("Salvar")

        if submitted:
            novo_dado = pd.DataFrame([{
                "data": data,
                "embarcacao": embarcacao,
                "id_mergulho": id_mergulho,
                "tempo_equipagem": tempo_equipagem,
                "tempo_mergulho": tempo_mergulho,
                "tempo_reposicionamento": tempo_reposicionamento,
                "abortado_mergulhador": 0,
                "abortado_embarcacao": 0
            }])

            df = pd.concat([df, novo_dado], ignore_index=True)
            salvar_dados(df)

            st.success("✅ Registro salvo com sucesso!")

# =========================
# TELA 2 - DASHBOARD
# =========================
if menu == "Dashboard Quinzenal":

    st.header("📊 Dashboard Quinzenal")

    if df.empty:
        st.warning("Sem dados ainda.")
    else:
        df["data"] = pd.to_datetime(df["data"])

        # =========================
        # FILTROS
        # =========================
        colf1, colf2 = st.columns(2)

        with colf1:
            embarcacoes = ["Todas"] + list(df["embarcacao"].unique())
            filtro_embarcacao = st.selectbox("Filtrar por Embarcação", embarcacoes)

        with colf2:
            dias = st.slider("Período (dias)", 7, 30, 15)

        if filtro_embarcacao != "Todas":
            df = df[df["embarcacao"] == filtro_embarcacao]

        df_filtrado = df[df["data"] >= (pd.Timestamp.today() - pd.Timedelta(days=dias))]

        if df_filtrado.empty:
            st.warning("Sem dados no período selecionado.")
        else:
            # =========================
            # KPIs
            # =========================
            total_equipagem = df_filtrado["tempo_equipagem"].sum()
            total_mergulho = df_filtrado["tempo_mergulho"].sum()
            total_repo = df_filtrado["tempo_reposicionamento"].sum()

            total_geral = total_equipagem + total_mergulho + total_repo

            eficiencia = (total_mergulho / total_geral) * 100 if total_geral > 0 else 0

            # CLASSIFICAÇÃO
            if eficiencia < 40:
                performance = "🔴 Ruim"
            elif eficiencia < 60:
                performance = "🟡 Regular"
            elif eficiencia < 80:
                performance = "🟢 Bom"
            else:
                performance = "🔵 Excelente"

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            kpi1.metric("⏱️ Tempo Total (min)", int(total_geral))
            kpi2.metric("🌊 Tempo de Mergulho (min)", int(total_mergulho))
            kpi3.metric("⚡ Eficiência (%)", f"{eficiencia:.1f}")
            kpi4.metric("🏆 Performance", performance)

            # =========================
            # GRÁFICOS
            # =========================
            col1, col2 = st.columns(2)

            with col1:
                dados_pizza = pd.DataFrame({
                    "Categoria": ["Equipagem", "Mergulho", "Reposicionamento"],
                    "Tempo": [total_equipagem, total_mergulho, total_repo]
                })

                fig_pizza = px.pie(
                    dados_pizza,
                    names="Categoria",
                    values="Tempo",
                    title="Distribuição de Tempo Operacional"
                )

                st.plotly_chart(fig_pizza, use_container_width=True)

            with col2:
                resumo_emb = df_filtrado.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()

                fig_bar = px.bar(
                    resumo_emb,
                    x="embarcacao",
                    y="tempo_mergulho",
                    title="Tempo de Mergulho por Embarcação"
                )

                st.plotly_chart(fig_bar, use_container_width=True)

            # =========================
            # TENDÊNCIA (linha)
            # =========================
            st.subheader("📈 Tendência de Eficiência")

            df_filtrado["total"] = (
                df_filtrado["tempo_equipagem"] +
                df_filtrado["tempo_mergulho"] +
                df_filtrado["tempo_reposicionamento"]
            )

            df_filtrado["eficiencia"] = (
                df_filtrado["tempo_mergulho"] / df_filtrado["total"] * 100
            )

            tendencia = df_filtrado.groupby("data")["eficiencia"].mean().reset_index()

            fig_line = px.line(
                tendencia,
                x="data",
                y="eficiencia",
                title="Eficiência ao Longo do Tempo"
            )

            st.plotly_chart(fig_line, use_container_width=True)

            # =========================
            # RANKING
            # =========================
            st.subheader("🏆 Ranking de Embarcações")

            ranking = df_filtrado.groupby("embarcacao").agg({
                "tempo_mergulho": "sum",
                "tempo_equipagem": "sum",
                "tempo_reposicionamento": "sum"
            }).reset_index()

            ranking["total"] = (
                ranking["tempo_mergulho"] +
                ranking["tempo_equipagem"] +
                ranking["tempo_reposicionamento"]
            )

            ranking["eficiencia"] = (
                ranking["tempo_mergulho"] / ranking["total"] * 100
            )

            ranking = ranking.sort_values(by="eficiencia", ascending=False)

            st.dataframe(ranking)
