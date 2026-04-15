import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")

# =========================
# TÍTULO
# =========================
st.title("🌊 CES - Controle de Eficiência Subaquática")
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
            embarcacao = st.text_input("Embarcação")
            id_mergulho = st.text_input("ID do Mergulho")

        with col2:
            tempo_equipagem = st.number_input("Tempo de Equipagem (min)", 0)
            tempo_mergulho = st.number_input("Tempo de Mergulho Efetivo (min)", 0)
            tempo_reposicionamento = st.number_input("Reposicionamento (min)", 0)

            abortado_mergulhador = st.checkbox("Abortado pelo Mergulhador")
            abortado_embarcacao = st.checkbox("Abortado pela Embarcação")

        submit = st.form_submit_button("Salvar")

    if submit:
        nova_linha = pd.DataFrame([{
            "data": data,
            "embarcacao": embarcacao,
            "id_mergulho": id_mergulho,
            "tempo_equipagem": tempo_equipagem,
            "tempo_mergulho": tempo_mergulho,
            "tempo_reposicionamento": tempo_reposicionamento,
            "abortado_mergulhador": int(abortado_mergulhador),
            "abortado_embarcacao": int(abortado_embarcacao)
        }])

        df = pd.concat([df, nova_linha], ignore_index=True)
        salvar_dados(df)

        st.success("✅ Registro salvo com sucesso!")

# =========================
# TELA 2 - DASHBOARD
# =========================
elif menu == "Dashboard Quinzenal":

    st.header("📊 Painel Operacional")

    if df.empty:
        st.warning("Nenhum dado disponível.")
    else:
        df["data"] = pd.to_datetime(df["data"])

        # =========================
        # CÁLCULOS
        # =========================
        df["eficiencia"] = df["tempo_mergulho"] / df["tempo_equipagem"]
        df["tempo_improdutivo"] = df["tempo_equipagem"] - df["tempo_mergulho"]

        df["score_operacional"] = df["eficiencia"] * 100
        df.loc[df["abortado_mergulhador"] == 1, "score_operacional"] -= 30
        df.loc[df["abortado_embarcacao"] == 1, "score_operacional"] -= 20

        # =========================
        # CLASSIFICAÇÃO
        # =========================
        def classificar(score):
            if score < 40:
                return "Crítico"
            elif score < 60:
                return "Baixo"
            elif score < 75:
                return "Regular"
            elif score < 90:
                return "Bom"
            else:
                return "Excelente"

        df["classificacao"] = df["score_operacional"].apply(classificar)

        # filtro quinzena
        df_q = df[df["data"].dt.day <= 15]

        # =========================
        # KPIs
        # =========================
        tempo_total_mergulho = df_q["tempo_mergulho"].sum()
        tempo_total_equipagem = df_q["tempo_equipagem"].sum()
        tempo_total_reposicionamento = df_q["tempo_reposicionamento"].sum()

        eficiencia_media = (tempo_total_mergulho / tempo_total_equipagem) if tempo_total_equipagem > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total de Mergulhos", len(df_q))
        col2.metric("Tempo de Mergulho (min)", tempo_total_mergulho)
        col3.metric("Reposicionamento (min)", tempo_total_reposicionamento)
        col4.metric("Eficiência Média", f"{eficiencia_media:.2%}")

        # =========================
        # GRÁFICO 1 - BARRA
        # =========================
        tempo_improdutivo_total = tempo_total_equipagem - tempo_total_mergulho

        fig1 = px.bar(
            x=["Tempo Produtivo", "Reposicionamento", "Tempo Improdutivo"],
            y=[tempo_total_mergulho, tempo_total_reposicionamento, tempo_improdutivo_total],
            title="Distribuição do Tempo Operacional"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # =========================
        # GRÁFICO 2 - LINHA
        # =========================
        df_dia = df_q.groupby("data")["eficiencia"].mean().reset_index()

        fig2 = px.line(
            df_dia,
            x="data",
            y="eficiencia",
            title="Eficiência ao Longo do Tempo"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # =========================
        # GRÁFICO 3 - ABORTOS
        # =========================
        fig3 = px.bar(
            x=["Mergulhador", "Embarcação"],
            y=[df_q["abortado_mergulhador"].sum(), df_q["abortado_embarcacao"].sum()],
            title="Interrupções Operacionais"
        )
        st.plotly_chart(fig3, use_container_width=True)

        # =========================
        # GRÁFICO 4 - PIZZA
        # =========================
        fig4 = px.pie(
            names=["Tempo Produtivo", "Reposicionamento", "Tempo Improdutivo"],
            values=[
                tempo_total_mergulho,
                tempo_total_reposicionamento,
                tempo_improdutivo_total
            ],
            title="Distribuição Percentual do Tempo Operacional"
        )
        st.plotly_chart(fig4, use_container_width=True)

        # =========================
        # GRÁFICO 5 - CLASSIFICAÇÃO
        # =========================
        fig5 = px.histogram(
            df_q,
            x="classificacao",
            title="Distribuição da Eficiência Operacional"
        )
        st.plotly_chart(fig5, use_container_width=True)

        # =========================
        # LEGENDA
        # =========================
        st.markdown("### 📘 Critérios de Classificação")
        st.markdown("""
        - 🔴 Crítico: abaixo de 40  
        - 🟠 Baixo: 40 a 60  
        - 🟡 Regular: 60 a 75  
        - 🔵 Bom: 75 a 90  
        - 🟢 Excelente: acima de 90  
        """)

        # =========================
        # TABELA FINAL
        # =========================
        st.subheader("📈 Análise por Mergulho")

        st.dataframe(
            df_q.sort_values(by="score_operacional", ascending=False)[
                ["data","embarcacao","id_mergulho","score_operacional","classificacao"]
            ]
        )
