import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- Config ---
st.set_page_config(page_title="Suivi Conso Navires", layout="wide")

ROOT = r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring"
DB = os.path.join(ROOT, "bdd2", "conso.db")

# --- Lecture DB ---
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB)
    df_ann = pd.read_sql_query("SELECT * FROM conso_annuelle ORDER BY annee, navire", conn)
    df_mois = pd.read_sql_query("SELECT * FROM conso_mensuelle ORDER BY annee, mois, navire", conn)
    conn.close()
    return df_ann, df_mois

df_ann, df_mois = load_data()

# --- UI ---
st.title("⚓ Dashboard consommation des navires")

mode = st.radio("Vue :", ["Vue annuelle", "Vue mensuelle"], horizontal=True)

# ======================================================================
# Vue annuelle
# ======================================================================
if mode == "Vue annuelle":
    st.subheader("📈 Consommation annuelle")

    navires = sorted(df_ann["navire"].unique())
    années = sorted(df_ann["annee"].unique())

    c1, c2, c3 = st.columns([1.5, 1, 1])

    selected_nav = c1.multiselect("Navires :", navires, default=navires)
    min_y, max_y = c2.select_slider("Période :", options=années, value=(années[0], années[-1]))
    metric = c3.radio("Indicateur :", ["m³ (Total)", "L/mille (Spécifique)"])

    df = df_ann[
        (df_ann["navire"].isin(selected_nav)) &
        (df_ann["annee"] >= min_y) &
        (df_ann["annee"] <= max_y)
    ]

    if metric.startswith("m³"):
        col = "conso_m3"
        title = "Consommation totale (m³)"
    else:
        col = "conso_l_mille"
        title = "Consommation spécifique (L/mille)"

    fig = px.line(df, x="annee", y=col, color="navire", markers=True, title=title)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)

# ======================================================================
# Vue mensuelle
# ======================================================================
else:
    st.subheader("📊 Consommation mensuelle")

    navires = sorted(df_mois["navire"].unique())
    années = sorted(df_mois["annee"].unique())

    c1, c2 = st.columns(2)
    selected_nav = c1.multiselect("Navires :", navires, default=navires)
    selected_year = c2.selectbox("Année :", années, index=len(années)-1)

    df = df_mois[
        (df_mois["navire"].isin(selected_nav)) &
        (df_mois["annee"] == selected_year)
    ]

    fig = px.line(df, x="mois", y="conso_m3", color="navire", markers=True,
                  title=f"Consommation mensuelle (m³) — {selected_year}")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)
