# Printing and cutting the alarm-clock case

Everything here is a **baseline, untested** starting point. Print the fit coupons first and adjust `cad/DIMENSIONS.json`, not the slicer scale.

![Alarm-clock case, model render](img/hero_alarm_clock.png)

## Which files to use

| Use | Files | Orientation |
|---|---|---|
| **Slice these** | `cad/stl/*.stl` or `cad/3mf/*.3mf`, or the ready plates in `cad/print/` | Print orientation, already on the bed |
| **Laser-cut this** | `cad/Window_panel_3mm_1to1.dxf` | 2D, 1:1 millimetres |
| CAD reference only | `cad/step/*.step`, `cad/Assembly_RevC_alarm_clock.step` | Assembly coordinates: **do not slice** |
| View only | `cad/view/*.stl` (whole clock, chassis) | Includes glass and PCB envelopes: **never print** |

## Parts and plates

| Plate | Parts | Notes |
|---|---|---|
| `plate_0_fit_coupons.3mf` | 06 fit coupon, 07 unpowered lead-pattern coupon | Print first |
| `plate_A_case_shell.3mf` | 01 alarm-clock case (upright, open bottom on the bed) | 234 × 80 × 112 mm; tree supports (see below) |
| `plate_B_floor_clamp_rods.3mf` | 02 floor, 03 cable clamp, 3 × 04 button rods | Rods stand cap-down; add a brim |

Coupon 07 carries only the IN-14 lead pattern. **It is never a powered tube spacer.** Keep the factory spacers on your tubes.

Print the button rods in the **same colour as the case**: they sit just to the right of the window, behind the smoked panel.

![Case from below: window slot rails, button guides, corner blocks](img/case_underside.png)

## Printer

Every part fits a Bambu Lab P1S (256 × 256 × 256 mm). Any printer with at least 240 × 85 mm of bed and 115 mm of height works.

## Baseline settings (PETG, matte)

| Setting | Value |
|---|---|
| Layer height | 0.20 mm |
| Walls | 4 |
| Top / bottom layers | 5 / 5 |
| Infill | 20–25 % (gyroid or grid) |
| Supports | **Case (01):** tree supports, automatic, with *on build plate only* turned **off**. They form inside under the roof and the three button guides, and in the window opening; the outside needs none. **Everything else:** none |
| Brim | 5 mm on the case and the rods |
| Seam | Aligned at the back, so the front face and window bezel stay clean |

## Inspect in the slicer before printing

- **Window slot:** two vertical rails inside the front wall, a top stop above the window, and a 3.3 mm slot open at the bottom.
- **Button guides:** three tubes hanging from the roof at the right-hand end, with 6.6 mm holes through the top.
- **Corner blocks:** four solid blocks in the bottom corners, each with a 1.7 mm pilot hole.
- **Floor standoffs:** five 5 mm posts on part 02, 19.4 mm tall, each with a 1.7 mm pilot at the top.
- **Cable path:** the 4.2 mm rear hole, and the cradle and two bosses on the floor.
- **Grille:** the dimples on the left end are blind (they do not go through the wall).

## After printing

- Tap every 1.7 mm pilot with an M2 tap; clear the chips.
- Check that each rod slides freely in its guide.
- Remove all support material from inside the case, especially around the window slot.

## Window panel

Cut `cad/Window_panel_3mm_1to1.dxf` (layer `CUT`, millimetres, 1:1) from **3 mm cast acrylic**. Smoked grey gives the classic alarm-clock look: the glowing digits show through and the rest of the inside disappears. Clear also works. Before cutting, confirm the laser software reads it as 206 × 92.8 mm, and peel the protective film only at assembly.

The panel slides up into its slot from the open bottom of the case. Before the case goes on, put three small dots of clear neutral-cure silicone in the slot (both top corners and the middle of the top edge) so the panel stays in the case when you lift the case off later.

## Changing a dimension

1. Edit the value in `cad/DIMENSIONS.json` (for example `window_x` or `button_hole_d`).
2. Run `scripts/render_cad`. It rebuilds every STEP, STL, 3MF, plate, the DXF, the drawings and the previews, then runs the geometry checks, so the outputs never drift from the source.
3. Reprint the coupon. Record the change in [VALIDATION.md](VALIDATION.md).

**Never scale a part uniformly to fix a hole.** That moves every screw post too.
