"""MVP de loadouts (solo arma 1) con hotkeys globales.

F9  -> guarda el arma 1 actual como loadout 1
F10 -> guarda el arma 1 actual como loadout 2
F11 -> carga loadout 1
F12 -> carga loadout 2

Uso:
    python loadout_hotkeys.py <pid> <address_hex> <loadouts.json>
"""
import ctypes
import ctypes.wintypes
import json
import struct
import sys

import memscan

user32 = ctypes.windll.user32

VK_F9, VK_F10, VK_F11, VK_F12 = 0x78, 0x79, 0x7A, 0x7B
HOTKEYS = {
    1: (VK_F9, "guardar loadout 1"),
    2: (VK_F10, "guardar loadout 2"),
    3: (VK_F11, "cargar loadout 1"),
    4: (VK_F12, "cargar loadout 2"),
}
SAVE_SLOTS = {1: "1", 2: "2"}
LOAD_SLOTS = {3: "1", 4: "2"}

WM_HOTKEY = 0x0312


def load_store(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_store(file, store):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def main():
    pid = int(sys.argv[1])
    addr = int(sys.argv[2], 16)
    file = sys.argv[3]

    for hk_id, (vk, _) in HOTKEYS.items():
        ok = user32.RegisterHotKey(None, hk_id, 0, vk)
        if not ok:
            print("no pude registrar hotkey", hk_id, "(en uso por otra app?)")

    print("escuchando F9/F10 (guardar 1/2) y F11/F12 (cargar 1/2). Ctrl+C para salir.")
    sys.stdout.flush()

    msg = ctypes.wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                store = load_store(file)
                if hk_id in SAVE_SLOTS:
                    h = memscan.open_process(pid)
                    data = memscan.read(h, addr, 4)
                    value = struct.unpack("<i", data)[0]
                    store[SAVE_SLOTS[hk_id]] = value
                    save_store(file, store)
                    print("[guardado] loadout %s = weapon1 %d" % (SAVE_SLOTS[hk_id], value))
                elif hk_id in LOAD_SLOTS:
                    slot = LOAD_SLOTS[hk_id]
                    if slot not in store:
                        print("[cargar] loadout %s vacio" % slot)
                        continue
                    value = store[slot]
                    h = memscan.open_process(pid, write=True)
                    ok = memscan.write(h, addr, struct.pack("<i", value))
                    print("[cargado] loadout %s -> weapon1 %d :" % (slot, value), "OK" if ok else "FALLO")
                sys.stdout.flush()
    finally:
        for hk_id in HOTKEYS:
            user32.UnregisterHotKey(None, hk_id)


if __name__ == "__main__":
    main()
