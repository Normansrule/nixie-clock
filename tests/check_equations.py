#!/usr/bin/env python3
"""Numerical checks for every equation in docs/EQUATIONS.md.

These are arithmetic checks of the documented design numbers. They are NOT
measurements and do not show the physical circuit behaves this way.
Run:  python3 tests/check_equations.py        (exit code 0 = all asserts pass)
Add --svg to regenerate docs/img/discharge.svg and docs/img/anode_current.svg.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

V_HV = 170.0            # V, NCH8200HV fixed nominal output (v2.1 data sheet); VERIFY on the bench
R_ANODE = 22e3          # ohm, RA1..RA6 (1 W PR01)
R_LAMP = 220e3          # ohm, RL1, RL2 (1 W PR01)
P_RATED_ANODE = 1.0     # W
V_TUBE_RANGE = (135.0, 145.0, 155.0)   # V, IN-14 typical maintaining 145 V (Tube-Tester); +/-10 V spread assumed
I_TYP_IN14 = 2.5        # mA, IN-14 typical cathode current (Tube-Tester)
V_NE2 = 60.0            # V, assumed NE-2 maintaining voltage (VERIFY)
R_BLEED = 2 * 110e3     # ohm, RH1 + RH2
R_SENSE_TOP = 2 * 1e6   # ohm, RS1 + RS2
R_SENSE_BOT = 22e3      # ohm, RS3
C_HV_BOARD = 100e-9     # F, CHV
C_CONVERTER_ASSUMED = 1e-6  # F, NCH8200HV internal output capacitance: UNKNOWN, assumed for illustration
V_ADC_REF = 5.0         # V, AVCC reference (Nano 5 V rail, +/- a few percent)
ADC_MAX = 1023
RV1, RV2 = 47e3, 10e3   # VIN sense divider
DS3231_PPM = 2.0        # +/-ppm, 0..40 C (DS3231SN datasheet)

checks = []


def check(name, value, lo, hi, unit):
    ok = lo <= value <= hi
    checks.append((name, value, unit, ok, lo, hi))
    return value


# 1. Tube anode current  I = (V_HV - V_tube) / R_anode
i_nom = check("anode current @ V_tube=145 V", (V_HV - 145) / R_ANODE * 1e3, 1.13, 1.14, "mA")
i_hi = check("anode current @ V_tube=135 V", (V_HV - 135) / R_ANODE * 1e3, 1.59, 1.60, "mA")
i_lo = check("anode current @ V_tube=155 V", (V_HV - 155) / R_ANODE * 1e3, 0.68, 0.69, "mA")

check("22 k start value vs IN-14 typical 2.5 mA", i_nom / I_TYP_IN14 * 100, 45, 46, "% of typical")
check("anode resistor that would give 2.5 mA at 145 V", (V_HV - 145) / (I_TYP_IN14 / 1e3) / 1e3, 10, 10, "kOhm")
check("fault power in that lower value (why lower R needs a higher rating)", V_HV ** 2 / 10e3, 2.89, 2.89, "W")

# 2. Resistor power  P = I^2 R  (normal) and V^2/R (single fault: tube or cathode path shorted)
p_norm_worst = check("RA power, normal worst case (135 V tube)", (i_hi / 1e3) ** 2 * R_ANODE * 1e3, 55, 56, "mW")
check("RA utilisation, normal worst case", p_norm_worst / 1e3 / P_RATED_ANODE * 100, 5.5, 5.6, "% of 1 W")
p_fault = check("RA power if the full rail appears across it (fault)", V_HV ** 2 / R_ANODE, 1.31, 1.32, "W")
assert p_fault > P_RATED_ANODE, "the fault case exceeds 1 W: documented as an open item, do not hide it"
i_lamp = check("NE-2 lamp current", (V_HV - V_NE2) / R_LAMP * 1e3, 0.49, 0.51, "mA")
check("RL power, normal", (i_lamp / 1e3) ** 2 * R_LAMP * 1e3, 54, 56, "mW")
check("RL power, fault", V_HV ** 2 / R_LAMP * 1e3, 131, 132, "mW")

# Converter load, all six digits + both lamps lit (135 V tube = heaviest case)
i_load = check("HV load, 6 digits + 2 lamps (135 V tubes)", 6 * i_hi + 2 * i_lamp, 10.5, 10.7, "mA")
i_bleed = V_HV / R_BLEED * 1e3
check("bleeder current", i_bleed, 0.77, 0.78, "mA")
check("NCH8200HV headroom: load vs 30 mA peak rating", i_load / 30 * 100, 35, 36, "% of peak")
check("HV output power incl. bleeder + sense", V_HV * (i_load + i_bleed + V_HV / (R_SENSE_TOP + R_SENSE_BOT) * 1e3) / 1e3, 1.93, 1.96, "W")

# 5. 12 V input current (converter efficiency 86-89.65 % per NCH8200HV data sheet; logic load assumed 50 mA)
p_hv = V_HV * (i_load + i_bleed + V_HV / (R_SENSE_TOP + R_SENSE_BOT) * 1e3) / 1e3
check("12 V input current, all lit, 86 % efficiency + 50 mA logic", p_hv / 0.86 / 12 + 0.050, 0.23, 0.25, "A")

# 6. Sealed wood-clad case: average internal temperature rise  dT = P / (U * A),  U = 1 / (1/h + t_wood / k_wood)
#    P: converter input + Nano regulator (7 V x 50 mA) + drivers/logic (assumed 0.1 W)
#    A: outer box of the hardwood case (fillets ignored). The wood resistance is applied to every face,
#    which is pessimistic for the PETG floor and the acrylic window. The printed inner wall and the inside
#    air film are ignored, as before.
P_case = p_hv / 0.86 + 7 * 0.050 + 0.1
A_case = 2 * (0.254 * 0.100 + 0.254 * 0.1215 + 0.100 * 0.1215)    # m2
R_WOOD = 0.0095 / 0.15                                            # m2K/W: 9.5 mm walnut, k ~0.15 W/mK across the grain (assumed)
check("heat dissipated inside the case", P_case, 2.6, 2.8, "W")
check("case outer area (wood box)", A_case, 0.136, 0.138, "m2")
check("wood wall resistance", R_WOOD, 0.063, 0.064, "m2K/W")
check("average internal rise, h = 5 W/m2K (pessimistic)", P_case / (A_case / (1 / 5 + R_WOOD)), 5.1, 5.4, "K")
check("average internal rise, h = 10 W/m2K (typical natural convection + radiation)", P_case / (A_case / (1 / 10 + R_WOOD)), 3.1, 3.4, "K")

# 3. Bleeder / discharge  tau = R * C ; t(V) = tau * ln(V0 / V)
r_par = 1 / (1 / R_BLEED + 1 / (R_SENSE_TOP + R_SENSE_BOT))
check("discharge resistance (bleeder || sense)", r_par / 1e3, 198.3, 198.5, "kOhm")
tau_board = check("tau, board CHV only", r_par * C_HV_BOARD * 1e3, 19.8, 19.9, "ms")
tau_assumed = check("tau, CHV + assumed 1 uF in converter", r_par * (C_HV_BOARD + C_CONVERTER_ASSUMED) * 1e3, 218, 219, "ms")
check("time to 10 V, assumed capacitance", tau_assumed * math.log(V_HV / 10), 617, 620, "ms")
tau_open = check("tau if the bleeder path is open (sense divider only)", (R_SENSE_TOP + R_SENSE_BOT) * (C_HV_BOARD + C_CONVERTER_ASSUMED), 2.2, 2.3, "s")
check("time to 10 V if the bleeder path is open", tau_open * math.log(V_HV / 10), 6.2, 6.4, "s")
check("bleeder power per resistor", (V_HV / 2) ** 2 / (R_BLEED / 2) * 1e3, 65, 66, "mW")
check("bleeder volts per resistor", V_HV / 2, 85, 85, "V")

# HV sense divider
v_a0 = check("A0 voltage at 170 V", V_HV * R_SENSE_BOT / (R_SENSE_TOP + R_SENSE_BOT), 1.84, 1.86, "V")
check("A0 ADC count at 170 V", v_a0 / V_ADC_REF * ADC_MAX, 378, 379, "counts")
check("HV volts per ADC count", V_ADC_REF / ADC_MAX * (R_SENSE_TOP + R_SENSE_BOT) / R_SENSE_BOT, 0.44, 0.45, "V")
check("HV full scale (A0 = 5 V)", V_ADC_REF * (R_SENSE_TOP + R_SENSE_BOT) / R_SENSE_BOT, 459, 460, "V")
check("A0 clamp current if RS3 opens", (V_HV - 5.5) / R_SENSE_TOP * 1e6, 82, 83, "uA")
v_a1 = check("A1 voltage at 12 V input", 12 * RV2 / (RV1 + RV2), 2.10, 2.11, "V")
check("VIN full scale (A1 = 5 V)", 5 * (RV1 + RV2) / RV2, 28.4, 28.6, "V")

# 4. RTC drift
check("DS3231 worst drift per day at 2 ppm", DS3231_PPM * 1e-6 * 86400, 0.17, 0.18, "s/day")
check("DS3231 worst drift per year at 2 ppm", DS3231_PPM * 1e-6 * 86400 * 365, 63, 64, "s/year")

width = max(len(c[0]) for c in checks)
fail = 0
for name, v, unit, ok, lo, hi in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {v:10.4g} {unit}")
    fail += not ok
print(f"\n{len(checks) - fail}/{len(checks)} equation checks passed")


def svg_chart(path, title, xlabel, ylabel, series, xmax, ymax, hlines=()):
    W, H, L, B, T, R = 640, 360, 70, 50, 40, 20
    pw, ph = W - L - R, H - B - T
    X = lambda x: L + x / xmax * pw
    Y = lambda y: T + ph - y / ymax * ph
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif" font-size="12">',
           '<rect width="100%" height="100%" fill="#14110f"/>',
           f'<text x="{L}" y="24" fill="#f4e9dc" font-size="15" font-weight="600">{title}</text>']
    for k in range(6):
        gx, gy = xmax * k / 5, ymax * k / 5
        out.append(f'<line x1="{X(gx)}" y1="{T}" x2="{X(gx)}" y2="{T+ph}" stroke="#3a322c"/>')
        out.append(f'<line x1="{L}" y1="{Y(gy)}" x2="{L+pw}" y2="{Y(gy)}" stroke="#3a322c"/>')
        out.append(f'<text x="{X(gx)}" y="{T+ph+16}" fill="#b9a99a" text-anchor="middle">{gx:g}</text>')
        out.append(f'<text x="{L-8}" y="{Y(gy)+4}" fill="#b9a99a" text-anchor="end">{gy:g}</text>')
    for yv, lab in hlines:
        out.append(f'<line x1="{L}" y1="{Y(yv)}" x2="{L+pw}" y2="{Y(yv)}" stroke="#e05a4f" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{L+pw-4}" y="{Y(yv)-5}" fill="#e05a4f" text-anchor="end">{lab}</text>')
    for i, (lab, color, pts) in enumerate(series):
        d = " ".join(f"{X(x):.1f},{Y(min(y, ymax)):.1f}" for x, y in pts)
        out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        out.append(f'<rect x="{L+12}" y="{T+10+i*18}" width="14" height="4" fill="{color}"/>')
        out.append(f'<text x="{L+32}" y="{T+15+i*18}" fill="#f4e9dc">{lab}</text>')
    out.append(f'<text x="{L+pw/2}" y="{H-10}" fill="#b9a99a" text-anchor="middle">{xlabel}</text>')
    out.append(f'<text transform="translate(16 {T+ph/2}) rotate(-90)" fill="#b9a99a" text-anchor="middle">{ylabel}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out))


if "--svg" in sys.argv:
    img = ROOT / "docs" / "img"
    img.mkdir(parents=True, exist_ok=True)
    ts = [k * 0.02 for k in range(0, 301)]
    s = [
        ("CHV only (100 nF), bleeders OK", "#ff9a3c", [(t, V_HV * math.exp(-t / (r_par * C_HV_BOARD))) for t in ts]),
        ("+ assumed 1 uF in converter, bleeders OK", "#ffd08a", [(t, V_HV * math.exp(-t / (r_par * 1.1e-6))) for t in ts]),
        ("bleeder path OPEN (sense divider only)", "#e05a4f", [(t, V_HV * math.exp(-t / ((R_SENSE_TOP + R_SENSE_BOT) * 1.1e-6))) for t in ts]),
    ]
    svg_chart(img / "discharge.svg", "HV rail after the converter stops (model, not a measurement)", "time after HV off (s)", "rail voltage (V)", s, 6, 180, [(10, "10 V: proceed threshold after measuring")])
    vt = [130 + k * 0.1 for k in range(0, 301)]
    s2 = [("22 kOhm (Rev C start value)", "#ff9a3c", [(v - 130, (V_HV - v) / R_ANODE * 1e3) for v in vt])]
    svg_chart(img / "anode_current.svg", "IN-14 digit current vs tube maintaining voltage (170 V rail)", "V_tube - 130 V", "anode current (mA)", s2, 30, 2.0)
    print("wrote docs/img/discharge.svg and docs/img/anode_current.svg")

sys.exit(1 if fail else 0)
