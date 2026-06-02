#!/usr/bin/env python3
import time
import sys
import os
import argparse
import threading
from pathlib import Path
import numpy as np
import json

HAS_MATPLOTLIB = True
try:
    import matplotlib.pyplot as plt
except ImportError:
    HAS_MATPLOTLIB = False

# Ajout du chemin vers DexUMI
DEXUMI_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "DexUMI"
if str(DEXUMI_ROOT) not in sys.path:
    sys.path.insert(0, str(DEXUMI_ROOT))

# Imports des bibliothèques DDS
try:
    from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
    from inspire_sdkpy import inspire_dds
except ImportError as e:
    print(f"Erreur : Impossible d'importer unitree_sdk2py ou inspire_sdkpy : {e}")
    print("Assurez-vous de lancer ce script dans le bon environnement Python (ex: venv actif ou shell Nix).")
    sys.exit(1)

# Import du capteur FSR DexUMI
try:
    from dexumi.encoder.fsr import FSRSensor
except ImportError as e:
    print(f"Erreur : Impossible d'importer dexumi.encoder.fsr : {e}")
    print(f"Veuillez vérifier que le dépôt DexUMI est présent dans {DEXUMI_ROOT}")
    sys.exit(1)


class HandFsrCalibrator:
    def __init__(self):
        self.motor_force = 0
        self.motor_pos = 0
        self.tactile_tip = 0
        self.tactile_top = 0
        self.lock = threading.Lock()

    def state_callback(self, msg: inspire_dds.inspire_hand_state):
        with self.lock:
            # L'index est à l'index 3 (0: Auriculaire, 1: Annulaire, 2: Majeur, 3: Index, 4: Pouce Flex, 5: Pouce Rot)
            if len(msg.force_act) > 3:
                self.motor_force = msg.force_act[3]
            if len(msg.pos_act) > 3:
                self.motor_pos = msg.pos_act[3]

    def touch_callback(self, msg: inspire_dds.inspire_hand_touch):
        with self.lock:
            # fingerfour correspond à l'index
            self.tactile_tip = sum(msg.fingerfour_tip_touch)
            self.tactile_top = sum(msg.fingerfour_top_touch)

    def get_latest_data(self, sensor):
        # Récupère la dernière lecture FSR 0
        fsr_frame = sensor.get_numeric_frame()
        fsr_val = None
        if fsr_frame is not None and fsr_frame.fsr_values is not None:
            if len(fsr_frame.fsr_values) > 0:
                fsr_val = fsr_frame.fsr_values[0]

        with self.lock:
            return {
                "fsr": fsr_val,
                "motor_force": self.motor_force,
                "motor_pos": self.motor_pos,
                "tactile_tip": self.tactile_tip,
                "tactile_top": self.tactile_top
            }


def wait_enter_live(sensor, calibrator):
    """Affiche les valeurs en direct sur une seule ligne et attend l'appui sur Entrée."""
    stop_event = threading.Event()

    def live_thread():
        while not stop_event.is_set():
            data = calibrator.get_latest_data(sensor)
            fsr_str = f"{data['fsr']:.0f}" if data['fsr'] is not None else "N/A"
            sys.stdout.write(
                f"\r  [EN DIRECT] FSR0: {fsr_str:<5} | Force Moteur: {data['motor_force']:<4} | Pos: {data['motor_pos']:<4} | Tip: {data['tactile_tip']:<5} | Top: {data['tactile_top']:<5}   "
            )
            sys.stdout.flush()
            time.sleep(0.1)

    t = threading.Thread(target=live_thread, daemon=True)
    t.start()

    user_input = input().strip().lower()

    stop_event.set()
    t.join(timeout=0.5)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return user_input


def collect_average_point(sensor, calibrator, num_samples, sample_interval):
    """Échantillonne les capteurs et calcule la moyenne de chaque métrique."""
    fsr_list = []
    force_list = []
    pos_list = []
    tip_list = []
    top_list = []

    print(f"  --> Mesure en cours ({num_samples} échantillons)...")
    for _ in range(num_samples):
        data = calibrator.get_latest_data(sensor)
        if data["fsr"] is not None:
            fsr_list.append(data["fsr"])
        force_list.append(data["motor_force"])
        pos_list.append(data["motor_pos"])
        tip_list.append(data["tactile_tip"])
        top_list.append(data["tactile_top"])
        time.sleep(sample_interval)

    if not fsr_list:
        print("  [Erreur] Aucun échantillon FSR valide reçu pendant la mesure.")
        return None

    return {
        "fsr": np.mean(fsr_list),
        "fsr_std": np.std(fsr_list),
        "motor_force": np.mean(force_list),
        "motor_pos": np.mean(pos_list),
        "tactile_tip": np.mean(tip_list),
        "tactile_top": np.mean(top_list)
    }


def compute_r2(x, y, coeffs):
    y_pred = np.polyval(coeffs, x)
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    return 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 1.0


def main():
    parser = argparse.ArgumentParser(description="Calibration et mapping entre Inspire Hand (Index) et DexUMI FSR 0.")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="Port UART du capteur FSR (ex: /dev/ttyUSB0)")
    parser.add_argument("--samples", type=int, default=20, help="Nombre d'échantillons à moyenner par point (default: 20)")
    parser.add_argument("--interval", type=float, default=0.05, help="Intervalle d'échantillonnage en secondes (default: 0.05)")
    parser.add_argument("--degree", type=int, default=2, help="Degré du polynôme de mapping (default: 2)")
    parser.add_argument("--out-img", type=str, default="calibration_result.png", help="Nom du fichier image du graphique")
    args = parser.parse_args()

    # Initialisation de la classe de calibration
    calibrator = HandFsrCalibrator()

    # Initialisation DDS
    print("Initialisation du réseau DDS...")
    ChannelFactoryInitialize(0)

    print("Abonnement aux topics DDS d'Inspire Hand...")
    sub_state = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub_state.Init(calibrator.state_callback, 10)

    sub_touch = ChannelSubscriber("rt/inspire_hand/touch/r", inspire_dds.inspire_hand_touch)
    sub_touch.Init(calibrator.touch_callback, 10)

    # Initialisation FSR DexUMI
    print(f"Connexion au capteur FSR DexUMI sur {args.port}...")
    sensor = FSRSensor(uart_port=args.port, verbose=False)

    try:
        sensor.start_streaming()
        print("Démarrage du flux de données FSR. Stabilisation...")
        time.sleep(1.5)
    except Exception as e:
        print(f"Erreur lors de l'initialisation du FSR DexUMI : {e}")
        sys.exit(1)

    # Listes pour stocker les points enregistrés
    recorded_points = []

    print("\n" + "=" * 80)
    print(" OUTIL DE CALIBRATION ET MAPPING : INSPIRE HAND (INDEX) VS FSR 0")
    print("=" * 80)
    print("Instructions :")
    print("  1. Positionnez ou serrez un objet avec plus ou moins de force.")
    print("  2. Appuyez sur ENTRÉE pour capturer et moyenner le point de mesure courant.")
    print("  3. Répétez l'opération pour différentes intensités de serrage et objets.")
    print("  4. Saisissez 'q' puis ENTRÉE pour arrêter et calculer le mapping.")
    print("=" * 80 + "\n")

    try:
        while True:
            print(f"Point de mesure #{len(recorded_points) + 1} en préparation...")
            print("Appuyez sur ENTRÉE pour capturer le point, ou 'q' + ENTRÉE pour terminer.")
            
            cmd = wait_enter_live(sensor, calibrator)
            if cmd == 'q':
                print("Fin de l'acquisition demandée.")
                break

            # Capture et moyenne des points
            pt = collect_average_point(sensor, calibrator, args.samples, args.interval)
            if pt is not None:
                recorded_points.append(pt)
                print(f"  [SUCCÈS] Enregistré : FSR={pt['fsr']:.1f} (std={pt['fsr_std']:.1f}) | Force Moteur={pt['motor_force']:.1f} | Pos={pt['motor_pos']:.1f} | Tip={pt['tactile_tip']:.1f} | Top={pt['tactile_top']:.1f}\n")

    except KeyboardInterrupt:
        print("\nInterruption clavier reçue.")
    finally:
        print("Arrêt du flux FSR...")
        sensor.stop_streaming()

    # Analyse et Mapping
    num_pts = len(recorded_points)
    print(f"\nNombre de points enregistrés : {num_pts}")

    if num_pts < 3:
        print("Nombre de points insuffisant pour calculer un mapping de qualité (minimum 3 requis).")
        sys.exit(0)

    # Extraction des données
    fsr_arr = np.array([pt["fsr"] for pt in recorded_points])
    force_arr = np.array([pt["motor_force"] for pt in recorded_points])
    pos_arr = np.array([pt["motor_pos"] for pt in recorded_points])
    tip_arr = np.array([pt["tactile_tip"] for pt in recorded_points])
    top_arr = np.array([pt["tactile_top"] for pt in recorded_points])

    # Calcul des fits polynomiaux
    # On souhaite prédire les valeurs Inspire à partir de la valeur brute du FSR
    deg = args.degree
    p_force = np.polyfit(fsr_arr, force_arr, deg)
    p_pos = np.polyfit(fsr_arr, pos_arr, deg)
    p_tip = np.polyfit(fsr_arr, tip_arr, deg)
    p_top = np.polyfit(fsr_arr, top_arr, deg)

    r2_force = compute_r2(fsr_arr, force_arr, p_force)
    r2_pos = compute_r2(fsr_arr, pos_arr, p_pos)
    r2_tip = compute_r2(fsr_arr, tip_arr, p_tip)
    r2_top = compute_r2(fsr_arr, top_arr, p_top)

    print("\n" + "=" * 80)
    print(" RÉSULTATS DU MAPPING (Fonction d'estimation des valeurs Inspire en fonction du FSR)")
    print("=" * 80)

    def print_equation(name, coeffs, r2):
        deg_len = len(coeffs)
        terms = []
        for i, c in enumerate(coeffs):
            power = deg_len - 1 - i
            if power > 1:
                terms.append(f"{c:+.4e} * FSR^{power}")
            elif power == 1:
                terms.append(f"{c:+.4e} * FSR")
            else:
                terms.append(f"{c:+.4f}")
        equation = " ".join(terms)
        print(f"• {name} :\n  {name} = {equation}\n  R² = {r2:.4f}\n")

    print_equation("Force Moteur", p_force, r2_force)
    print_equation("Position Moteur", p_pos, r2_pos)
    print_equation("Tip Tactile (Bout)", p_tip, r2_tip)
    print_equation("Top Tactile (Pulpe)", p_top, r2_top)

    # Affichage du code Python généré
    print("=" * 80)
    print(" CODE PYTHON DE MAPPING PRÊT À L'EMPLOI :")
    print("=" * 80)
    coeffs_str = f"P_FORCE = {list(p_force)}\n" \
                 f"P_POS = {list(p_pos)}\n" \
                 f"P_TIP = {list(p_tip)}\n" \
                 f"P_TOP = {list(p_top)}\n"
    print(coeffs_str)
    print("""def estimate_hand_values(fsr_value):
    import numpy as np
    return {
        "motor_force": np.polyval(P_FORCE, fsr_value),
        "motor_pos": np.polyval(P_POS, fsr_value),
        "tactile_tip": np.polyval(P_TIP, fsr_value),
        "tactile_top": np.polyval(P_TOP, fsr_value)
    }
""")
    print("=" * 80 + "\n")

    # Sauvegarde des données en JSON
    data_to_save = {
        "degree": deg,
        "points": recorded_points,
        "p_force": list(p_force),
        "p_pos": list(p_pos),
        "p_tip": list(p_tip),
        "p_top": list(p_top),
        "r2_force": r2_force,
        "r2_pos": r2_pos,
        "r2_tip": r2_tip,
        "r2_top": r2_top
    }
    json_out = Path(__file__).parent / "calibration_data.json"
    try:
        with open(json_out, "w") as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Données de calibration sauvegardées dans : {json_out}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

    # Génération du graphique
    if HAS_MATPLOTLIB:
        print("Génération du graphique...")
        try:
            fig, axs = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f"Mapping de l'index de la main Inspire par rapport au FSR 0 (Polynôme degré {deg})", fontsize=16)

            # Tri des points par FSR pour tracer une ligne courbe lisse
            sort_idx = np.argsort(fsr_arr)
            fsr_sorted = fsr_arr[sort_idx]
            
            # Génération d'une courbe continue lisse
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
            plt.savefig(args.out_img)
            print(f"Graphique sauvegardé sous : {args.out_img}")
            
            # Affichage du graphique
            plt.show()
        except Exception as e:
            print(f"Erreur lors de la génération ou de l'affichage du graphique : {e}")
    else:
        print("\n[INFO] matplotlib n'est pas disponible dans cet environnement Python.")
        print(f"Les points et les coefficients de mapping ont été enregistrés dans '{json_out}'.")
        print("Pour générer et afficher le graphique, exécutez le script de tracé dédié dans l'environnement virtuel :")
        print(f"  ./.venv/bin/python plot_calibration.py --data {json_out} --out {args.out_img}")



if __name__ == "__main__":
    main()
