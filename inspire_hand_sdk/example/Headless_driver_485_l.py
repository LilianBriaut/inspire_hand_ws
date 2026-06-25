from inspire_sdkpy import inspire_sdk, inspire_hand_defaut
import time

if __name__ == "__main__":

    ## Publier toutes les données
    # states_structure = [
    #         ('pos_act', 1534, 6, 'short'),
    #         ('angle_act', 1546, 6, 'short'),
    #         ('force_act', 1582, 6, 'short'),
    #         ('current', 1594, 6, 'short'),
    #         ('err', 1606, 3, 'byte'),
    #         ('status', 1612, 3, 'byte'),
    #         ('temperature', 1618, 3, 'byte')
    #     ]

    ## Publier uniquement ces données pour augmenter la fréquence de publication
    states_structure = [
            ('angle_act', 1546, 6, 'short'),
            ('force_act', 1582, 6, 'short'),
            ('status', 1612, 3, 'byte'),
        ]

    handler = inspire_sdk.ModbusDataHandler(LR='l', device_id=2, use_serial=True, serial_port='/dev/ttyUSB0',states_structure=states_structure)

    call_count = 0  # Compteur d'appels
    start_time = time.perf_counter()  # Enregistrer le temps de début

    try:
        while True:
            data_dict = handler.read()  # Lire les données
            call_count += 1  # Incrémenter le compteur
            time.sleep(0.001)  # Pause de 1 ms

            # Calculer et afficher la fréquence toutes les 20 itérations
            if call_count % 20 == 0:
                elapsed_time = time.perf_counter() - start_time  # Calculer la durée totale
                frequency = call_count / elapsed_time  # Calculer la fréquence (Hz)
                print(f"Fréquence actuelle : {frequency:.2f} Hz, appels : {call_count}, durée : {elapsed_time:.6f} s")
    except KeyboardInterrupt:
        elapsed_time = time.perf_counter() - start_time  # Calculer la durée totale
        frequency = call_count / elapsed_time if elapsed_time > 0 else 0  # Calculer la fréquence finale
        print(f"Programme terminé. Appels totaux : {call_count}, durée totale : {elapsed_time:.6f} s, fréquence finale : {frequency:.2f} Hz")
