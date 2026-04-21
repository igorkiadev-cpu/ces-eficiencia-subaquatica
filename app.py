import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

# =========================
# 🗄️ BANCO DE DADOS
# =========================
DB_PATH = "ces.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def inicializar_banco():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operacoes (
        data TEXT,
        embarcacao TEXT,
        id_mergulho INTEGER,
        tempo_equipagem REAL,
        tempo_mergulho REAL,
        tempo_reposicionamento REAL,
        abortado_mergulhador BOOLEAN,
        abortado_embarcacao BOOLEAN,
        observacoes TEXT
    )
    """)

    conn.commit()
    conn.close()

def salvar_dados(novo_dado):
    conn = get_connection()

    existente = pd.read_sql(
        "SELECT * FROM operacoes WHERE data=? AND id_mergulho=?",
        conn,
        params=(
            str(novo_dado["data"].iloc[0]),
            int(novo_dado["id_mergulho"].iloc[0])
        )
    )

    if not existente.empty:
        conn.close()
        return False

    novo_dado.to_sql("operacoes", conn, if_exists="append", index=False)
    conn.close()
    return True

def carregar_dados():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM operacoes", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

inicializar_banco()
df = carregar_dados()

# =========================
# HEADER
# =========================
st.title("CES - Controle de Eficiência Subaquática")
st.caption("Operational Efficiency System")

# =========================
# MENU
# =========================
menu = st.sidebar.selectbox(
    "Menu",
    ["Registro", "Dashboard Executivo"]
)

# =========================
# 📥 REGISTRO
# =========================
if menu == "Registro":

    st.header("Registro de Mergulho")

    with st.form("form"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data")
            embarcacao = st.selectbox(
                "Embarcação",
                ["Amaralina", "Humaitá", "Cidade de Ouro Preto"]
            )
            numero_mergulho = st.selectbox("Número do Mergulho", list(range(0, 11)))

        with col2:
            tempo_equipagem = st.number_input("Equipagem (min)", 0)
            tempo_mergulho = st.number_input("Mergulho (min)", 0)
            tempo_repo = st.number_input("Reposicionamento (min)", 0)

            tipo_operacao = st.selectbox(
                "Status",
                ["Produtivo", "Abortado pelo Mergulhador", "Abortado pela Embarcação"]
            )

        obs = st.text_area("Observações")

        if st.form_submit_button("Salvar"):

            novo = pd.DataFrame([{
                "data": data,
                "embarcacao": embarcacao,
                "id_mergulho": numero_mergulho,
                "tempo_equipagem": tempo_equipagem,
                "tempo_mergulho": tempo_mergulho,
                "tempo_reposicionamento": tempo_repo,
                "abortado_mergulhador": tipo_operacao == "Abortado pelo Mergulhador",
                "abortado_embarcacao": tipo_operacao == "Abortado pela Embarcação",
                "observacoes": obs
            }])

            if salvar_dados(novo):
                st.success("Registro salvo!")
            else:
                st.error("Já existe esse mergulho nessa data!")

# =========================
# 📊 DASHBOARD
# =========================
if menu == "Dashboard Executivo":

    st.header("Dashboard Executivo")

    if df.empty:
        st.warning("Sem dados.")
    else:
        df["data"] = pd.to_datetime(df["data"])

        dias = st.slider("Período (dias)", 7, 30, 15)
        custo_dia = st.number_input("Custo diário operação ($)", 0)

        df = df[df["data"] >= (pd.Timestamp.today() - pd.Timedelta(days=dias))]

        df["status"] = df.apply(
            lambda r: "Abortado pelo Mergulhador" if r["abortado_mergulhador"]
            else "Abortado pela Embarcação" if r["abortado_embarcacao"]
            else "Produtivo", axis=1
        )

        total_mergulhos = len(df)
        total_equip = df["tempo_equipagem"].sum()
        total_merg = df["tempo_mergulho"].sum()
        total_repo = df["tempo_reposicionamento"].sum()

        total = total_equip + total_merg + total_repo

        eficiencia = (total_merg / total * 100) if total > 0 else 0

        abortos = df[df["status"] != "Produtivo"].shape[0]
        taxa_abortos = (abortos / total_mergulhos * 100) if total_mergulhos else 0

        # 💰 CUSTO
        custo_min = custo_dia / 1440 if custo_dia > 0 else 0
        custo_perdido = (total_equip + total_repo) * custo_min

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Mergulhos", total_mergulhos)
        k2.metric("Eficiência %", f"{eficiencia:.1f}")
        k3.metric("Abortos %", f"{taxa_abortos:.1f}")
        k4.metric("💰 Custo Perdido", f"${custo_perdido:,.0f}")

        # 🍕 PIZZA
        resumo = df["status"].value_counts().reset_index()
        resumo.columns = ["status", "qtd"]

        fig1 = px.pie(resumo, names="status", values="qtd", hole=0.5)

        # 📈 LINHA
        trend = df.groupby("data")["tempo_mergulho"].sum().reset_index()
        fig2 = px.line(trend, x="data", y="tempo_mergulho")

        # 🏆 BAR
        bar = df.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()
        fig3 = px.bar(bar, x="embarcacao", y="tempo_mergulho")

        col1, col2 = st.columns(2)
        col1.plotly_chart(fig1, use_container_width=True)
        col2.plotly_chart(fig2, use_container_width=True)

        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Insights")

        if eficiencia < 50:
            st.error("Baixa eficiência")

        if taxa_abortos > 20:
            st.warning("Alta taxa de abortos")

        st.subheader("Observações")
        st.dataframe(df[["data", "observacoes"]].dropna().tail(5))

        # 📄 PDF
        def gerar_pdf(df):
            doc = SimpleDocTemplate("relatorio.pdf")
            styles = getSampleStyleSheet()
            elems = [Paragraph("Relatório CES", styles["Title"])]

            for _, r in df.tail(10).iterrows():
                elems.append(Paragraph(f"{r['data']} - {r['embarcacao']}", styles["Normal"]))

            doc.build(elems)
            with open("relatorio.pdf", "rb") as f:
                return f.read()

        pdf = gerar_pdf(df)

        st.download_button(
            "Baixar PDF",
            pdf,
            file_name="relatorio.pdf"
        )
