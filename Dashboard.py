import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Dashboard JIFMAR",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

MOIS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
           "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

NAVIRES = ["JIF SURVEYOR", "JIF GYPTIS", "JIF LACYDON"]

COLORS = {
    "JIF SURVEYOR": "#3b82f6",
    "JIF GYPTIS":   "#f97316",
    "JIF LACYDON":  "#22c55e",
}

st.markdown("""
<style>
    .main-title {
        font-size:1.9rem;font-weight:700;color:#1a3a5c;
        border-left:5px solid #2563eb;padding-left:14px;margin-bottom:4px;
    }
    .subtitle { color:#64748b;font-size:0.95rem;padding-left:19px;margin-bottom:20px; }
    .section-header {
        font-size:1.1rem;font-weight:600;color:#1e3a5f;
        border-bottom:2px solid #2563eb;padding-bottom:6px;margin:24px 0 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================
@st.cache_data(show_spinner=False)
def load_all_data():
    rows_annuel  = []
    rows_mensuel = []

    def to_float(val):
        try:
            v = float(str(val).replace(",","."))
            return None if np.isnan(v) else v
        except:
            return None

    # --- Format ancien 2020-2024 ---
    for year in [2020, 2021, 2022, 2023, 2024]:
        path = f"Consomation/Consomation_{year}.xlsx"
        if not os.path.exists(path):
            continue
        df = pd.read_excel(path, header=None)
        ships = [str(df.iloc[1, j+1]).strip() for j in range(3)]

        for i, mois in enumerate(MOIS_FR):
            for j, ship in enumerate(ships):
                dist = to_float(df.iloc[2+i, j+1])
                rows_mensuel.append({
                    "annee": year, "mois": mois, "mois_ordre": i,
                    "navire": ship, "distance_nm": dist,
                    "conso_litres": None, "vmax_nds": None, "conso_vmax_lh": None
                })

        for j, ship in enumerate(ships):
            conso_m3 = to_float(df.iloc[18, j+1])
            lm_raw   = str(df.iloc[22, j+1])
            conso_lm = to_float(lm_raw) if "#" not in lm_raw else None
            dist_tot = to_float(df.iloc[15, j+1])
            rows_annuel.append({
                "annee": year, "navire": ship,
                "dist_totale": dist_tot, "conso_m3": conso_m3, "conso_lm": conso_lm
            })

    # --- Format 2025 ---
    path25 = "Consomation/Récap_Distances_Consos_Vitesses_2025.xlsx"
    if os.path.exists(path25):
        df25 = pd.read_excel(path25, header=None)
        ships = [str(df25.iloc[1, j+1]).strip() for j in range(3)]

        for i, mois in enumerate(MOIS_FR):
            for j, ship in enumerate(ships):
                dist  = to_float(df25.iloc[2+i, j+1])
                cl    = to_float(df25.iloc[2+i, j+6])
                vmax  = to_float(df25.iloc[2+i, 11+j*2])
                cvmax = to_float(df25.iloc[2+i, 12+j*2])
                # Conso 0 = navire à quai = None
                if cl == 0: cl = None
                rows_mensuel.append({
                    "annee": 2025, "mois": mois, "mois_ordre": i,
                    "navire": ship, "distance_nm": dist,
                    "conso_litres": cl, "vmax_nds": vmax, "conso_vmax_lh": cvmax
                })

        for j, ship in enumerate(ships):
            conso_m3 = to_float(df25.iloc[18, j+1])
            lm_raw   = str(df25.iloc[22, j+1])
            conso_lm = to_float(lm_raw) if "#" not in lm_raw else None
            dist_tot = to_float(df25.iloc[15, j+1])
            rows_annuel.append({
                "annee": 2025, "navire": ship,
                "dist_totale": dist_tot, "conso_m3": conso_m3, "conso_lm": conso_lm
            })

    # --- Format 2026 ---
    path26 = "Consomation/Récap_2026.xlsx"
    if os.path.exists(path26):
        df26 = pd.read_excel(path26, header=None)
        ships = [str(df26.iloc[1, j+1]).strip() for j in range(3)]

        for i, mois in enumerate(MOIS_FR):
            for j, ship in enumerate(ships):
                dist  = to_float(df26.iloc[2+i, j+1])
                cl    = to_float(df26.iloc[2+i, j+5])
                vmax  = to_float(df26.iloc[2+i, j+9])
                cvmax = to_float(df26.iloc[2+i, j+13])
                if any(v is not None for v in [dist, cl, vmax]):
                    rows_mensuel.append({
                        "annee": 2026, "mois": mois, "mois_ordre": i,
                        "navire": ship, "distance_nm": dist,
                        "conso_litres": cl, "vmax_nds": vmax, "conso_vmax_lh": cvmax
                    })

        for j, ship in enumerate(ships):
            dist_tot = to_float(df26.iloc[15, j+1])
            rows_annuel.append({
                "annee": 2026, "navire": ship,
                "dist_totale": dist_tot, "conso_m3": None, "conso_lm": None
            })

    df_ann = pd.DataFrame(rows_annuel)
    df_men = pd.DataFrame(rows_mensuel)
    df_ann["annee"] = df_ann["annee"].astype(int)
    df_men["annee"] = df_men["annee"].astype(int)
    return df_ann, df_men


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## ⚓ JIFMAR Dashboard")
    st.markdown("---")
    page = st.radio("Navigation", ["📊 Dashboard", "📥 Importer des données"])
    st.markdown("---")

with st.spinner("Chargement..."):
    df_ann, df_men = load_all_data()

all_years = sorted(df_ann["annee"].unique())

with st.sidebar:
    if page == "📊 Dashboard":
        year_range = st.slider(
            "📅 Période",
            min_value=int(min(all_years)), max_value=int(max(all_years)),
            value=(int(min(all_years)), int(max(all_years)))
        )
        selected_navires = st.multiselect("🚢 Navires", NAVIRES, default=NAVIRES)
    st.caption(f"Données : {min(all_years)} → {max(all_years)}")


# ============================================================
# PAGE IMPORT
# ============================================================
if page == "📥 Importer des données":
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;
                background:linear-gradient(135deg,#1e3a5f,#1d4ed8);
                border-radius:12px;padding:18px 24px;margin-bottom:20px;">
        <div style="font-size:2rem;">📥</div>
        <div>
            <span style="color:white;font-size:1.4rem;font-weight:700;">Importer de nouvelles données</span>
            <span style="background:#f59e0b;color:#1a1a1a;font-size:0.65rem;font-weight:800;
                         padding:2px 8px;border-radius:20px;letter-spacing:1px;margin-left:10px;">BÊTA</span>
            <div style="color:#93c5fd;font-size:0.85rem;margin-top:4px;">
                Fonctionnalité en cours de développement.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.warning("⚠️ Pour ajouter des données, placez vos fichiers dans le dossier `Consomation/` du repo GitHub puis redéployez sur Streamlit Cloud.")

    tab1, tab2 = st.tabs(["📋 Format Consomation 2020–2024", "📋 Format Récap 2025–2026+"])

    with tab1:
        st.markdown("#### Structure du fichier `Consomation_YYYY.xlsx`")
        st.dataframe({
            "Ligne": ["1","2","3 à 14","15","18 ⚠️","22 ⚠️"],
            "Colonne A": ["Titre libre","Année (ex: 2025)",
                          "Mois (Janvier…Décembre)",
                          "TOTAL","(vide)","(vide)"],
            "Colonnes B / C / D": [
                "Vide",
                "JIF SURVEYOR | JIF GYPTIS | JIF LACYDON",
                "Distance mensuelle (NM)",
                "Total annuel (NM)",
                "🔴 Conso annuelle m³ par navire",
                "🔴 Conso L/mille par navire",
            ]
        }, use_container_width=True, hide_index=True)
        st.error("Les lignes 18 et 22 sont lues directement par le script. Ne pas déplacer.")

    with tab2:
        st.markdown("#### Structure du fichier `Récap_Distances_Consos_Vitesses_2025.xlsx`")
        st.info("""
**3 blocs côte à côte, même feuille :**
- **Bloc Distance** (col A→D) : distances NM par mois
- **Bloc Conso** (col F→I) : consommation mensuelle en litres
- **Bloc Vitesse** (col K→Q) : vitesse max (nœuds) + conso à Vmax (L/h) par navire
""")
        st.markdown("#### Structure du fichier `Récap_2026.xlsx`")
        st.info("""
**4 blocs côte à côte :**
- **Bloc Distance** (col A→D) : distances NM
- **Bloc Conso** (col E→H) : conso litres
- **Bloc Vmax** (col I→L) : vitesse max (nœuds)
- **Bloc Conso Vmax** (col M→P) : conso instantanée à Vmax (L/h)

Dans tous les cas : **ligne 2 = noms navires**, **lignes 3→14 = données mensuelles**.
""")
    st.stop()


# ============================================================
# PAGE DASHBOARD
# ============================================================
if not selected_navires:
    st.warning("Sélectionnez au moins un navire dans la sidebar.")
    st.stop()

st.markdown('<p class="main-title">📊 Dashboard Flotte JIFMAR</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Suivi des performances — JIF SURVEYOR · JIF GYPTIS · JIF LACYDON</p>',
            unsafe_allow_html=True)

y0, y1 = year_range
df_ann_f = df_ann[
    (df_ann["annee"] >= y0) & (df_ann["annee"] <= y1) &
    (df_ann["navire"].isin(selected_navires))
].copy()
df_men_f = df_men[
    (df_men["annee"] >= y0) & (df_men["annee"] <= y1) &
    (df_men["navire"].isin(selected_navires))
].copy()


# ---- KPIs ----
c1, c2, c3, c4 = st.columns(4)
with c1:
    v = df_ann_f["dist_totale"].sum()
    st.metric("🌊 Distance totale", f"{v:,.0f} NM" if v else "—")
with c2:
    v = df_ann_f["conso_m3"].sum()
    st.metric("⛽ Conso totale", f"{v:,.1f} m³" if v else "—")
with c3:
    v = df_ann_f[df_ann_f["conso_lm"].notna()]["conso_lm"].mean()
    st.metric("📏 Moy. L/mille", f"{v:.2f}" if pd.notna(v) else "—")
with c4:
    st.metric("📅 Période", f"{y0} → {y1}")

st.markdown("---")


# ============================================================
# GRAPHE 1 — Conso L/mille dans le temps (besoin Henri #1)
# ============================================================
st.markdown('<p class="section-header">📈 Consommation spécifique (L/mille) par navire dans le temps</p>',
            unsafe_allow_html=True)
st.caption("Litres consommés par mille nautique parcouru — indicateur clé d'efficience énergétique.")

df_lm = df_ann_f[df_ann_f["conso_lm"].notna()].copy()

if not df_lm.empty:
    fig1 = go.Figure()
    for nav in selected_navires:
        d = df_lm[df_lm["navire"] == nav].sort_values("annee")
        if d.empty: continue
        fig1.add_trace(go.Scatter(
            x=d["annee"], y=d["conso_lm"],
            mode="lines+markers+text", name=nav,
            line=dict(color=COLORS[nav], width=2.5),
            marker=dict(size=9),
            text=[f"{v:.1f}" for v in d["conso_lm"]],
            textposition="top center", textfont=dict(size=10),
        ))
    years_lm = sorted(df_lm["annee"].unique())
    fig1.update_layout(
        template="plotly_white", height=420,
        xaxis=dict(title="Année", tickmode="array",
                   tickvals=years_lm, ticktext=[str(y) for y in years_lm]),
        yaxis=dict(title="L / mille nautique"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    st.plotly_chart(fig1, use_container_width=True)

    missing = df_ann_f[df_ann_f["conso_lm"].isna()][["annee","navire"]].values.tolist()
    if missing:
        st.caption("ℹ️ Données L/mille absentes pour : " +
                   ", ".join(f"{n} ({y})" for y,n in missing))
else:
    st.info("Pas de données L/mille disponibles pour cette sélection.")

st.markdown("---")


# ============================================================
# GRAPHE 2 — Distance annuelle + Conso gasoil (besoin Henri #2)
# ============================================================
st.markdown('<p class="section-header">📊 Distance annuelle & Consommation gasoil par navire</p>',
            unsafe_allow_html=True)
st.caption("Vue côte à côte : milles parcourus et gasoil consommé chaque année.")

col_a, col_b = st.columns(2)

with col_a:
    df_d = df_ann_f[df_ann_f["dist_totale"].notna()]
    fig2a = go.Figure()
    for nav in selected_navires:
        d = df_d[df_d["navire"] == nav].sort_values("annee")
        if d.empty: continue
        fig2a.add_trace(go.Bar(
            x=d["annee"].astype(str), y=d["dist_totale"], name=nav,
            marker_color=COLORS[nav],
            text=[f"{v:,.0f}" for v in d["dist_totale"]],
            textposition="outside", textfont=dict(size=9),
        ))
    fig2a.update_layout(
        template="plotly_white", barmode="group", height=420,
        title="Distance annuelle (NM)",
        xaxis_title="Année", yaxis_title="Milles nautiques",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig2a, use_container_width=True)

with col_b:
    df_c = df_ann_f[df_ann_f["conso_m3"].notna()]
    fig2b = go.Figure()
    for nav in selected_navires:
        d = df_c[df_c["navire"] == nav].sort_values("annee")
        if d.empty: continue
        fig2b.add_trace(go.Bar(
            x=d["annee"].astype(str), y=d["conso_m3"], name=nav,
            marker_color=COLORS[nav],
            text=[f"{v:.1f}" for v in d["conso_m3"]],
            textposition="outside", textfont=dict(size=9),
            showlegend=False,
        ))
    fig2b.update_layout(
        template="plotly_white", barmode="group", height=420,
        title="Consommation gasoil annuelle (m³)",
        xaxis_title="Année", yaxis_title="m³",
    )
    st.plotly_chart(fig2b, use_container_width=True)

st.markdown("---")


# ============================================================
# GRAPHE 3 — Conso mensuelle litres 2025-2026
# ============================================================
st.markdown('<p class="section-header">📅 Consommation mensuelle en litres (2025–2026)</p>',
            unsafe_allow_html=True)
st.caption("Détail mois par mois de la consommation réelle de gasoil.")

df_cm = df_men_f[df_men_f["conso_litres"].notna()].copy()
df_cm["periode"] = df_cm["annee"].astype(str) + " – " + df_cm["mois"]
df_cm = df_cm.sort_values(["annee","mois_ordre"])

if not df_cm.empty:
    fig3 = go.Figure()
    for nav in selected_navires:
        d = df_cm[df_cm["navire"] == nav]
        if d.empty: continue
        fig3.add_trace(go.Bar(
            x=d["periode"], y=d["conso_litres"], name=nav,
            marker_color=COLORS[nav],
            text=[f"{v:,.0f}" for v in d["conso_litres"]],
            textposition="outside", textfont=dict(size=8),
        ))
    fig3.update_layout(
        template="plotly_white", barmode="group", height=440,
        xaxis=dict(title="Période", tickangle=45),
        yaxis=dict(title="Litres"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Données de consommation mensuelle disponibles uniquement pour 2025 et 2026.")

st.markdown("---")


# ============================================================
# GRAPHE 4 — Vitesse max + Conso à Vmax (besoin Henri #3)
# ============================================================
st.markdown('<p class="section-header">🚀 Vitesse max & Consommation à Vmax par navire (2025–2026)</p>',
            unsafe_allow_html=True)
st.caption("Relevés mensuels de la vitesse maximale (nœuds) et de la consommation instantanée associée (L/h).")

df_vit = df_men_f[df_men_f["vmax_nds"].notna()].copy()
df_vit["periode"] = df_vit["annee"].astype(str) + " – " + df_vit["mois"]
df_vit = df_vit.sort_values(["annee","mois_ordre"])

if not df_vit.empty:
    tv1, tv2 = st.tabs(["⚡ Vitesse max (nœuds)", "💧 Conso instantanée à Vmax (L/h)"])

    with tv1:
        fig4a = go.Figure()
        for nav in selected_navires:
            d = df_vit[df_vit["navire"] == nav]
            if d.empty: continue
            fig4a.add_trace(go.Scatter(
                x=d["periode"], y=d["vmax_nds"],
                mode="lines+markers+text", name=nav,
                line=dict(color=COLORS[nav], width=2),
                marker=dict(size=8),
                text=[f"{v:.1f}" for v in d["vmax_nds"]],
                textposition="top center", textfont=dict(size=9),
            ))
        fig4a.update_layout(
            template="plotly_white", height=420,
            xaxis=dict(title="Période", tickangle=45),
            yaxis=dict(title="Vitesse (nœuds)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified",
        )
        st.plotly_chart(fig4a, use_container_width=True)

    with tv2:
        df_cv = df_men_f[df_men_f["conso_vmax_lh"].notna()].copy()
        df_cv["periode"] = df_cv["annee"].astype(str) + " – " + df_cv["mois"]
        df_cv = df_cv.sort_values(["annee","mois_ordre"])

        if not df_cv.empty:
            fig4b = go.Figure()
            for nav in selected_navires:
                d = df_cv[df_cv["navire"] == nav]
                if d.empty: continue
                fig4b.add_trace(go.Bar(
                    x=d["periode"], y=d["conso_vmax_lh"], name=nav,
                    marker_color=COLORS[nav],
                    text=[f"{v:.0f}" for v in d["conso_vmax_lh"]],
                    textposition="outside", textfont=dict(size=9),
                ))
            fig4b.update_layout(
                template="plotly_white", barmode="group", height=420,
                xaxis=dict(title="Période", tickangle=45),
                yaxis=dict(title="L/h"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig4b, use_container_width=True)
        else:
            st.info("Pas de données conso à Vmax pour cette sélection.")
else:
    st.info("Données de vitesse disponibles uniquement pour 2025 et 2026.")

st.markdown("---")


# ============================================================
# TABLEAU RÉCAP
# ============================================================
with st.expander("📄 Tableau récapitulatif annuel complet"):
    recap = df_ann_f[["annee","navire","dist_totale","conso_m3","conso_lm"]].copy()
    recap.columns = ["Année","Navire","Distance (NM)","Conso (m³)","L/mille"]
    recap = recap.sort_values(["Année","Navire"])
    st.dataframe(
        recap.style.format({
            "Distance (NM)": lambda x: f"{x:,.0f}" if pd.notna(x) else "—",
            "Conso (m³)":    lambda x: f"{x:.1f}"  if pd.notna(x) else "—",
            "L/mille":       lambda x: f"{x:.2f}"  if pd.notna(x) else "—",
        }),
        use_container_width=True, hide_index=True
    )
