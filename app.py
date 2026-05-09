import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import date

st.set_page_config(layout="wide")

# =========================
# SESSION STATE
# =========================
if "salvo" not in st.session_state:
    st.session_state.salvo = False

if "ultimo_numero" not in st.session_state:
    st.session_state.ultimo_numero = None

if "salvando" not in st.session_state:
    st.session_state.salvando = False

# =========================
# BANCO
# =========================
DB_PATH = "ces.db"

def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    c = conn()
    c.execute("""
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
    c.close()

def load():
    c = conn()
    try:
        df = pd.read_sql("SELECT * FROM operacoes", c)
    except:
        df = pd.DataFrame()
    c.close()
    return df

def next_dive(df, d):
    if df.empty:
        return 1
    df["data"] = pd.to_datetime(df["data"])
    hoje = df[df["data"] == pd.to_datetime(d)]
    return 1 if hoje.empty else hoje["numero_mergulho"].max() + 1

def save(df_new):
    c = conn()
    df_new.to_sql("operacoes", c, if_exists="append", index=False)
    c.close()

# INIT
init_db()
df = load()

# =========================
# UI
# =========================
st.title("CES - Controle de Eficiência Subaquática")
menu = st.sidebar.radio("Menu", ["Operação", "Análise"])

# =========================
# OPERAÇÃO
# =========================
if menu == "Operação":

    st.header("Registro Rápido")

    # 🔥 Mensagem persistente + som
    if st.session_state.salvo:
        st.success(f"✅ Mergulho #{st.session_state.ultimo_numero} salvo com sucesso!")
        st.audio("https://www.soundjay.com/buttons/sounds/button-3.mp3")
        st.session_state.salvo = False

    d = st.date_input("Data", value=date.today())
    numero = next_dive(df, d)

    # 🔥 Visual melhorado
    st.markdown(f"### 🔵 Próximo mergulho: **#{numero}**")

    embarcacao = st.selectbox("Embarcação", ["Amaralina", "Humaitá", "Ouro Preto"])

    status = st.radio(
        "Status",
        ["produtivo", "abortado_mergulhador", "abortado_embarcacao"]
    )

    motivo = None
    if "abortado" in status:
        motivo = st.text_input("Motivo")

    c1, c2, c3 = st.columns(3)
    equip = c1.number_input("Equipagem (min)", 0)
    merg = c2.number_input("Mergulho (min)", 0)
    repo = c3.number_input("Reposicionamento (min)", 0)

    obs = st.text_area("Observações")

    # 🔥 Anti duplo clique
    botao_desabilitado = st.session_state.salvando

    if st.button("Salvar", disabled=botao_desabilitado):

        st.session_state.salvando = True

        with st.spinner("Salvando mergulho..."):

            new = pd.DataFrame([{
                "data": str(d),
                "embarcacao": embarcacao,
                "numero_mergulho": numero,
                "tempo_equipagem": equip,
                "tempo_mergulho": merg,
                "tempo_reposicionamento": repo,
                "status": status,
                "motivo_abortado": motivo,
                "observacoes": obs
            }])

            save(new)

        # controle de feedback
        st.session_state.salvo = True
        st.session_state.ultimo_numero = numero
        st.session_state.salvando = False

        st.rerun()

# =========================
# ANÁLISE
# =========================
elif menu == "Análise":

    st.header("Dashboard da Quinzena")

    if df.empty:
        st.warning("Sem dados")
        st.stop()

    df["data"] = pd.to_datetime(df["data"])
    df = df[df["data"] >= pd.Timestamp.today() - pd.Timedelta(days=15)]

    total = len(df)
    abort = (df["status"] != "produtivo").mean()

    t_equip = df["tempo_equipagem"].sum()
    t_merg = df["tempo_mergulho"].sum()
    t_repo = df["tempo_reposicionamento"].sum()

    total_time = t_equip + t_merg + t_repo
    eficiencia = (t_merg / total_time * 100) if total_time > 0 else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Mergulhos", total)
    k2.metric("Eficiência", f"{eficiencia:.1f}%")
    k3.metric("Abortos", f"{abort:.0%}")

    # ALERTAS
    if eficiencia < 60:
        st.error("⚠️ Baixa eficiência operacional")

    if abort > 0.3:
        st.warning("⚠️ Alta taxa de abortos")

    # PIZZA
    st.subheader("Status")
    st.plotly_chart(px.pie(df, names="status", hole=0.5), use_container_width=True)

    # TENDÊNCIA
    trend = df.groupby("data")["tempo_mergulho"].sum().reset_index()
    st.plotly_chart(px.line(trend, x="data", y="tempo_mergulho"), use_container_width=True)

    # EMBARCAÇÃO
    bar = df.groupby("embarcacao")["tempo_mergulho"].sum().reset_index()
    st.plotly_chart(px.bar(bar, x="embarcacao", y="tempo_mergulho"), use_container_width=True)

    # RESUMO EXECUTIVO
    st.subheader("Resumo Executivo")

    resumo = f"""
    Na quinzena foram realizados {total} mergulhos.
    A eficiência operacional foi de {eficiencia:.1f}%.
    A taxa de abortos foi de {abort:.0%}.
    """

    st.info(resumo)

    # DOWNLOAD
    st.download_button(
        "📥 Baixar relatório",
        data=df.to_csv(index=False),
        file_name="relatorio_quinzena.csv"
    )
