import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import glob
import os
import math

folder = r"C:\Users\SanyLou’eyZEMAL\OneDrive - Jifmar Offshore Services\Documents\Porjet_Monitoring"
files = glob.glob(os.path.join(folder, "Consomation_*.xlsx"))

data = []

for f in files:
    year = os.path.basename(f).split('_')[1].split('.')[0]
    try:
        df = pd.read_excel(f, header=None)

        # --- noms des navires ---
        ship_names = df.iloc[1, 1:].dropna().tolist()

        # --- consommation annuelle (m³) ---
        conso_m3 = df.iloc[18, 1:len(ship_names)+1].tolist()

        # --- consommation litre/mille (ligne 22-23) ---
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

            # Si erreur (#DIV/0!) ou distance=0 => 0
            if math.isnan(lm) or lm == 0:
                lm = 0.0

            data.append({
                "Année": int(year),
                "Navire": ship,
                "Consommation_m3": m3,
                "Conso_Litre_Mille": lm
            })

        print(f"[OK] {os.path.basename(f)} traité.")

    except PermissionError:
        print(f"[⛔] Fichier ouvert dans Excel : {f}")
    except Exception as e:
        print(f"[Erreur] {f} : {e}")

# === Vérif ===
if not data:
    print("❌ Aucune donnée trouvée.")
    exit()

df_all = pd.DataFrame(data)
df_all = df_all.sort_values(by=["Navire", "Année"])

# === Création de la figure avec deux graphes + un tableau ===
fig = plt.figure(figsize=(14, 10))
gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 0.6])

# --- Graphique 1 : Consommation m³ ---
ax1 = fig.add_subplot(gs[0])
for ship, group in df_all.groupby("Navire"):
    ax1.plot(group["Année"], group["Consommation_m3"], marker='o', linewidth=2, label=ship)
    for x, y in zip(group["Année"], group["Consommation_m3"]):
        ax1.text(x, y + 1, f"{y:.1f}", ha='center', fontsize=8)
ax1.set_title("Consommation annuelle totale (m³)", fontsize=13, weight='bold')
ax1.set_xlabel("Année")
ax1.set_ylabel("m³")
ax1.grid(True, linestyle='--', linewidth=0.5)
ax1.legend()

# --- Graphique 2 : Consommation spécifique (L/mille) ---
ax2 = fig.add_subplot(gs[1])
for ship, group in df_all.groupby("Navire"):
    ax2.plot(group["Année"], group["Conso_Litre_Mille"], marker='s', linewidth=2, label=ship)
    for x, y in zip(group["Année"], group["Conso_Litre_Mille"]):
        ax2.text(x, y + 0.2, f"{y:.2f}", ha='center', fontsize=8)
ax2.set_title("Consommation spécifique (Litre / Mille Nautique)", fontsize=13, weight='bold')
ax2.set_xlabel("Année")
ax2.set_ylabel("L/mille")
ax2.grid(True, linestyle='--', linewidth=0.5)
ax2.legend()

# --- Tableau récapitulatif ---
ax3 = fig.add_subplot(gs[2])
ax3.axis('off')

# On pivot le tableau pour bien afficher
table_data = df_all.pivot_table(index=["Année"], columns=["Navire"], values=["Consommation_m3", "Conso_Litre_Mille"])
table_data = table_data.round(2)

# Affichage du tableau dans Matplotlib
table = ax3.table(cellText=table_data.values,
                  colLabels=[f"{a}\n{b}" for a,b in table_data.columns],
                  rowLabels=table_data.index,
                  loc='center')

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.2)

plt.tight_layout()
plt.show()
