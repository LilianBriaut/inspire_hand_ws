#!/usr/bin/env python3
import time
import sys
import os
import argparse
import json
import numpy as np
from pathlib import Path

# Ajustement du sys.path pour importer DexUMI
DEXUMI_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "DexUMI"
if str(DEXUMI_ROOT) not in sys.path:
    sys.path.insert(0, str(DEXUMI_ROOT))

# Import des composants DexUMI
try:
    from dexumi.encoder.encoder import InspireEncoder, XhandEncoder
    from dexumi.hand_sdk.inspire.hand_api_cls import InspireSDK
except ImportError as e:
    print(f"Erreur : Impossible d'importer les composants de DexUMI : {e}")
    print(f"Veuillez vérifier que DexUMI est présent à l'adresse {DEXUMI_ROOT}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Téléopération en temps réel de la main Inspire Hand avec l'exosquelette DexUMI.")
    parser.add_argument("--encoder-port", type=str, default="/dev/ttyUSB0", help="Port série de l'encodeur de l'exosquelette (ex: /dev/ttyUSB0)")
    parser.add_argument("--hand-port", type=str, default="/dev/ttyUSB1", help="Port série de la main Inspire Hand (ex: /dev/ttyUSB1)")
    parser.add_argument("--encoder-type", type=str, choices=["inspire", "xhand"], default="inspire", help="Type d'encodeur (inspire ou xhand)")
    parser.add_argument("--freq", type=float, default=30.0, help="Fréquence de contrôle en Hz (default: 30.0)")
    parser.add_argument("--calib", action="store_true", help="Forcer une nouvelle calibration interactive de l'exosquelette")
    parser.add_argument("--alpha", type=float, default=0.3, help="Coefficient de lissage du filtre (0.0 = lissage max, 1.0 = pas de lissage)")
    parser.add_argument("--deadband", type=int, default=6, help="Seuil de zone morte (0-1000) pour filtrer les micro-mouvements résiduels")
    args = parser.parse_args()




    print("\n" + "=" * 80)
    print(" DÉMARRAGE DE LA TÉLÉOPÉRATION INSPIRE HAND <-> EXOSQUELETTE DEXUMI")
    print("=" * 80 + "\n")

    # 1. Connexion à l'encodeur de l'exosquelette
    print(f"[1/3] Connexion à l'encodeur ({args.encoder_type}) sur le port {args.encoder_port}...")
    if args.encoder_type == "inspire":
        encoder = InspireEncoder(uart_port=args.encoder_port, verbose=False)
    else:
        encoder = XhandEncoder(uart_port=args.encoder_port, verbose=False)
        
    try:
        encoder.start_streaming()
        print("  -> Flux de données de l'encodeur activé avec succès.")
        time.sleep(1.0)
    except Exception as e:
        print(f"  -> [ERREUR] Impossible de connecter l'encodeur : {e}")
        print("     Vérifiez le port série et les permissions (chmod/dialout).")
        sys.exit(1)

    # 2. Connexion à la main robotique Inspire Hand
    print(f"[2/3] Connexion à la main Inspire Hand sur le port {args.hand_port}...")
    hand = InspireSDK(port=args.hand_port, read_rate=30, verbose=False)
    if not hand.connect():
        print("  -> [ERREUR] Impossible de se connecter à la main Inspire Hand.")
        print("     Vérifiez l'alimentation de la main et le branchement du câble série/RS485.")
        encoder.stop_streaming()
        sys.exit(1)
    print("  -> Main robotique connectée avec succès.")

    try:
        # 3. Étape d'autocalibration interactive ou chargement
        print("\n" + "=" * 80)
        print(" [3/3] ÉTAPE D'AUTOCALIBRATION INTERACTIVE")
        print("=" * 80)
        
        calib_file = Path(__file__).parent / "exoskeleton_calibration.json"
        do_calibration = args.calib or not calib_file.exists()
        
        # Test de réception des premières trames de l'exosquelette
        print("\nAttente des premières données de l'exosquelette...")
        frame = None
        for _ in range(50):
            frame = encoder.get_numeric_frame()
            if frame is not None and frame.joint_angles is not None:
                break
            time.sleep(0.1)
            
        if frame is None or frame.joint_angles is None:
            print("[ERREUR] Aucune donnée reçue de l'exosquelette.")
            print("Vérifiez que le boîtier de l'exosquelette est alimenté et allumé.")
            hand.disconnect()
            encoder.stop_streaming()
            sys.exit(1)
            
        num_joints = len(frame.joint_angles)
        print(f"-> Détecté : {num_joints} jointures sur l'exosquelette.")

        if not do_calibration:
            try:
                with open(calib_file, "r") as f:
                    calib_data = json.load(f)
                open_angles = np.array(calib_data["open_angles"])
                close_angles = np.array(calib_data["close_angles"])
                # Vérification de la compatibilité du nombre de jointures
                if len(open_angles) != num_joints or len(close_angles) != num_joints:
                    print(f"  -> [INFO] Nombre de jointures incohérent dans '{calib_file}'. Recalibration obligatoire.")
                    do_calibration = True
                else:
                    print(f"  -> Chargement de la calibration précédente depuis '{calib_file}' :")
                    print(f"     Angles ouverts : {[round(float(a), 1) for a in open_angles]}")
                    print(f"     Angles fermés  : {[round(float(a), 1) for a in close_angles]}")
            except Exception as e:
                print(f"  -> [INFO] Impossible de charger la calibration précédente ({e}). Recalibration...")
                do_calibration = True

        if do_calibration:
            print("\nCette étape va enregistrer la plage de mouvements de vos doigts sur l'exosquelette.")
            # Calibration Main Ouverte
            input("\n--> Ouvrez COMPLÈTEMENT votre main (exosquelette au repos) et appuyez sur ENTRÉE...")
            frame = encoder.get_numeric_frame()
            if frame is None or frame.joint_angles is None:
                raise RuntimeError("Perte du signal de l'encodeur pendant l'autocalibration.")
            open_angles = np.array(frame.joint_angles)
            print(f"Angles de référence (ouverts) enregistrés : {[round(float(a), 1) for a in open_angles]}")

            # Calibration Main Fermée
            input("\n--> Fermez COMPLÈTEMENT votre main (serrez le poing) et appuyez sur ENTRÉE...")
            frame = encoder.get_numeric_frame()
            if frame is None or frame.joint_angles is None:
                raise RuntimeError("Perte du signal de l'encodeur pendant l'autocalibration.")
            close_angles = np.array(frame.joint_angles)
            print(f"Angles de référence (fermés) enregistrés : {[round(float(a), 1) for a in close_angles]}")

            # Enregistrement dans le fichier JSON
            try:
                with open(calib_file, "w") as f:
                    json.dump({
                        "open_angles": list(open_angles),
                        "close_angles": list(close_angles)
                    }, f, indent=4)
                print(f"Calibration sauvegardée dans '{calib_file}'.")
            except Exception as e:
                print(f"  -> [AVERTISSEMENT] Impossible de sauvegarder la calibration : {e}")


        print("\n" + "=" * 80)
        print(" CALIBRATION TERMINÉE - DÉBUT DE LA TÉLÉOPÉRATION")
        print("=" * 80)
        print("Bougez vos doigts ! La main robotique va suivre vos mouvements (filtre actif).")
        print("Appuyez sur Ctrl+C à tout moment pour arrêter.")
        print("-" * 80 + "\n")

        # 4. Boucle de contrôle temps réel
        dt = 1.0 / args.freq
        filtered_angles = None
        last_sent_motor_values = None
        alpha = args.alpha
        deadband = args.deadband
        
        while True:
            t0 = time.monotonic()
            
            frame = encoder.get_numeric_frame()
            if frame is not None and frame.joint_angles is not None:
                current_angles = np.array(frame.joint_angles)
                
                # Filtrage passe-bas exponentiel (EMA)
                if filtered_angles is None:
                    filtered_angles = current_angles
                else:
                    filtered_angles = alpha * current_angles + (1 - alpha) * filtered_angles
                
                # Calcul de la valeur moteur linéaire (0 à 1000) pour chaque doigt
                motor_values = np.zeros(6, dtype=np.int32)
                for i in range(min(num_joints, 6)):
                    denom = close_angles[i] - open_angles[i]
                    if abs(denom) > 1e-3:
                        # Inversion : 1000 (ouvert) -> 0 (fermé)
                        val = 1000 - ((filtered_angles[i] - open_angles[i]) / denom * 1000)
                    else:
                        val = 1000
                    # On sature la valeur entre 0 (fermé) et 1000 (ouvert)
                    motor_values[i] = int(np.clip(val, 0, 1000))
                
                # Filtrage par zone morte (deadband) pour éviter les micro-vibrations à l'arrêt
                if last_sent_motor_values is None:
                    last_sent_motor_values = motor_values.copy()
                    should_send = True
                else:
                    should_send = False
                    for i in range(6):
                        if abs(motor_values[i] - last_sent_motor_values[i]) >= deadband:
                            last_sent_motor_values[i] = motor_values[i]
                            should_send = True
                
                # Envoi de la commande uniquement en cas de changement significatif
                if should_send:
                    command = hand.write_hand_angle(
                        last_sent_motor_values[5],  # val1: Robot Auriculaire <- Exo Auriculaire (joint 5)
                        last_sent_motor_values[4],  # val2: Robot Annulaire   <- Exo Annulaire (joint 4)
                        last_sent_motor_values[3],  # val3: Robot Index       <- Exo Index (joint 3)
                        last_sent_motor_values[2],  # val4: Robot Majeur      <- Exo Majeur (joint 2)
                        last_sent_motor_values[0],  # val5: Robot Pouce Flex  <- Exo Pouce Rot (joint 0)
                        last_sent_motor_values[1]   # val6: Robot Pouce Rot   <- Exo Pouce Flex (joint 1)
                    )
                    hand.send_command(command)
                
                # Affichage de diagnostic sur une ligne dynamique (affiche les valeurs après filtrage et zone morte)
                sys.stdout.write(
                    f"\r[En cours] Angles Exo: {[int(a) for a in filtered_angles]} | Consignes Main (0-1000): {list(last_sent_motor_values)}   "
                )
                sys.stdout.flush()
                
            # Gestion précise de la fréquence de boucle
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, dt - elapsed))

    except KeyboardInterrupt:
        print("\n\nArrêt de la téléopération demandé par l'utilisateur.")
    except Exception as e:
        print(f"\n\n[ERREUR] Une erreur est survenue pendant la téléopération : {e}")
    finally:
        print("Arrêt des flux et déconnexion des matériels...")
        hand.disconnect()
        encoder.stop_streaming()
        print("Téléopération arrêtée proprement.")


if __name__ == "__main__":
    main()
