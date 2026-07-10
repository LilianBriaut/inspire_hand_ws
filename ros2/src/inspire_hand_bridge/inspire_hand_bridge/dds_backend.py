"""Raw-DDS side of the bridge (Cyclone DDS, same wire types as the production driver).

The DDS type definitions live in the already-deployed ``inspire_sdkpy`` package
(inspire_hand_ws/inspire_hand_sdk). They are imported from there — never
copied nor regenerated — so the bridge always matches the driver's wire types.

``inspire_sdkpy/__init__.py`` pulls heavy runtime dependencies the bridge does
not need (PyQt5, pymodbus, unitree_sdk2py). To keep the ROS 2 runtime light we
import the ``inspire_sdkpy.inspire_dds`` subpackage without executing the
parent ``__init__``: a stub parent module is registered first, then the
subpackage (which only depends on cyclonedds) is imported normally.

Version constraint: cyclonedds must stay on the 0.10.x line. The production
driver and teleop stack run cyclonedds 0.10.2; cyclonedds 11.x advertises
XTypes type objects that crash 0.10.x participants on discovery (verified:
segfault in ddsi_xt_type_init_impl). See scripts/setup_py312_dds.sh.
"""

from __future__ import annotations

import importlib.util
import sys
import types


def load_inspire_dds():
    """Import inspire_sdkpy.inspire_dds without executing inspire_sdkpy.__init__."""
    if "inspire_sdkpy.inspire_dds" in sys.modules:
        return sys.modules["inspire_sdkpy.inspire_dds"]
    if "inspire_sdkpy" not in sys.modules:
        spec = importlib.util.find_spec("inspire_sdkpy")
        if spec is None or not spec.submodule_search_locations:
            raise ImportError(
                "inspire_sdkpy is not importable. Install it for the Python running "
                "ROS 2 (see inspire_hand_bridge/scripts/setup_py312_dds.sh)."
            )
        stub = types.ModuleType("inspire_sdkpy")
        stub.__path__ = list(spec.submodule_search_locations)
        stub.__spec__ = spec
        sys.modules["inspire_sdkpy"] = stub
    import inspire_sdkpy.inspire_dds as inspire_dds  # noqa: PLC0415

    return inspire_dds


class InspireDds:
    """Participant + endpoints on the production DDS topics of one hand.

    Matches the driver/teleop conventions (unitree_sdk2py channels with default
    QoS): writer rt/inspire_hand/ctrl/<lr>, readers rt/inspire_hand/state/<lr>
    and rt/inspire_hand/touch/<lr>, DDS domain 0 by default.
    """

    def __init__(self, lr: str, domain_id: int = 0):
        if lr not in ("l", "r"):
            raise ValueError(f"lr must be 'l' or 'r', got {lr!r}")
        self._types = load_inspire_dds()

        from cyclonedds.domain import DomainParticipant  # noqa: PLC0415
        from cyclonedds.pub import DataWriter  # noqa: PLC0415
        from cyclonedds.sub import DataReader  # noqa: PLC0415
        from cyclonedds.topic import Topic  # noqa: PLC0415

        self.participant = DomainParticipant(domain_id)
        self.ctrl_writer = DataWriter(
            self.participant,
            Topic(self.participant, f"rt/inspire_hand/ctrl/{lr}", self._types.inspire_hand_ctrl),
        )
        self.state_reader = DataReader(
            self.participant,
            Topic(self.participant, f"rt/inspire_hand/state/{lr}", self._types.inspire_hand_state),
        )
        self.touch_reader = DataReader(
            self.participant,
            Topic(self.participant, f"rt/inspire_hand/touch/{lr}", self._types.inspire_hand_touch),
        )

    def write_ctrl(self, angle_set: list[int], mode: int = 0b0001, speed_set=None, force_set=None) -> None:
        msg = self._types.inspire_hand_ctrl(
            pos_set=[0] * 6,
            angle_set=[int(v) for v in angle_set],
            force_set=[int(v) for v in (force_set if force_set is not None else [0] * 6)],
            speed_set=[int(v) for v in (speed_set if speed_set is not None else [0] * 6)],
            mode=int(mode),
        )
        self.ctrl_writer.write(msg)

    def take_latest_state(self):
        """Return the newest inspire_hand_state sample, or None."""
        return self._take_latest(self.state_reader)

    def take_latest_touch(self):
        """Return the newest inspire_hand_touch sample, or None."""
        return self._take_latest(self.touch_reader)

    @staticmethod
    def _take_latest(reader):
        latest = None
        for sample in reader.take(32):
            latest = sample
        return latest
