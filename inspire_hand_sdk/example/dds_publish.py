import time
import sys

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.utils.thread import Thread

from inspire_sdkpy import inspire_hand_defaut,inspire_dds
import numpy as np

if __name__ == '__main__':

    if len(sys.argv)>1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)
    # Créer un publisher pour publier les données définies dans la classe UserData
    pubr = ChannelPublisher("rt/inspire_hand/ctrl/r", inspire_dds.inspire_hand_ctrl)
    pubr.Init()

    publ = ChannelPublisher("rt/inspire_hand/ctrl/l", inspire_dds.inspire_hand_ctrl)
    publ.Init()
    cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
    short_value=1000


    cmd.angle_set=[0,0,0,0,1000,1000]
    cmd.mode=0b0001
    publ.Write(cmd)
    pubr.Write(cmd)

    time.sleep(1.0)

    cmd.angle_set=[0,0,0,0,0,1000]
    cmd.mode=0b0001
    publ.Write(cmd)
    pubr.Write(cmd)

    time.sleep(3.0)

    for cnd in range(100000):

            # Adresse de départ des registres, 0x05CE correspond à 1486
        start_address = 1486
        num_registers = 6  # 6 registres
        # Générer la liste des valeurs à écrire, chaque registre est une valeur short

        if (cnd+1) % 10 == 0:
            short_value = 1000-short_value  # Valeur short à écrire



        values_to_write = [short_value] * num_registers
        values_to_write[-1]=1000-values_to_write[-1]
        values_to_write[-2]=1000-values_to_write[-2]

        value_to_write_np=np.array(values_to_write)
        value_to_write_np=np.clip(value_to_write_np,200,800)
        # value_to_write_np[3]=800

        # Modes combinés implémentés en binaire :
        # mode 0 : 0000 (aucune opération)
        # mode 1 : 0001 (angle)
        # mode 2 : 0010 (position)
        # mode 3 : 0011 (angle + position)
        # mode 4 : 0100 (contrôle en force)
        # mode 5 : 0101 (angle + force)
        # mode 6 : 0110 (position + force)
        # mode 7 : 0111 (angle + position + force)
        # mode 8 : 1000 (vitesse)
        # mode 9 : 1001 (angle + vitesse)
        # mode 10 : 1010 (position + vitesse)
        # mode 11 : 1011 (angle + position + vitesse)
        # mode 12 : 1100 (force + vitesse)
        # mode 13 : 1101 (angle + force + vitesse)
        # mode 14 : 1110 (position + force + vitesse)
        # mode 15 : 1111 (angle + position + force + vitesse)
        cmd.angle_set=value_to_write_np.tolist()
        cmd.mode=0b0001
        # Publier le message
        if  publ.Write(cmd) and pubr.Write(cmd):
            # print("Publication réussie. msg:", cmd.crc)
            pass
        else:
            print("En attente d'un subscriber.")

        time.sleep(0.1)

