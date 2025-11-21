import pandas as pd
import sqlite3
import glob
import os
import math

# === Configuration ===
folder = r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring"
files = glob.glob(os.path.join(folder, "Consomation_*.xlsx"))
db_path = os.path.join(folder, "conso.db")

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# === Création / Connexion DB ===
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# === Création des tables ===
cur.execute("""
CREATE TABLE IF NOT EXISTS conso_annuelle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    annee INTEGER,
    navire TEXT,
    conso_m3 REAL,
    conso_l_mille REAL,
    UNIQUE(annee, navire) ON CONFLICT REPLACE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS conso_mensuelle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    annee INTEGER,
    mois TEXT,
    navire TEXT,
    conso_m3 REAL,
    UNIQUE(annee, mois, navire) ON CONFLICT REPLACE
)
""")
conn.commit()

# === Extraction ===
for f in files:
    year = int(os.path.basename(f).split('_')[1].split('.')[0])
    print(f"📄 Lecture : {os.path.basename(f)}")

    try:
        df = pd.read_excel(f, header=None)
        ship_names = df.iloc[1, 1:].dropna().tolist()

        # --- extraction consommation annuelle ---
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

            if math.isnan(lm):
                lm = 0.0

            cur.execute("""
            REPLACE INTO conso_annuelle (annee, navire, conso_m3, conso_l_mille)
            VALUES (?, ?, ?, ?)
            """, (year, ship.strip(), m3, lm))

        # --- extraction consommation mensuelle ---
        for i, val in enumerate(df.iloc[:, 0]):
            if isinstance(val, str) and val.strip().lower() in MOIS_FR:
                mois = val.strip().capitalize()
                row = df.iloc[i, 1:len(ship_names)+1].tolist()

                for ship, conso in zip(ship_names, row):
                    try:
                        conso = float(str(conso).replace(",", "."))
                    except:
                        conso = 0.0

                    cur.execute("""
                    REPLACE INTO conso_mensuelle (annee, mois, navire, conso_m3)
                    VALUES (?, ?, ?, ?)
                    """, (year, mois, ship.strip(), conso))

        conn.commit()
        print(f"✅ {os.path.basename(f)} importé dans SQLite")

    except Exception as e:
        print(f"⚠️ Erreur lors de la lecture de {f} : {e}")

conn.close()
print("🎉 Extraction terminée — Base conso.db générée.")
