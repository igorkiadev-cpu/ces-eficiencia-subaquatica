import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import date

st.set_page_config(layout="wide")

# =========================
# 🗄️ BANCO
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
        numero_mergulho INTEGER,
        tempo_equipagem REAL,
        tempo_mergulho REAL,
        tempo_reposicionamento REAL,
        status TEXT,
        motivo_abortado TEXT,
        observacoes TEXT
    )
    """)

    conn.commit()
    conn.close()

def carregar_dados():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM operacoes", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def gerar_numero_mergulho(df, data):
    if df.empty:
        return 1

    df["data"] = pd.to_datetime(df["data"])
    hoje_df = df[df["data"] == pd.to_datetime(data)]

    if hoje_df.empty:
        return 1
    else:
        return hoje_df["numero_mergulho"].max() + 1

def salvar_dados(novo):
    conn = get_connection()

    existente = pd.read_sql(
        "SELECT * FROM operacoes WHERE data=? AND numero_mergulho=?",
        conn,
        params=(novo["data"][0], int(novo["numero_mergulho"][0]))
    )

    if not existente.empty:
        conn.close()
        return False

    novo.to_sql("operacoes", conn, if_exists="append", index=False)
    conn.close()
    return True

# INIT
inicializar_banco()
df = carregar_dados()

# =========================
# HEADER
# =========================
st.title("CES - Controle de Eficiência Subaquática")
st.caption("Operational Efficiency System")

menu = st.sidebar.radio("Menu", ["Operação", "Análise da Quinzena"])

# =========================
# 📥 OPERAÇÃO
# =========================
if menu == "Operação":

    st.header("Registro de Mergulho")

    data_input = st.date_input("Data", value=date.today())

    numero_auto = gerar_numero_mergulho(df, data_input)

    st.info(f"Número do mergulho: {numero_auto}")

    embarcacao = st.selectbox(
        "Embarcação",
        ["Amaralina", "Humaitá", "Cidade de Ouro Preto"]
    )

    status = st.radio(
        "Status",
        ["produtivo", "abortado_mergulhador", "abortado_embarcacao"]
    )

    motivo = None

    if status == "abortado_mergulhador":
        motivo = st.selectbox("Motivo", ["Correnteza", "Swell"])

    elif status == "abortado_embarcacao":
        motivo = st.selectbox("Motivo", ["Swell Alto", "Posição", "Vento"])

    col1, col2, col3 = st.columns(3)

    with col1:
        tempo_equip = st.number_input("Equipagem (min)", min_value=0)

    with col2:
        tempo_merg = st.number_input("Mergulho (min)", min_value=0)

    with col3:
        tempo_repo = st.number_input("Reposicionamento (min)", min_value=0)

    obs = st.text_area("Observações")

    if st.button("Salvar"):

        novo = pd.DataFrame([{
            "data": str(data_input),
            "embarcacao": embarcacao,
            "numero_mergulho": numero_auto,
            "tempo_equipagem": tempo_equip,
            "tempo_mergulho": tempo_merg,
            "tempo_reposicionamento": tempo_repo,
            "status": status,
            "motivo_abortado": motivo,
            "observacoes": obs
        }])

        if salvar_dados(novo):
            st.success("Salvo com sucesso!")
            st.rerun()
        else:
            st.error("Erro: mergulho duplicado!")

# =========================
# 📊 ANÁLISE
# =========================
elif menu == "Análise da Quinzena":

    st.header("Dashboard Executivo")

    if df.empty:
        st.warning("Sem dados")
    else:
        df["data"] = pd.to_datetime(df["data"])

        df_q = df[
            df["data"] >= (pd.Timestamp.today() - pd.Timedelta(days=15))
        ].copy()

        total_mergulhos = len(df_q)

        total_equip = df_q["tempo_equipagem"].sum()
        total_merg = df_q["tempo_mergulho"].sum()
        total_repo = df_q["tempo_reposicionamento"].sum()

        total = total_equip + total_merg + total_repo
        eficiencia = (total_merg / total * 100) if total > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Mergulhos", total_mergulhos)
        k2.metric("Eficiência", f"{eficiencia:.1f}%")
        k3.metric("Tempo Produtivo", f"{total_merg:.0f} min")

        # 🍕 Pizza
        fig = px.pie(df_q, names="status", hole=0.6)
        st.plotly_chart(fig, use_container_width=True)

        # 📈 tendência
        trend = df_q.groupby("data")["tempo_mergulho"].sum().reset_index()
        st.plotly_chart(px.line(trend, x="data", y="tempo_mergulho"),
                        use_container_width=True)

        # 🏆 produção
        bar = df_q.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()
        st.plotly_chart(px.bar(bar, x="embarcacao", y="tempo_mergulho"),
                        use_container_width=True)
