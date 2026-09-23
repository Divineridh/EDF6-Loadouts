# EDF6 Loadouts

Guardar y cargar el equipamiento de Earth Defense Force 6 escribiendo directo en la memoria del
proceso. Sin Cheat Engine ni terceros — herramientas propias en `tools/`.

Juego: `C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6` (proceso `EDF6.exe`, x64,
sin WOW64). Instalado junto a un mod que agrega slots de armas: los 6 slots por clase de abajo son
con ese mod, y el layout puede ser distinto en el juego vanilla.

## Estado

Fase de mapeo de datos. El overlay (estilo [EDF6-Compendium](../EDF6-Compendium), loadouts nombrados
por clase, vistos como la tarjeta del juego) viene después de cerrar lo que falta verificar.

## La tabla de equipamiento

Una sola estructura en el heap guarda la clase activa y el equipamiento de las 4 clases:

| offset | contenido |
|--------|-----------|
| +0 | clase activa: 0 Ranger, 1 Wing Diver, 2 Air Raider, 3 Fencer |
| +4 | desconocido (vale 3 en todas las lecturas) |
| +8 | Ranger: 6 slots int32 |
| +32 | Wing Diver: 6 slots |
| +56 | Air Raider: 6 slots |
| +80 | Fencer: 6 slots |
| +104 | `-1` de relleno |

Cada clase tiene **4 armas + 2 de soporte** (equipo del Ranger, core de la Wing Diver, vehículos del
Air Raider, accesorios del Fencer), en el mismo orden que la tarjeta de clase del lobby.

Cada slot es el **índice del catálogo** de armas (0-1563), el que genera
[EDF6-UI](../EDF6-UI) con `tools/weapons.py` en el orden de `WEAPON/WEAPONTABLE.SGO`. El motor usa
ese índice directamente.

⚠️ Los vehículos (EF31 Nereid, categoría 9) figuran como "Ranger" en `catalog.json`: el
`category // 100` no sirve para ellos. Por eso la validación de clase solo mira los 4 slots de arma.

## Lo verificado en juego

- **Escribir un slot re-equipa el arma**, sin hookear `EDF.dll`: probado en arma 1 y 2 y soportes
  de la clase activa, y en armas de otra clase (se ven al cambiar a ella).
- **Escribir +0 cambia la clase.** El personaje del lobby no se actualiza solo; al abrir
  "Class/Equipment" aparece la clase nueva con su equipamiento.
- Cambiar de clase desde el menú no pisa lo escrito en los otros bloques.
- El formato y el orden se mantienen entre sesiones; la dirección no (heap).

## Pendiente de verificar

- Si lo escrito **llega al save** (al reiniciar, el arma 1 de Air Raider volvió a una elegida desde
  el menú, no a la última escrita).
- Si una misión arrancada **sin pasar por "Class/Equipment"** usa la clase y armas escritas.
- Qué pasa si se escribe **durante una misión**.
- Qué es el int32 de +4, y el encabezado anterior a la tabla (3075, 3080, 5746, 2981 y ceros).

## Encontrar la tabla

```bash
python tools/memscan.py findtable <pid>
```

Busca la firma completa con una regex sobre bytes (corre en C; sin numpy): clase en [0,3], un int32,
24 slots no nulos menores a 1564 y un `-1`. Después valida que las 4 armas de cada bloque sean de su
clase. En una sesión real da un único candidato en ~90 s. El tiempo es casi todo `ReadProcessMemory`
copiando el heap entre procesos: desde un plugin inyectado sería mucho menor.

Limitación: exige slots no nulos, así que un slot con el índice 0 (Broken PA-11) hace que no la
encuentre. Admitir ceros hace que la regex caiga en backtracking sobre las zonas de memoria en cero y
tarde minutos.

## Otras herramientas

```bash
python tools/memscan.py dump    <pid> <address_hex> <bytes_antes> <bytes_despues>
python tools/memscan.py peek    <pid> <address_hex>
python tools/memscan.py poke    <pid> <address_hex> <valor_i32>
python tools/memscan.py findptr <pid> <address_hex> <max_offset_hex>

# búsqueda por valor exacto, como se encontró la tabla la primera vez:
python tools/memscan.py first <pid> <id_arma_actual> pass1.pkl
python tools/memscan.py next  <pid> <id_nueva_arma>  pass1.pkl pass2.pkl
```

`tools/loadout_hotkeys.py` es el primer MVP (solo arma 1, dirección pasada a mano): F9/F10 guardan,
F11/F12 cargan. Queda como prueba de concepto; el overlay lo reemplaza. `loadouts.json` y los `.pkl`
no se versionan.
