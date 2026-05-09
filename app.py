import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import date
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide")

# =========================
# SESSION STATE
# =========================
for key in ["salvo", "ultimo_numero", "salvando"]:
    if key not in st.session_state:
        st.session_state[key] = False if key != "ultimo_numero" else None

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
        observacoes TEXT,
        data_inicio_quinzena TEXT,
        data_fim_quinzena TEXT,
        quinzena_id TEXT,
        quinzena_label TEXT
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

# =========================
# PDF COMPLETO COM GRÁFICOS
# =========================
def gerar_pdf_completo(resumo, figs, titulo):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    # TÍTULO
    story.append(Paragraph(f"<b>{titulo}</b>", styles["Title"]))
    story.append(Spacer(1, 20))

    # TEXTO
    for linha in resumo.split("\n"):
        story.append(Paragraph(linha, styles["Normal"]))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))

    # GRÁFICOS
    for fig in figs:
        img_bytes = fig.to_image(format="png")
        img_buffer = io.BytesIO(img_bytes)

        story.append(Image(img_buffer, width=400, height=250))
        story.append(Spacer(1, 20))

    doc.build(story)
    buffer.seek(0)
    return buffer

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

    st.subheader("📅 Quinzena")

    c1, c2 = st.columns(2)
    with c1:
        data_inicio_q = st.date_input("Início", value=date.today())
    with c2:
        data_fim_q = st.date_input("Fim", value=date.today())

    quinzena_id = f"{data_inicio_q.strftime('%Y%m%d')}_{data_fim_q.strftime('%Y%m%d')}"
    quinzena_label = f"{data_inicio_q.strftime('%d/%m')} a {data_fim_q.strftime('%d/%m')}"

    st.info(f"Quinzena ativa: {quinzena_label}")

    if st.session_state.salvo:
        st.success(f"✅ Mergulho #{st.session_state.ultimo_numero} salvo!")
        st.session_state.salvo = False

    d = st.date_input("Data", value=date.today())
    numero = next_dive(df, d)

    st.markdown(f"### 🔵 Próximo mergulho: **#{numero}**")

    embarcacao = st.selectbox("Embarcação", ["Amaralina", "Humaitá", "Ouro Preto"])

    status = st.radio("Status", ["produtivo", "abortado_mergulhador", "abortado_embarcacao"])

    motivo = None
    if status == "abortado_mergulhador":
        motivo = st.selectbox("Motivo", ["correnteza", "swell"])
    elif status == "abortado_embarcacao":
        motivo = st.selectbox("Motivo", ["swell", "posicao_degradante"])

    c1, c2, c3 = st.columns(3)
    equip = c1.number_input("Equipagem", 0)
    merg = c2.number_input("Mergulho", 0)
    repo = c3.number_input("Reposicionamento", 0)

    obs = st.text_area("Observações")

    if st.button("Salvar", disabled=st.session_state.salvando):

        if "abortado" in status and not motivo:
            st.warning("Selecione o motivo")
            st.stop()

        new = pd.DataFrame([{
            "data": str(d),
            "embarcacao": embarcacao,
            "numero_mergulho": numero,
            "tempo_equipagem": equip,
            "tempo_mergulho": merg,
            "tempo_reposicionamento": repo,
            "status": status,
            "motivo_abortado": motivo,
            "observacoes": obs,
            "data_inicio_quinzena": str(data_inicio_q),
            "data_fim_quinzena": str(data_fim_q),
            "quinzena_id": quinzena_id,
            "quinzena_label": quinzena_label
        }])

        save(new)

        st.session_state.salvo = True
        st.session_state.ultimo_numero = numero
        st.rerun()

# =========================
# ANÁLISE
# =========================
elif menu == "Análise":

    st.header("Dashboard por Quinzena")

    if df.empty:
        st.warning("Sem dados")
        st.stop()

    quinzenas = df[["quinzena_id", "quinzena_label"]].drop_duplicates()

    selecionada = st.selectbox(
        "Selecione a quinzena",
        quinzenas["quinzena_id"],
        format_func=lambda x: quinzenas[quinzenas["quinzena_id"] == x]["quinzena_label"].values[0]
    )

    df = df[df["quinzena_id"] == selecionada]

    if df.empty:
        st.warning("Sem dados nessa quinzena")
        st.stop()

    total = len(df)
    abort = (df["status"] != "produtivo").mean()

    t_equip = df["tempo_equipagem"].sum()
    t_merg = df["tempo_mergulho"].sum()
    t_repo = df["tempo_reposicionamento"].sum()

    total_time = t_equip + t_merg + t_repo
    eficiencia = (t_merg / total_time * 100) if total_time > 0 else 0

    motivos_df = df["motivo_abortado"].dropna()
    principal_motivo = motivos_df.value_counts().idxmax() if not motivos_df.empty else None

    insight = "Alta eficiência." if eficiencia > 70 else "Eficiência moderada." if eficiencia > 50 else "Baixa eficiência."

    if principal_motivo:
        insight += f" Principal causa: {principal_motivo}."

    resumo = f"""
Quinzena: {df["quinzena_label"].iloc[0]}

Mergulhos: {total}
Eficiência: {eficiencia:.1f}%
Abortos: {abort:.0%}

{insight}
"""

    # =========================
    # GRÁFICOS
    # =========================
    fig1 = px.pie(df, names="status", hole=0.5)

    figs = [fig1]

    if not motivos_df.empty:
        mc = motivos_df.value_counts().reset_index()
        mc.columns = ["motivo", "qtd"]
        fig2 = px.bar(mc, x="motivo", y="qtd")
        figs.append(fig2)

    trend = df.groupby("data")["tempo_mergulho"].sum().reset_index()
    fig3 = px.line(trend, x="data", y="tempo_mergulho")
    figs.append(fig3)

    pdf = gerar_pdf_completo(
        resumo,
        figs,
        f"Relatório Operacional - Quinzena {df['quinzena_label'].iloc[0]}"
    )

    # =========================
    # DOWNLOAD
    # =========================
    st.download_button("📄 Baixar Relatório Completo", pdf, "relatorio_quinzena.pdf")

    # =========================
    # DASHBOARD
    # =========================
    k1, k2, k3 = st.columns(3)
    k1.metric("Mergulhos", total)
    k2.metric("Eficiência", f"{eficiencia:.1f}%")
    k3.metric("Abortos", f"{abort:.0%}")

    st.plotly_chart(fig1, use_container_width=True)

    if not motivos_df.empty:
        st.plotly_chart(fig2, use_container_width=True)

    st.plotly_chart(fig3, use_container_width=True)
