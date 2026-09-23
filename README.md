# EDF6 Loadouts

Guardar y cargar el arma equipada en Earth Defense Force 6 con hotkeys, escribiendo directo en la
memoria del proceso. Sin Cheat Engine ni terceros — herramientas propias en `tools/`.

Juego: `C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6` (proceso `EDF6.exe`, x64,
sin WOW64).

## Estado: MVP de una sola arma

Hoy solo cubre **weapon 1**. Sirvió para validar que el enfoque (memory hacking sin hookear
`EDF.dll`) es viable antes de invertir en un plugin C++ inyectado.

## Hallazgos

**El índice del catálogo de armas es el ID real que usa el motor en runtime.** El catálogo sale de
[EDF6-UI](../EDF6-UI) (`tools/weapons.py` genera `build/catalog.json`, mismo orden que
`WEAPON/WEAPONTABLE.SGO`). Se confirmó equipando 3 armas de Air Raider con IDs conocidos
(Limpet Gun=1041, Heavy Bomber Phobos Z Plan 4=1005, Vulcan Cannon M1=964) y acotando por
descarte: escanear memoria privada (`MEM_PRIVATE`) buscando el valor exacto tras equipar la
primera arma (1576 candidatos), filtrar por el valor tras equipar la segunda (2 candidatos), y
filtrar de nuevo tras equipar la tercera (1 candidato único y estable).

**Hay una tabla de ~40-56 entradas int32** alrededor de esa dirección: una por categoría de arma,
con el índice de la última arma seleccionada en esa categoría, compartida entre clases (una entrada
catalogada como "Ranger" apareció mezclada entre entradas de Air Raider) y rellena con `-1` para
categorías sin selección todavía. Esta misma tabla alimenta la tarjeta de perfil del jugador ("battle
card"): las 6 armas que muestra son 6 entradas consecutivas de esta tabla.

**Escribir la entrada re-equipa el arma de verdad**, confirmado visualmente en el HUD/pantalla. No
hace falta hookear ninguna función de `EDF.dll` ni sincronizar munición o sonido aparte — el motor
lee esta tabla como fuente de verdad.

## Limitación pendiente: la dirección no es estable

La dirección se ubica hoy cruzando procesos (`ReadProcessMemory` desde afuera) y **cambia en cada
arranque del juego** (heap, ASLR). Un pointer scan encontró una capa intermedia en heap (varias
copias del mismo patrón, probablemente una estructura de jugador) sin resolver hasta un offset
estable del módulo — haría falta un debugger tipo x64dbg (no instalado) para seguir esa cadena con
un breakpoint de acceso.

Alternativa más simple, pendiente de implementar: un plugin C++ inyectado (como
[EDF6-Compendium](../EDF6-Compendium), que ya usa MinHook + imgui) puede repetir este mismo escaneo
**desde adentro** del proceso al cargar, sin cruzar procesos ni resolver punteros multinivel.

## Herramientas

```bash
# localizar la tabla (repetir cada partida hasta resolver el pointer path):
python tools/memscan.py first  <pid> <id_arma_actual>     pass1.pkl
python tools/memscan.py next   <pid> <id_nueva_arma>      pass1.pkl pass2.pkl
python tools/memscan.py next   <pid> <id_otra_arma_mas>   pass2.pkl pass3.pkl   # hasta 1 candidato

# inspeccionar:
python tools/memscan.py dump    <pid> <address_hex> <bytes_antes> <bytes_despues>
python tools/memscan.py findptr <pid> <address_hex> <max_offset_hex>
python tools/memscan.py peek    <pid> <address_hex>
python tools/memscan.py poke    <pid> <address_hex> <valor_i32>

# loadouts manuales (un solo guardado por nombre):
python tools/memscan.py loadout_save <pid> <address_hex> <nombre> loadouts.json
python tools/memscan.py loadout_load <pid> <address_hex> <nombre> loadouts.json
```

Para jugar con hotkeys en vez de comandos sueltos, una vez localizada la dirección:

```bash
python tools/loadout_hotkeys.py <pid> <address_hex> loadouts.json
```

F9/F10 guardan el arma 1 actual como loadout 1/2, F11 carga loadout 1, F12 carga loadout 2 (F12
puede fallar si Windows/Steam ya lo tiene reservado — no rompe el resto).

`loadouts.json` es estado de la sesión, no se versiona.

## Próximos pasos

- Mapear el offset de **weapon 2** (probablemente un bloque paralelo a esta misma tabla).
- Mapear qué offset corresponde a qué categoría, para poder guardar/cargar un set completo de una
  sola vez en vez de una sola arma.
- Decidir entre resolver el pointer path o migrar a un plugin inyectado que la re-escanea cada
  partida.
