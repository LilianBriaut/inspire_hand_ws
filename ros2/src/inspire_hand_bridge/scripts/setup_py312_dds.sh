#!/usr/bin/env bash
# Install the bridge's non-rosdep Python dependencies for the Python that
# runs ROS 2 Jazzy (Python 3.12): cyclonedds 0.10.2 (binding) + inspire_sdkpy.
#
# WHY NOT `pip install cyclonedds` (11.x cp312 wheel):
#   The production driver (inspire_hand_sdk) and the h1v2 teleop stack run
#   cyclonedds 0.10.2. cyclonedds 11.x participants advertise XTypes type
#   objects that crash 0.10.x participants at discovery time (verified
#   segfault in ddsi_xt_type_init_impl on the 0.10.2 side).
#
# WHY BUILD AGAINST THE ROS-SHIPPED libddsc (0.10.5):
#   The bridge process hosts BOTH rclpy (whose rmw_cyclonedds_cpp loads
#   /opt/ros/jazzy's libddsc.so.0) and this Python binding. Two different
#   libddsc builds in one process crash (verified: iceoryx-related ABI
#   assertion in dds_write.c). Building the binding against the exact ROS
#   library means a single shared libddsc in-process.
#
#   ros-jazzy-cyclonedds does not use the prefix layout the binding's build
#   detector expects (lib/, include/, bin/ directly under one root), so a
#   small symlink "shim" prefix is created.
#
# Runtime requirement (add to your shell profile / launch environment):
#   export CYCLONEDDS_HOME=$HOME/.local/opt/cyclonedds-ros-shim
# and run inside a sourced ROS 2 Jazzy environment (libddsc needs
# LD_LIBRARY_PATH for its iceoryx dependencies).
set -euo pipefail

SHIM="${CYCLONEDDS_SHIM:-$HOME/.local/opt/cyclonedds-ros-shim}"
ROS_PREFIX="${ROS_PREFIX:-/opt/ros/jazzy}"
SDK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)/inspire_hand_sdk"
PY=/usr/bin/python3

echo ">> Creating shim prefix $SHIM -> $ROS_PREFIX cyclonedds"
mkdir -p "$SHIM/lib" "$SHIM/include"
ln -sfn "$ROS_PREFIX/lib/x86_64-linux-gnu/libddsc.so"   "$SHIM/lib/libddsc.so"
ln -sfn "$ROS_PREFIX/lib/x86_64-linux-gnu/libddsc.so.0" "$SHIM/lib/libddsc.so.0"
ln -sfn "$ROS_PREFIX/lib/x86_64-linux-gnu/cmake"        "$SHIM/lib/cmake"
ln -sfn "$ROS_PREFIX/include/CycloneDDS/dds"            "$SHIM/include/dds"
ln -sfn "$ROS_PREFIX/include/CycloneDDS/ddsc"           "$SHIM/include/ddsc"
ln -sfn "$ROS_PREFIX/bin"                               "$SHIM/bin"

echo ">> Building cyclonedds==0.10.2 (sdist) for $PY against $SHIM"
CYCLONEDDS_HOME="$SHIM" "$PY" -m pip install --user --break-system-packages \
  --no-deps --no-cache-dir --no-binary cyclonedds cyclonedds==0.10.2

echo ">> Installing inspire_sdkpy (editable, no heavy deps) from $SDK_DIR"
"$PY" -m pip install --user --break-system-packages --no-deps -e "$SDK_DIR"

echo
echo "Done. Add to your environment before running the bridge:"
echo "  export CYCLONEDDS_HOME=$SHIM"
