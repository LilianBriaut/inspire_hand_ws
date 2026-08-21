# inspire_hand_ws/ros2 — ROS 2 (Jazzy) pour l'Inspire Hand RH56DFTP

Workspace colcon exposant le contrôle moteur et la peau tactile de la main
RH56DFTP à ROS 2, **par-dessus le pipeline DDS existant** (driver Modbus→DDS
`inspire_hand_sdk`, jamais contourné : un seul chemin d'écriture vers le
hardware).

**Nœud ROS 2 classique, sans `ros2_control`.** On commande la main en publiant
une *position cible* (un `sensor_msgs/JointState` en radians) ; le bridge écrit
une seule commande DDS par message et c'est le **firmware de la main** qui
génère le mouvement fluide vers cette cible — exactement la logique de
`scripts/hand_teleop/open_hand.py`, mais exposée en ROS. Pas d'interpolation de
trajectoire côté ROS (c'était le rôle du JointTrajectoryController, retiré :
sur cette main il est redondant avec le firmware et rend le geste saccadé).

```
   commande (toi / script / MoveIt-exec adapté)              DDS (prod, inchangé)
┌──────────────────────┐  /rh56dftp/<side>/joint_command   ┌─────────────────┐
│  ros2 topic pub …     │──────────────────────────────────►│                 │
│  (JointState, %)      │                                   │   bridge_node   │  rt/inspire_hand/ctrl/{l,r}
└──────────────────────┘                                    │  (inspire_hand_ │─────────────────────────────►┌────────────────┐
                                                             │    bridge)      │◄─────────────────────────────│ inspire_hand_  │──► Modbus TCP
┌──────────────────────┐  /rh56dftp/<side>/joint_states     │                 │  rt/inspire_hand/state/{l,r} │ sdk (driver)   │    (main réelle)
│ robot_state_publisher │◄──────────────────────────────────│                 │◄─────────────────────────────│                │
│   → TF → RViz         │  (14 joints: actionnés+mimic+poignet)                │  rt/inspire_hand/touch/{l,r} └────────────────┘
└──────────────────────┘                                    └─────────────────┘
         /rh56dftp/tactile/<side>/<region>  (17 × Image mono16) ◄──────┘
```

## Packages

| Package | Contenu |
|---|---|
| `src/rh56dftp_description_ros2/` (nom ament : **`rh56dftp_description`**) | wrapper qui installe tel quel le package agnostique voisin `../rh56dftp_description` (URDF/meshes/tactile/config). Rend résolubles `$(find rh56dftp_description)` et `package://rh56dftp_description/...` sans modifier le package validé. |
| `src/inspire_hand_bridge/` | nœud bridge DDS↔ROS 2 (Python), launch. |

Plus de dépendance source : `deps.repos` est vide (les checkouts `ros2_control`
ont été retirés avec l'abandon de `ros2_control`).

## Build

```bash
cd inspire_hand_ws/ros2
source /opt/ros/jazzy/setup.bash        # hors venv h1v2 ! (python 3.12)
colcon build --symlink-install --cmake-args -DBUILD_TESTING=OFF
```

Dépendances Python hors rosdep (une fois) :

```bash
./src/inspire_hand_bridge/scripts/setup_py312_dds.sh
export CYCLONEDDS_HOME=$HOME/.local/opt/cyclonedds-ros-shim   # à mettre en .bashrc
```

⚠️ **Versions cyclonedds — ne pas « simplifier »** : le binding Python est
volontairement compilé (sdist 0.10.2) contre la `libddsc` **livrée par ROS
Jazzy** (0.10.5). Deux raisons vérifiées expérimentalement :
1. `pip install cyclonedds` (11.x, seule roue cp312) fait **segfaulter par
   simple découverte** les participants 0.10.x — donc le driver de prod
   (`ddsi_xt_type_init_impl`, XTypes).
2. Le process du bridge héberge aussi `rmw_cyclonedds_cpp` : deux `libddsc`
   différentes dans un même process crashent (assertion iceoryx dans
   `dds_write.c`). Une seule lib partagée = build contre celle de ROS.

## Lancer

```bash
source /opt/ros/jazzy/setup.bash && source install/setup.bash
export CYCLONEDDS_HOME=$HOME/.local/opt/cyclonedds-ros-shim

ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left
# ou les deux mains :
ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=right   # 2e terminal
```

Le launch ne démarre que deux nœuds : `robot_state_publisher` (URDF→TF) et
`bridge_node`. Si `ros2 launch` n'existe pas (plugin CLI non installé) :

```bash
python3 install/inspire_hand_bridge/share/inspire_hand_bridge/scripts/run_launch.py side:=left
```

### Visualiser dans RViz (modèle + tactile)

```bash
ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left rviz:=true
```

`rviz:=true` ajoute deux nœuds : `tactile_cloud_node`, qui fusionne les 17 topics
`Image` en un unique `PointCloud2` colorié (bleu = pas de contact → rouge =
saturation) exprimé dans `<side>_hand_root`, et `rviz2` chargé avec
`rviz/tactile_<side>.rviz` (RobotModel + TF + PointCloud2). Le nuage sort sur
`/rh56dftp/tactile/<side>/cloud`.

Le nuage seul, sans RViz (pour l'enregistrer dans un bag par exemple) :

```bash
ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left tactile_cloud:=true
```

Paramètre utile : `pressure_max` (défaut `200`) borne l'échelle de couleur en
counts bruts. Si tous les taxels saturent en rouge, augmente-le ; s'ils restent
bleus, baisse-le.

Le nuage est **posé sur la surface des pads** : chaque frame `_touch` porte une
pose dérivée des meshes (Z = normale de surface) et la grille est dimensionnée à
l'emprise réelle du pad — pas un pas uniforme. Source :
`rh56dftp_description/tactile/pad_geometry.yaml` (généré par
`tools/estimate_tactile_frames.py`, baké dans les `<origin>` par `tools/build.py`).
Précision : sub-mm sur les bouts de doigts, ~1–2 mm sur les phalanges, jusqu'à
~1,5 cm aux coins de la paume (grille plane approximant une surface courbe).

> Il faut que le **driver DDS de la main tourne**. `bridge_node` ne publie
> `/joint_states` que lorsqu'il reçoit un état sur `rt/inspire_hand/state/{l,r}` ;
> or les frames tactiles sont chacune derrière 4 joints mobiles (poignet + 2
> phalanges du doigt), donc sans `/joint_states` `robot_state_publisher` ne place
> ni les doigts ni les pads, et RViz affiche « No transform ». De même les points
> tactiles viennent de `rt/inspire_hand/touch/{l,r}`. Bref, sans main réelle
> connectée, RViz reste quasi vide — c'est attendu.

### Commander la main

`position` est un **pourcentage d'ouverture** dans `[0, 100]` : `0` = fermé,
`100` = grand ouvert. C'est exactement `angle_set / 10` (registre Inspire).

```bash
# ouvre l'index, ferme les 3 autres doigts, pouce en opposition (mêmes valeurs
# que open_hand.py : angle_set [0,0,0,1000,100,1000])
ros2 topic pub --once /rh56dftp/left/joint_command sensor_msgs/msg/JointState '{
  name:     [left_little_1_joint, left_ring_1_joint, left_middle_1_joint, left_index_1_joint, left_thumb_2_joint, left_thumb_1_joint],
  position: [0,                   0,                 0,                   100,                10,                 100]
}'
```

Commande partielle possible (un seul doigt) : les autres joints tiennent leur
position courante — le nœud amorce ses cibles à partir du premier état mesuré.
Envoie les 6 joints pour un contrôle pleinement déterministe.

```bash
# ferme l'index à moitié, laisse le reste où il est
ros2 topic pub --once /rh56dftp/left/joint_command sensor_msgs/msg/JointState \
  '{name: [left_index_1_joint], position: [50]}'
```

> **Attention** — `joint_command` prenait des radians avant ; il prend maintenant
> des pourcentages. Les anciennes commandes en radians restent numériquement dans
> `[0, 100]` et sont donc acceptées **sans erreur**, avec un sens inversé : `0.0`
> voulait dire « grand ouvert », il veut maintenant dire « fermé ». Relis tes
> scripts et tes bags avant de rejouer quoi que ce soit.

### Topics (par main)

- `/rh56dftp/<side>/joint_command` — **commande** : `sensor_msgs/JointState`,
  `position` = pourcentage d'ouverture `[0, 100]` (0 = fermé, 100 = ouvert),
  apparié par nom (6 joints actionnés ; mimic et poignets ignorés s'ils sont
  présents). Hors bornes → clampé + WARN. Une commande = une écriture DDS.
- `/rh56dftp/<side>/joint_states` — **état complet** : `sensor_msgs/JointState`
  des 14 joints (6 actionnés depuis les registres + 6 mimic calculés depuis
  l'URDF + 2 poignets à 0), publié par le nœud lui-même (plus de
  `joint_state_broadcaster`). Consommé par `robot_state_publisher` → TF → RViz.
- `/rh56dftp/tactile/<side>/<region>` — 17 topics `sensor_msgs/Image`
  `mono16` (grille = `grid` de `tactile_layout.yaml`, `frame_id` =
  `<side>_<region>_touch`, frame présente dans le TF). QoS/fréquence
  réglables par région via les params `tactile.<region>.{reliability,depth,throttle_hz}`
  du nœud bridge.
- `/rh56dftp/tactile/<side>/cloud` — `sensor_msgs/PointCloud2` (XYZ+RGB), fusion
  des 17 régions dans `<side>_hand_root`. Publié uniquement si
  `tactile_cloud:=true` ou `rviz:=true`. C'est ce que la config RViz affiche.

`/tf` et `/tf_static` restent **globaux** (tf2 utilise des noms absolus) ; seul
`robot_description` est namespacé, d'où le topic absolu dans les configs RViz.

### Conversion d'unités

Trois unités, deux ancres. Les ancres sont les limites URDF du joint :
`lower` = ouvert, `upper` = fermé. Tout est linéaire entre les deux.

| Unité | Ouvert | Fermé | Où |
|---|---|---|---|
| registre Inspire `angle_set` | `1000` | `0` | DDS |
| ouverture % | `100` | `0` | `joint_command` |
| radians URDF | `lower` (0) | `upper` | `joint_states`, TF |

Le pourcentage existe parce que `upper` **diffère par joint** — `1.3443` rad pour
les quatre doigts longs, `1.3104` pour `thumb_1`, `0.5235` pour `thumb_2` : « fermé »
n'a pas de valeur unique en radians, ce qui rend les commandes à la main pénibles.
L'état reste en radians car `robot_state_publisher` l'exige ; l'asymétrie
commande (%) / état (rad) est donc voulue.

Attention au sens : `InspireHand_policy._compute_hand_cmd` (téléop) manipule un
`closure_cmd` **inverse** (0 = ouvert, 1 = fermé), qu'il invertit avant l'`angle_set`.

Sources de vérité : `rh56dftp_description/config/actuator_mapping.yaml` + URDF
(parsés au démarrage, aucune table dupliquée). Les mimic (multiplicateur/offset)
sont lus directement dans les balises `<mimic>` de l'URDF.

## Notes / limitations connues

- Les WARN `Failed to parse type hash ... rt/inspire_hand/...` émis par
  `rmw_cyclonedds_cpp` sont **bénins** : le rmw découvre les topics DDS bruts
  (non-ROS) du driver et ne sait pas les hasher. Ignorer.
- `~/.ros/cyclonedds_unicast.xml` (via `CYCLONEDDS_URI`) référence l'interface
  robot `enx387c76150b3f` : participant DDS du bridge en échec si le câble
  n'est pas branché. Pour les tests sans robot : `unset CYCLONEDDS_URI`.
  (Le driver unitree auto-détermine son interface et ignore cette variable.)
- `thumb_rot` (registre 5) : mapping linéaire nominal sur les limites URDF de
  `thumb_1_joint` ; le sens/plage réels sur le hardware restent à valider (la
  téléop borne ce registre à [400,1000] côté exosquelette).
- Pas de trajectoire côté ROS : si tu as besoin d'exécuter une trajectoire
  MoveIt sur la main, il faudrait ajouter un serveur d'action
  `FollowJointTrajectory` (ou réintroduire `ros2_control` + JointTrajectory-
  Controller). Retiré ici volontairement : sur cette main, le firmware fait
  déjà la génération de mouvement, et le JTC dégradait la fluidité
  (ré-échantillonnage 100 Hz + quantification sur 1000 pas).

## Provenance (vendored / dépendance / neuf)

- **Neuf** (ce dépôt) : `inspire_hand_bridge` (nœud, launch),
  wrapper `rh56dftp_description_ros2`.
- **Dépendances non modifiées** : `inspire_sdkpy` (BSD-3),
  `cyclonedds` 0.10.2 (EPL-2.0/BSD-3).
- **Vendored** : rien de nouveau (le seul vendoring du workspace reste
  `rh56dftp_description`, cf. son `NOTICE`).

Détails licences : [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
