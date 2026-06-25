from pymodbus.client import ModbusTcpClient
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel
from pymodbus.exceptions import ConnectionException

from inspire_sdkpy import defaut_ip

registers = {
    1000: {"name": "HAND_ID", "description": "ID de la main dextre", "length": 1},
    1002: {"name": "REDU_RATIO", "description": "Paramètre de baudrate", "length": 1},
    1032: {"name": "DEFAULT_SPEED_SET", "description": "Vitesse à la mise sous tension pour chaque DDL", "length": 6},
    1044: {"name": "DEFAULT_FORCE_SET", "description": "Seuil de contrôle en force à la mise sous tension pour chaque DDL", "length": 6},
    1700: {"name": "ip", "description": "Partie IP", "length": 2},
}

register_set={
    1005: {"name": "SAVE", "description": "Sauvegarder les données en Flash", "length": 1},
    1006: {"name": "RESET_PARA", "description": "Réinitialiser les paramètres d'usine", "length": 1},
    1009: {"name": "GESTURE_FORCE_CLB", "description": "Calibration du capteur de force", "length": 1}

}

baud_rates = {
    0: 115200,
    1: 57600,
    2: 19200,
    3: 921600
}
baud_rates_reverse = {value: key for key, value in baud_rates.items()}



class ModbusHandler:
    def __init__(self, ip, port, id=1):
        self.client = ModbusTcpClient(ip, port)
        try:
            if not self.client.connect():
                raise ConnectionException(f"Impossible de se connecter au dispositif : {ip}:{port}")
            print(f"Connexion réussie : {ip}:{port}, ID : {id}")
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            self.client = None  # Mettre à None pour vérifier la connexion ultérieurement
        self.id = id

    def read_register(self, address, count):
        response = self.client.read_holding_registers(address, count,self.id)
        if response.isError():
            print("Erreur de lecture du registre :", response)
            return None
        return response.registers

    def write_register(self, address, value):
        response = self.client.write_register(address, value,self.id)
        if response.isError():
            print("Erreur d'écriture du registre :", response)
            return False
        return True
    def write_registers(self, address, value):
        response = self.client.write_registers(address, value,self.id)
        if response.isError():
            print("Erreur d'écriture des registres :", response)
            return False
        return True

    def close(self):
        if self.client:
            self.client.close()
            print("Connexion fermée")

class MainWindow(QMainWindow):
    def __init__(self,ip=defaut_ip,port=6000):
        super().__init__()
        self.id=self.find_online_devices(ip,port)
        self.modbus = ModbusHandler(ip, port,self.id)  # Remplacer par l'IP et le port réels
        self.initUI()
        self.read_registers()

    def find_online_devices(self,ip=defaut_ip,port=6000):
        for i in range(100):  # Plage d'ID supposée : 0 à 99
            self.modbus = ModbusHandler(ip, port,i)  # Remplacer par l'IP et le port réels
            res = self.modbus.read_register(1000, 1)  # Tentative de lecture du registre 1000
            device_id = 0
            if res is not None:
                device_id = res[0]
                print(f'Dispositif en ligne trouvé : ID = {device_id}')
            else:
                print(f'Aucun dispositif trouvé : ID = {i}')
            self.modbus.close()  # Fermer la connexion
            return device_id

    def initUI(self):
        self.setWindowTitle('Paramètres de la main dextre')

        layout = QVBoxLayout()

        read_button = QPushButton('Lire les paramètres')
        read_button.clicked.connect(self.read_registers)
        layout.addWidget(read_button)

        write_button = QPushButton('Écrire les paramètres')
        write_button.clicked.connect(self.save_registers)
        layout.addWidget(write_button)

        save_button = QPushButton('Sauvegarder les paramètres')
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button)

        reset_button = QPushButton('Réinitialiser les paramètres d\'usine')
        reset_button.clicked.connect(self.reset_para)
        layout.addWidget(reset_button)

        clb_button = QPushButton('Calibrer le capteur de force')
        clb_button.clicked.connect(self.cesture_force_clb)
        layout.addWidget(clb_button)

        clean_button = QPushButton('Effacer les erreurs')
        clean_button.clicked.connect(self.clean_error)
        layout.addWidget(clean_button)

        self.register_inputs = {}
        for i ,(address, info) in enumerate(registers.items()):
            layout.addWidget(QLabel(info['description']))
            if not info['name']=='ip':
                inputs = [QLineEdit() for _ in range(info['length'])]
            else :
                inputs = [QLineEdit() for _ in range(info['length']*2)]

            for input_field in inputs:
                layout.addWidget(input_field)
            self.register_inputs[address]=inputs

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.show()
    def save(self):
        self.modbus.write_register(1005, 1)
        print("Registre de sauvegarde des paramètres")

        pass

    def reset_para(self):
        self.modbus.write_register(1006, 1)
        pass

    def cesture_force_clb(self):
        self.modbus.write_registers(1486,[1000]*6)
        self.modbus.write_register(1009,1)
        pass
    def clean_error(self):
        self.modbus.write_register(1004,1)

    def read_registers(self):
        print("Lecture de tous les paramètres")
        for address, info in registers.items():
            if info["length"] == 1:
                values = self.modbus.read_register(address, info["length"] )
                if values is not None:
                    if info['name']=='REDU_RATIO':
                        self.register_inputs[address][0].setText(str(baud_rates[values[0]]))  # Un seul champ par registre
                    else:
                        self.register_inputs[address][0].setText(str(values[0]))  # Un seul champ par registre
            elif info["length"] == 6:
                values = self.modbus.read_register(address, info["length"] )
                if values is not None:
                    for j in range(6):
                        self.register_inputs[address][j].setText(str(values[j]))
            elif info['name']=='ip':
                values = self.modbus.read_register(address, 2)
                print(f'Registre IP : {values}')
                values = self.read_and_parse_ip(values)
                if values is not None:
                    for j in range(4):
                        self.register_inputs[address][j].setText(str(values[j]))

            print(f'Registre : {info["name"]} = {values}')

    def read_and_parse_ip(self,values):
        if values is not None and len(values) == 2:
            byte1 = values[0] & 0xFF
            byte2 = (values[0] >> 8) & 0xFF
            byte3 = values[1] & 0xFF
            byte4 = (values[1] >> 8) & 0xFF

            ip_bytes = [byte1, byte2, byte3, byte4]
            return ip_bytes
        else:
            print('Échec de lecture ou valeur de retour incorrecte')
            return None
    def bytes_to_short(self, values):
        # Combiner 4 octets en 2 short (octet de poids fort en premier)
        short1 = (values[1] << 8) | values[0]
        short2 = (values[3] << 8) | values[2]
        return [short1, short2]

    def save_registers(self):
        for address, info in registers.items():
            if info["length"] == 1:
                if info['name']=='REDU_RATIO':
                    value = baud_rates_reverse[int(self.register_inputs[address][0].text())]
                else:
                    value = int(self.register_inputs[address][0].text())

                self.modbus.write_register(address, value)
            elif info["length"] == 6:
                values = [int(input_field.text()) for input_field in self.register_inputs[address]]
                self.modbus.write_registers(address,values)
            elif info['name']=='ip':
                values = [int(input_field.text()) for input_field in self.register_inputs[address]]
                values=self.bytes_to_short(values)
                print(f'Écriture IP : {self.read_and_parse_ip(values)}, registres : {values}')
                self.modbus.write_registers(address,values)


            pass
        print("Écriture de tous les paramètres")


    def closeEvent(self, event):
        self.modbus.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # window = MainWindow(ip=defaut_ip)
    window = MainWindow(ip='192.168.123.211')
    sys.exit(app.exec_())
