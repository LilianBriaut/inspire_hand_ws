import time
import sys
import os
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from inspire_sdkpy import inspire_dds

# Variables pour stocker les dernières données reçues
motor_forces = [0] * 6
tactile_tip_forces = {
    "Auriculaire (Little)": 0,
    "Annulaire (Ring)": 0,
    "Majeur (Middle)": 0,
    "Index": 0,
    "Pouce (Thumb)": 0
}
tactile_top_forces = {
    "Auriculaire (Little)": 0,
    "Annulaire (Ring)": 0,
    "Majeur (Middle)": 0,
    "Index": 0,
    "Pouce (Thumb)": 0
}

def state_callback(msg: inspire_dds.inspire_hand_state):
    global motor_forces
    motor_forces = list(msg.force_act)
    display_data()

def touch_callback(msg: inspire_dds.inspire_hand_touch):
    global tactile_tip_forces, tactile_top_forces
    
    # Somme des capteurs tactiles de l'extrême bout du doigt (tip_touch, matrice 3x3 = 9 capteurs)
    tactile_tip_forces["Auriculaire (Little)"] = sum(msg.fingerone_tip_touch)
    tactile_tip_forces["Annulaire (Ring)"]     = sum(msg.fingertwo_tip_touch)
    tactile_tip_forces["Majeur (Middle)"]     = sum(msg.fingerthree_tip_touch)
    tactile_tip_forces["Index"]                = sum(msg.fingerfour_tip_touch)
    tactile_tip_forces["Pouce (Thumb)"]        = sum(msg.fingerfive_tip_touch)
    
    # Somme des capteurs tactiles de la pulpe du bout du doigt (top_touch, matrice 12x8 = 96 capteurs)
    tactile_top_forces["Auriculaire (Little)"] = sum(msg.fingerone_top_touch)
    tactile_top_forces["Annulaire (Ring)"]     = sum(msg.fingertwo_top_touch)
    tactile_top_forces["Majeur (Middle)"]     = sum(msg.fingerthree_top_touch)
    tactile_top_forces["Index"]                = sum(msg.fingerfour_top_touch)
    tactile_top_forces["Pouce (Thumb)"]        = sum(msg.fingerfive_top_touch)
    
    display_data()

last_print_time = 0
def display_data():
    global last_print_time
    current_time = time.time()
    # Limiter le rafraîchissement d'affichage à 10Hz maximum pour la lisibilité
    if current_time - last_print_time < 0.1:
        return
    last_print_time = current_time
    
    # Effacer le terminal (optionnel, pour un affichage fixe propre)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=" * 60)
    print(" LECTURE DES FORCES SUR LE BOUT DES DOIGTS (MAIN DROITE)")
    print("=" * 60)
    print("\n1. CAPTEURS TACTILES DU BOUT DES DOIGTS (Somme des pressions brutes)")
    print("-" * 60)
    print(f"{'Doigt':<22} | {'Tip Touch (matrice 3x3)':<22} | {'Top Touch (matrice 12x8)':<22}")
    print("-" * 60)
    for finger in tactile_tip_forces.keys():
        tip_val = tactile_tip_forces[finger]
        top_val = tactile_top_forces[finger]
        print(f"{finger:<22} | {tip_val:<22} | {top_val:<22}")
        
    print("\n2. FORCES ACTUELLES DES MOTEURS (Force de serrage / Retour d'effort)")
    print("-" * 60)
    print(f"Auriculaire (Little)  : {motor_forces[0]}")
    print(f"Annulaire (Ring)      : {motor_forces[1]}")
    print(f"Majeur (Middle)      : {motor_forces[2]}")
    print(f"Index                 : {motor_forces[3]}")
    print(f"Pouce Flexion (Thumb) : {motor_forces[4]}")
    print(f"Pouce Rotation        : {motor_forces[5]}")
    print("-" * 60)
    print("Appuyez sur Ctrl+C pour quitter.")

if __name__ == '__main__':
    print("Initialisation du réseau DDS...")
    ChannelFactoryInitialize(0)
    
    # Abonnement au topic de retour d'effort des moteurs
    sub_state = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub_state.Init(state_callback, 10)
    
    # Abonnement au topic des capteurs de pression tactiles
    sub_touch = ChannelSubscriber("rt/inspire_hand/touch/r", inspire_dds.inspire_hand_touch)
    sub_touch.Init(touch_callback, 10)
    
    print("En attente des données du Driver...")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nFin de la lecture.")
