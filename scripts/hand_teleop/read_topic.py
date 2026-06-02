import time
import sys
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from inspire_sdkpy import inspire_dds

def state_callback(msg: inspire_dds.inspire_hand_state):
    print("--- NOUVEAU MESSAGE (STATE) ---")
    print(f"Position actuelle : {msg.pos_act}")
    print(f"Angle actuel      : {msg.angle_act}")
    print(f"Force actuelle    : {msg.force_act}")
    print(f"Température       : {msg.temperature}")
    print(f"Statut            : {msg.status}")
    print(f"Erreur            : {msg.err}")
    print("-------------------------------\n")

if __name__ == '__main__':
    print("Initialisation du réseau DDS...")
    ChannelFactoryInitialize(0)
    
    # On s'abonne au topic de la main droite (rt/inspire_hand/state/r)
    sub = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub.Init(state_callback, 10)
    
    print("En écoute sur le topic 'rt/inspire_hand/state/r'...")
    print("Appuyez sur Ctrl+C pour quitter.")
    
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Fin de l'écoute.")
