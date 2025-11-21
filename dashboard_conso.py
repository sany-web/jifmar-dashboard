import streamlit as st
import pandas as pd
import glob
import os
import plotly.express as px
import plotly.io as pio

# --- Configuration ---
st.set_page_config(page_title="Suivi de la consommation des navires", layout="wide")

# Chemin vers le dossier contenant les fichiers Excel
folder = r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring"
files = glob.glob(os.path.join(folder, "Consomation_*.xlsx"))

# --- Mois en français ---
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# --- Chargement des données ---
@st.cache_data
def charger_donnees():
    data_annee = []
    data_mois = []

    for f in files:
        year = os.path.basename(f).split('_')[1].split('.')[0]
        try:
            df = pd.read_excel(f, header=None)
            ship_names = df.iloc[1, 1:].dropna().tolist()

            # --- Consommation annuelle ---
            conso_m3 = df.iloc[18, 1:len(ship_names)+1].tolist()
            conso_L_mile = df.iloc[22, 1:len(ship_names)+1].tolist()

            for ship, m3, lm in zip(ship_names, conso_m3, conso_L_mile):
                try:
                    m3 = float(str(m3).replace(",", "."))
                except:
                    m3 = 0.0
                try:
                    lm = float(str(lm).replace(",", "."))
                except:
                    lm = 0.0
                data_annee.append({
                    "Année": int(year),
                    "Navire": ship.strip(),
                    "Consommation_m3": m3,
                    "Conso_Litre_Mille": lm
                })

            # --- Consommation mensuelle (m³ uniquement) ---
            for i, val in enumerate(df.iloc[:, 0]):
                if isinstance(val, str) and val.strip().lower() in MOIS_FR:
                    mois = val.strip().capitalize()
                    row = df.iloc[i, 1:len(ship_names)+1].tolist()
                    for ship, conso in zip(ship_names, row):
                        try:
                            conso = float(str(conso).replace(",", "."))
                        except:
                            conso = 0.0
                        data_mois.append({
                            "Année": int(year),
                            "Mois": mois,
                            "Navire": ship.strip(),
                            "Consommation_m3": conso
                        })

        except Exception as e:
            st.warning(f"Erreur lecture {f} : {e}")

    return pd.DataFrame(data_annee), pd.DataFrame(data_mois)

# --- Chargement des données ---
df_annee, df_mois = charger_donnees()

# --- Titre principal ---
st.title("⚓ Suivi de la consommation des navires")
st.markdown("Analyse interactive des consommations **annuelles et mensuelles** des navires Jifmar Offshore Services.")

# --- Sélecteur de mode d’affichage ---
view_mode = st.radio("📅 Type de vue :", ["Vue annuelle", "Vue mensuelle"])

# ======================================================================
# ============================ VUE ANNUELLE ============================
# ======================================================================
if view_mode == "Vue annuelle":
    st.subheader("📈 Consommation annuelle")

    navires = df_annee["Navire"].unique().tolist()
    col1, col2, col3 = st.columns([1.2, 1, 1])

    selected_navires = col1.multiselect("Navires :", navires, default=navires)
    annees = sorted(df_annee["Année"].unique())
    annee_min, annee_max = col2.select_slider("Période :", options=annees, value=(annees[0], annees[-1]))
    metric = col3.radio("Unité :", ["m³ (Consommation totale)", "L/mille (Consommation spécifique)"])

    # Filtrage
    df_f = df_annee[
        (df_annee["Navire"].isin(selected_navires)) &
        (df_annee["Année"] >= annee_min) &
        (df_annee["Année"] <= annee_max)
    ]

    # Choix du graphique
    if metric.startswith("m³"):
        y_col = "Consommation_m3"
        title = "Consommation annuelle totale (m³)"
    else:
        y_col = "Conso_Litre_Mille"
        title = "Consommation spécifique (L/mille)"

    fig = px.line(df_f, x="Année", y=y_col, color="Navire", markers=True,
                  title=title, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- Bouton d'export du graphique ---
    if st.button("📤 Télécharger le graphique (HTML)"):
        output_path = os.path.join(folder, "graphique_annuel.html")
        pio.write_html(fig, file=output_path, auto_open=False)
        st.success(f"✅ Fichier sauvegardé : {output_path}")

    st.dataframe(df_f.style.format({y_col: "{:.2f}"}), use_container_width=True)

# ======================================================================
# ============================ VUE MENSUELLE ===========================
# ======================================================================
else:
    st.subheader("📊 Consommation mensuelle (m³)")

    navires = df_mois["Navire"].unique().tolist()
    col1, col2 = st.columns(2)
    selected_navires = col1.multiselect("Navires :", navires, default=navires)
    annees = sorted(df_mois["Année"].unique())
    selected_year = col2.selectbox("Année :", annees, index=len(annees)-1)

    # Filtrage
    df_f = df_mois[
        (df_mois["Navire"].isin(selected_navires)) &
        (df_mois["Année"] == selected_year)
    ]

    fig = px.line(df_f, x="Mois", y="Consommation_m3", color="Navire", markers=True,
                  title=f"Consommation mensuelle (m³) - {selected_year}",
                  template="plotly_white",
                  category_orders={"Mois": [m.capitalize() for m in MOIS_FR]})
    st.plotly_chart(fig, use_container_width=True)

    # --- Bouton d'export du graphique ---
    if st.button("📤 Télécharger le graphique (HTML)"):
        output_path = os.path.join(folder, f"graphique_mensuel_{selected_year}.html")
        pio.write_html(fig, file=output_path, auto_open=False)
        st.success(f"✅ Fichier sauvegardé : {output_path}")

    st.dataframe(df_f.style.format({"Consommation_m3": "{:.2f}"}), use_container_width=True)
