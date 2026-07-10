"""Fuse the 17 per-region tactile Image topics into one colored PointCloud2.

Each region publishes a rows x cols sensor_msgs/Image (mono16 pressure counts)
in its own TF frame (<prefix><region>_touch, see tactile_layout.yaml). This
node builds one point per taxel on a small grid local to that frame (taxel
pitch approximates the physical pad size), looks up the region's transform
into a common frame via tf2, and publishes every region's points as a single
PointCloud2 (XYZ + RGB) so RViz needs only one PointCloud2 display to show
pressure directly on the hand mesh.

Color: blue (no contact) -> red (near-saturation), linear on raw sensor counts
in [0, pressure_max] (declared parameter, default 200 — Inspire touch counts
saturate well below the int16 range in practice; adjust if taxels clip white).
"""

from __future__ import annotations

import struct

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import Image, PointCloud2, PointField
from tf2_ros import Buffer, TransformException, TransformListener

from .tactile import TactileRegion, load_regions

TAXEL_PITCH_M = 0.0025  # local grid spacing between adjacent taxels (region pad ~= rows*cols*pitch)


def _region_local_points(region: TactileRegion) -> np.ndarray:
    # Grid centered on the region frame origin, in the frame's local XY plane.
    ys = (np.arange(region.cols) - (region.cols - 1) / 2.0) * TAXEL_PITCH_M
    xs = (np.arange(region.rows) - (region.rows - 1) / 2.0) * TAXEL_PITCH_M
    xx, yy = np.meshgrid(xs, ys, indexing="ij")
    zz = np.zeros_like(xx)
    return np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1)  # (rows*cols, 3)


def _jet_rgb(t: np.ndarray) -> np.ndarray:
    # t in [0, 1] -> (N, 3) uint8, blue -> cyan -> yellow -> red.
    t = np.clip(t, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4 * t - 3), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0.0, 1.0)
    return (np.stack([r, g, b], axis=1) * 255).astype(np.uint8)


class TactileCloudNode(Node):
    def __init__(self) -> None:
        super().__init__("tactile_cloud_node")

        side = self.declare_parameter("side", "right").value
        prefix = self.declare_parameter("prefix", f"{side}_").value
        tactile_prefix = self.declare_parameter("tactile_topic_prefix", f"/rh56dftp/tactile/{side}").value
        self._target_frame = self.declare_parameter("target_frame", f"{prefix}hand_root").value
        self._pressure_max = float(self.declare_parameter("pressure_max", 200.0).value)
        publish_rate = float(self.declare_parameter("publish_rate_hz", 20.0).value)

        share = get_package_share_directory("rh56dftp_description")
        self._regions = load_regions(share, prefix)
        self._local_points = {r.name: _region_local_points(r) for r in self._regions}
        self._latest: dict[str, Image] = {}

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        sensor_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        for region in self._regions:
            topic = f"{tactile_prefix}/{region.name}"
            self.create_subscription(
                Image, topic, lambda msg, name=region.name: self._on_image(name, msg), sensor_qos
            )

        self._cloud_pub = self.create_publisher(PointCloud2, f"{tactile_prefix}/cloud", sensor_qos)
        self.create_timer(1.0 / publish_rate, self._publish_cloud)

        self.get_logger().info(
            f"tactile_cloud_node up: side={side} target_frame={self._target_frame} "
            f"regions={len(self._regions)} -> {tactile_prefix}/cloud"
        )

    def _on_image(self, name: str, msg: Image) -> None:
        self._latest[name] = msg

    def _publish_cloud(self) -> None:
        all_xyz: list[np.ndarray] = []
        all_rgb: list[np.ndarray] = []

        for region in self._regions:
            msg = self._latest.get(region.name)
            if msg is None:
                continue
            try:
                tf = self._tf_buffer.lookup_transform(self._target_frame, msg.header.frame_id, Time())
            except TransformException:
                continue

            values = np.frombuffer(bytes(msg.data), dtype="<u2").astype(np.float32)
            if values.size != region.taxels:
                continue

            local = self._local_points[region.name]
            t = tf.transform.translation
            q = tf.transform.rotation
            rot = _quat_to_matrix(q.x, q.y, q.z, q.w)
            world = local @ rot.T + np.array([t.x, t.y, t.z])

            all_xyz.append(world)
            all_rgb.append(_jet_rgb(values / self._pressure_max))

        if not all_xyz:
            return

        xyz = np.concatenate(all_xyz, axis=0)
        rgb = np.concatenate(all_rgb, axis=0)
        self._cloud_pub.publish(_make_cloud(self._target_frame, self.get_clock().now().to_msg(), xyz, rgb))


def _quat_to_matrix(x: float, y: float, z: float, w: float) -> np.ndarray:
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def _make_cloud(frame_id: str, stamp, xyz: np.ndarray, rgb: np.ndarray) -> PointCloud2:
    n = xyz.shape[0]
    rgb_packed = (rgb[:, 0].astype(np.uint32) << 16) | (rgb[:, 1].astype(np.uint32) << 8) | rgb[:, 2].astype(
        np.uint32
    )

    buf = bytearray(n * 16)
    for i in range(n):
        struct.pack_into("<fffI", buf, i * 16, xyz[i, 0], xyz[i, 1], xyz[i, 2], int(rgb_packed[i]))

    msg = PointCloud2()
    msg.header.frame_id = frame_id
    msg.header.stamp = stamp
    msg.height = 1
    msg.width = n
    msg.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        PointField(name="rgb", offset=12, datatype=PointField.UINT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 16
    msg.row_step = 16 * n
    msg.is_dense = True
    msg.data = bytes(buf)
    return msg


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TactileCloudNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
