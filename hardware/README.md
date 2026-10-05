# Hardware (KiCad, Rev C)

**Status: UNVALIDATED.** Generated files for schematic review and layout. No copper, no routing, no Gerbers.

| File | What it is | How it was made |
|---|---|---|
| `NET_MAP.csv` | Every connection: net, ref, pin, pin name, domain (LV / LOGIC12 / HV), status, note | `scripts/make_design_tables.py` |
| `COMPONENT_PLACEMENT.csv` | Planning positions in **enclosure** coordinates (mm), side, rotation | same |
| `Nixie_RevC.kicad_pro` | Project, with an `HV` net class and patterns that put `HV170`, `ANODE*`, `T?_K?`, `LAMP?_A`, `SEP?_K`, `HV_BLEED_MID`, `HV_SENSE_MID` in it | `scripts/make_kicad.py` |
| `Nixie_RevC.kicad_sch` + `digit_1.kicad_sch` + `digit_2.kicad_sch` | Root sheet (power, logic, level shifters, HV supply, RTC) and one child sheet per driver bank | generated from `NET_MAP.csv`; every connection is a **global label** at a pin |
| `Nixie_RevC.kicad_sym` | Local symbol library: generic box symbols, one per part type | generated |
| `Nixie_RevC.pretty/` | **PLACEHOLDER** footprints: courtyard and fab outline only, **no pads** (plus a real M2 NPTH mounting hole) | generated |
| `sym-lib-table`, `fp-lib-table` | Project-local library tables | generated |
| `Nixie_RevC.kicad_dru` | Starting HV clearance rules for the future routed board | written by hand in the generator; **check against IPC-2221B** |
| `Nixie_RevC_placement.kicad_pcb` | 218 × 64 mm 4-layer outline, five M2 holes, placeholder courtyards (top: tubes, lamps, switches; bottom: everything else, plus keep-outs under the tube and lamp leads) | pcbnew Python API |
| `reports/` | Native netlist export, netlist-vs-net-map comparison, native DRC report of the placement board | `scripts/make_kicad.py` |

**Coordinates.** The placement board uses KiCad's Y-down axis with the clock's front edge at the bottom of the screen. Enclosure point (x, y) sits at board (20 + x, 20 + 80 − y) mm.

## What the native checks do and do not show

- `kicad-cli sch export netlist` reads the generated schematic, and every one of the 106 shared nets matches `NET_MAP.csv`. So the schematic **files** faithfully encode the net map. This is not ERC, and it cannot tell you whether the net map is *right*.
- pcbnew DRC on the placement board reports 0 violations: the outline, holes and courtyards do not collide. There is no copper, so it says nothing about clearances or connectivity.

## To turn this into a board

1. Open `Nixie_RevC.kicad_pro` in KiCad 7 or newer. Redraw the root sheet into readable blocks (the generated one is a label-connected parts list).
2. Replace placeholders with real footprints: PLCC-44 for the HV5522PJ-G, SOIC-16W for the DS3231SN, the IN-14 direct-solder pattern **measured from your tubes**, the NCH8200HV **measured from your module**.
3. Run native ERC. Fix everything or document every waiver.
4. Route 4 layers with `Nixie_RevC.kicad_dru`. Keep HV on one side of the board, away from the Nano and the logic. Keep the top side to tubes, lamps, switches, the HV_ARM header and the TP1–TP4 test pads along the rear edge (reached with the alarm-clock case lifted off).
5. Run native DRC. Have the HV layout reviewed by someone experienced.
6. Only then plot Gerbers and drill files. Record all of it in `docs/VALIDATION.md`.

Regenerate everything here with `python3 scripts/make_design_tables.py && python3 scripts/make_kicad.py` (needs KiCad 7.x with `kicad-cli` and the `pcbnew` Python module).
