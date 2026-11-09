#!/usr/bin/env python3
"""
Gamepad Studio - remap the A55 controller from your computer.

Needs only Python 3 (tkinter is included with the standard Windows and macOS
installers; on Linux, install the "python3-tk" package if it's missing).

How to use:
  1. Hold GUIDE while plugging the controller into your computer.
     A drive called CIRCUITPY appears.
  2. Run:  python gamepad_studio.py
  3. Click a button on the board (or use the lists), pick what it sends,
     then click "Save to controller". The new mapping works right away.
"""

import glob
import json
import os
import string
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ---------------------------------------------------------------- data

OUTPUTS = [
    ("A", "A"), ("B", "B"), ("X", "X"), ("Y", "Y"),
    ("LB", "LB"), ("RB", "RB"), ("LT", "LT"), ("RT", "RT"),
    ("BACK", "Back"), ("START", "Start"), ("GUIDE", "Guide"),
    ("L3", "L3 (left stick click)"), ("R3", "R3 (right stick click)"),
    ("DPAD_UP", "D-pad up"), ("DPAD_DOWN", "D-pad down"),
    ("DPAD_LEFT", "D-pad left"), ("DPAD_RIGHT", "D-pad right"),
    ("NONE", "Nothing"),
]
CODE_TO_NAME = dict(OUTPUTS)
NAME_TO_CODE = {name: code for code, name in OUTPUTS}
SHORT = {
    "A": "A", "B": "B", "X": "X", "Y": "Y", "LB": "LB", "RB": "RB",
    "LT": "LT", "RT": "RT", "BACK": "Back", "START": "Start", "GUIDE": "Guide",
    "L3": "L3", "R3": "R3", "DPAD_UP": "Up", "DPAD_DOWN": "Down",
    "DPAD_LEFT": "Left", "DPAD_RIGHT": "Right", "NONE": "Off",
}

# Physical buttons, positioned to match the PCB layout (mm from top-left).
# back=True: switch is on the back of the board. r: thumbstick radius.
PHYS = [
    dict(id="UP", label="Up", glyph="↑", side="left", x=31.0, y=55.2),
    dict(id="DOWN", label="Down", glyph="↓", side="left", x=30.7, y=85.1),
    dict(id="LEFT", label="Left", glyph="←", side="left", x=19.7, y=70.2),
    dict(id="RIGHT", label="Right", glyph="→", side="left", x=46.9, y=65.3),
    dict(id="LB", label="LB", side="left", x=28.0, y=44.9, back=True),
    dict(id="LT", label="LT", side="left", x=32.1, y=66.3, back=True),
    dict(id="L3", label="L3", side="left", x=20.9, y=21.3, r=12.4),
    dict(id="GUIDE", label="Guide", side="left", x=27.4, y=124.5),
    dict(id="A", label="A", side="right", x=252.6, y=44.6),
    dict(id="B", label="B", side="right", x=264.0, y=29.4),
    dict(id="X", label="X", side="right", x=241.3, y=29.4),
    dict(id="Y", label="Y", side="right", x=252.6, y=14.1),
    dict(id="RB", label="RB", side="right", x=252.8, y=45.0, back=True),
    dict(id="RT", label="RT", side="right", x=247.9, y=66.2, back=True),
    dict(id="R3", label="R3", side="right", x=241.7, y=74.6, r=12.9),
    dict(id="BACK", label="Back", side="right", x=238.3, y=104.9),
    dict(id="START", label="Start", side="right", x=252.9, y=126.6),
]
SWITCH_MM = 12  # switch body size

DEFAULT_BUTTONS = {
    "A": "A", "B": "B", "X": "X", "Y": "Y", "LB": "LB", "RB": "RB",
    "LT": "LT", "RT": "RT", "BACK": "BACK", "START": "START", "GUIDE": "GUIDE",
    "L3": "L3", "R3": "R3", "UP": "DPAD_UP", "DOWN": "DPAD_DOWN",
    "LEFT": "DPAD_LEFT", "RIGHT": "DPAD_RIGHT",
}
BUTTON_ORDER = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "BACK", "START",
                "GUIDE", "L3", "R3", "UP", "DOWN", "LEFT", "RIGHT"]

# Board outline (mm), same shape as the PCB
OUTLINE = [
    (1.0, 91.2), (1.0, 7.4), (1.5, 5.1), (2.7, 3.1), (4.4, 1.5), (6.7, 0.3),
    (9.0, 0.0), (269.2, 0.0), (271.5, 0.4), (273.8, 1.6), (275.5, 3.4),
    (276.7, 5.7), (277.0, 8.0), (277.0, 90.0), (277.8, 118.0), (275.9, 125.0),
    (272.2, 131.0), (266.9, 135.8), (260.4, 138.9), (253.5, 140.0),
    (246.4, 139.1), (240.0, 136.4), (234.6, 131.9), (231.2, 127.2),
    (228.9, 121.8), (226.0, 101.6), (225.0, 98.2), (223.4, 95.6), (221.3, 93.3),
    (218.8, 91.6), (215.7, 90.4), (212.2, 90.0), (65.8, 90.0), (62.0, 90.5),
    (58.5, 92.0), (55.6, 94.4), (53.4, 97.4), (52.0, 101.6), (49.1, 121.8),
    (46.8, 127.2), (43.5, 131.8), (38.8, 135.9), (33.0, 138.7), (26.8, 139.9),
    (20.6, 139.6), (14.7, 137.8), (9.2, 134.4), (4.9, 129.9), (1.9, 124.4),
    (0.5, 120.0), (0.0, 115.7),
]

# Colors
MASK = "#1f5b3b"
MASK_EDGE = "#164430"
SILK = "#f3f4ec"
GOLD = "#d9ad45"
GOLD_SOFT = "#7c8a3f"
BG = "#e7ebe4"


def defaults():
    return {
        "xiao_in_right_grip": True,
        "buttons": dict(DEFAULT_BUTTONS),
        "invert": {"LX": False, "LY": False, "RX": False, "RY": False},
        "swap_sticks": False,
        "deadzone": 0.06,
    }


def sanitize(obj):
    """Turns loaded JSON into a complete, valid mapping (bad values -> defaults)."""
    cfg = defaults()
    if not isinstance(obj, dict):
        raise ValueError("mapping.json must contain a JSON object")
    if isinstance(obj.get("xiao_in_right_grip"), bool):
        cfg["xiao_in_right_grip"] = obj["xiao_in_right_grip"]
    if isinstance(obj.get("swap_sticks"), bool):
        cfg["swap_sticks"] = obj["swap_sticks"]
    dz = obj.get("deadzone")
    if isinstance(dz, (int, float)) and not isinstance(dz, bool) and 0 <= dz <= 0.5:
        cfg["deadzone"] = float(dz)
    buttons = obj.get("buttons")
    if isinstance(buttons, dict):
        for k in DEFAULT_BUTTONS:
            if buttons.get(k) in CODE_TO_NAME:
                cfg["buttons"][k] = buttons[k]
    invert = obj.get("invert")
    if isinstance(invert, dict):
        for k in ("LX", "LY", "RX", "RY"):
            if isinstance(invert.get(k), bool):
                cfg["invert"][k] = invert[k]
    return cfg


def to_json_text(cfg):
    ordered = {
        "xiao_in_right_grip": cfg["xiao_in_right_grip"],
        "buttons": {k: cfg["buttons"][k] for k in BUTTON_ORDER},
        "invert": {k: cfg["invert"][k] for k in ("LX", "LY", "RX", "RY")},
        "swap_sticks": cfg["swap_sticks"],
        "deadzone": round(cfg["deadzone"], 2),
    }
    return json.dumps(ordered, indent=2) + "\n"


def find_circuitpy():
    """Returns the CIRCUITPY drive's folder, or None if it isn't plugged in."""
    if sys.platform.startswith("win"):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetErrorMode(0x0001)  # no "insert a disk" popups for empty drives
        mask = kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if not mask & (1 << i):
                continue
            root = letter + ":\\"
            label = ctypes.create_unicode_buffer(261)
            ok = kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root), label, 261, None, None, None, None, 0)
            if ok and label.value == "CIRCUITPY":
                return root
        return None
    if sys.platform == "darwin":
        candidates = ["/Volumes/CIRCUITPY"]
    else:
        candidates = (glob.glob("/media/*/CIRCUITPY") + glob.glob("/run/media/*/CIRCUITPY")
                      + ["/media/CIRCUITPY", "/mnt/CIRCUITPY"])
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def write_file(path, text):
    # fsync so the drive really has it before you unplug
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


# ---------------------------------------------------------------- app

class GamepadStudio:
    SCALE = 3.0
    PAD = 14  # canvas margin in pixels

    def __init__(self, root):
        self.root = root
        self.cfg = defaults()
        self.selected = None
        self.drive = None          # CIRCUITPY folder, when found
        self.manual_file = None    # a mapping.json opened by hand
        self.dirty = False

        root.title("Gamepad Studio")
        root.configure(bg=BG)
        root.minsize(900, 700)

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", background=BG)
        style.configure("TLabel", background=BG)
        style.configure("TCheckbutton", background=BG)
        style.configure("TRadiobutton", background=BG)
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, font=("TkDefaultFont", 10, "bold"))
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Muted.TLabel", foreground="#56645a")
        style.configure("Changed.TCombobox", fieldbackground="#f3e3b5")
        style.configure("Accent.TButton", font=("TkDefaultFont", 10, "bold"))

        self.build_header()
        self.build_board()
        self.build_controls()
        self.build_footer()

        self.refresh_drive(load=True)
        self.set_view("front")
        self.render()
        self.root.after(2000, self.poll_drive)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----- layout

    def build_header(self):
        top = ttk.Frame(self.root, padding=(16, 12, 16, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Gamepad Studio", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Open file…", command=self.open_file).pack(side="right")
        ttk.Button(top, text="Find controller", command=lambda: self.refresh_drive(load=True)).pack(side="right", padx=6)
        self.drive_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.drive_var, style="Muted.TLabel",
                  padding=(16, 0, 16, 6)).pack(fill="x")

    def build_board(self):
        self.view = "front"
        self.view_var = tk.StringVar(value="front")
        toggle = ttk.Frame(self.root, padding=(16, 0, 16, 4))
        toggle.pack(fill="x")
        ttk.Label(toggle, text="Board side:").pack(side="left")
        for txt, val in (("Front", "front"), ("Back", "back")):
            ttk.Radiobutton(toggle, text=txt, value=val, variable=self.view_var,
                            command=lambda v=val: self.set_view(v)).pack(side="left", padx=(8, 0))
        w = int(278 * self.SCALE + 2 * self.PAD)
        h = int(141 * self.SCALE + 2 * self.PAD)
        self.canvas = tk.Canvas(self.root, width=w, height=h, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=16)
        s, p = self.SCALE, self.PAD

        pts = [c for (x, y) in OUTLINE for c in (x * s + p, y * s + p)]
        self.canvas.create_polygon(pts, fill=MASK, outline=MASK_EDGE, width=2)
        self.canvas.create_rectangle(56 * s + p, 4 * s + p, 222 * s + p, 86 * s + p,
                                     outline="#7fa58f", dash=(6, 4))
        self.canvas.create_text(139 * s + p, 45 * s + p, text="phone", fill="#7fa58f",
                                font=("TkDefaultFont", 14, "bold"))
        self.canvas.create_text(139 * s + p, 80 * s + p,
                                text="switch to Back to see LB, LT, RB and RT",
                                fill="#7fa58f", font=("TkDefaultFont", 9))

        self.pad_items = {}
        for b in PHYS:
            x, y = b["x"] * s + p, b["y"] * s + p
            dash = (4, 3) if b.get("back") else None
            if "r" in b:
                r = b["r"] * s
                shape = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                                outline=SILK, width=2, fill=MASK)
            else:
                h = SWITCH_MM * s / 2
                shape = self.canvas.create_rectangle(x - h, y - h, x + h, y + h,
                                                     outline=SILK, width=2, fill=MASK, dash=dash)
            label = self.canvas.create_text(x, y - 5, text=b.get("glyph", b["label"]), fill=SILK,
                                            font=("TkDefaultFont", 9, "bold"))
            sends = self.canvas.create_text(x, y + 9, text="", fill=GOLD,
                                            font=("TkDefaultFont", 8, "bold"))
            tag = "back" if b.get("back") else "front"
            for item in (shape, label, sends):
                self.canvas.addtag_withtag(tag, item)
            for item in (shape, label):
                self.canvas.tag_bind(item, "<Button-1>", lambda e, bid=b["id"]: self.select(bid, focus=True))
                self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
                self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.config(cursor=""))
            self.pad_items[b["id"]] = (shape, label, sends)

    def set_view(self, view):
        """Front shows the face buttons; Back shows LB, LT, RB and RT."""
        self.view = view
        self.view_var.set(view)
        top, bottom = ("back", "front") if view == "back" else ("front", "back")
        self.canvas.tag_raise(top)
        self.canvas.itemconfigure(bottom, state="disabled")
        self.canvas.itemconfigure(top, state="normal")
        self.render_board()

    def build_controls(self):
        body = ttk.Frame(self.root, padding=(16, 8))
        body.pack(fill="both", expand=True)
        names = [name for _, name in OUTPUTS]
        self.combos = {}
        self.row_labels = {}

        for col, (title, side) in enumerate((("Left side", "left"), ("Right side", "right"))):
            frame = ttk.LabelFrame(body, text=title, padding=8)
            frame.grid(row=0, column=col, sticky="nsew", padx=(0, 12))
            for row, b in enumerate(x for x in PHYS if x["side"] == side):
                lab = ttk.Label(frame, text=b["label"], width=7)
                lab.grid(row=row, column=0, sticky="w", pady=2)
                cb = ttk.Combobox(frame, values=names, state="readonly", width=22)
                cb.grid(row=row, column=1, sticky="ew", pady=2)
                cb.bind("<<ComboboxSelected>>", lambda e, bid=b["id"]: self.on_combo(bid))
                cb.bind("<FocusIn>", lambda e, bid=b["id"]: self.select(bid))
                self.combos[b["id"]] = cb
                self.row_labels[b["id"]] = lab

        settings = ttk.LabelFrame(body, text="Sticks and board", padding=8)
        settings.grid(row=0, column=2, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)

        ttk.Label(settings, text="Flip a stick axis").grid(row=0, column=0, columnspan=2, sticky="w")
        self.inv_vars = {}
        labels = {"LX": "Left stick, left/right", "LY": "Left stick, up/down",
                  "RX": "Right stick, left/right", "RY": "Right stick, up/down"}
        for i, k in enumerate(("LX", "LY", "RX", "RY")):
            v = tk.BooleanVar()
            ttk.Checkbutton(settings, text=labels[k], variable=v,
                            command=lambda k=k, v=v: self.set_value(("invert", k), v.get())
                            ).grid(row=1 + i, column=0, columnspan=2, sticky="w")
            self.inv_vars[k] = v

        self.swap_var = tk.BooleanVar()
        ttk.Checkbutton(settings, text="Swap left and right sticks", variable=self.swap_var,
                        command=lambda: self.set_value(("swap_sticks",), self.swap_var.get())
                        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(settings, text="Deadzone").grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.dz_var = tk.IntVar()
        self.dz_label = ttk.Label(settings, width=5)
        self.dz_label.grid(row=6, column=1, sticky="e", pady=(10, 0))
        ttk.Scale(settings, from_=0, to=20, orient="horizontal", variable=self.dz_var,
                  command=self.on_deadzone).grid(row=7, column=0, columnspan=2, sticky="ew")

        ttk.Label(settings, text="XIAO position").grid(row=8, column=0, sticky="w", pady=(10, 0))
        self.side_var = tk.StringVar()
        for i, (txt, val) in enumerate((("Right grip", "right"), ("Left grip", "left"))):
            ttk.Radiobutton(settings, text=txt, value=val, variable=self.side_var,
                            command=lambda: self.set_value(("xiao_in_right_grip",), self.side_var.get() == "right")
                            ).grid(row=9 + i, column=0, columnspan=2, sticky="w")
        settings.columnconfigure(0, weight=1)

    def build_footer(self):
        bar = ttk.Frame(self.root, padding=(16, 4, 16, 14))
        bar.pack(fill="x")
        self.save_btn = ttk.Button(bar, text="Save to controller", style="Accent.TButton", command=self.save)
        self.save_btn.pack(side="left")
        ttk.Button(bar, text="Save as file…", command=self.save_as).pack(side="left", padx=6)
        ttk.Button(bar, text="Reset to defaults", command=self.reset).pack(side="left")
        self.status_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left", padx=12)

    # ----- state changes

    def select(self, bid, focus=False):
        self.selected = bid
        is_back = any(b["id"] == bid and b.get("back") for b in PHYS)
        if (self.view == "back") != is_back:
            self.set_view("back" if is_back else "front")
        self.render_board()
        for k, lab in self.row_labels.items():
            lab.configure(font=("TkDefaultFont", 10, "bold") if k == bid else ("TkDefaultFont", 10))
        if focus:
            self.combos[bid].focus_set()

    def on_combo(self, bid):
        self.cfg["buttons"][bid] = NAME_TO_CODE[self.combos[bid].get()]
        self.changed()

    def on_deadzone(self, _value):
        v = int(round(float(self.dz_var.get())))
        if round(self.cfg["deadzone"] * 100) != v:
            self.cfg["deadzone"] = v / 100
            self.changed()
        self.dz_label.configure(text=f"{v}%")

    def set_value(self, path, value):
        target = self.cfg
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        self.changed()

    def changed(self):
        self.dirty = True
        self.render()
        self.status_var.set("Unsaved changes")

    def reset(self):
        self.cfg = defaults()
        self.changed()

    # ----- drawing

    def render_board(self):
        dim_outline, dim_fill = "#5f8a73", MASK
        for b in PHYS:
            bid = b["id"]
            shape, label, sends = self.pad_items[bid]
            active = (self.view == "back") == bool(b.get("back"))
            out = self.cfg["buttons"][bid]
            changed = out != DEFAULT_BUTTONS[bid]
            if not active:
                self.canvas.itemconfigure(shape, fill=dim_fill, outline=dim_outline)
                self.canvas.itemconfigure(label, fill=dim_outline,
                                          text="" if b.get("back") else b.get("glyph", b["label"]))
                self.canvas.itemconfigure(sends, text="")
                continue
            self.canvas.itemconfigure(label, text=b.get("glyph", b["label"]))
            if bid == self.selected:
                self.canvas.itemconfigure(shape, fill=GOLD, outline=GOLD)
                self.canvas.itemconfigure(label, fill="#1b1405")
                self.canvas.itemconfigure(sends, fill="#1b1405")
            else:
                self.canvas.itemconfigure(shape, fill=GOLD_SOFT if changed else MASK,
                                          outline=GOLD if changed else SILK)
                self.canvas.itemconfigure(label, fill=SILK)
                self.canvas.itemconfigure(sends, fill=GOLD)
            self.canvas.itemconfigure(sends, text=("→ " + SHORT[out]) if changed else "")

    def render(self):
        self.render_board()
        for bid, cb in self.combos.items():
            out = self.cfg["buttons"][bid]
            cb.set(CODE_TO_NAME[out])
            cb.configure(style="Changed.TCombobox" if out != DEFAULT_BUTTONS[bid] else "TCombobox")
        for k, v in self.inv_vars.items():
            v.set(self.cfg["invert"][k])
        self.swap_var.set(self.cfg["swap_sticks"])
        dz = int(round(self.cfg["deadzone"] * 100))
        self.dz_var.set(dz)
        self.dz_label.configure(text=f"{dz}%")
        self.side_var.set("right" if self.cfg["xiao_in_right_grip"] else "left")

    # ----- files

    def target_path(self):
        if self.drive:
            return os.path.join(self.drive, "mapping.json")
        return self.manual_file

    def load_from(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                self.cfg = sanitize(json.load(f))
            self.dirty = False
            self.render()
            self.status_var.set(f"Loaded {os.path.basename(path)}")
        except FileNotFoundError:
            self.cfg = defaults()
            self.render()
            self.status_var.set("No mapping.json yet. Saving will create one.")
        except (OSError, ValueError) as e:
            messagebox.showerror("Couldn’t read mapping", f"{path}\n\n{e}\n\nShowing the default layout instead.")
            self.cfg = defaults()
            self.render()

    def refresh_drive(self, load=False):
        found = find_circuitpy()
        was = self.drive
        self.drive = found
        if found:
            self.drive_var.set(f"Controller found at {found}")
            if load or (was is None and not self.dirty):
                self.load_from(os.path.join(found, "mapping.json"))
        elif self.manual_file:
            self.drive_var.set(f"Editing {self.manual_file} (controller not connected)")
        else:
            self.drive_var.set("Controller not found. Hold Guide while plugging it in, "
                               "or use Open file… to edit a saved mapping.")

    def poll_drive(self):
        self.refresh_drive()
        self.root.after(2000, self.poll_drive)

    def open_file(self):
        path = filedialog.askopenfilename(title="Open mapping.json",
                                          filetypes=[("Mapping", "*.json"), ("All files", "*.*")])
        if path:
            self.manual_file = path
            self.load_from(path)
            self.refresh_drive()

    def save(self):
        path = self.target_path()
        if not path:
            messagebox.showinfo("Controller not found",
                                "Hold Guide while plugging the controller into this computer, "
                                "then click Save again.\n\nOr use Save as file… to keep it for later.")
            return
        try:
            write_file(path, to_json_text(self.cfg))
        except OSError as e:
            messagebox.showerror("Couldn’t save", f"{path}\n\n{e}")
            return
        self.dirty = False
        where = "the controller" if self.drive else os.path.basename(path)
        self.status_var.set(f"Saved to {where}. It’s active now.")

    def save_as(self):
        path = filedialog.asksaveasfilename(title="Save mapping as", initialfile="mapping.json",
                                            defaultextension=".json",
                                            filetypes=[("Mapping", "*.json")])
        if not path:
            return
        try:
            write_file(path, to_json_text(self.cfg))
            self.status_var.set(f"Saved {os.path.basename(path)}")
        except OSError as e:
            messagebox.showerror("Couldn’t save", f"{path}\n\n{e}")

    def on_close(self):
        if self.dirty and not messagebox.askyesno("Unsaved changes",
                                                  "You have changes that aren’t saved. Quit anyway?"):
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    GamepadStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
