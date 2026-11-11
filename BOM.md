# Bill of materials

Prototype build: plug-together RAK WisBlock parts running Meshtastic, US 915 MHz.
Prices are single-unit list prices seen on 2026-11-11 and exclude shipping; blank means not checked.

## Collar unit

| # | Item | Part | Qty | Price | Link | Notes |
|---|------|------|-----|-------|------|-------|
| 1 | Base board | RAK19003 WisBlock Mini Base | 1 | $8.99 | [RAK store](https://store.rakwireless.com/products/wisblock-base-board-rak19003) | 30 x 35 mm. Includes USB-C cable and module screws. |
| 2 | MCU + LoRa + Bluetooth | RAK4631, **US915**, **Arduino** variant | 1 | $17.99 | [RAK store](https://store.rakwireless.com/products/rak4631-lpwan-node) | Includes a LoRa PCB antenna and a Bluetooth antenna (both MHF-1 / U.FL). |
| 3 | GPS | RAK12500 (u-blox ZOE-M8Q) | 1 | $19.00 | [RAK store](https://store.rakwireless.com/products/wisblock-gnss-location-module-rak12500) / [Rokland, $26.97](https://store.rokland.com/collections/802-11ah-wi-fi-halow/products/rak-wireless-rak12500-gnss-gps-location-module-u-blox-zoe-m8q) | Goes in slot C. Includes a GPS antenna. RAK lists it as replaced by the RAK12501. |
| 4 | LoRa antenna (collar strip) | Molex 2111400100, 38 x 10 x 0.1 mm, 100 mm cable | 1 | $2.61 | [DigiKey](https://www.digikey.com/en/products/detail/molex/2111400100/9953925) | Adhesive flex antenna, U.FL. Replaces the PCB antenna from item 2. |
| 5 | LoRa antenna, longer option | Molex 1052620001, 79 x 10 mm | 1 | | [DigiKey](https://www.digikey.com/en/products/detail/molex,-llc/1052620001/3918562) | Optional, to range-test against item 4. Confirm band and cable length on the listing. |
| 6 | Battery | Adafruit 1317, 3.7 V 150 mAh LiPo, 19.75 x 26 x 3.8 mm | 1 | | [Adafruit](https://www.adafruit.com/products/1317) | Fits the 20 x 30 x 5 mm battery bay. A generic 502030 cell (250 mAh, JST-PH 2.0) also fits. |
| 7 | Case | Printed from `case/collar_pod_case.step` | 1 | | | Form-factor study, not print-ready yet. |
| 8 | Collar | Breakaway cat collar, 10 mm (3/8 in) webbing | 1 | | | |

Checked subtotal for items 1-4: **$48.59**, plus battery.

## Receiver (carried by you)

| # | Item | Part | Qty | Price | Link | Notes |
|---|------|------|-----|-------|------|-------|
| 9 | Handheld Meshtastic node | Seeed SenseCAP Card Tracker T1000-E | 1 | about $40 | [RobotShop](https://www.robotshop.com/products/sensecap-card-tracker-t1000-e-for-meshtastic) | Pairs with the Meshtastic phone app over Bluetooth. $39.90 was the launch price. |

## Check before ordering or powering up

- **Battery polarity.** RAK warns that not all JST-PH batteries are wired the same way as the RAK19003.
  Compare the battery plug with the board markings before connecting; swap the pins in the plug if they differ.
- **RAK4631 variant.** Order the Arduino variant, not RUI3. I believe this is the one Meshtastic expects; confirm on the Meshtastic RAK4631 page.
- **GPS antenna size.** The case assumes a 15 x 15 x 4 mm patch. The antenna bundled with the RAK12500 has not been measured.
- **RAK12500 availability.** If it is gone, the RAK12501 is the successor; its fit on the RAK19003 has not been checked.
- **Assembled board height.** The case assumes 9.5 mm; measure the real stack before printing.
