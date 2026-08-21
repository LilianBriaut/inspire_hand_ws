import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from inspire_sdkpy import inspire_hand_defaut, inspire_dds

driver_l_connected = True
driver_r_connected = True

def state_callback_l(msg):
    global driver_l_connected
    driver_l_connected = True

def state_callback_r(msg):
    global driver_r_connected
    driver_r_connected = True

if __name__ == '__main__':
    ChannelFactoryInitialize(0)

    sub_l = ChannelSubscriber("rt/inspire_hand/state/l", inspire_dds.inspire_hand_state)
    sub_l.Init(state_callback_l, 10)
    sub_r = ChannelSubscriber("rt/inspire_hand/state/r", inspire_dds.inspire_hand_state)
    sub_r.Init(state_callback_r, 10)

    publ = ChannelPublisher("rt/inspire_hand/ctrl/l", inspire_dds.inspire_hand_ctrl)
    publ.Init()
    pubr = ChannelPublisher("rt/inspire_hand/ctrl/r", inspire_dds.inspire_hand_ctrl)
    pubr.Init()

    cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
    cmd.mode = 1
    cmd.angle_set = [1000, 1000, 1000, 600, 500, 0]

    print("En attente des deux drivers...")
    while not (driver_l_connected and driver_r_connected):
        time.sleep(0.1)

    print("Les deux drivers trouvés ! Envoi...")
    for _ in range(5):
        publ.Write(cmd)
        pubr.Write(cmd)
        time.sleep(0.1)

    time.sleep(1.0)
    print("Terminé !")
