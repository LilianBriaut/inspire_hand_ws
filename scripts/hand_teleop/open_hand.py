import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from inspire_sdkpy import inspire_hand_defaut, inspire_dds

driver_connected = False

def state_callback(msg: inspire_dds.inspire_hand_state):
    global driver_connected
    driver_connected = True

if __name__ == '__main__':
    # Initialisation du réseau
    ChannelFactoryInitialize(0)
    
    sub = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub.Init(state_callback, 10)
    
    pubr = ChannelPublisher("rt/inspire_hand/ctrl/r", inspire_dds.inspire_hand_ctrl)
    pubr.Init()
    
    cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
    cmd.mode = 1 # Mode "Angle"
    cmd.angle_set = [1000, 1000, 1000, 1000, 1000, 1000] #470 alentour de 400
    
    print("En attente de la connexion avec le Driver (écoute de rt/inspire_hand/state/r)...")
    
    # On attend de recevoir au moins un message d'état du Driver
    while not driver_connected:
        time.sleep(0.1)
        
    print("Driver trouvé ! Envoi de la commande...")
    
    # Envoi de la commande
    for _ in range(5):
        pubr.Write(cmd)
        time.sleep(0.1)
        
    time.sleep(1.0)
    print("Terminé !")
