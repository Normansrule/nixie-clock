# Credits and data sheets

Every value taken from a data sheet is marked in [`hardware/NET_MAP.csv`](hardware/NET_MAP.csv) (status `DATASHEET`) or listed as an untested assumption in [`docs/VALIDATION.md`](docs/VALIDATION.md). Links were found or opened on 2026-09-30, except the onsemi, Microchip ATmega328P and Arduino pages, which are the manufacturers' usual product pages and were not re-checked. Manufacturers move files: search the part number on the manufacturer's site if a link breaks.

| Part | Document | Used for | Status |
|---|---|---|---|
| IN-14 Nixie tube | [Tube-Tester IN-14 page](https://www.tube-tester.com/sites/nixie/data/in-14/in-14.htm); [IN-14 data (PDF)](https://download.elektronicastynus.be/57/in-14_datasheet.pdf) | 145 V typical maintaining voltage, 2.5 mA typical current, 19 mm × 55 mm bulb, 13 leads | Lead-circle diameter **not verified** (placeholder) |
| HV5522 (HV5522PJ-G) | [Microchip product page](https://www.microchip.com/en-us/product/hv5522); [data sheet DS20005699](https://ww1.microchip.com/downloads/en/DeviceDoc/20005699A.pdf); [Supertex-era data sheet](https://www.mouser.com/datasheet/2/268/supertex_hv5522-1181179.pdf) | PLCC-44 pinout, function table (POL/BL), shift direction, falling-edge clock, VDD 10.8–13.2 V, VIH ≥ VDD − 2 V, 220 V outputs | Read from the Supertex-era sheet; **recheck against DS20005699** |
| DS3231SN# | [Analog Devices DS3231 product page](https://www.analog.com/en/products/ds3231.html); [data sheet (PDF)](https://www.analog.com/media/en/technical-documentation/data-sheets/ds3231.pdf) | Pinout, ±2 ppm (0–40 °C), OSF and EOSC bits, grounding pins 5–12 | Pin 5–12 grounding **verify** |
| NCH8200HV | [Omnixie product page](https://omnixie.io/nch8200hv.html); [NCH8200HV data sheet v2.1 (PDF)](https://nixieclock.org/wp-content/uploads/2023/02/NCH8200HV-Datasheet-EN-v2.1.0.3.pdf) | 2.5–15 V in, ~170 V fixed out, 30 mA peak, 86–89.65 % efficiency, pin order, no reverse-polarity protection | Outline and output capacitance **not documented** |
| ATmega328P / Arduino Nano | [Microchip ATmega328P](https://www.microchip.com/en-us/product/atmega328p); [Arduino Nano A000005](https://docs.arduino.cc/hardware/nano/) | ADC, watchdog, Nano header pinout | |
| DMP3098L-7 | [Diodes Inc. DMP3098L data sheet DS31447](https://datasheet.octopart.com/DMP3098L-7-Diodes-Inc.-datasheet-12534397.pdf) | −30 V P-MOSFET, SOT-23 | V_GS limit **verify** against adapter overshoot |
| 1812L075/33DR | [Littelfuse 1812L PolySwitch data sheet](https://www.littelfuse.com/assetdocs/resettable-ptcs-1812l-datasheet?assetguid=ca5c80cb-504e-4a8a-8e74-0107520a1717) | 0.75 A hold, 33 V PTC | |
| MMBT3904 / MMBT3906 | [onsemi MMBT3904](https://www.onsemi.com/products/discrete-power-modules/general-purpose-and-low-vcesat-transistors/mmbt3904); [onsemi MMBT3906](https://www.onsemi.com/products/discrete-power-modules/general-purpose-and-low-vcesat-transistors/mmbt3906) | Level shifters | |
| Omron B3F-1062-G | [Omron B3F series](https://components.omron.com/us-en/products/switches/B3F) | 6 × 6 mm body, 7 mm height | Body height **verify** (drove the pocket change) |
| Vishay PR01 | [Vishay PR01/PR02/PR03](https://www.vishay.com/en/product/28729/); [data sheet (PDF)](https://www.vishay.com/docs/28729/pr010203.pdf) | 1 W axial anode and lamp resistors | |
| NE-2 neon lamp | Generic; supplier data | ~60 V maintaining voltage assumed | **verify** |

## Standards and references

- OWASP Top 10:2025, A03 Software Supply Chain Failures: [A03:2025](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/).
- IPC-2221B Table 6-1 (conductor spacing): the source to check the HV clearances in `hardware/Nixie_RevC.kicad_dru` against. Not reproduced here.

## Tools

CadQuery, OpenCASCADE, ezdxf, VTK, KiCad, avr-gcc and ArduinoCore-avr. Versions are in [`sbom/toolchain.spdx.json`](sbom/toolchain.spdx.json).

## Author

Aleksander Norman. Rev C documentation, generators and checks prepared with Claude (Anthropic).
