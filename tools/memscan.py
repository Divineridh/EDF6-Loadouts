"""Scanner de memoria casero (estilo Cheat Engine) para localizar el ID del
arma equipada en EDF6.exe, via ctypes + ReadProcessMemory. Sin dependencias
externas.

Uso:
    python memscan.py first  <pid> <valor_i32> <out.pkl>
    python memscan.py next   <pid> <valor_i32> <in.pkl>  <out.pkl>
    python memscan.py show   <pid> <in.pkl>
    python memscan.py peek   <pid> <address_hex>
    python memscan.py poke   <pid> <address_hex> <valor_i32>
    python memscan.py dump   <pid> <address_hex> <bytes_antes> <bytes_despues>
    python memscan.py findptr <pid> <address_hex> <max_offset_hex>
    python memscan.py findtable <pid>
    python memscan.py loadout_save <pid> <address_hex> <nombre> <loadouts.json>
    python memscan.py loadout_load <pid> <address_hex> <nombre> <loadouts.json>
"""
import ctypes
import json
import os
import pickle
import re
import struct
import sys
from ctypes import wintypes as wt

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01

k32 = ctypes.windll.kernel32


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("PartitionId", wt.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


def open_process(pid, write=False):
    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if write:
        access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
    h = k32.OpenProcess(access, False, pid)
    if not h:
        raise SystemExit("no pude abrir el proceso %d (correr como admin?)" % pid)
    return h


def write(h, addr, data):
    n = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))
    return ok and n.value == len(data)


def regions(h):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if (
            mbi.State == MEM_COMMIT
            and mbi.Type == MEM_PRIVATE
            and not (mbi.Protect & PAGE_GUARD)
            and mbi.Protect != PAGE_NOACCESS
            and mbi.RegionSize > 0
        ):
            yield mbi.BaseAddress or 0, mbi.RegionSize
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr <= 0:
            break


def read(h, base, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(n))
    if not ok:
        return b""
    return buf.raw[: n.value]


def scan_value(h, value):
    needle = struct.pack("<i", value)
    hits = []
    for base, size in regions(h):
        data = read(h, base, size)
        if not data:
            continue
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            if i % 4 == 0:
                hits.append(base + i)
            start = i + 1
    return hits


def filter_addresses(h, addresses, value):
    needle = struct.pack("<i", value)
    out = []
    for addr in addresses:
        data = read(h, addr, 4)
        if data == needle:
            out.append(addr)
    return out


def cmd_first(pid, value, outfile):
    h = open_process(pid)
    hits = scan_value(h, value)
    with open(outfile, "wb") as f:
        pickle.dump(hits, f)
    print("candidatos: %d -> %s" % (len(hits), outfile))


def cmd_next(pid, value, infile, outfile):
    h = open_process(pid)
    with open(infile, "rb") as f:
        addresses = pickle.load(f)
    hits = filter_addresses(h, addresses, value)
    with open(outfile, "wb") as f:
        pickle.dump(hits, f)
    print("candidatos: %d (de %d) -> %s" % (len(hits), len(addresses), outfile))
    for a in hits[:50]:
        print(hex(a))


def cmd_show(pid, infile):
    h = open_process(pid)
    with open(infile, "rb") as f:
        addresses = pickle.load(f)
    print("total: %d" % len(addresses))
    for a in addresses[:50]:
        data = read(h, a, 4)
        val = struct.unpack("<i", data)[0] if len(data) == 4 else None
        print(hex(a), val)


def cmd_peek(pid, addr_hex):
    h = open_process(pid)
    addr = int(addr_hex, 16)
    data = read(h, addr, 4)
    val = struct.unpack("<i", data)[0] if len(data) == 4 else None
    print(hex(addr), val)


def cmd_loadout_save(pid, addr_hex, name, file):
    h = open_process(pid)
    addr = int(addr_hex, 16)
    data = read(h, addr, 4)
    value = struct.unpack("<i", data)[0]
    try:
        with open(file, "r", encoding="utf-8") as f:
            store = json.load(f)
    except FileNotFoundError:
        store = {}
    store[name] = value
    with open(file, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)
    print("guardado loadout %r = weapon1 %d" % (name, value))


def cmd_loadout_load(pid, addr_hex, name, file):
    h = open_process(pid, write=True)
    addr = int(addr_hex, 16)
    with open(file, "r", encoding="utf-8") as f:
        store = json.load(f)
    value = store[name]
    ok = write(h, addr, struct.pack("<i", value))
    print("cargado loadout %r -> weapon1 %d :" % (name, value), "OK" if ok else "FALLO")


def cmd_poke(pid, addr_hex, value):
    h = open_process(pid, write=True)
    addr = int(addr_hex, 16)
    value = int(value)
    before = read(h, addr, 4)
    ok = write(h, addr, struct.pack("<i", value))
    after = read(h, addr, 4)
    print("escritura:", "OK" if ok else "FALLO")
    print("antes:", struct.unpack("<i", before)[0] if len(before) == 4 else before)
    print("ahora:", struct.unpack("<i", after)[0] if len(after) == 4 else after)


def cmd_dump(pid, addr_hex, before, after):
    h = open_process(pid)
    addr = int(addr_hex, 16)
    before = int(before)
    after = int(after)
    start = addr - before
    data = read(h, start, before + after)
    for off in range(0, len(data) - 3, 4):
        val = struct.unpack("<i", data[off : off + 4])[0]
        a = start + off
        marker = "  <== target" if a == addr else ""
        print("%016x  %+6d  i32=%-12d hex=%08x%s" % (a, a - addr, val, val & 0xFFFFFFFF, marker))


def all_regions(h):
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if (
            mbi.State == MEM_COMMIT
            and not (mbi.Protect & PAGE_GUARD)
            and mbi.Protect != PAGE_NOACCESS
            and mbi.RegionSize > 0
        ):
            yield mbi.BaseAddress or 0, mbi.RegionSize, mbi.Type
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if addr <= 0:
            break


WEAPON_COUNT = 1564
CATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "EDF6-UI", "build", "catalog.json")


def load_catalog():
    try:
        with open(CATALOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


CLASSES = ["Ranger", "Wing Diver", "Air Raider", "Fencer"]
SLOTS_PER_CLASS = 6
WEAPON_SLOTS_PER_CLASS = 4
NONZERO_WEAPON_DWORD = rb"(?:[\x01-\xff][\x00-\x06]|\x00[\x01-\x06])\x00\x00"
TABLE_SIGNATURE = re.compile(
    rb"[\x00-\x03]\x00\x00\x00....(?:%s){%d}\xff\xff\xff\xff"
    % (NONZERO_WEAPON_DWORD, len(CLASSES) * SLOTS_PER_CLASS),
    re.DOTALL,
)


def parse_table(blob):
    active_class, unknown = struct.unpack_from("<ii", blob, 0)
    slots = struct.unpack_from("<%di" % (len(CLASSES) * SLOTS_PER_CLASS), blob, 8)
    return active_class, unknown, [list(slots[i * SLOTS_PER_CLASS : (i + 1) * SLOTS_PER_CLASS]) for i in range(len(CLASSES))]


def weapons_match_classes(loadouts, catalog):
    for class_name, slots in zip(CLASSES, loadouts):
        for weapon in slots[:WEAPON_SLOTS_PER_CLASS]:
            if weapon >= WEAPON_COUNT or catalog[weapon]["class"] != class_name:
                return False
    return True


def find_tables(h, catalog):
    for base, size in regions(h):
        data = read(h, base, size)
        if not data:
            continue
        for m in TABLE_SIGNATURE.finditer(data):
            if m.start() % 4:
                continue
            active_class, unknown, loadouts = parse_table(m.group())
            if weapons_match_classes(loadouts, catalog):
                yield base + m.start(), active_class, unknown, loadouts


def cmd_findtable(pid):
    h = open_process(pid)
    catalog = load_catalog()
    if catalog is None:
        raise SystemExit("falta %s (correr EDF6-UI/tools/weapons.py)" % CATALOG)
    found = 0
    for addr, active_class, unknown, loadouts in find_tables(h, catalog):
        found += 1
        print("== %016x  clase activa=%d (%s)  desconocido=%d" % (addr, active_class, CLASSES[active_class], unknown))
        for class_name, slots in zip(CLASSES, loadouts):
            print("   %s" % class_name)
            for i, weapon in enumerate(slots):
                print("      %d  %5d  %s" % (i + 1, weapon, catalog[weapon]["name"] if weapon < WEAPON_COUNT else "?"))
    print("tablas: %d" % found)


def cmd_findptr(pid, target_hex, max_offset):
    h = open_process(pid)
    target = int(target_hex, 16)
    max_offset = int(max_offset, 0)
    hits = []
    for base, size, rtype in all_regions(h):
        data = read(h, base, size)
        if not data:
            continue
        for off in range(0, len(data) - 7, 8):
            val = struct.unpack("<Q", data[off : off + 8])[0]
            delta = target - val
            if 0 <= delta <= max_offset:
                hits.append((base + off, val, delta, rtype))
    print("punteros candidatos: %d" % len(hits))
    for addr, val, delta, rtype in hits[:80]:
        print("%016x  ->  %016x  (+%d)  type=%s" % (addr, val, delta, "PRIVATE" if rtype == MEM_PRIVATE else "MAPPED/IMAGE"))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(1)
    op = args[0]
    if op == "first":
        cmd_first(int(args[1]), int(args[2]), args[3])
    elif op == "next":
        cmd_next(int(args[1]), int(args[2]), args[3], args[4])
    elif op == "show":
        cmd_show(int(args[1]), args[2])
    elif op == "peek":
        cmd_peek(int(args[1]), args[2])
    elif op == "dump":
        cmd_dump(int(args[1]), args[2], args[3], args[4])
    elif op == "findptr":
        cmd_findptr(int(args[1]), args[2], args[3])
    elif op == "findtable":
        cmd_findtable(int(args[1]))
    elif op == "poke":
        cmd_poke(int(args[1]), args[2], args[3])
    elif op == "loadout_save":
        cmd_loadout_save(int(args[1]), args[2], args[3], args[4])
    elif op == "loadout_load":
        cmd_loadout_load(int(args[1]), args[2], args[3], args[4])
    else:
        print(__doc__)
        raise SystemExit(1)
