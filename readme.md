
---

# Inspire Hand SDK Usage Guide

```
direnv allow
python -m venv --system-site-packages .venv
source .venv/bin/activate
pip install ./inspire_hand_sdk
python -c "import inspire_sdkpy; print(inspire_sdkpy.__file__)"
```


## Control Modes

The Inspire Hand SDK supports multiple control modes, defined as follows:

- **Mode 0**: `0000` (No operation)
- **Mode 1**: `0001` (Angle)
- **Mode 2**: `0010` (Position)
- **Mode 3**: `0011` (Angle + Position)
- **Mode 4**: `0100` (Force control)
- **Mode 5**: `0101` (Angle + Force control)
- **Mode 6**: `0110` (Position + Force control)
- **Mode 7**: `0111` (Angle + Position + Force control)
- **Mode 8**: `1000` (Velocity)
- **Mode 9**: `1001` (Angle + Velocity)
- **Mode 10**: `1010` (Position + Velocity)
- **Mode 11**: `1011` (Angle + Position + Velocity)
- **Mode 12**: `1100` (Force control + Velocity)
- **Mode 13**: `1101` (Angle + Force control + Velocity)
- **Mode 14**: `1110` (Position + Force control + Velocity)
- **Mode 15**: `1111` (Angle + Position + Force control + Velocity)

## Usage Examples

Below are instructions for using common examples:

1. **DDS Control Command Publisher**:

    Run the following script to publish control commands:
    ```bash
    python inspire_hand_sdk/example/dds_publish.py
    ```

2. **DDS Subscriber for Inspire Hand Status and Tactile Sensor Data with Visualization**:

    Run the following script to subscribe to the Inspire Hand status and sensor data, and visualize the results:
    ```bash
    python inspire_hand_sdk/example/dds_subscribe.py
    ```

3. **Inspire Hand DDS Driver (Headless Mode)**:

    Use the following script for the headless mode driver:
    ```bash
    python inspire_hand_sdk/example/Headless_driver.py
    ```

4. **Inspire Hand Configuration Panel**:

    Run the following script to use the Inspire Hand configuration panel:
    ```bash
    python inspire_hand_sdk/example/init_set_inspire_hand.py
    ```

5. **Inspire Hand DDS Driver (Panel Mode)**:

    Use the following script to enter panel mode for the Inspire Hand DDS driver:
    ```bash
    python inspire_hand_sdk/example/Vision_driver.py
    ```

---
