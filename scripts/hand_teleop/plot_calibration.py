#!/usr/bin/env python3
import sys
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Tracé des résultats de calibration enregistrés par calibrate_hand_fsr.py.")
    default_data = str(Path(__file__).parent / "calibration_data.json")
    parser.add_argument("--data", type=str, default=default_data, help="Chemin vers le fichier JSON des données de calibration")
    parser.add_argument("--out", type=str, default="calibration_result.png", help="Nom du fichier image du graphique à sauvegarder")
    args = parser.parse_args()

    try:
        with open(args.data, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {args.data} : {e}")
        sys.exit(1)

    points = data.get("points", [])
    if not points:
        print("Erreur : Aucun point de mesure trouvé dans le fichier.")
        sys.exit(1)

    deg = data.get("degree", 2)
    p_force = np.array(data["p_force"])
    p_pos = np.array(data["p_pos"])
    p_tip = np.array(data["p_tip"])
    p_top = np.array(data["p_top"])

    # Extraction des données
    fsr_arr = np.array([pt["fsr"] for pt in points])
    force_arr = np.array([pt["motor_force"] for pt in points])
    pos_arr = np.array([pt["motor_pos"] for pt in points])
    tip_arr = np.array([pt["tactile_tip"] for pt in points])
    top_arr = np.array([pt["tactile_top"] for pt in points])

    # Re-calcul des R² pour affichage si absents du fichier
    def compute_r2(x, y, coeffs):
        y_pred = np.polyval(coeffs, x)
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        return 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 1.0

    r2_force = data.get("r2_force", compute_r2(fsr_arr, force_arr, p_force))
    r2_pos = data.get("r2_pos", compute_r2(fsr_arr, pos_arr, p_pos))
    r2_tip = data.get("r2_tip", compute_r2(fsr_arr, tip_arr, p_tip))
    r2_top = data.get("r2_top", compute_r2(fsr_arr, top_arr, p_top))

    # Génération du graphique
    print("Génération du graphique...")
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Mapping de l'index de la main Inspire par rapport au FSR 0 (Polynôme degré {deg})", fontsize=16)

    # Courbe de fit continue
    fsr_line = np.linspace(np.min(fsr_arr), np.max(fsr_arr), 300)

    # 1. Force Moteur
    ax = axs[0, 0]
    ax.scatter(fsr_arr, force_arr, color="blue", label="Points mesurés")
    ax.plot(fsr_line, np.polyval(p_force, fsr_line), color="red", linestyle="--", label=f"Fit (R²={r2_force:.3f})")
    ax.set_title("Force Moteur en fonction du FSR")
    ax.set_xlabel("Valeur FSR 0 (ADC)")
    ax.set_ylabel("Force Moteur")
    ax.legend()
    ax.grid(True)

    # 2. Position Moteur
    ax = axs[0, 1]
    ax.scatter(fsr_arr, pos_arr, color="green", label="Points mesurés")
    ax.plot(fsr_line, np.polyval(p_pos, fsr_line), color="red", linestyle="--", label=f"Fit (R²={r2_pos:.3f})")
    ax.set_title("Position Moteur en fonction du FSR")
    ax.set_xlabel("Valeur FSR 0 (ADC)")
    ax.set_ylabel("Position Moteur")
    ax.legend()
    ax.grid(True)

    # 3. Tip Tactile (Bout)
    ax = axs[1, 0]
    ax.scatter(fsr_arr, tip_arr, color="purple", label="Points mesurés")
    ax.plot(fsr_line, np.polyval(p_tip, fsr_line), color="red", linestyle="--", label=f"Fit (R²={r2_tip:.3f})")
    ax.set_title("Tactile Tip (Somme) en fonction du FSR")
    ax.set_xlabel("Valeur FSR 0 (ADC)")
    ax.set_ylabel("Somme des pressions Tip")
    ax.legend()
    ax.grid(True)

    # 4. Top Tactile (Pulpe)
    ax = axs[1, 1]
    ax.scatter(fsr_arr, top_arr, color="orange", label="Points mesurés")
    ax.plot(fsr_line, np.polyval(p_top, fsr_line), color="red", linestyle="--", label=f"Fit (R²={r2_top:.3f})")
    ax.set_title("Tactile Top (Somme) en fonction du FSR")
    ax.set_xlabel("Valeur FSR 0 (ADC)")
    ax.set_ylabel("Somme des pressions Top")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(args.out)
    print(f"Graphique sauvegardé sous : {args.out}")
    plt.show()

if __name__ == "__main__":
    main()
