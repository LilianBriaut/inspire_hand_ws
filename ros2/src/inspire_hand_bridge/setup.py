from glob import glob

from setuptools import setup

package_name = "inspire_hand_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/scripts", glob("scripts/*.sh") + glob("scripts/*.py")),
        ("share/" + package_name + "/rviz", glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Lilian Briaut",
    maintainer_email="lilian.briaut@gmail.com",
    description="DDS to ROS 2 bridge for the Inspire Hand RH56DFTP (control + tactile)",
    license="MIT",
    entry_points={
        "console_scripts": [
            "bridge_node = inspire_hand_bridge.bridge_node:main",
            "tactile_cloud_node = inspire_hand_bridge.tactile_cloud_node:main",
        ],
    },
)
