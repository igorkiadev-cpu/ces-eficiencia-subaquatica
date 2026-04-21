import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3

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
        id_mergulho INTEGER,
        tempo_equipagem REAL,
        tempo_mergulho REAL,
        tempo_reposicionamento REAL,
        abortado_mergulhador BOOLEAN,
        abortado_embarcacao BOOLEAN,
        motivo_abortado TEXT,
        observacoes TEXT
    )
    """)

    conn.commit()
    conn.close()

def salvar_dados(novo):
    conn = get_connection()

    existente = pd.read_sql(
        "SELECT * FROM operacoes WHERE data=? AND id_mergulho=?",
        conn,
        params=(novo["data"][0], int(novo["id_mergulho"][0]))
    )

    if not existente.empty:
        conn.close()
        return False

    novo.to_sql("operacoes", conn, if_exists="append", index=False)
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

menu = st.sidebar.selectbox("Menu", ["Registro", "Dashboard Executivo"])

# =========================
# 📥 REGISTRO
# =========================
if menu == "Registro":

    st.header("Registro de Mergulho")

    tipo_operacao = st.selectbox(
        "Status",
        ["Produtivo", "Abortado pelo Mergulhador", "Abortado pela Embarcação"]
    )

    motivo_abortado = None

    if tipo_operacao == "Abortado pelo Mergulhador":
        motivo_abortado = st.selectbox(
            "Motivo (Mergulhador)",
            ["Correnteza", "Swell (Refluxo)"]
        )

    elif tipo_operacao == "Abortado pela Embarcação":
        motivo_abortado = st.selectbox(
            "Motivo (Embarcação)",
            ["Swell Alto", "Posição Conflitante", "Vento"]
        )

    with st.form("form"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data")
            embarcacao = st.selectbox(
                "Embarcação",
                ["Amaralina", "Humaitá", "Cidade de Ouro Preto"]
            )
            numero = st.selectbox("Número do Mergulho", list(range(0, 21)))  # 🔥 0 a 20

        with col2:
            equip = st.number_input("Equipagem", 0)
            merg = st.number_input("Mergulho", 0)
            repo = st.number_input("Reposicionamento", 0)

        obs = st.text_area("Observações")

        if st.form_submit_button("Salvar"):

            novo = pd.DataFrame([{
                "data": str(data),
                "embarcacao": embarcacao,
                "id_mergulho": numero,
                "tempo_equipagem": equip,
                "tempo_mergulho": merg,
                "tempo_reposicionamento": repo,
                "abortado_mergulhador": tipo_operacao == "Abortado pelo Mergulhador",
                "abortado_embarcacao": tipo_operacao == "Abortado pela Embarcação",
                "motivo_abortado": motivo_abortado,
                "observacoes": obs
            }])

            if salvar_dados(novo):
                st.success("Salvo!")
            else:
                st.error("Duplicado!")

# =========================
# 📊 DASHBOARD
# =========================
if menu == "Dashboard Executivo":

    st.header("Dashboard Executivo")

    if df.empty:
        st.warning("Sem dados")
    else:
        df["data"] = pd.to_datetime(df["data"])

        dias = st.slider("Período", 7, 30, 15)

        # 🔥 NÃO sobrescreve df original
        df_filtrado = df[df["data"] >= (pd.Timestamp.today() - pd.Timedelta(days=dias))]

        df_filtrado["status"] = df_filtrado.apply(
            lambda r: "Abortado Mergulhador" if r["abortado_mergulhador"]
            else "Abortado Embarcação" if r["abortado_embarcacao"]
            else "Produtivo", axis=1
        )

        # 🔥 TOTAL CORRETO FINAL
        total_mergulhos = df_filtrado.groupby(["data", "id_mergulho"]).ngroups

        total_equip = df_filtrado["tempo_equipagem"].sum()
        total_merg = df_filtrado["tempo_mergulho"].sum()
        total_repo = df_filtrado["tempo_reposicionamento"].sum()

        total = total_equip + total_merg + total_repo
        eficiencia = (total_merg / total * 100) if total > 0 else 0

        # PERFORMANCE
        if eficiencia < 40:
            perf = "🔴 Ruim"
        elif eficiencia < 60:
            perf = "🟡 Regular"
        elif eficiencia < 80:
            perf = "🟢 Bom"
        else:
            perf = "🔵 Excelente"

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mergulhos", total_mergulhos)
        k2.metric("Eficiência", f"{eficiencia:.1f}%")
        k3.metric("Tempo Produtivo", f"{total_merg:.0f} min")
        k4.metric("Performance", perf)

        # 🍕 PIZZA
        resumo = df_filtrado["status"].value_counts().reset_index()
        resumo.columns = ["status", "qtd"]

        fig1 = px.pie(resumo, names="status", values="qtd", hole=0.6)
        fig1.update_traces(textinfo='percent+label')
        fig1.update_layout(height=500)

        st.plotly_chart(fig1, use_container_width=True)

        # 📈 tendência
        trend = df_filtrado.groupby("data")["tempo_mergulho"].sum().reset_index()
        st.plotly_chart(px.line(trend, x="data", y="tempo_mergulho"),
                        use_container_width=True)

        # 🏆 produção
        bar = df_filtrado.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()
        st.plotly_chart(px.bar(bar, x="embarcacao", y="tempo_mergulho"),
                        use_container_width=True)

        # 📥 DOWNLOAD (VOLTOU 🔥)
        st.subheader("Exportação de Dados")

        csv = df_filtrado.to_csv(index=False).encode('utf-8')

        st.download_button(
            "📥 Baixar Log da Quinzena",
            data=csv,
            file_name="ces_quinzena.csv",
            mime="text/csv"
        )
