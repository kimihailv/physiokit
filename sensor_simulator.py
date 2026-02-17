"""
Virtual sensor simulator for PhysioKit testing.

Patches the serial port layer so PhysioKit receives fake sensor data
without any physical device. No external tools needed.

Usage:
    1. Run:  python sensor_simulator.py
    2. PhysioKit will launch with a fake port "SIMULATOR" in the dropdown
    3. Select it, connect, and use PhysioKit as normal

Press Ctrl+C to stop.
"""

import math
import time
import threading
import io

# --- Configuration (must match your PhysioKit experiment JSON) ---
NCHANNELS = 4                              # eda, resp, ppg, ppg
SAMPLING_RATE = 250                        # Hz

# Simulated signal parameters
SIGNALS = [
    {"name": "eda",  "baseline": 512, "amplitude": 20,  "freq_hz": 0.05},
    {"name": "resp", "baseline": 512, "amplitude": 200, "freq_hz": 0.25},
    {"name": "ppg1", "baseline": 512, "amplitude": 300, "freq_hz": 1.2},
    {"name": "ppg2", "baseline": 512, "amplitude": 300, "freq_hz": 1.2},
]


class FakeSerial:
    """Drop-in replacement for serial.Serial that generates fake sensor data."""

    def __init__(self, *args, **kwargs):
        self.port = None
        self.baudrate = 115200
        self.timeout = None
        self.parity = None
        self.stopbits = None
        self.bytesize = None
        self.is_open = False
        self._t = 0.0
        self._interval = 1.0 / SAMPLING_RATE
        self._lock = threading.Lock()

    def open(self):
        self.is_open = True
        self._t = 0.0

    def close(self):
        self.is_open = False

    def readline(self, size=None):
        """Generate one line of fake sensor data, paced at the sampling rate."""
        time.sleep(self._interval)
        values = []
        for sig in SIGNALS[:NCHANNELS]:
            val = sig["baseline"] + sig["amplitude"] * math.sin(
                2 * math.pi * sig["freq_hz"] * self._t
            )
            values.append(str(int(round(val))))
        self._t += self._interval
        return (",".join(values) + "\r\n").encode()

    def write(self, data):
        pass

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass


class FakeListPortInfo:
    """Mimics serial.tools.list_ports.ListPortInfo."""
    def __init__(self):
        self.device = "SIMULATOR"
        self.name = "SIMULATOR"
        self.description = "SIMULATOR - Virtual Sensor"
        self.hwid = "SIMULATOR"

    def __str__(self):
        return self.description

    def __iter__(self):
        return iter((self.device, self.description, self.hwid))

    def __lt__(self, other):
        return self.device < other.device


def fake_comports():
    return [FakeListPortInfo()]


# --- Monkey-patch serial before importing PhysioKit ---
import serial
import serial.tools.list_ports as list_ports

serial._real_Serial = serial.Serial
serial.Serial = FakeSerial
list_ports._real_comports = list_ports.comports
list_ports.comports = fake_comports

print("=" * 50)
print("  Sensor simulator active")
print(f"  Channels: {NCHANNELS}  Sample rate: {SAMPLING_RATE} Hz")
print("  A fake port 'SIMULATOR' will appear in PhysioKit")
print("=" * 50)
print()

# --- Now launch PhysioKit, passing through all CLI arguments ---
# e.g.: python sensor_simulator.py --config path/to/sw_config.json
import runpy
runpy.run_module("PhysioKit2.main", run_name="__main__", alter_sys=True)
