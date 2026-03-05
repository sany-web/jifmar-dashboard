import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import os
import glob
import tempfile
from pathlib import Path
from io import BytesIO

# ============================================================
# CONFIG
# ============================================================
DB_CONSO    = "bdd2/conso.db"
DB_DISTANCE = "bdd2/distance.db"

CONSO_FOLDER    = "Consomation"
DISTANCE_FOLDER = "Distance"

MOIS_FR = ["janvier","février","mars","avril","mai","juin",
           "juillet","août","septembre","octobre","novembre","décembre"]
MOIS_CAP = [m.capitalize() for m in MOIS_FR]

VESSELS = ["JIF GYPTIS", "JIF LACYDON", "JIF SURVEYOR"]

st.set_page_config(
    page_title="Dashboard JIFMAR",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    .main-title { font-size: 2rem; font-weight: 700; color: #1a3a5c; }
    .section-title { font-size: 1.2rem; font-weight: 600; color: #2563eb; border-left: 4px solid #2563eb; padding-left: 10px; margin: 1rem 0; }
    .kpi-card { background: linear-gradient(135deg,#1a3a5c,#2563eb); border-radius:12px; padding:16px 20px; color:white; text-align:center; }
    .kpi-val { font-size:1.8rem; font-weight:700; }
    .kpi-label { font-size:0.85rem; opacity:0.85; }
    .stAlert { border-radius: 8px; }
    div[data-testid="metric-container"] { background:#f0f4ff; border-radius:10px; padding:10px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HAVERSINE
# ============================================================
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

# ============================================================
# LOADERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_conso():
    conn = sqlite3.connect(DB_CONSO)
    df_ann  = pd.read_sql("SELECT * FROM conso_annuelle",  conn)
    df_mois = pd.read_sql("SELECT * FROM conso_mensuelle", conn)
    conn.close()
    df_ann["annee"] = df_ann["annee"].astype(int)
    df_mois["annee"] = df_mois["annee"].astype(int)
    return df_ann, df_mois

@st.cache_data(show_spinner=False)
def load_distance():
    conn = sqlite3.connect(DB_DISTANCE)
    df = pd.read_sql("SELECT * FROM distance_evolution", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)
    df["year"] = df["date"].dt.year
    df.sort_values("date", inplace=True)
    return df

# ============================================================
# IMPORT HELPERS
# ============================================================
def import_conso_excel(file_obj, filename):
    """Parse a Consomation_YYYY.xlsx and insert into conso.db. Returns (year, ships, message)."""
    try:
        year = int(filename.split("_")[1].split(".")[0])
    except:
        return None, [], "❌ Nom de fichier invalide. Format attendu : Consomation_YYYY.xlsx"

    try:
        df = pd.read_excel(file_obj, header=None)
        ship_names = df.iloc[1, 1:].dropna().tolist()
        conso_m3 = df.iloc[18, 1:len(ship_names)+1].tolist()
        conso_lm = df.iloc[22, 1:len(ship_names)+1].tolist()

        conn = sqlite3.connect(DB_CONSO)
        cur = conn.cursor()

        inserted = 0
        for ship, m3, lm in zip(ship_names, conso_m3, conso_lm):
            try: m3 = float(str(m3).replace(",","."))
            except: m3 = 0.0
            try: lm = float(str(lm).replace(",","."))
            except: lm = 0.0
            if np.isnan(lm): lm = 0.0
            cur.execute("REPLACE INTO conso_annuelle (annee,navire,conso_m3,conso_l_mille) VALUES(?,?,?,?)",
                        (year, ship.strip(), m3, lm))
            inserted += 1

        for i, val in enumerate(df.iloc[:, 0]):
            if isinstance(val, str) and val.strip().lower() in MOIS_FR:
                mois = val.strip().capitalize()
                row = df.iloc[i, 1:len(ship_names)+1].tolist()
                for ship, conso in zip(ship_names, row):
                    try: conso = float(str(conso).replace(",","."))
                    except: conso = 0.0
                    cur.execute("REPLACE INTO conso_mensuelle (annee,mois,navire,conso_m3) VALUES(?,?,?,?)",
                                (year, mois, ship.strip(), conso))

        conn.commit()
        conn.close()
        return year, ship_names, f"✅ **{filename}** importé — {year}, {inserted} navires : {', '.join(ship_names)}"
    except Exception as e:
        return None, [], f"❌ Erreur : {e}"

def import_distance_csv(file_obj, filename, vessel_name):
    """Parse a GPS CSV and insert into distance.db. Returns message."""
    try:
        df = pd.read_csv(file_obj, sep=';')
        df.columns = [c.strip().strip('"') for c in df.columns]
        df = df[['Date','Latitude','Longitude']].copy()
        df['date'] = pd.to_datetime(df['Date'], errors='coerce')
        df.dropna(subset=['date','Latitude','Longitude'], inplace=True)
        df['vessel'] = vessel_name
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)

        df['distance'] = 0.0
        for i in range(1, len(df)):
            df.at[i,'distance'] = haversine_nm(
                df.at[i-1,'Latitude'], df.at[i-1,'Longitude'],
                df.at[i,'Latitude'],   df.at[i,'Longitude'])

        df['date_only'] = df['date'].dt.date
        sampled = df.groupby('date_only').first().reset_index()
        sampled['date'] = sampled['date'].astype(str)

        conn = sqlite3.connect(DB_DISTANCE)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO distance_evolution (vessel,date,distance,latitude,longitude) VALUES(?,?,?,?,?)",
            sampled[['vessel','date','distance','Latitude','Longitude']].values.tolist())
        conn.commit()
        n = cursor.rowcount
        conn.close()
        return f"✅ **{filename}** → {vessel_name} : {len(sampled)} points insérés"
    except Exception as e:
        return f"❌ Erreur ({filename}) : {e}"

# ============================================================
# LOAD DATA
# ============================================================
with st.spinner("Chargement des données..."):
    df_ann, df_mois = load_conso()
    df_dist = load_distance()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/anchor.png", width=60)
    st.markdown("## ⚓ JIFMAR Dashboard")
    st.markdown("---")

    page = st.radio("Navigation", ["📊 Dashboard", "📥 Importer des données"])
    st.markdown("---")

    if page == "📊 Dashboard":
        min_year = int(min(df_ann["annee"].min(), df_dist["year"].min()))
        max_year = int(max(df_ann["annee"].max(), df_dist["year"].max()))

        year_start, year_end = st.slider(
            "📅 Période",
            min_value=min_year, max_value=max_year,
            value=(min_year, max_year))

        all_ships = sorted(df_ann["navire"].unique())
        selected_ships = st.multiselect("🚢 Navires", all_ships, default=all_ships)

    st.markdown("---")
    st.caption(f"Données : 2020 → {max_year}")

# ============================================================
# PAGE : IMPORT
# ============================================================
if page == "📥 Importer des données":
    st.markdown('<p class="main-title">📥 Importer de nouvelles données</p>', unsafe_allow_html=True)
    st.markdown("Ajoutez les fichiers pour les années 2025, 2026 et au-delà sans toucher au code.")

    tab1, tab2 = st.tabs(["⛽ Consommation (Excel)", "🗺️ Distances GPS (CSV)"])

    with tab1:
        st.markdown('<p class="section-title">Importer un fichier Consomation_YYYY.xlsx</p>', unsafe_allow_html=True)
        st.info("Format attendu : `Consomation_2025.xlsx`, `Consomation_2026.xlsx`...")

        uploaded_conso = st.file_uploader(
            "Glisser/déposer le fichier Excel",
            type=["xlsx"],
            accept_multiple_files=True,
            key="conso_upload")

        if uploaded_conso:
            for f in uploaded_conso:
                year, ships, msg = import_conso_excel(f, f.name)
                st.markdown(msg)
            if any(import_conso_excel(f, f.name)[0] for f in uploaded_conso):
                load_conso.clear()
                st.success("Cache rechargé. Rendez-vous sur le Dashboard !")

    with tab2:
        st.markdown('<p class="section-title">Importer des CSV GPS par navire</p>', unsafe_allow_html=True)
        st.info("Format attendu : CSV avec séparateur `;` et colonnes `Date`, `Latitude`, `Longitude`")

        col_v, col_f = st.columns([1, 2])
        with col_v:
            vessel_choice = st.selectbox("Navire concerné", VESSELS)
        with col_f:
            uploaded_csv = st.file_uploader(
                "Glisser/déposer les fichiers CSV",
                type=["csv"],
                accept_multiple_files=True,
                key="dist_upload")

        if uploaded_csv and vessel_choice:
            for f in uploaded_csv:
                msg = import_distance_csv(f, f.name, vessel_choice)
                st.markdown(msg)
            load_distance.clear()
            st.success("Cache rechargé. Rendez-vous sur le Dashboard !")

# ============================================================
# PAGE : DASHBOARD
# ============================================================
else:
    st.markdown('<p class="main-title">📊 Dashboard Global – Flotte JIFMAR</p>', unsafe_allow_html=True)

    if not selected_ships:
        st.warning("Sélectionnez au moins un navire dans le menu de gauche.")
        st.stop()

    # Filter
    df_ann_f  = df_ann[(df_ann["annee"]  >= year_start) & (df_ann["annee"]  <= year_end) & (df_ann["navire"].isin(selected_ships))]
    df_mois_f = df_mois[(df_mois["annee"] >= year_start) & (df_mois["annee"] <= year_end) & (df_mois["navire"].isin(selected_ships))]
    df_dist_f = df_dist[(df_dist["year"]  >= year_start) & (df_dist["year"]  <= year_end) & (df_dist["vessel"].isin(selected_ships))]

    # ---- KPIs ----
    st.markdown("### 🔢 Indicateurs clés")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        total_m3 = df_ann_f["conso_m3"].sum()
        st.metric("⛽ Conso totale", f"{total_m3:.1f} m³")
    with k2:
        avg_lm = df_ann_f[df_ann_f["conso_l_mille"] > 0]["conso_l_mille"].mean()
        st.metric("📏 Moy. L/mille", f"{avg_lm:.2f}" if not np.isnan(avg_lm) else "N/A")
    with k3:
        total_dist = df_dist_f["distance"].sum()
        st.metric("🌊 Distance totale", f"{total_dist:,.0f} NM")
    with k4:
        n_years = year_end - year_start + 1
        st.metric("📅 Période", f"{year_start} → {year_end} ({n_years} ans)")

    st.markdown("---")

    # ============================================================
    # SECTION CONSOMMATION
    # ============================================================
    st.markdown("## ⛽ Consommation")
    tab_c1, tab_c2, tab_c3 = st.tabs(["📈 Annuelle (L/mille)", "📦 Annuelle (m³)", "📅 Mensuelle (m³)"])

    with tab_c1:
        df_lm = df_ann_f[df_ann_f["conso_l_mille"] > 0]
        if not df_lm.empty:
            fig = px.line(df_lm, x="annee", y="conso_l_mille", color="navire",
                          markers=True, template="plotly_white",
                          labels={"conso_l_mille":"L / mille","annee":"Année","navire":"Navire"},
                          title="Consommation spécifique annuelle (L/mille)")
            fig.update_traces(line_width=2.5)
            st.plotly_chart(fig, use_container_width=True)
            st.download_button("📤 Exporter HTML", pio.to_html(fig), "conso_lmille.html", "text/html")
        else:
            st.info("Pas de données L/mille disponibles pour la sélection.")

    with tab_c2:
        if not df_ann_f.empty:
            fig2 = px.bar(df_ann_f, x="annee", y="conso_m3", color="navire",
                          barmode="group", template="plotly_white",
                          labels={"conso_m3":"Consommation (m³)","annee":"Année","navire":"Navire"},
                          title="Consommation annuelle totale (m³)")
            st.plotly_chart(fig2, use_container_width=True)
            st.download_button("📤 Exporter HTML", pio.to_html(fig2), "conso_m3.html", "text/html")

    with tab_c3:
        if not df_mois_f.empty:
            annees_dispo = sorted(df_mois_f["annee"].unique())
            selected_year_m = st.selectbox("Année", annees_dispo, index=len(annees_dispo)-1, key="mois_year")
            df_m = df_mois_f[df_mois_f["annee"] == selected_year_m]
            fig3 = px.line(df_m, x="mois", y="conso_m3", color="navire", markers=True,
                           template="plotly_white",
                           category_orders={"mois": MOIS_CAP},
                           labels={"conso_m3":"Consommation (m³)","mois":"Mois","navire":"Navire"},
                           title=f"Consommation mensuelle (m³) – {selected_year_m}")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Pas de données mensuelles disponibles.")

    # ============================================================
    # SECTION DISTANCES
    # ============================================================
    st.markdown("---")
    st.markdown("## 🌊 Distances parcourues")
    tab_d1, tab_d2, tab_d3, tab_d4 = st.tabs(["📈 Cumulée", "📊 Annuelle", "📅 Mensuelle", "🗺️ Carte GPS"])

    with tab_d1:
        if not df_dist_f.empty:
            df_cum = df_dist_f.copy()
            df_cum["distance_cum"] = df_cum.groupby("vessel")["distance"].cumsum()
            fig_cum = px.line(df_cum, x="date", y="distance_cum", color="vessel",
                              template="plotly_white",
                              labels={"distance_cum":"Distance cumulée (NM)","date":"Date","vessel":"Navire"},
                              title="Distance cumulée par navire")
            st.plotly_chart(fig_cum, use_container_width=True)
            st.download_button("📤 Exporter HTML", pio.to_html(fig_cum), "dist_cumulee.html", "text/html")

    with tab_d2:
        if not df_dist_f.empty:
            df_yearly = df_dist_f.groupby(["year","vessel"])["distance"].sum().reset_index()
            fig_yr = px.bar(df_yearly, x="year", y="distance", color="vessel",
                            barmode="group", template="plotly_white",
                            labels={"distance":"Distance (NM)","year":"Année","vessel":"Navire"},
                            title="Distance annuelle par navire")
            st.plotly_chart(fig_yr, use_container_width=True)

    with tab_d3:
        if not df_dist_f.empty:
            df_dist_f["month"] = df_dist_f["date"].dt.to_period("M").astype(str)
            df_monthly = df_dist_f.groupby(["month","vessel"])["distance"].sum().reset_index()
            fig_mo = px.line(df_monthly, x="month", y="distance", color="vessel",
                             markers=True, template="plotly_white",
                             labels={"distance":"Distance (NM)","month":"Mois","vessel":"Navire"},
                             title="Distance mensuelle par navire")
            fig_mo.update_xaxes(tickangle=45)
            st.plotly_chart(fig_mo, use_container_width=True)

    with tab_d4:
        if len(df_dist_f) > 1:
            # Sample for map performance
            df_map = df_dist_f.groupby("vessel").apply(
                lambda x: x.iloc[::max(1, len(x)//500)]).reset_index(drop=True)
            fig_map = px.scatter_mapbox(
                df_map, lat="latitude", lon="longitude",
                color="vessel", hover_name="date",
                zoom=4, height=600, template="plotly_white",
                title="Carte GPS – Positions des navires")
            fig_map.update_layout(mapbox_style="open-street-map",
                                  mapbox_center={"lat": df_map["latitude"].mean(),
                                                 "lon": df_map["longitude"].mean()},
                                  margin={"r":0,"t":30,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Pas assez de données GPS pour la sélection.")

    # ============================================================
    # TABLEAU BRUT
    # ============================================================
    with st.expander("📄 Données brutes – Consommation annuelle"):
        st.dataframe(df_ann_f.sort_values(["annee","navire"]), use_container_width=True)

    with st.expander("📄 Données brutes – Distances (échantillon)"):
        st.dataframe(df_dist_f.head(500), use_container_width=True)
