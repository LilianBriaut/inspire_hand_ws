# Protocole de Test - Inspire Hands (Ethernet)

Ce document récapitule la configuration réseau et les étapes pour tester et visualiser les deux mains Inspire connectées en Ethernet via le routeur.

---

## 1. Configuration Réseau

Pour que le PC et les deux mains communiquent sans conflit, les adresses IP physiques suivantes ont été configurées :

* **PC (Interface filaire `eno1`)** :
  * IP 1 : `192.168.11.100/24` (pour la configuration initiale d'usine)
  * IP 2 : `192.168.123.100/24` (sous-réseau opérationnel)
* **Main Droite (Right)** : `192.168.123.210`
* **Main Gauche (Left)** : `192.168.123.211`

> [!NOTE]
> Vous pouvez tester la connectivité des deux mains en lançant :
> ```bash
> ping 192.168.123.210  # Main Droite
> ping 192.168.123.211  # Main Gauche
> ```

---

## 2. Procédure de Test

Pour lancer les tests, vous devez toujours exporter la variable d'environnement Qt dans votre terminal actuel si vous utilisez l'interface graphique (PyQt5) sous Nix :

```bash
export QT_PLUGIN_PATH=$(nix eval --raw .#py-inspire-hand-ws.qt-env)
```

### Étape 1 : Démarrer le Driver de Pont (Modbus TCP <-> DDS)
Ce script fait le pont entre le protocole réseau ModbusTCP des mains et les messages DDS (utilisés par le robot H1). Il doit tourner en continu en arrière-plan pendant vos tests.

* **Option A : Mode Visuel (Recommandé - Affiche la télémétrie des deux mains)**
  ```bash
  nix shell --command python inspire_hand_sdk/example/Vision_driver_double.py
  ```
  *(La méthode de démarrage multi-processus a été configurée sur `spawn` pour éviter les conflits d'OpenGL/X11 entre les deux fenêtres).*

* **Option B : Mode Headless (Sans interface graphique - Affiche les fréquences dans le terminal)**
  ```bash
  nix shell --command python inspire_hand_sdk/example/Headless_driver_double.py
  ```

---

### Étape 2 : Faire bouger les mains (Publishing DDS)
Une fois le driver de pont lancé à l'Étape 1, ouvrez un **autre terminal** et lancez le script de contrôle pour envoyer des commandes cycliques d'ouverture/fermeture des doigts via DDS :

```bash
nix shell --command python inspire_hand_sdk/example/dds_publish.py
```

---

### Étape 3 : Visualiser les messages DDS (Subscribing DDS)
Pendant que le driver tourne, vous pouvez également lancer un outil de visualisation séparé qui s'abonne aux messages DDS publiés par les mains pour analyser le retour d'effort ou de position d'une main :

```bash
nix shell --command python inspire_hand_sdk/example/dds_subscribe.py
```
*(Par défaut, il s'abonne à la main droite `r`. Vous pouvez éditer la ligne `DDSHandler(LR='r')` tout en bas du script [dds_subscribe.py](file:///home/lilian/Documents/h1v2-imitation/inspire_hand_ws/inspire_hand_sdk/example/dds_subscribe.py) pour passer sur `'l'` pour la main gauche).*
