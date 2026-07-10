"""Bringup for one RH56DFTP hand: description + plain DDS bridge (no ros2_control).

    ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left

Everything runs in the namespace /rh56dftp/<side> so both hands can run
side by side (launch twice with side:=left and side:=right). Joint names
carry the <side>_ prefix, so TF and /joint_states never collide.

Topic layout (per side):
  /rh56dftp/<side>/joint_command      you -> bridge   (sensor_msgs/JointState, rad)
  /rh56dftp/<side>/joint_states       bridge -> RSP   (full 14-joint state)
  /rh56dftp/tactile/<side>/<region>   tactile skin    (17 topics)

Only two nodes: robot_state_publisher (URDF -> TF) and the bridge. The bridge
commands the hand's firmware with a single position target per message; the
smooth motion is generated on the hand, not here (no trajectory controller).
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _setup(context, *args, **kwargs):
    side = LaunchConfiguration("side").perform(context)
    if side not in ("left", "right"):
        raise RuntimeError(f"side must be 'left' or 'right', got {side!r}")
    prefix = f"{side}_"
    namespace = f"/rh56dftp/{side}"
    command_topic = f"{namespace}/joint_command"
    states_topic = f"{namespace}/joint_states"

    description_share = get_package_share_directory("rh56dftp_description")

    import xacro  # noqa: PLC0415

    # Plain kinematic description (no <ros2_control> overlay): the framework-
    # agnostic rh56dftp_description, processed as-is.
    robot_description = xacro.process_file(
        str(Path(description_share) / "urdf" / "rh56dftp.xacro"),
        mappings={"side": side, "prefix": prefix},
    ).toxml()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace=namespace,
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    bridge = Node(
        package="inspire_hand_bridge",
        executable="bridge_node",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "side": side,
                "prefix": prefix,
                "joint_command_topic": command_topic,
                "joint_states_topic": states_topic,
                "tactile_topic_prefix": f"/rh56dftp/tactile/{side}",
            }
        ],
    )

    return [robot_state_publisher, bridge]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("side", default_value="left", description="left or right"),
            OpaqueFunction(function=_setup),
        ]
    )
