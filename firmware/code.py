# code.py - A55 controller for XIAO RP2040 running CircuitPython.
#
# Reads 16 buttons from two chained 74HC165s, GUIDE on its own pin and two
# analog sticks, then sends a USB gamepad report (descriptor is in boot.py).
# Button remapping, stick inversion/swap and deadzone come from mapping.json.
#
# Don't touch the sticks while plugging in: their centers are calibrated then.

import json
import struct
import time

import analogio
import board
import digitalio
import keypad
import usb_hid

# ---------- What each 74HC165 input (D0..D7) is wired to ----------
LEFT_CHIP = ("UP", "DOWN", "LEFT", "RIGHT", "LB", "LT", "L3", "BACK")
RIGHT_CHIP = ("A", "B", "X", "Y", "RB", "RT", "R3", "START")

# ---------- Outputs ----------
# Bit positions follow the Linux/Android gamepad order.
OUTPUT_BITS = {
    "A": 0, "B": 1, "X": 3, "Y": 4,
    "LB": 6, "RB": 7, "LT": 8, "RT": 9,
    "BACK": 10, "START": 11, "GUIDE": 12, "L3": 13, "R3": 14,
}
DPAD_OUTPUTS = ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT")

# Hat values for (up, down, left, right); 0 = centered
HAT = {
    (True, False, False, False): 1, (True, False, False, True): 2,
    (False, False, False, True): 3, (False, True, False, True): 4,
    (False, True, False, False): 5, (False, True, True, False): 6,
    (False, False, True, False): 7, (True, False, True, False): 8,
}

DEFAULT_CONFIG = {
    "xiao_in_right_grip": True,
    "buttons": {
        "A": "A", "B": "B", "X": "X", "Y": "Y",
        "LB": "LB", "RB": "RB", "LT": "LT", "RT": "RT",
        "BACK": "BACK", "START": "START", "GUIDE": "GUIDE",
        "L3": "L3", "R3": "R3",
        "UP": "DPAD_UP", "DOWN": "DPAD_DOWN",
        "LEFT": "DPAD_LEFT", "RIGHT": "DPAD_RIGHT",
    },
    "invert": {"LX": False, "LY": False, "RX": False, "RY": False},
    "swap_sticks": False,
    "deadzone": 0.06,
}


def load_config():
    cfg = {
        "xiao_in_right_grip": DEFAULT_CONFIG["xiao_in_right_grip"],
        "buttons": dict(DEFAULT_CONFIG["buttons"]),
        "invert": dict(DEFAULT_CONFIG["invert"]),
        "swap_sticks": DEFAULT_CONFIG["swap_sticks"],
        "deadzone": DEFAULT_CONFIG["deadzone"],
    }
    try:
        with open("/mapping.json") as f:
            user = json.load(f)
    except (OSError, ValueError) as e:
        print("mapping.json not loaded, using defaults:", e)
        return cfg
    for key in ("xiao_in_right_grip", "swap_sticks", "deadzone"):
        if key in user:
            cfg[key] = user[key]
    for key in ("buttons", "invert"):
        if isinstance(user.get(key), dict):
            cfg[key].update(user[key])
    return cfg


def action_for(output):
    """Returns (button bitmask, d-pad index or -1) for an output name."""
    if output in OUTPUT_BITS:
        return 1 << OUTPUT_BITS[output], -1
    if output in DPAD_OUTPUTS:
        return 0, DPAD_OUTPUTS.index(output)
    return 0, -1   # "NONE" or unknown: button does nothing


def key_names(xiao_in_right_grip):
    """Physical button for each shift-register key number.
    Key 0 is the first bit read: D7 of the chip wired to DATA (the near chip)."""
    near, far = (RIGHT_CHIP, LEFT_CHIP) if xiao_in_right_grip else (LEFT_CHIP, RIGHT_CHIP)
    return [near[7 - k] for k in range(8)] + [far[7 - k] for k in range(8)]


class Axis:
    def __init__(self, pin, invert, deadzone):
        self.adc = analogio.AnalogIn(pin)
        self.invert = invert
        self.deadzone = int(deadzone * 32767)
        self.center = self.raw()

    def raw(self):
        total = 0
        for _ in range(4):
            total += self.adc.value
        return total // 4

    def read(self):
        delta = self.raw() - self.center
        if abs(delta) < self.deadzone:
            return 0
        if delta > 0:
            span = 65535 - self.center - self.deadzone
            out = (delta - self.deadzone) / span
        else:
            span = self.center - self.deadzone
            out = (delta + self.deadzone) / span
        out = max(-1.0, min(1.0, out))
        if self.invert:
            out = -out
        return int(out * 127)


def find_gamepad():
    for device in usb_hid.devices:
        if device.usage_page == 0x01 and device.usage == 0x05:
            return device
    raise RuntimeError("Gamepad not found: check that boot.py is on the board")


# ---------- Setup ----------
cfg = load_config()
gamepad = find_gamepad()

names = key_names(cfg["xiao_in_right_grip"])
key_actions = [action_for(cfg["buttons"].get(n, "NONE")) for n in names]
guide_action = action_for(cfg["buttons"].get("GUIDE", "NONE"))

keys = keypad.ShiftRegisterKeys(
    clock=board.D8,
    data=board.D9,
    latch=board.D7,
    key_count=16,
    value_when_pressed=False,
    interval=0.002,
)
guide_pin = digitalio.DigitalInOut(board.D10)
guide_pin.switch_to_input(pull=digitalio.Pull.UP)

time.sleep(0.1)
inv = cfg["invert"]
dz = cfg["deadzone"]
lx = Axis(board.A0, inv.get("LX", False), dz)
ly = Axis(board.A1, inv.get("LY", False), dz)
rx = Axis(board.A2, inv.get("RX", False), dz)
ry = Axis(board.A3, inv.get("RY", False), dz)

pressed = [False] * 16
event = keypad.Event()
last_report = None
last_sent = 0.0

# ---------- Main loop ----------
while True:
    while keys.events.get_into(event):
        pressed[event.key_number] = event.pressed

    buttons = 0
    dpad = [False, False, False, False]
    for k in range(16):
        if pressed[k]:
            mask, d = key_actions[k]
            buttons |= mask
            if d >= 0:
                dpad[d] = True
    if not guide_pin.value:
        mask, d = guide_action
        buttons |= mask
        if d >= 0:
            dpad[d] = True

    hat = HAT.get(tuple(dpad), 0)

    left = (lx.read(), ly.read())
    right = (rx.read(), ry.read())
    if cfg["swap_sticks"]:
        left, right = right, left

    # Order: X, Y, Z, Rz, Rx, Ry, hat, buttons (left stick = X/Y, right = Z/Rz)
    report = struct.pack("<bbbbbbBH", left[0], left[1], right[0], right[1], 0, 0, hat, buttons)

    now = time.monotonic()
    if report != last_report or now - last_sent > 0.05:
        try:
            gamepad.send_report(report)
            last_report = report
            last_sent = now
        except OSError:
            time.sleep(0.05)   # not connected to a host yet
