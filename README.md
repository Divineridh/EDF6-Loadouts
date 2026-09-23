# EDF6 Loadouts

Guardar y cargar el equipamiento de Earth Defense Force 6 escribiendo directo en la memoria del
proceso. Sin Cheat Engine ni terceros — herramientas propias en `tools/`.

Juego: `C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6` (proceso `EDF6.exe`, x64,
sin WOW64). Instalado junto a un mod que agrega slots de armas: los 6 slots por clase de abajo son
con ese mod, y el layout puede ser distinto en el juego vanilla.

## Estado

Mapeo de datos cerrado y verificado en juego. Sigue el overlay (estilo
[EDF6-Compendium](../EDF6-Compendium), loadouts nombrados por clase, vistos como la tarjeta del
juego).

## Diseño del overlay (acordado)

- **Vive en la DLL del Compendium**, como un panel propio. Reusa el hook de Present encadenado
  con el overlay de Steam, la detección de tecla por tres caminos, el bloqueo de input, el catálogo y
  el lector del save. Dos DLLs hookeando el mismo WndProc y las mismas funciones de user32 se
  pisarían. Este repo queda como la investigación y la spec de datos.
- **Se abre con F2**, configurable en `config.ini` igual que el F1 del Compendium. Textos en inglés.
- **Tarjetas como la de clase del juego**: título propio, 4 armas, separador, 2 de soporte, con el
  Lv del catálogo (coincide con el que muestra el juego). Pestañas por clase. Primero va "Equipped
  now", leída en vivo de la tabla, con "Save as new". Si un guardado coincide con lo equipado, se
  marca.
- **Load** escribe los 6 slots y, si es de otra clase, también la clase activa. Avisa según el
  contexto: en el lobby, que hay que abrir Class/Equipment para ver el personaje; en misión, que se
  aplica desde la próxima.
- **Varios loadouts nombrados por clase** en `Mods\Loadouts\loadouts.json`. Cada slot guarda el
  índice y el nombre del arma, así un cambio de índices (update, DLC) se detecta en vez de equipar
  otra arma sin avisar.
- **La tabla se busca dentro del proceso** la primera vez que se abre el panel, se cachea la
  dirección y se re-valida con la firma en cada lectura. En C++ se pueden admitir slots en cero.
- **v2, editor**: tocar un slot abre un selector con las armas que tenés de esa clase (del save).
  Antes hay que mapear qué categorías acepta cada tipo de slot: escribir un soporte en un slot de
  arma no está probado y podría cerrar el juego.
- Sin confirmar: el Lv en amarillo de la tarjeta parece marcar las armas con mejora máxima (dato que
  el save tiene).

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
- Una misión arrancada **directo desde el lobby**, sin abrir "Class/Equipment", usa la clase y las
  armas escritas.
- **Llega al save**: después de una misión y un reinicio, la clase y los slots escritos siguen ahí.
  Si se cierra el juego sin que haya guardado de por medio, se pierde (así pasó la primera vez).
- **Durante una misión**, escribir no toca al personaje que ya está en el mapa: el cambio queda
  aplicado para la siguiente y se ve en el lobby al volver. Sirve para dejar un loadout "en cola".
- Cambiar de clase desde el menú no pisa lo escrito en los otros bloques.
- El formato y el orden se mantienen entre sesiones; la dirección no (heap).

## Sin resolver

- Qué es el int32 de +4 (siempre 3) y el encabezado anterior a la tabla (3075, 3080, 5746, 2981 y
  ceros). No hace falta para leer ni escribir loadouts.
- Cómo hacer que el personaje del lobby se actualice al cambiar la clase sin abrir el menú.

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
