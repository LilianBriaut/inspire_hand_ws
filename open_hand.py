import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from inspire_sdkpy import inspire_hand_defaut, inspire_dds

if __name__ == '__main__':
    # Initialisation du réseau
    ChannelFactoryInitialize(0)
    pubr = ChannelPublisher("rt/inspire_hand/ctrl/r", inspire_dds.inspire_hand_ctrl)
    pubr.Init()
    
    cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
    cmd.mode = 1 # Mode "Angle"
    
    # Rappel des index des doigts : [Petit_doigt, Annulaire, Majeur, Index, Pouce_Flexion, Pouce_Rotation]
    # Valeurs possibles : 0 (Ouvert) à 1000 (Fermé)
    
    print("Ouverture de l'pink...")
    cmd.angle_set = [1000, 1000, 1000, 1000, 400, 1000] 
    
    for _ in range(5):
        pubr.Write(cmd)
        time.sleep(0.1)
        
    time.sleep(3.0) # On attend 3 secondes
    
    # print("Ouverture de l'index...")
    # cmd.angle_set = [0, 0, 0, 0, 0, 0] 
    
    # for _ in range(5):
    #     pubr.Write(cmd)
    #     time.sleep(0.1)
        
    # print("Terminé !")
