# boot.py - runs once when the controller is plugged in.
#
# Normal plug-in:   the phone sees only a gamepad.
# Hold GUIDE while plugging in ("setup mode"): the CIRCUITPY drive and serial
#   console also appear, so you can edit mapping.json or code.py.
#
# Locked out? Press the XIAO's R (reset) button, then press it again while the
# LED blinks yellow. That starts safe mode, which skips this file.

import board
import digitalio
import storage
import usb_cdc
import usb_hid

# Standard gamepad: 6 axes (X, Y, Z, Rz, Rx, Ry), a hat switch, 16 buttons.
# Report is 9 bytes. Uses the Gamepad usage so Android/Linux map the buttons
# to A, B, X, Y, LB, RB, LT, RT, Back, Start, Guide, L3, R3 automatically.
GAMEPAD_DESCRIPTOR = bytes((
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x05,        # Usage (Gamepad)
    0xA1, 0x01,        # Collection (Application)
    0x09, 0x30, 0x09, 0x31, 0x09, 0x32,  #   Usage X, Y, Z
    0x09, 0x35, 0x09, 0x33, 0x09, 0x34,  #   Usage Rz, Rx, Ry
    0x15, 0x81,        #   Logical Min (-127)
    0x25, 0x7F,        #   Logical Max (127)
    0x75, 0x08,        #   Report Size (8)
    0x95, 0x06,        #   Report Count (6)
    0x81, 0x02,        #   Input (Data, Var, Abs)
    0x09, 0x39,        #   Usage (Hat switch)
    0x15, 0x01,        #   Logical Min (1)
    0x25, 0x08,        #   Logical Max (8)
    0x35, 0x00,        #   Physical Min (0)
    0x46, 0x3B, 0x01,  #   Physical Max (315)
    0x65, 0x14,        #   Unit (degrees)
    0x75, 0x08,        #   Report Size (8)
    0x95, 0x01,        #   Report Count (1)
    0x81, 0x42,        #   Input (Data, Var, Abs, Null state)
    0x65, 0x00,        #   Unit (none)
    0x45, 0x00,        #   Physical Max (0)
    0x05, 0x09,        #   Usage Page (Button)
    0x19, 0x01,        #   Usage Min (1)
    0x29, 0x10,        #   Usage Max (16)
    0x15, 0x00,        #   Logical Min (0)
    0x25, 0x01,        #   Logical Max (1)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x10,        #   Report Count (16)
    0x81, 0x02,        #   Input (Data, Var, Abs)
    0xC0,              # End Collection
))

gamepad = usb_hid.Device(
    report_descriptor=GAMEPAD_DESCRIPTOR,
    usage_page=0x01,
    usage=0x05,
    report_ids=(0,),
    in_report_lengths=(9,),
    out_report_lengths=(0,),
)
usb_hid.enable((gamepad,))

guide = digitalio.DigitalInOut(board.D10)
guide.switch_to_input(pull=digitalio.Pull.UP)
setup_mode = not guide.value   # pressed = pulled to GND
guide.deinit()

if not setup_mode:
    storage.disable_usb_drive()
    usb_cdc.disable()

try:
    import usb_midi
    usb_midi.disable()
except ImportError:
    pass
