# rh56dftp_description

Framework-agnostic description of the **Inspire Hand RH56DFTP** (tactile variant):
URDF / xacro / meshes for the 6-DOF hand, plus a representation of the tactile
sensor skin (17 regions, 1062 taxels) as URDF frames.

It is intentionally **not** a ROS 2 (ament) package — the parent project
`h1v2-imitation` is DDS-based and uses **Pinocchio/Pink + MuJoCo**, so this
package ships plain, pre-expanded URDFs consumable directly by those tools
(and by RViz via the xacro), with no ROS dependency.

> The RH56DFTP motor **and tactile** data are already exposed over DDS by the
> driver in [`../inspire_hand_sdk`](../inspire_hand_sdk) (topics
> `rt/inspire_hand/{ctrl,state,touch}/{l,r}`) and consumed by
> `packages/robot_deploy/.../InspireHand_policy.py`. This package adds the
> **geometric description** that was missing, not a new driver.

## Sources & attribution

| Source | Used for | License |
| --- | --- | --- |
| [ookkshirsagar/rh56dfx_description](https://github.com/ookkshirsagar/rh56dfx_description) | URDF/xacro + meshes (RH56DFX shares RH56DFTP kinematics) | MIT — see [LICENSE](LICENSE) |
| [yuzhench/inspire-hand-rh56-py](https://github.com/yuzhench/inspire-hand-rh56-py) | RH56DFTP tactile protocol **reference only** (no code copied) | — |

Full per-file attribution is in [NOTICE](NOTICE). We do **not** fork
`rh56dfx_description`: the scope diverges (DFX has no tactile sensor).

## Layout

```
rh56dftp_description/
├── urdf/
│   ├── rh56dftp_macro.xacro     # kinematics (adapted from rh56dfx_macro.xacro)
│   ├── tactile_frames.xacro     # GENERATED — 17 tactile frames (macro)
│   ├── rh56dftp.xacro           # top-level: hand + tactile frames
│   ├── rh56dftp_left.urdf        # GENERATED — plain URDF, relative mesh paths
│   └── rh56dftp_right.urdf       # GENERATED
├── meshes/{left,right}/{visual,collision}/*.STL   # reused verbatim
├── tactile/tactile_layout.yaml  # CANONICAL 17-region tactile map (source of truth)
├── config/actuator_mapping.yaml # URDF joints <-> Inspire DDS register order
├── tools/build.py               # regenerates the GENERATED files (no ROS needed)
├── LICENSE  NOTICE  README.md
```

## Usage

**Pinocchio / MuJoCo (no ROS):** load the pre-expanded URDF directly.
```python
import pinocchio as pin
model = pin.buildModelFromUrdf("urdf/rh56dftp_left.urdf")   # mesh paths are ../meshes/left/...
```
Mesh paths are relative to `urdf/`. Regenerate with a different root (e.g. absolute,
or `package://…` for ROS) via `tools/build.py expand --mesh-root <ROOT>`.

**RViz / ROS xacro (optional):** expand `urdf/rh56dftp.xacro` with the standard
`xacro` tool using `side:=left prefix:=left_` (prefix must equal `<side>_`).

**Regenerate GENERATED artifacts** after editing `tactile/tactile_layout.yaml`:
```bash
python3 tools/build.py all      # frames + both URDFs  (or: --check, frames, expand)
```

## Kinematics

6 actuated finger DOF + 2 wrist DOF (8 total), 6 coupled distal joints via URDF
`<mimic>`. Never command mimic joints directly. See
[config/actuator_mapping.yaml](config/actuator_mapping.yaml) for the
URDF-joint ↔ Inspire DDS register-index mapping
(`[pinky, ring, middle, index, thumb_bend, thumb_rot]`).

## Tactile frames

Each of the 17 regions in [tactile/tactile_layout.yaml](tactile/tactile_layout.yaml)
becomes a fixed frame `<prefix><region>_touch` (e.g. `left_index_top_touch`)
anchored on the closest existing link (`_tip`/`_2`/`_1`/`palm`…). The YAML records,
per region: DDS field, grid `(rows, cols)`, taxel count and Modbus address — so a
DDS consumer can map each published matrix onto a 3D frame.

- **Total taxels = 1062** (matches the SDK register map and `inspire_hand_touch.idl`).
- ⚠️ The project brief quotes **1185** cells; that figure does not match the shipped
  register map. We follow the SDK (1062) and flag 1185 for hardware-datasheet
  verification (`../inspire_R1/*.pdf`).
- **Frame placement is nominal** (frame at the parent-link origin). Precise
  per-pad metric pose/orientation is deferred refinement pending the RH56DFTP
  datasheet geometry.

## What was reused / modified / added (vs. rh56dfx_description)

- **Reused verbatim:** all left/right visual + collision STL meshes.
- **Modified:** `rh56dftp_macro.xacro` (renamed macro + mesh path; CRLF→LF;
  removed a stray `ac` token) — *kinematics unchanged*; `rh56dftp.xacro`
  (renamed, fixed the world-link child ref, default `prefix=<side>_`).
- **Not carried over:** the ROS2/ament layer (package.xml, CMakeLists, launch,
  ros2_control, MoveIt configs) — this package is framework-agnostic by design.
- **Added (original):** `tactile_frames.xacro`, `tactile_layout.yaml`,
  `actuator_mapping.yaml`, `tools/build.py`, the two pre-expanded URDFs,
  this README and NOTICE.
