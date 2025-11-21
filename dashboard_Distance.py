import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# ------------------------------
# 📌 CONFIG
# ------------------------------
DB_PATH = r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring\bdd2\distance.db"
st.set_page_config(page_title="Monitoring Navires", layout="wide")
st.title("📊 Dashboard Multi-Navires – JIFMAR")


# ------------------------------
# 🔄 Chargement des données
# ------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM distance_evolution", conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    df["year"] = df["date"].dt.year

    return df


df = load_data()

# ------------------------------
# 🎛️ FILTRES
# ------------------------------
vessels = sorted(df["vessel"].unique())

# Multi sélection navires
selected_vessels = st.sidebar.multiselect(
    "🚢 Choisir un ou plusieurs navires",
    vessels,
    default=vessels  # tous sélectionnés par défaut
)

years = sorted(df["year"].unique())

# Intervalle d’années
year_range = st.sidebar.slider(
    "📅 Intervalle d'années",
    min_value=min(years),
    max_value=max(years),
    value=(min(years), max(years))
)

start_year, end_year = year_range

# Filtrage global
filtered = df[
    (df["vessel"].isin(selected_vessels)) &
    (df["year"] >= start_year) &
    (df["year"] <= end_year)
].sort_values("date")

st.markdown(
    f"### 🔎 Navires : **{', '.join(selected_vessels)}** | "
    f"Années : **{start_year} → {end_year}**"
)


# ------------------------------
# 📈 Distance cumulée multi-navires
# ------------------------------
with st.container():
    st.subheader("📈 Distance cumulée – Comparaison entre navires")

    df_cum = filtered.copy()
    df_cum["distance_cum"] = df_cum.groupby("vessel")["distance"].cumsum()

    fig = px.line(
        df_cum,
        x="date",
        y="distance_cum",
        color="vessel",
        markers=False,
        labels={"distance_cum": "Distance cumulée (NM)", "date": "Date", "vessel": "Navire"},
        title="Comparaison des distances cumulées"
    )

    st.plotly_chart(fig, use_container_width=True)


# ------------------------------
# 📊 Distance journalière multi-navires
# ------------------------------
with st.container():
    st.subheader("📊 Distance journalière – Comparaison")

    df_daily = (
        filtered.groupby([filtered["date"].dt.date, "vessel"])["distance"]
        .sum()
        .reset_index()
    )
    df_daily.columns = ["date", "vessel", "daily_distance"]

    fig_daily = px.bar(
        df_daily,
        x="date",
        y="daily_distance",
        color="vessel",
        labels={"daily_distance": "Distance (NM)", "date": "Date"},
        title="Distance journalière – Multi-navires"
    )

    st.plotly_chart(fig_daily, use_container_width=True)


# ------------------------------
# 🗺️ Carte des points (pas reliés)
# ------------------------------
with st.container():
    st.subheader("🗺️ Carte des positions GPS (points non reliés)")

    if len(filtered) > 1:

        fig_map = px.scatter_mapbox(
            filtered,
            lat="latitude",
            lon="longitude",
            color="vessel",
            hover_name="date",
            zoom=5,
            height=650
        )

        fig_map.update_layout(
            mapbox_style="open-street-map",
            mapbox_center={"lat": filtered["latitude"].mean(),
                           "lon": filtered["longitude"].mean()},
            margin={"r":0,"t":0,"l":0,"b":0},
        )

        st.plotly_chart(fig_map, use_container_width=True)

    else:
        st.info("Pas assez de données pour afficher la carte.")


# ------------------------------
# 📄 Tableau brut
# ------------------------------
with st.expander("📄 Afficher les données brutes"):
    st.dataframe(filtered)
