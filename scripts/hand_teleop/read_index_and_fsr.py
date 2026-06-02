#!/usr/bin/env python3
import time
import sys
import os
import argparse
from pathlib import Path

# Adjust the path to import DexUMI correctly
DEXUMI_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "DexUMI"
if str(DEXUMI_ROOT) not in sys.path:
    sys.path.insert(0, str(DEXUMI_ROOT))

# Try importing DDS dependencies
try:
    from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
    from inspire_sdkpy import inspire_dds
except ImportError as e:
    print(f"Error: Unable to import unitree_sdk2py or inspire_sdkpy: {e}")
    print("Please make sure you are running this script within the correct python environment (e.g. Nix shell or active virtual environment).")
    sys.exit(1)

# Try importing DexUMI FSR dependencies
try:
    from dexumi.encoder.fsr import FSRSensor
except ImportError as e:
    print(f"Error: Unable to import dexumi.encoder.fsr: {e}")
    print(f"Please verify that DexUMI is present at {DEXUMI_ROOT}")
    sys.exit(1)

# Global variables for storing the latest data
motor_force_index = 0
tactile_tip_force_index = 0
tactile_top_force_index = 0

# DDS callback for hand state
def state_callback(msg: inspire_dds.inspire_hand_state):
    global motor_force_index
    # Index finger is at position 3 in force_act (0: Little, 1: Ring, 2: Middle, 3: Index, 4: Thumb Flex, 5: Thumb Rot)
    if len(msg.force_act) > 3:
        motor_force_index = msg.force_act[3]

# DDS callback for tactile/touch sensors
def touch_callback(msg: inspire_dds.inspire_hand_touch):
    global tactile_tip_force_index, tactile_top_force_index
    # fingerfour represents the Index finger
    tactile_tip_force_index = sum(msg.fingerfour_tip_touch)
    tactile_top_force_index = sum(msg.fingerfour_top_touch)

def main():
    parser = argparse.ArgumentParser(description="Read Inspire Hand Index forces and DexUMI FSR 0 in real-time.")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="UART port of the DexUMI FSR sensor (e.g., /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM1)")
    parser.add_argument("--freq", type=float, default=10.0, help="Display refresh frequency in Hz (default: 10.0)")
    parser.add_argument("--threshold", type=int, default=4000, help="FSR 0 contact threshold (default: 4000)")
    args = parser.parse_args()

    print("Initialisation du réseau DDS...")
    ChannelFactoryInitialize(0)

    # Subscribing to DDS topics for the Inspire Hand (Right Hand)
    print("Abonnement aux topics DDS de l'Inspire Hand...")
    sub_state = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub_state.Init(state_callback, 10)

    sub_touch = ChannelSubscriber("rt/inspire_hand/touch/r", inspire_dds.inspire_hand_touch)
    sub_touch.Init(touch_callback, 10)

    # Initializing DexUMI FSR sensor
    print(f"Connexion au capteur FSR DexUMI sur {args.port}...")
    sensor = FSRSensor(uart_port=args.port, verbose=False)
    
    try:
        sensor.start_streaming()
        print("Démarrage du flux de données FSR...")
        time.sleep(1.0) # Allow connection to stabilize
    except Exception as e:
        print(f"Erreur lors de l'initialisation du FSR DexUMI : {e}")
        print("Vérifiez les permissions du port série et la connexion.")
        sys.exit(1)

    print("\nLecture en temps réel démarrée. Affichage en cours...\n")
    
    period = 1.0 / args.freq
    try:
        while True:
            t0 = time.monotonic()
            
            # Read FSR 0 value (the first one)
            fsr_frame = sensor.get_numeric_frame()
            fsr_val = None
            contact_status = "Inconnu"
            
            if fsr_frame is not None and fsr_frame.fsr_values is not None:
                if len(fsr_frame.fsr_values) > 0:
                    fsr_val = fsr_frame.fsr_values[0]
                    # Lower value means higher pressure. Check if below threshold.
                    contact_status = "OUI" if fsr_val < args.threshold else "NON"

            # Clean and display data in terminal
            os.system('cls' if os.name == 'nt' else 'clear')
            print("=" * 60)
            print(" LECTURE TEMPS RÉEL : INDEX (INSPIRE) & FSR 0 (DexUMI)")
            print("=" * 60)
            
            print("\n1. MAIN INSPIRE (INDEX UNIQUEMENT)")
            print("-" * 60)
            print(f"  Force Moteur (Serrage)        : {motor_force_index}")
            print(f"  Pression Bout (Tip Touch 3x3) : {tactile_tip_force_index}")
            print(f"  Pression Pulpe (Top Touch 12x8): {tactile_top_force_index}")
            
            print("\n2. CAPTEUR FSR DexUMI (PREMIER UNIQUEMENT)")
            print("-" * 60)
            if fsr_val is not None:
                print(f"  Valeur FSR 0 brute (0-65535)  : {fsr_val:.0f}")
                print(f"  Contact Détecté (seuil={args.threshold}) : {contact_status}")
            else:
                print("  [En attente de données du FSR...]")
                
            print("-" * 60)
            print("Appuyez sur Ctrl+C pour quitter.")
            
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, period - elapsed))
            
    except KeyboardInterrupt:
        print("\nArrêt demandé...")
    finally:
        print("Fermeture du flux FSR...")
        sensor.stop_streaming()
        print("Fin de la lecture.")

if __name__ == "__main__":
    main()
