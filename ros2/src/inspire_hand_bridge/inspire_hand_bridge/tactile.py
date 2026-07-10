"""Tactile skin republishing: one ROS 2 topic per region, sensor_msgs/Image mono16.

Region list, DDS field names, grids and parent frames all come from the
canonical rh56dftp_description/tactile/tactile_layout.yaml — no second table.

Every region of the RH56DFTP layout is a dense rows x cols grid (3x3, 12x8,
10x8, 14x8), so sensor_msgs/Image (encoding mono16) fits all 17 regions; no
region needs a fallback encoding. Raw DDS values are int16 sensor counts
(non-negative in practice); they are clamped to [0, 32767] and published as
unsigned mono16.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from sensor_msgs.msg import Image


@dataclass(frozen=True)
class TactileRegion:
    name: str
    dds_field: str
    rows: int
    cols: int
    taxels: int
    frame_id: str


def load_regions(description_share: str | Path, prefix: str) -> list[TactileRegion]:
    layout_yaml = Path(description_share) / "tactile" / "tactile_layout.yaml"
    with open(layout_yaml) as f:
        layout = yaml.safe_load(f)

    frame_suffix = layout.get("frame_suffix", "_touch")
    regions = []
    for name, spec in layout["regions"].items():
        rows, cols = spec["grid"]
        if rows * cols != spec["taxels"]:
            raise ValueError(f"Region {name}: grid {rows}x{cols} != taxels {spec['taxels']}")
        regions.append(
            TactileRegion(
                name=name,
                dds_field=spec["dds_field"],
                rows=rows,
                cols=cols,
                taxels=spec["taxels"],
                frame_id=f"{prefix}{name}{frame_suffix}",
            )
        )

    expected = layout.get("totals", {})
    if expected:
        if len(regions) != expected.get("regions", len(regions)):
            raise ValueError(f"Expected {expected['regions']} regions, parsed {len(regions)}")
        total = sum(r.taxels for r in regions)
        if total != expected.get("taxels", total):
            raise ValueError(f"Expected {expected['taxels']} taxels, parsed {total}")
    return regions


def region_image(region: TactileRegion, values, stamp) -> Image:
    data = np.asarray(values, dtype=np.int16)
    if data.size != region.taxels:
        raise ValueError(f"Region {region.name}: got {data.size} values, expected {region.taxels}")
    msg = Image()
    msg.header.stamp = stamp
    msg.header.frame_id = region.frame_id
    msg.height = region.rows
    msg.width = region.cols
    msg.encoding = "mono16"
    msg.is_bigendian = 0
    msg.step = region.cols * 2
    msg.data = np.clip(data, 0, np.iinfo(np.int16).max).astype("<u2").tobytes()
    return msg
