EDF6 Loadouts
=============

Save what each class has equipped under a name and load it back whenever you
want, even for another class: it writes the 6 slots and switches the active
class. F2 opens the panel.

REQUIREMENTS
------------
  - EDFModLoader: https://github.com/BlueAmulet/EDFModLoader
  - EDF6 Compendium v0.4.0 or newer:
    https://github.com/Divineridh/EDF6-Compendium/releases

This mod is a Compendium module: the Compendium draws the panel, reads the key
and provides the weapon list. Without it nothing shows up.

Tested with a mod that gives each class 6 weapon slots. Without that mod the
equipment may not be found; in that case the panel says so and writes nothing.

INSTALL
-------
Copy the Mods folder from this package over the game's, the one next to
EDF6.exe:

    EARTH DEFENSE FORCE 6\Mods\Plugins\EDF6Loadouts.dll
    EARTH DEFENSE FORCE 6\Mods\Loadouts\config.ini

Coming from Compendium 0.3.0 or older: your saved loadouts are copied from
Mods\Compendium\loadouts.tsv to Mods\Loadouts\loadouts.tsv the first time.

USING IT
--------
  Ctrl S   save what is equipped as a new loadout
  Enter    load the selected loadout
  R        rename it
  Del      delete it
  Q / E    previous / next class
  F2       close

Loading in the lobby applies right away; open Class/Equipment to see the
character change. Loading during a mission applies from the next one.

KEY
---
F2 by default. Change it in Mods\Loadouts\config.ini: remove the # from the
"key" line and put the virtual-key code you want.

IF IT DOESN'T SHOW UP
---------------------
With the Compendium installed, everything is written to Compendium.log, next
to EDF6.exe:

  - "modulos: registrado Loadouts"   the Compendium accepted it
  - "loadouts: table at ..."          it found the equipment in memory

If the first one is missing, check that the Compendium is v0.4.0 or newer. If
the Compendium isn't installed, the message goes to Loadouts.log.
