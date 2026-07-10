"""inspire_hand_bridge node — plain ROS 2 <-> DDS bridge for one RH56DFTP hand.

No ros2_control: this is a classic node. You command the hand by publishing a
target *position* (like scripts/hand_teleop/open_hand.py does on raw DDS, but
through a ROS interface); the hand's firmware generates the smooth motion to
that target itself. There is no trajectory interpolation here on purpose — a
single DDS write per command, which is what makes the motion fluid.

ROS side (per hand, topics namespaced by side):
  - subscribes  <joint_command_topic>  (sensor_msgs/JointState, radians by name)
    — target position for the 6 actuated joints (partial commands allowed once
    state is flowing; send all 6 for fully deterministic control);
  - publishes   <joint_states_topic>   (sensor_msgs/JointState) — the FULL 14-joint
    state (actuated + mimic + wrist), for robot_state_publisher / TF / RViz;
  - publishes   <tactile_topic_prefix>/<region> (sensor_msgs/Image mono16),
    one topic per region of tactile_layout.yaml (17 regions).

DDS side (production driver topics, cyclonedds 0.10.x):
  - writes  rt/inspire_hand/ctrl/{l,r}   (angle mode by default)
  - reads   rt/inspire_hand/state/{l,r}  and rt/inspire_hand/touch/{l,r}

The command path is event-driven (ROS callback -> DDS write). State and
tactile are polled from DDS readers by ROS timers.
"""

from __future__ import annotations

import math

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)
from sensor_msgs.msg import Image, JointState

from .dds_backend import InspireDds
from .hand_mapping import HandMapping
from .tactile import load_regions, region_image

CTRL_MODE_ANGLE = 0b0001
CTRL_MODE_FORCE = 0b0100
CTRL_MODE_SPEED = 0b1000


class InspireHandBridge(Node):
    def __init__(self) -> None:
        super().__init__("inspire_hand_bridge")

        side = self.declare_parameter("side", "left").value
        if side not in ("left", "right"):
            raise ValueError(f"Parameter 'side' must be 'left' or 'right', got {side!r}")
        lr = "l" if side == "left" else "r"
        prefix = self.declare_parameter("prefix", f"{side}_").value

        domain_id = self.declare_parameter("dds_domain_id", 0).value
        command_topic = self.declare_parameter("joint_command_topic", f"/rh56dftp/{side}/joint_command").value
        states_topic = self.declare_parameter("joint_states_topic", f"/rh56dftp/{side}/joint_states").value
        tactile_prefix = self.declare_parameter("tactile_topic_prefix", f"/rh56dftp/tactile/{side}").value

        state_rate = self.declare_parameter("state_rate_hz", 100.0).value
        tactile_poll_rate = self.declare_parameter("tactile_poll_rate_hz", 50.0).value
        publish_tactile = self.declare_parameter("publish_tactile", True).value

        self._ctrl_mode = self.declare_parameter("ctrl_mode", CTRL_MODE_ANGLE).value
        initial_speed = list(self.declare_parameter("initial_speed", [-1]).value)
        initial_force = list(self.declare_parameter("initial_force", [-1]).value)

        share = get_package_share_directory("rh56dftp_description")
        self._mapping = HandMapping(share, side, prefix)
        self._actuated = set(self._mapping.joint_names)

        # Persistent target for the 6 actuated joints. DDS ctrl needs all 6 at
        # once, so we merge incoming (possibly partial) commands into this dict
        # and seed it once from the first measured state (below), so a command
        # touching a single finger holds the others where they are.
        self._targets: dict[str, float] = {}

        # --- DDS endpoints (same wire conventions as the production driver) ---
        self._dds = InspireDds(lr, domain_id)

        # Optional one-shot speed/force setup (driver only writes registers for
        # set mode bits, so angle-only messages afterwards leave them alone).
        setup_mode = 0
        if len(initial_speed) == 6:
            setup_mode |= CTRL_MODE_SPEED
        if len(initial_force) == 6:
            setup_mode |= CTRL_MODE_FORCE
        if setup_mode:
            self._dds.write_ctrl(
                [0] * 6,
                mode=setup_mode & ~CTRL_MODE_ANGLE,
                speed_set=initial_speed if setup_mode & CTRL_MODE_SPEED else None,
                force_set=initial_force if setup_mode & CTRL_MODE_FORCE else None,
            )
            self.get_logger().info(f"Sent initial speed/force setup (mode={setup_mode:#06b})")

        # --- ROS interfaces ---
        # Command: reliable keep-last, so a `ros2 topic pub` / script command is
        # not dropped.
        command_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self._command_sub = self.create_subscription(JointState, command_topic, self._on_joint_command, command_qos)

        # State: standard /joint_states QoS (reliable keep-last 10), what
        # robot_state_publisher subscribes with.
        states_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self._state_pub = self.create_publisher(JointState, states_topic, states_qos)
        self.create_timer(1.0 / state_rate, self._poll_state)

        self._regions = []
        self._tactile_pubs = {}
        self._tactile_last_pub: dict[str, float] = {}
        self._tactile_throttle: dict[str, float] = {}
        if publish_tactile:
            self._regions = load_regions(share, prefix)
            for region in self._regions:
                # Per-region QoS/rate overrides, e.g.:
                #   tactile.index_top.reliability: reliable
                #   tactile.index_top.depth: 1
                #   tactile.index_top.throttle_hz: 10.0   (0 = every driver sample)
                reliability = self.declare_parameter(f"tactile.{region.name}.reliability", "best_effort").value
                depth = self.declare_parameter(f"tactile.{region.name}.depth", 5).value
                throttle = self.declare_parameter(f"tactile.{region.name}.throttle_hz", 0.0).value
                qos = QoSProfile(
                    history=QoSHistoryPolicy.KEEP_LAST,
                    depth=depth,
                    reliability=(
                        QoSReliabilityPolicy.RELIABLE
                        if reliability == "reliable"
                        else QoSReliabilityPolicy.BEST_EFFORT
                    ),
                    durability=QoSDurabilityPolicy.VOLATILE,
                )
                self._tactile_pubs[region.name] = self.create_publisher(Image, f"{tactile_prefix}/{region.name}", qos)
                self._tactile_throttle[region.name] = float(throttle)
                self._tactile_last_pub[region.name] = 0.0
            self.create_timer(1.0 / tactile_poll_rate, self._poll_touch)

        self.get_logger().info(
            f"Bridge up: side={side} dds=rt/inspire_hand/*/{lr} (domain {domain_id}) "
            f"command={command_topic} states={states_topic} "
            f"tactile={'%s/<region> (%d regions)' % (tactile_prefix, len(self._regions)) if publish_tactile else 'off'}"
        )

    # ------------------------------------------------------------------
    # ROS -> DDS (command path)
    # ------------------------------------------------------------------

    def _on_joint_command(self, msg: JointState) -> None:
        # Merge the finite target positions of actuated joints into self._targets.
        # Non-actuated joints (mimic / wrist) in the message are ignored: they
        # are coupled or fixed, never commanded directly.
        updated = False
        for name, value in zip(msg.name, msg.position):
            if name in self._actuated and math.isfinite(value):
                self._targets[name] = value
                updated = True
        if not updated:
            return

        registers = self._mapping.radians_to_registers(self._targets)
        if registers is None:
            # Fewer than the 6 actuated joints are known yet (no state seed and a
            # partial first command). Wait until all 6 have a target.
            self.get_logger().warn(
                f"Command received for {len(self._targets)}/6 actuated joints; "
                "waiting for the rest (or for state to seed the others).",
                throttle_duration_sec=5.0,
            )
            return
        self._dds.write_ctrl(registers, mode=self._ctrl_mode)

    # ------------------------------------------------------------------
    # DDS -> ROS (state + tactile paths)
    # ------------------------------------------------------------------

    def _poll_state(self) -> None:
        sample = self._dds.take_latest_state()
        if sample is None:
            return
        positions = self._mapping.full_joint_state(sample.angle_act)

        # Seed command targets from the first measured pose, so a later partial
        # command holds the untouched joints at their current position instead
        # of jumping. Only until the first command arrives.
        if not self._targets:
            for name in self._mapping.joint_names:
                self._targets[name] = positions[name]

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self._mapping.all_joint_names
        msg.position = [positions[name] for name in self._mapping.all_joint_names]
        self._state_pub.publish(msg)

    def _poll_touch(self) -> None:
        sample = self._dds.take_latest_touch()
        if sample is None:
            return
        stamp = self.get_clock().now().to_msg()
        now = self.get_clock().now().nanoseconds * 1e-9
        for region in self._regions:
            throttle = self._tactile_throttle[region.name]
            if throttle > 0.0 and (now - self._tactile_last_pub[region.name]) < 1.0 / throttle:
                continue
            values = getattr(sample, region.dds_field)
            self._tactile_pubs[region.name].publish(region_image(region, values, stamp))
            self._tactile_last_pub[region.name] = now


def main(args=None) -> None:
    rclpy.init(args=args)
    node = InspireHandBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
