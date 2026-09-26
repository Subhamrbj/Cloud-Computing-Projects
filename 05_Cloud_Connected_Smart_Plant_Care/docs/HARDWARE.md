# Optional ESP32 extension

The shipped, verified application uses virtual sensors. The ESP32 sketch is a reference implementation and has not been compiled or bench-tested against a physical board.

## Parts and wiring

Use an ESP32 development board, capacitive moisture sensor with a 3.3 V-safe analog output, DHT22, low-voltage DC pump, appropriately rated logic-level MOSFET driver or relay module, flyback protection, tubing, a reservoir, and a float switch. Do not power a pump from an ESP32 pin or its 3.3 V regulator.

| Component | ESP32 connection | Notes |
|---|---|---|
| Soil sensor analog output | GPIO34 | ADC input; calibrate dry/wet readings |
| DHT22 data | GPIO4 | Pull-up as required by the breakout |
| Pump driver control | GPIO26 | Verify active-high/active-low polarity with an LED first |
| Low-tank float switch | GPIO27 to ground | INPUT_PULLUP; LOW means empty in the example |
| Sensor ground | GND | Common ground for non-isolated drivers |
| Pump power | Separate rated low-voltage supply | Fuse supply; keep electronics dry |

Never connect mains electricity. Use a physical power switch and a reservoir arrangement that cannot siphon continuously. Normally-off pump hardware and a physical cutoff are required for unattended operation.

## Firmware setup

1. Install the ESP32 Arduino board package, ArduinoJson 7, Adafruit DHT sensor library and Adafruit Unified Sensor.
2. Put `plant_node.ino` in an Arduino sketch folder named `plant_node`. Copy `config.example.h` there as `config.h`.
3. Create a device in the dashboard. Put its ID and one-time key in the local config, along with Wi-Fi and HTTPS host settings.
4. Obtain the correct trusted root certificate for that host. Keep TLS validation enabled. Network time is needed for certificate checks and timestamps.
5. Calibrate DRY_ADC/WET_ADC with your sensor. Confirm relay polarity without the pump connected.
6. Flash, monitor logs, test loss of Wi-Fi, empty tank, dry soil, wet soil, and relay cutoff before installing tubing.

Each HTTP exchange occurs with the pump off. A valid response permits at most a one-second local pulse, further bounded by cloud command expiry. A low-tank switch can cut off the pulse. Failed requests do not activate the pump. This deliberately conservative prototype trades watering throughput for bounded operation.

No light sensor is fitted; the sketch reports zero and the UI must be interpreted accordingly. The tank field is a binary 0/100 indication, not a calibrated volume. Add BH1750 and analog tank measurements later. Keep API schema, user authorization, database, and dashboard unchanged when substituting the device for the simulator.

Before production: hardware watchdog, signed firmware/secure boot, per-device key rotation/revocation, verified relay feedback, anti-siphon plumbing, enclosure protection, and electrical review. The cloud event journal records commands, not independently measured water delivery.
