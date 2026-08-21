"""Bringup for one RH56DFTP hand: description + plain DDS bridge (no ros2_control).

    ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left
    ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=left rviz:=true

Everything runs in the namespace /rh56dftp/<side> so both hands can run
side by side (launch twice with side:=left and side:=right). Joint names
carry the <side>_ prefix, so TF and /joint_states never collide. Note /tf and
/tf_static stay global (tf2 uses absolute topic names), only robot_description
is namespaced — hence the absolute Description Topic in the RViz configs.

Topic layout (per side):
  /rh56dftp/<side>/joint_command      you -> bridge   (JointState, opening % 0..100)
  /rh56dftp/<side>/joint_states       bridge -> RSP   (full 14-joint state, rad)
  /rh56dftp/tactile/<side>/<region>   tactile skin    (17 Image topics)
  /rh56dftp/tactile/<side>/cloud      fused PointCloud2 (tactile_cloud:=true)

Core is two nodes: robot_state_publisher (URDF -> TF) and the bridge. The bridge
commands the hand's firmware with a single position target per message; the
smooth motion is generated on the hand, not here (no trajectory controller).

Optional, for visualisation only:
  tactile_cloud:=true  fuse the 17 tactile images into one colored PointCloud2
  rviz:=true           open RViz on rviz/tactile_<side>.rviz (implies tactile_cloud)
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _as_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")


def _setup(context, *args, **kwargs):
    side = LaunchConfiguration("side").perform(context)
    if side not in ("left", "right"):
        raise RuntimeError(f"side must be 'left' or 'right', got {side!r}")
    rviz = _as_bool(LaunchConfiguration("rviz").perform(context))
    # RViz shows tactile through the fused cloud, so it needs the cloud node.
    tactile_cloud = rviz or _as_bool(LaunchConfiguration("tactile_cloud").perform(context))

    prefix = f"{side}_"
    namespace = f"/rh56dftp/{side}"
    command_topic = f"{namespace}/joint_command"
    states_topic = f"{namespace}/joint_states"
    tactile_prefix = f"/rh56dftp/tactile/{side}"

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
                "tactile_topic_prefix": tactile_prefix,
            }
        ],
    )

    nodes = [robot_state_publisher, bridge]

    if tactile_cloud:
        nodes.append(
            Node(
                package="inspire_hand_bridge",
                executable="tactile_cloud_node",
                namespace=namespace,
                output="screen",
                parameters=[
                    {
                        "side": side,
                        "prefix": prefix,
                        "tactile_topic_prefix": tactile_prefix,
                        "target_frame": f"{prefix}hand_root",
                    }
                ],
            )
        )

    if rviz:
        # Left in the global namespace: the config's topics are absolute and tf2
        # uses absolute /tf, so namespacing RViz would buy nothing.
        rviz_config = Path(get_package_share_directory("inspire_hand_bridge")) / "rviz" / f"tactile_{side}.rviz"
        if not rviz_config.is_file():
            raise RuntimeError(f"RViz config not found: {rviz_config} (rebuild the package?)")
        nodes.append(
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", str(rviz_config)],
                output="screen",
            )
        )

    return nodes


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("side", default_value="left", description="left or right"),
            DeclareLaunchArgument(
                "tactile_cloud",
                default_value="false",
                description="Publish the fused tactile PointCloud2 (implied by rviz:=true)",
            ),
            DeclareLaunchArgument("rviz", default_value="false", description="Open RViz on tactile_<side>.rviz"),
            OpaqueFunction(function=_setup),
        ]
    )
