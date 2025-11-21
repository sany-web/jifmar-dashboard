import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

# ---------------------------------------------------
# 📌 CONFIGURATION
# ---------------------------------------------------

# CHEMINS RELATIFS — OBLIGATOIRE POUR STREAMLIT CLOUD
DB_CONSO = "bdd2/conso.db"
DB_DISTANCE = "bdd2/distance.db"

st.set_page_config(page_title="Dashboard JIFMAR", layout="wide")
st.title("📊 Dashboard Global – Navires JIFMAR")


# ---------------------------------------------------
# 🔄 CHARGEMENT DES DONNÉES
# ---------------------------------------------------

@st.cache_data
def load_conso():
    conn = sqlite3.connect(DB_CONSO)
    df_ann = pd.read_sql_query("SELECT * FROM conso_annuelle", conn)
    conn.close()

    df_ann["annee"] = df_ann["annee"].astype(int)
    return df_ann


@st.cache_data
def load_distance():
    conn = sqlite3.connect(DB_DISTANCE)
    df = pd.read_sql_query("SELECT * FROM distance_evolution", conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    df["year"] = df["date"].dt.year
    df.sort_values("date", inplace=True)

    return df


df_ann = load_conso()
df_dist = load_distance()


# ---------------------------------------------------
# 🎚️ FILTRE GLOBAL : ANNÉES + NAVIRE
# ---------------------------------------------------

min_year = int(min(df_ann["annee"].min(), df_dist["year"].min()))
max_year = int(max(df_ann["annee"].max(), df_dist["year"].max()))

year_start, year_end = st.slider(
    "📅 Sélection de la période (années)",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)

navires = sorted(df_ann["navire"].unique())
selected_ship = st.selectbox("🚢 Choisir un navire :", navires)


# ---------------------------------------------------
# =============== SECTION CONSOMMATION (L/mille) ===============
# ---------------------------------------------------

st.header("⛽ Consommation des Navires (L/mille)")

df_ann_f = df_ann[
    (df_ann["annee"] >= year_start) &
    (df_ann["annee"] <= year_end) &
    (df_ann["navire"] == selected_ship)
]

# --------- GRAPHIQUE ANNUEL L/MILLE ---------

st.subheader(f"📈 Consommation annuelle (L/mille) – {selected_ship}")

fig_ann = px.line(
    df_ann_f,
    x="annee",
    y="conso_l_mille",
    color="navire",
    markers=True,
    title=f"Consommation spécifique annuelle (L/mille) – {selected_ship}",
    labels={"conso_l_mille": "Litre / mille", "annee": "Année"}
)

st.plotly_chart(fig_ann, use_container_width=True)

st.download_button(
    "📤 Télécharger consommation annuelle (HTML)",
    data=pio.to_html(fig_ann),
    file_name=f"conso_annuelle_{selected_ship}.html",
    mime="text/html"
)

st.markdown("---")


# ---------------------------------------------------
# =============== SECTION DISTANCES ===============
# ---------------------------------------------------

st.header(f"📍 Distances parcourues – {selected_ship}")

df_dist_f = df_dist[
    (df_dist["year"] >= year_start) &
    (df_dist["year"] <= year_end) &
    (df_dist["vessel"] == selected_ship)
]


# --------- DISTANCE CUMULÉE ---------

st.subheader(f"📈 Distance cumulée – {selected_ship}")

df_cum = df_dist_f.copy()
df_cum["distance_cum"] = df_cum["distance"].cumsum()

fig_dist_cum = px.line(
    df_cum,
    x="date",
    y="distance_cum",
    color="vessel",
    title=f"Distance cumulée – {selected_ship}",
    labels={"distance_cum": "Distance cumulée (NM)"}
)

st.plotly_chart(fig_dist_cum, use_container_width=True)

st.download_button(
    "📤 Télécharger distance cumulée (HTML)",
    data=pio.to_html(fig_dist_cum),
    file_name=f"distance_cumulee_{selected_ship}.html",
    mime="text/html"
)


# --------- DISTANCE JOURNALIÈRE ---------

st.subheader(f"📊 Distance journalière – {selected_ship}")

df_daily = df_dist_f.groupby(df_dist_f["date"].dt.date)["distance"].sum().reset_index()
df_daily.columns = ["date", "daily_distance"]

fig_daily = px.bar(
    df_daily,
    x="date",
    y="daily_distance",
    title=f"Distance journalière – {selected_ship}",
)

st.plotly_chart(fig_daily, use_container_width=True)

st.download_button(
    "📤 Télécharger distance journalière (HTML)",
    data=pio.to_html(fig_daily),
    file_name=f"distance_journaliere_{selected_ship}.html",
    mime="text/html"
)


# --------- CARTE GPS ---------

st.subheader(f"🗺️ Carte GPS – {selected_ship}")

if len(df_dist_f) > 1:

    fig_map = px.scatter_mapbox(
        df_dist_f,
        lat="latitude",
        lon="longitude",
        color="vessel",
        title=f"Carte GPS – {selected_ship}",
        zoom=5,
        height=600
    )

    fig_map.update_layout(mapbox_style="open-street-map")

    st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("Pas assez de données GPS pour afficher la carte.")

