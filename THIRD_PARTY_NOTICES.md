# THIRD_PARTY_NOTICES — inspire_hand_ws

Trace auditable des sources externes utilisées dans ce workspace : ce qui est
**vendored** (copié dans le dépôt, avec adaptation éventuelle), ce qui est une
**dépendance** (consommée sans copie), et les vérifications de licences.
Politique : cf. `docs/ros.md` §4–5 du dépôt parent `h1v2-imitation`.

Dernière mise à jour : **2026-07-02**. Licences vérifiées via l'API GitHub
(`GET /repos/<owner>/<repo>`, champ `license.spdx_id`) et lecture des fichiers
`LICENSE`/`package.xml`/`setup.py` locaux.

---

## 1. Vendored (code copié dans le dépôt)

| Source | Copié dans | Licence | Vérifiée | Récupéré |
|---|---|---|---|---|
| [ookkshirsagar/rh56dfx_description](https://github.com/ookkshirsagar/rh56dfx_description) | `rh56dftp_description/` (meshes verbatim, xacro adaptés) | **MIT** | ✅ API GitHub 2026-07-02 (`MIT`) + `LICENSE` local | 2026-07-01 |

Détail fichier par fichier : `rh56dftp_description/NOTICE`.
Le wrapper ament `ros2/src/rh56dftp_description_ros2/` ne copie rien : il
installe le contenu du package agnostique tel quel au build.

Aucun autre code externe n'a été vendored. En particulier, **rien** n'a été
repris de `renesas-rdk/inspire_rh56_hand_ros2_control` (aucune licence
publiée — vérifié 2026-07-02, `license: null` — donc invendorable) ni de
`tonydle/OnRobot_ROS2_Driver` / `ABC-iRobotics/onrobot-ros2` (MIT, servis de
références de lecture uniquement, zéro copie).

## 2. Dépendances (consommées sans copie)

| Dépendance | Rôle | Mode | Licence | Vérifiée |
|---|---|---|---|---|
| [ros-controls/topic_based_hardware_interfaces](https://github.com/ros-controls/topic_based_hardware_interfaces) (`joint_state_topic_hardware_interface`) | plugin `ros2_control` (hardware interface par topics) | binaire apt `ros-jazzy-joint-state-topic-hardware-interface` si dispo, sinon source via `ros2/deps.repos` (commit épinglé `144e3e9`) | **Apache-2.0** | ✅ API GitHub + `LICENSE`/`package.xml` du checkout, 2026-07-02 |
| [ros-controls/ros2_control_cmake](https://github.com/ros-controls/ros2_control_cmake) | macros CMake requises au build source du plugin | source via `ros2/deps.repos` (commit `3379ea2`) | **Apache-2.0** | ✅ API GitHub 2026-07-02 |
| `inspire_hand_sdk` / `inspire_sdkpy` (ce workspace, driver Modbus→DDS de prod) | types DDS + driver — **non modifié** | install pip editable (`--no-deps`) | **BSD-3-Clause** | ✅ `setup.py` local (`license="BSD-3-Clause"`, author Unitree) |
| [eclipse-cyclonedds/cyclonedds-python](https://github.com/eclipse-cyclonedds/cyclonedds-python) `cyclonedds==0.10.2` | binding DDS Python du bridge | pip (sdist compilé contre la libddsc de ROS Jazzy) | **EPL-2.0 OR BSD-3-Clause** (en-têtes sources) | ✅ en-têtes du sdist, 2026-07-02 |

## 3. Corrections par rapport à `docs/ros.md` §3

- `topic_based_hardware_interfaces` : la licence réelle est **Apache-2.0**,
  pas BSD 3-Clause comme indiqué (la table §3 disait « ✅ confirmée BSD-3 »).
- `yuzhench/inspire-hand-rh56-py` : **MIT** (⚠️ levée). N'est de toute façon
  plus une dépendance du bridge : le chemin retenu est DDS via
  `inspire_sdkpy`, pas Modbus direct (cf.
  `docs/prompt_ros2_rh56dftp_bridge.md`, point corrigé).
- `ookkshirsagar/rh56dfx_description` : **MIT** (⚠️ levée).
- `tonydle/OnRobot_ROS2_Driver` : **MIT** (⚠️ levée ; référence seulement).
- `renesas-rdk/inspire_rh56_hand_ros2_control` : **aucune licence** (⚠️
  confirmée bloquante pour tout vendoring — rien n'en est utilisé).
- Meshes Inspire officielles (CC BY-NC-SA) : sans objet ici — les meshes
  utilisées viennent de `rh56dfx_description` (MIT). La question d'une
  dérivation CAD amont reste ouverte côté upstream (cf. `docs/ros.md` §6.2).
