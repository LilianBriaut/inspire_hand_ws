"""URDF joints <-> Inspire DDS register mapping and unit conversion.

Single sources of truth (installed by the rh56dftp_description wrapper):
  - config/actuator_mapping.yaml : DDS register index (0..5) -> URDF joint suffix
  - urdf/rh56dftp_<side>.urdf    : joint position limits (radians) + <mimic> tags

Register convention (Inspire ANGLE_SET/ANGLE_ACT, order
[pinky, ring, middle, index, thumb_bend, thumb_rot]):
  1000 = fully open, 0 = fully closed.
URDF convention: lower limit (0) = open, upper limit = closed (flexion).
The conversion is linear between those two anchors — the same approximation
used by the existing teleop pipeline (InspireHand_policy._compute_hand_cmd).

Beyond the 6 actuated joints, the hand has coupled distal phalanges declared
as URDF <mimic> joints and two non-actuated wrist joints. Without ros2_control
there is no joint_state_broadcaster to fill those in, so this module also
computes the full joint state (actuated + mimic + wrist) that the bridge
publishes on /joint_states for robot_state_publisher / TF / RViz.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTER_COUNT = 6
REGISTER_MAX = 1000


@dataclass(frozen=True)
class RegisterJoint:
    register: int
    joint: str  # full URDF joint name, prefix included
    lower: float  # rad, open
    upper: float  # rad, closed


class HandMapping:
    def __init__(self, description_share: str | Path, side: str, prefix: str | None = None):
        share = Path(description_share)
        prefix = prefix if prefix is not None else f"{side}_"

        mapping_yaml = share / "config" / "actuator_mapping.yaml"
        with open(mapping_yaml) as f:
            mapping = yaml.safe_load(f)
        register_to_suffix: dict[int, str] = mapping["inspire_register_to_joint"]

        urdf_path = share / "urdf" / f"rh56dftp_{side}.urdf"
        limits, mimics, mimic_order = self._parse_joints(urdf_path)

        self.joints: list[RegisterJoint] = []
        for register in range(REGISTER_COUNT):
            name = prefix + register_to_suffix[register]
            if name not in limits:
                raise KeyError(f"Joint {name!r} (register {register}) not found in {urdf_path}")
            lower, upper = limits[name]
            self.joints.append(RegisterJoint(register, name, lower, upper))

        self.joint_names: list[str] = [j.joint for j in self.joints]
        self._by_name: dict[str, RegisterJoint] = {j.joint: j for j in self.joints}

        # name -> (source_joint, multiplier, offset), parsed from URDF <mimic> tags.
        self._mimics: dict[str, tuple[str, float, float]] = mimics

        # Non-actuated wrist DOF (state-only, held at 0), full names present in the URDF.
        non_inspire_suffixes: list[str] = list(mapping.get("non_inspire_joints", []))
        self._non_inspire_full: list[str] = [
            prefix + s for s in non_inspire_suffixes if (prefix + s) in limits
        ]

        # Full joint list for /joint_states, in a stable order:
        # 6 actuated (register order), then mimic joints (URDF order), then wrist.
        self.all_joint_names: list[str] = (
            list(self.joint_names) + list(mimic_order) + list(self._non_inspire_full)
        )

    @staticmethod
    def _parse_joints(
        urdf_path: Path,
    ) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[str, float, float]], list[str]]:
        """Parse movable joints: their (lower, upper) limits and any <mimic> coupling."""
        limits: dict[str, tuple[float, float]] = {}
        mimics: dict[str, tuple[str, float, float]] = {}
        mimic_order: list[str] = []
        root = ET.parse(urdf_path).getroot()
        for joint in root.iter("joint"):
            if joint.get("type") not in ("revolute", "prismatic"):
                continue
            name = joint.get("name")
            limit = joint.find("limit")
            if limit is not None:
                limits[name] = (float(limit.get("lower")), float(limit.get("upper")))
            mimic = joint.find("mimic")
            if mimic is not None:
                source = mimic.get("joint")
                multiplier = float(mimic.get("multiplier", 1.0))
                offset = float(mimic.get("offset", 0.0))
                mimics[name] = (source, multiplier, offset)
                mimic_order.append(name)
        return limits, mimics, mimic_order

    def radians_to_registers(self, positions: dict[str, float]) -> list[int] | None:
        """Map {joint_name: rad} -> ANGLE_SET[6]. None if any of the 6 joints is missing."""
        registers = [0] * REGISTER_COUNT
        for entry in self.joints:
            q = positions.get(entry.joint)
            if q is None:
                return None
            span = entry.upper - entry.lower
            ratio = (entry.upper - q) / span  # 1.0 at lower/open, 0.0 at upper/closed
            reg = round(ratio * REGISTER_MAX)
            registers[entry.register] = min(max(reg, 0), REGISTER_MAX)
        return registers

    def registers_to_radians(self, registers) -> dict[str, float]:
        """Map ANGLE_ACT[6] -> {joint_name: rad}. Out-of-range registers are clamped."""
        positions: dict[str, float] = {}
        for entry in self.joints:
            reg = min(max(int(registers[entry.register]), 0), REGISTER_MAX)
            span = entry.upper - entry.lower
            positions[entry.joint] = entry.upper - (reg / REGISTER_MAX) * span
        return positions

    def full_joint_state(self, registers) -> dict[str, float]:
        """ANGLE_ACT[6] -> {joint_name: rad} for ALL joints (actuated + mimic + wrist).

        Replaces what joint_state_broadcaster used to compute under ros2_control,
        so robot_state_publisher gets every movable joint and TF stays complete.
        """
        pos = self.registers_to_radians(registers)  # 6 actuated

        # Resolve mimics, iterating because a mimic may follow another mimic
        # (thumb_4 mimics thumb_3, which mimics the actuated thumb_2).
        remaining = dict(self._mimics)
        for _ in range(len(remaining) + 1):
            if not remaining:
                break
            progressed = False
            for name, (source, mult, off) in list(remaining.items()):
                if source in pos:
                    pos[name] = pos[source] * mult + off
                    del remaining[name]
                    progressed = True
            if not progressed:
                break
        for name in remaining:  # unresolved (should not happen) -> safe default
            pos.setdefault(name, 0.0)

        for name in self._non_inspire_full:  # wrist DOF, not driven by DDS
            pos.setdefault(name, 0.0)
        return pos
