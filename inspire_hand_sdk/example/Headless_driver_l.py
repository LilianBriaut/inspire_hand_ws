# from inspire_dds import inspire_hand_touch,inspire_hand_ctrl,inspire_hand_state
# from inspire_dds import inspire_hand_touch,inspire_hand_ctrl,inspire_hand_state
import sys
from inspire_sdkpy import inspire_sdk,inspire_hand_defaut
import time
# import inspire_sdkpy
if __name__ == "__main__":


    # handler=inspire_sdk.ModbusDataHandler(ip=inspire_hand_defaut.defaut_ip,LR='r',device_id=1)
    handler=inspire_sdk.ModbusDataHandler(ip='192.168.123.211',LR='l',device_id=1)
    time.sleep(0.5)

    call_count = 0  # Compteur d'appels
    start_time = time.perf_counter()  # Enregistrer le temps de début

    try:
        while True:
            data_dict = handler.read()  # Lire les données

            call_count += 1  # Incrémenter le compteur
            time.sleep(0.001)  # Pause de 1 ms

            # Calculer et afficher la fréquence toutes les 10 itérations
            if call_count % 10 == 0:
                elapsed_time = time.perf_counter() - start_time  # Calculer la durée totale
                frequency = call_count / elapsed_time  # Calculer la fréquence (Hz)
                print(f"Fréquence actuelle : {frequency:.2f} Hz, appels : {call_count}, durée : {elapsed_time:.6f} s")
    except KeyboardInterrupt:
        elapsed_time = time.perf_counter() - start_time  # Calculer la durée totale
        frequency = call_count / elapsed_time if elapsed_time > 0 else 0  # Calculer la fréquence finale
        print(f"Programme terminé. Appels totaux : {call_count}, durée totale : {elapsed_time:.6f} s, fréquence finale : {frequency:.2f} Hz")
