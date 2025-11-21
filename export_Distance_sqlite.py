import os
import pandas as pd
import sqlite3
from pathlib import Path
import numpy as np

# 🌍 Calcul distance entre 2 coordonnées (Haversine) en milles nautiques
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065  # Rayon de la Terre en miles nautiques
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


# 📁 Chemin racine des fichiers CSV
base_path = Path(r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring\Distance")
year_folders = ["Distance_2023-2022-2021-2020", "Distance_2024", "Distance_2025"]

# 📦 Dossier BDD
output_dir = base_path.parent / "bdd2"
output_dir.mkdir(exist_ok=True)
db_path = output_dir / "distance.db"

# 🚢 Navires
vessels = ["JIF GYPTIS", "JIF LACYDON", "JIF SURVEYOR"]


def export_all_vessels():

    print(f"\n📦 Création de {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table avec latitude + longitude pour la carte
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS distance_evolution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vessel TEXT,
            date TEXT,
            distance REAL,
            latitude REAL,
            longitude REAL,
            UNIQUE(vessel, date, latitude, longitude)
        )
    ''')
    conn.commit()

    for vessel_name in vessels:
        print(f"\n🚢 Traitement : {vessel_name}")
        all_data = []

        for year in year_folders:
            folder = base_path / year / vessel_name
            if not folder.exists():
                print(f"⚠️ Dossier manquant : {folder}")
                continue

            for file in folder.glob("*.csv"):
                try:
                    df = pd.read_csv(file, sep=';')
                    df.columns = [c.strip() for c in df.columns]

                    df = df[['Date', 'Latitude', 'Longitude']].copy()
                    df.rename(columns={'Date': 'date'}, inplace=True)

                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    df.dropna(subset=['date', 'Latitude', 'Longitude'], inplace=True)

                    df['vessel'] = vessel_name
                    all_data.append(df)

                except Exception as e:
                    print(f"❌ Erreur dans {file.name} : {e}")

        if not all_data:
            print(f"⛔ Aucune donnée trouvée pour {vessel_name}")
            continue

        df = pd.concat(all_data).sort_values(by='date')
        df.reset_index(drop=True, inplace=True)

        # 🔥 Calcul des distances réelles GPS -> GPS
        df['distance'] = 0.0
        for i in range(1, len(df)):
            df.at[i, 'distance'] = haversine_nm(
                df.at[i-1, 'Latitude'], df.at[i-1, 'Longitude'],
                df.at[i, 'Latitude'], df.at[i, 'Longitude']
            )

        # 🔍 Échantillonnage : 1 point tous les 2 jours
        df['date_only'] = df['date'].dt.date
        sampled_df = df.groupby('date_only').first().reset_index()
        sampled_df = sampled_df.iloc[::2]

        # Conversion vers string pour SQLite
        sampled_df['date'] = sampled_df['date'].astype(str)

        # 📌 Ajout Latitude + Longitude dans l'insertion SQLite
        cursor.executemany('''
            INSERT OR IGNORE INTO distance_evolution (vessel, date, distance, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        ''', sampled_df[['vessel', 'date', 'distance', 'Latitude', 'Longitude']].values.tolist())

        conn.commit()
        print(f"✅ {len(sampled_df)} points insérés pour {vessel_name}")

    conn.close()
    print("\n🎉 Export terminé →", db_path)


# 🚀 Lancement
if __name__ == "__main__":
    export_all_vessels()
