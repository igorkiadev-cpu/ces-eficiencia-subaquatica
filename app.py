import streamlit as st
import pandas as pd
import plotly.express as px
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

# =========================
# HEADER
# =========================
col1, col2 = st.columns([1, 6])

with col1:
    logo_path = "assets/belov.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=120)

with col2:
    st.title("CES - Controle de Eficiência Subaquática")
    st.caption("Operational Efficiency Dashboard")

DATA_PATH = "data/dives.csv"

# =========================
# SESSION STATE (UX)
# =========================
if "sucesso" not in st.session_state:
    st.session_state.sucesso = False

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
            "abortado_mergulhador","abortado_embarcacao","observacoes"
        ])

def salvar_dados(df):
    df.to_csv(DATA_PATH, index=False)

def gerar_pdf(df):
    doc = SimpleDocTemplate("relatorio.pdf")
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Relatório Operacional - CES", styles["Title"]))

    for _, row in df.tail(10).iterrows():
        texto = f"""
        Data: {row['data']} |
        Embarcação: {row['embarcacao']} |
        Mergulho: {row['id_mergulho']} |
        Tempo: {row['tempo_mergulho']} min
        """
        elementos.append(Paragraph(texto, styles["Normal"]))

    doc.build(elementos)

    with open("relatorio.pdf", "rb") as f:
        return f.read()

df = carregar_dados()

# =========================
# MENU
# =========================
menu = st.sidebar.selectbox(
    "Menu",
    ["Registro de Mergulho", "Dashboard Quinzenal"]
)

# =========================
# INPUT
# =========================
if menu == "Registro de Mergulho":

    st.header("📥 Registro de Operação")

    with st.form("formulario"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data")

            # 🔄 limpa mensagem ao mudar data
            if st.session_state.sucesso:
                st.session_state.sucesso = False

            embarcacao = st.selectbox(
                "Embarcação",
                ["Amaralina", "Humaitá", "Cidade de Ouro Preto"]
            )
            numero_mergulho = st.selectbox("Número do Mergulho", list(range(1, 21)))

        with col2:
            tempo_equipagem = st.number_input("Tempo de Equipagem (min)", 0)
            tempo_mergulho = st.number_input("Tempo de Mergulho Efetivo (min)", 0)
            tempo_reposicionamento = st.number_input("Reposicionamento (min)", 0)

            abortado_mergulhador = st.checkbox("Abortado pelo Mergulhador")
            abortado_embarcacao = st.checkbox("Abortado pela Embarcação")

        observacoes = st.text_area("Observações do Superintendente")

        submitted = st.form_submit_button("Salvar")

        if submitted:

            duplicado = df[
                (df["data"] == str(data)) &
                (df["id_mergulho"] == numero_mergulho)
            ]

            if not duplicado.empty:
                st.error("❌ Já existe esse número de mergulho nesta data!")
            else:
                novo_dado = pd.DataFrame([{
                    "data": data,
                    "embarcacao": embarcacao,
                    "id_mergulho": numero_mergulho,
                    "tempo_equipagem": tempo_equipagem,
                    "tempo_mergulho": tempo_mergulho,
                    "tempo_reposicionamento": tempo_reposicionamento,
                    "abortado_mergulhador": abortado_mergulhador,
                    "abortado_embarcacao": abortado_embarcacao,
                    "observacoes": observacoes
                }])

                df = pd.concat([df, novo_dado], ignore_index=True)
                salvar_dados(df)

                st.session_state.sucesso = True

    # ✅ mensagem fora do form
    if st.session_state.sucesso:
        st.success("✅ Registro salvo com sucesso!")

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard Quinzenal":

    st.header("📊 Dashboard Quinzenal")

    if df.empty:
        st.warning("Sem dados ainda.")
    else:
        df["data"] = pd.to_datetime(df["data"])

        colf1, colf2 = st.columns(2)

        with colf1:
            filtro_embarcacao = st.selectbox(
                "Embarcação",
                ["Todas"] + list(df["embarcacao"].unique())
            )

        with colf2:
            dias = st.slider("Período (dias)", 7, 30, 15)

        if filtro_embarcacao != "Todas":
            df = df[df["embarcacao"] == filtro_embarcacao]

        df_filtrado = df[df["data"] >= (pd.Timestamp.today() - pd.Timedelta(days=dias))]

        if not df_filtrado.empty:

            total_mergulhos = len(df_filtrado)

            total_equipagem = df_filtrado["tempo_equipagem"].sum()
            total_mergulho = df_filtrado["tempo_mergulho"].sum()
            total_repo = df_filtrado["tempo_reposicionamento"].sum()

            total_geral = total_equipagem + total_mergulho + total_repo

            eficiencia = (total_mergulho / total_geral) * 100 if total_geral > 0 else 0

            abortos = (
                df_filtrado["abortado_mergulhador"].sum() +
                df_filtrado["abortado_embarcacao"].sum()
            )

            taxa_abortos = (abortos / total_mergulhos * 100) if total_mergulhos > 0 else 0
            taxa_repo = (total_repo / total_geral * 100) if total_geral > 0 else 0

            if eficiencia < 40:
                performance = "🔴 Ruim"
            elif eficiencia < 60:
                performance = "🟡 Regular"
            elif eficiencia < 80:
                performance = "🟢 Bom"
            else:
                performance = "🔵 Excelente"

            k1, k2, k3, k4, k5 = st.columns(5)

            k1.metric("🔢 Mergulhos", total_mergulhos)
            k2.metric("⚡ Eficiência (%)", f"{eficiencia:.1f}")
            k3.metric("🚨 Abortos (%)", f"{taxa_abortos:.1f}")
            k4.metric("⚠️ Reposicionamento (%)", f"{taxa_repo:.1f}")
            k5.metric("🏆 Performance", performance)

            st.subheader("🧠 Insights Operacionais")

            if eficiencia < 50:
                st.error("Baixa eficiência operacional")

            if taxa_repo > 40:
                st.warning("Alto tempo de reposicionamento")

            if taxa_abortos > 20:
                st.warning("Alta taxa de abortos")

            col1, col2 = st.columns(2)

            with col1:
                fig_pizza = px.pie(
                    names=["Equipagem", "Mergulho", "Reposicionamento"],
                    values=[total_equipagem, total_mergulho, total_repo]
                )
                st.plotly_chart(fig_pizza, use_container_width=True)

            with col2:
                resumo = df_filtrado.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()
                fig_bar = px.bar(resumo, x="embarcacao", y="tempo_mergulho")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.subheader("📝 Últimas Observações")
            obs = df_filtrado[["data","observacoes"]].dropna().tail(5)
            st.dataframe(obs)

            # 📄 BOTÃO PDF
            pdf = gerar_pdf(df_filtrado)

            st.download_button(
                label="📄 Baixar Relatório PDF",
                data=pdf,
                file_name="relatorio_operacional.pdf",
                mime="application/pdf"
            )
