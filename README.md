# OpenTherm Gateway Firmware (Fork for Remeha eTwist + Heat Pump)

> [!NOTE]
> **Attribution Disclaimer:**  
> This repository is a fork of the OpenTherm Gateway (OTGW) PIC firmware created and maintained by **Schelte Bron**. The original project, hardware schematics, software, and comprehensive documentation can be found at **[otgw.tclcode.com](http://otgw.tclcode.com/)**.  
> The maintainer of this fork is **not** the original author of the source code. This fork was created specifically to apply targeted firmware changes to improve compatibility when pairing a **Remeha eTwist** thermostat with a **heat pump**.

---

## About the OpenTherm Gateway Project

The **OpenTherm Gateway (OTGW)** is an open-source hardware and software project designed to interface with heating systems that communicate using the OpenTherm protocol.

The gateway physically and logically sits as a "man-in-the-middle" between an OpenTherm thermostat (master) and an OpenTherm central heating appliance such as a boiler or heat pump (slave):

```
+--------------------+        +-----------------------+        +--------------------------+
| OpenTherm Master   | <----> |   OpenTherm Gateway   | <----> | OpenTherm Slave          |
| (e.g. Remeha       |        |   (PIC16F1847)        |        | (e.g. Heat Pump,         |
|  eTwist)           |        +-----------+-----------+        |  Hybrid / Gas Boiler)    |
+--------------------+                    |                    +--------------------------+
                                          | Serial / UART
                                          v
                               +----------------------+
                               |   NodeMCU / ESP8266  |
                               | (rvdbreemen firmware)|
                               +----------+-----------+
                                          | WiFi / MQTT / Web UI
                                          v
                               +----------------------+
                               | Home Assistant, etc. |
                               +----------------------+
```

### Key Functions & Integration
- **Transparent Monitoring:** Relays all standard OpenTherm messages between the thermostat and appliance while logging telemetry (flow temperatures, return temperatures, modulation levels, error codes, DHW status).
- **Message Manipulation & Overrides:** Allows injecting or altering specific OpenTherm commands on the fly (e.g., overriding room setpoints, central heating limits, domestic hot water temperatures, or supplying external outdoor temperature readings).
- **ESP Integration via [rvdbreemen/OTGW-firmware](https://github.com/rvdbreemen/OTGW-firmware):** In this setup, the OTGW is paired with an ESP8266/ESP32 NodeMCU module running the widely-used [OTGW-firmware by Robert van den Breemen](https://github.com/rvdbreemen/OTGW-firmware). This adds WiFi connectivity, MQTT support, Home Assistant autodiscovery, a browser-based Web UI, REST API, a filesystem explorer (FSexplorer), and on-device flashing of the PIC microcontroller.
- **Fail-Safe Operation:** Features hardware and watchdog fallback to pass-through mode if the microcontroller halts or is being updated, ensuring heating operation is not disrupted.

---

## Why This Fork?

When pairing a **Remeha eTwist** thermostat with certain modern heat pump systems, two specific operational challenges often arise:

1. **Glitched / Invalid Low Room Temperature Readings (MsgID 24):**  
   The Remeha eTwist occasionally transmits spurious or extreme low room temperature readings (including 0 °C or negative values). When passed to a heat pump relying on current room temperature for modulation, these erroneous spikes cause unpredictable heating behavior and unwanted modulation spikes.

2. **Unconfigurable Heating Curve ("Stooklijn") Upper Limit (MsgID 49):**  
   The eTwist's weather-dependent heating curve relies on the maximum central heating setpoint upper boundary reported by the slave appliance (OpenTherm Message ID 49). If the connected heat pump or boiler does not support lowering this upper bound via OpenTherm or its internal menu, the eTwist will calculate and request excessively high water flow temperatures that are unsuitable or inefficient for heat pump operation.

---

## Custom Features Added in This Fork

This fork introduces two new serial commands and corresponding status reporting options (tested and supported on **PIC16F1847**):

### 1. Room Temperature Lower Limit (`LT` and `PR=J`)
Filters room temperature reports (MsgID 24) sent by the thermostat:
- **`LT=<temperature>`**  
  Configures the minimum acceptable room temperature threshold (e.g. `LT=5.0`).
  - If the thermostat reports a room temperature below this limit (and fake room temperature `RT` is not active), the gateway intercepts the message and replaces it with the **last known valid temperature reading**.
  - If no valid reading has been received yet since startup, the message is converted into an `Invalid-Data` request.
  - Setting **`LT=0`** disables this filtering.
- **`PR=J`**  
  Prints the currently configured room temperature lower limit.

### 2. Maximum Central Heating Setpoint Upper Bound Cap (`HM` and `PR=H`)
Caps the maximum central heating setpoint upper bound reported to the thermostat in MsgID 49 responses:
- **`HM=<temperature>`**  
  Configures a ceiling on the central heating maximum setpoint bound reported back to the thermostat (e.g. `HM=55` or `HM=45`).
  - When the appliance answers MsgID 49, the gateway checks the reported maximum water temperature. If the boiler/heat pump reports a higher upper bound than the `HM` value, the gateway clamps the value to `HM` before delivering it to the thermostat.
  - This allows fine-tuning and restricting the upper limit of the eTwist's heating curve (*stooklijn*), preventing the thermostat from commanding flow temperatures beyond the heat pump's optimal range.
  - Setting **`HM=0`** disables the cap.
- **`PR=H`**  
  Prints the currently configured maximum central heating setpoint upper bound cap.

### Persistence
Both `LT` and `HM` settings are stored in the PIC16F1847 EEPROM and persist across gateway resets and power cycles.

---

## Building and Testing

### Prerequisites
- **gputils** (≥ 1.5.0) – PIC assembler and linker utilities (`gpasm`, `gplink`).
- **GNU make** – standard build tool.
- **Tcl** (`tclsh`) – required for generating `build.asm`.
- *(Optional, for unit tests)* **gpsim** (≥ 0.32.1) with the included `chmodule`.

### Building Firmware
To generate the firmware HEX file for the PIC16F1847:
```bash
make
```
This produces `gateway.hex`.

To build the interface and diagnostic firmware:
```bash
make interface.hex
make diagnose.hex
```

### Running the Test Suite
The repository includes an extensive regression test suite executed via `gpsim`:
```bash
make test
```
To run only the room temperature and central heating boundary tests:
```bash
make test TESTFLAGS="-match 'roomtemp-* chbound-*'"
```

---

## Flashing the Gateway

### Method A: Via [rvdbreemen/OTGW-firmware](https://github.com/rvdbreemen/OTGW-firmware) Web UI (Recommended)

If your OTGW is equipped with a NodeMCU/ESP module running Robert van den Breemen's OTGW-firmware, you can flash the PIC firmware over the network without taking hardware apart or using a dedicated programmer:

1. Open the **OTGW Web Interface** in your browser.
2. Navigate to **File System contents** (FSexplorer).
3. Open or navigate to the `/pic16f1847` directory.
4. Upload the compiled `gateway.hex` file into this folder.
5. Go to the **PIC firmware** feature in the web interface and execute the flash procedure.

Once the PIC boots the new firmware, you can send serial commands directly from the OTGW-firmware web console (or via MQTT / REST API):
```text
LT=5.0
HM=50
```

Verify your configuration:
```text
PR=J
PR=H
```

---

### Method B: Via OTmonitor or Serial Bootloader

For standalone USB/serial setups without the ESP module:
1. Connect to your OTGW using **[OTmonitor](http://otgw.tclcode.com/otmonitor.html)** or a serial terminal.
2. Follow the firmware upgrade procedure in OTmonitor to upload `gateway.hex` over the serial port.
3. Configure settings via the serial command prompt as shown above.

---

## Upstream References & Documentation

- **Official OTGW Website:** [http://otgw.tclcode.com/](http://otgw.tclcode.com/) by Schelte Bron.
- **NodeMCU / ESP OTGW Firmware:** [https://github.com/rvdbreemen/OTGW-firmware](https://github.com/rvdbreemen/OTGW-firmware) by Robert van den Breemen.
- **Firmware Reference:** See [FIRMWARE.html](FIRMWARE.html) or the [online firmware documentation](http://otgw.tclcode.com/firmware.html).
- **Changelog:** See [CHANGELOG.html](CHANGELOG.html) or the [online changelog](http://otgw.tclcode.com/changelog.html).
- **Hardware & Schematics:** [http://otgw.tclcode.com/hardware.html](http://otgw.tclcode.com/hardware.html)
- **License:** See [license.txt](license.txt) for original licensing terms by Schelte Bron.

