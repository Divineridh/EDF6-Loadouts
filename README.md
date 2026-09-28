# EDF6 Loadouts

Named loadouts for Earth Defense Force 6: save what each class has equipped, load it back whenever
you want, even for another class. It writes the equipment straight into the game's memory. F2 opens
the panel.

A module of [EDF6-Compendium](https://github.com/Divineridh/EDF6-Compendium): the Compendium owns
the Present hook, the input hooks and the weapon catalog, and this DLL registers a panel with it
(module API v3). The panel lived inside the Compendium up to its 0.3.0.

## Using it

| Key | Action |
|-----|--------|
| Ctrl S | save what the viewed class has equipped as a new loadout |
| Enter | load the selected loadout: writes its 6 slots and switches the active class |
| R | rename |
| Del | delete (asks first) |
| Q / E | previous / next class |
| ↑ / ↓ | move through the list |
| F2 | close |

In the lobby the character doesn't refresh by itself: open Class/Equipment to see it. A mission
started straight from the lobby already uses the new class and weapons. Loaded during a mission, it
applies from the next one.

Loadouts are saved in `Mods\Loadouts\loadouts.tsv`. Every slot stores the weapon index and its
name, so if an update shifts the indices the loadout is flagged as outdated instead of silently
equipping another weapon. On the first run, `Mods\Compendium\loadouts.tsv` from older Compendium
versions is copied over.

The key is set in `Mods\Loadouts\config.ini` with `key=0x71` (virtual-key code).

## Requirements

- [EDFModLoader](https://github.com/BlueAmulet/EDFModLoader)
- EDF6 Compendium 0.4.0 or newer

Tested with a mod that gives each class 6 weapon slots. The table layout below is with that mod;
the vanilla game may differ, in which case the table isn't found and nothing is written.

## The equipment table

A single heap structure holds the active class and the equipment of all four classes, as int32s:

| offset | content |
|--------|---------|
| +0 | active class: 0 Ranger, 1 Wing Diver, 2 Air Raider, 3 Fencer |
| +4 | unknown (always 3 so far) |
| +8 | Ranger: 6 slots |
| +32 | Wing Diver: 6 slots |
| +56 | Air Raider: 6 slots |
| +80 | Fencer: 6 slots |
| +104 | `-1` |

Each class has **4 weapons and 2 support items**, in the same order as the lobby's class card. Each
slot is the **catalog index** (0-1563, the order of `WEAPON/WEAPONTABLE.SGO`), which is the id the
engine uses directly.

An unequipped slot holds a placeholder, not `-1`: a hidden catalog entry (305, which the game shows
as "No Equipment"; 866, 867 and 1262 are the other hidden ones) or, in a support slot, 1362, which
the game shows as "Empty" for every class but Fencer (for Fencer it is Gunner's Exoskeleton).

The table is found by scanning the process's private read-write memory for that signature, with
every slot checked against its class. It takes around 400 ms. The address is cached and the
signature re-checked on every read, since it moves between sessions. The rules:

- a slot is empty or an item of the class, and each class has at least one weapon;
- Ranger and Air Raider share some items with the weapon-slot mod: vehicles (e.g. EF31 Nereid,
  listed as Ranger) go in either one's support slots, and Ranger turrets (Support Place Gun) in Air
  Raider's weapon slots;
- support slots are checked too, which rejects scan windows a few dwords off the real table;
- +4 isn't `-1`. The game also keeps an all-empty template with the same layout (placeholders and
  the first weapon of each category) whose +4 is `-1`; the real table's has been 0 or 3.

A save made with the vanilla config and then loaded with the weapon-slot mod can have items in
unexpected slots (e.g. Wing Diver's core in W4, since vanilla Wing Diver has only 4 slots).

Verified in game:

- writing a slot re-equips the weapon, for the active class and for the others;
- writing +0 switches the class;
- writes reach the save once the game saves after them;
- writing during a mission leaves the deployed character alone and applies from the next mission.

Still unknown: the int32 at +4, and how to refresh the lobby character without opening the menu.

## Build

```bash
build.bat
```

VS2019 Build Tools (MSVC 14.29). Dependencies aren't in the repo; clone them into `deps/`. **imgui
must be the same commit the Compendium is built with**, or the Compendium refuses the module (it
compares the imgui version and struct layout at registration):

```bash
git clone https://github.com/ocornut/imgui          deps/imgui
git clone https://github.com/Quarri6343/EDF6Plugins deps/EDF6Plugins
```

`src/edf6_overlay_api.h` is a copy of the Compendium's; keep them identical.

```bash
python tools/package.py
```

Writes `EDF6Loadouts.zip` to `../builds/` and refuses to package if a source file is newer than the
DLL.

## Diagnostics

Once registered, everything goes to `Compendium.log` with the `loadouts:` prefix. `modules:
registered Loadouts` means the Compendium accepted it; `loadouts: table at ...` that the equipment
was found. Before registering, or without the Compendium, messages go to `Loadouts.log`.

## Research tools

`tools/memscan.py` is how the table was found, from outside the process:

```bash
python tools/memscan.py findtable <pid>
python tools/memscan.py dump    <pid> <address_hex> <bytes_before> <bytes_after>
python tools/memscan.py peek    <pid> <address_hex>
python tools/memscan.py poke    <pid> <address_hex> <value_i32>
python tools/memscan.py findptr <pid> <address_hex> <max_offset_hex>
python tools/memscan.py first   <pid> <current_weapon_id> pass1.pkl
python tools/memscan.py next    <pid> <new_weapon_id> pass1.pkl pass2.pkl
```

`findtable` takes about 90 s: nearly all of it is `ReadProcessMemory` copying the heap across
processes. `tools/loadout_hotkeys.py` is the first proof of concept (weapon 1 only, F9-F12).
