#!/usr/bin/env python3
"""Fallback runner for systems missing the ros2launch CLI plugin.

Equivalent to:  ros2 launch inspire_hand_bridge rh56dftp.launch.py side:=<side>
Usage:          python3 run_launch.py [side:=left] [other:=args...]

(Prefer `sudo apt install ros-jazzy-ros2launch` and the standard command.)
"""

import sys
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchService
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def main() -> int:
    launch_file = str(
        Path(get_package_share_directory("inspire_hand_bridge")) / "launch" / "rh56dftp.launch.py"
    )
    launch_args = [arg.split(":=", 1) for arg in sys.argv[1:] if ":=" in arg]
    description = LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_file),
                launch_arguments=[(k, v) for k, v in launch_args],
            )
        ]
    )
    service = LaunchService()
    service.include_launch_description(description)
    return service.run()


if __name__ == "__main__":
    sys.exit(main())
