# LoRa2MQTT Add-on

Integrating your LoRa devices with Home Assistant over MQTT

![Project Stage][project-stage-shield]![Maintenance][maintenance-shield]

<img src="https://raw.githubusercontent.com/leofig-rj/leofig-hass-addons/main/lora2mqtt/pictures/LoRa2MQTT logo.png"/>

## Installation

You need a MQTT Broker to use these Add-on. If you don't have one, install this Add-on:
https://github.com/home-assistant/hassio-addons/tree/master/mosquitto

1. Follow the instructions on [README](https://github.com/leofig-rj/leofig-hass-addons/blob/master/README.md) of this repo to add it in Supervisor Add-on Store.
1. Search for the "LoRa2MQTT" add-on at the Supervisor Add-on store.
1. Install the "LoRa2MQTT" add-on.
1. Configure the "LoRa2MQTT" add-on.
1. Start the "LoRa2MQTT" add-on.

## Configuration

**Note**: _Remember to restart the add-on when the configuration is changed._

serial:
    port:   This is the serial port where the LoRa USB Adapter is connected.

net_id:     This is the ID used to identify devices in the LoRa2MQTT network.
            Change this if there is another LoRa2MQTT running nearby.
            Range from 0x00 to 0xFF.

synch_word: This is the synch_word used in LoRa library for Arduino.
            Use default.

data_path:  This is the path to the config.yaml used to save LoRa2MQTT data.
            Use default.

Example add-on configuration:

```yaml
serial:
    port: /dev/ttyACM0 
net_id: "0x00"
loglevel: INFO
```

### Option: `serial`

### Option: `net_id`

### Option: `loglevel`

- `DEBUG`: Shows detailed debug information.
- `INFO`: Default informations.
- `WARNING`: Little alerts.
- `ERROR`:  Only errors.

### Option: `synch_word`

### Option: `data_path`

## Device Examples

There are examples for a first experience with the device / LoRa2MQTT pair. They use the [LF_Lora][github_LF_LoRa] library.

The example [LF_LoRa_USB_Adapter_01][ex_usb] is to flash the USB adapter to be connected to the Home Assistant server and allow connection to devices.

Each example contains a corresponding LoRa MQTT configuration file. This example .ino / .py file pair serves as a basis for developing new devices.

They are:

- [LF_LoRa_Model_TEST01.ino][ex_01_ino] / [test01.py][ex_01_py]

- [LF_LoRa_Model_TEST02.ino][ex_02_ino] / [test02.py][ex_02_py]

- [LF_LoRa_Model_TEST03.ino][ex_03_ino] / [test03.py][ex_03_py]

## New Devices

New devices can be developed based on the above examples.
The .py configuration file for LoRa2MQTT should be placed in the /Config/lora2mqtt/models folder of the Home Assistant server.

To pair the device to the Home Assistant LoRa2MQTT AddOn:

- The first time, the device will have the LED blinking.
- To enter the device into pairing mode (if it is not already), click the button 5 times.
- In Home Assistant, go to Settings/Devices and Services/MQTT/Devices/LoRa2MQTT Bridge.
- Activate Config Mode.
- After a while the LED stops flashing and "info" of the LoRa2MQTT Bridge indicates the MAC of the connected device.
- Turn off the Config Mode of the LoRa2MQTT Bridge.
- A new device should appear on the LoRa2MQTT Bridge screen under "Connected Devices".

### Note

The configuration files for the examples are already included in LoRa2MQTT and the new ones should be placed in /Config/lora2mqtt/models.

## License

This libary is [licensed][license] under the [MIT Licence][mit].

<!-- Markdown link -->
[project-stage-shield]: https://img.shields.io/badge/project%20stage-development%20beta-red.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2025.svg
[github_LF_LoRa]: https://github.com/leofig-rj/Arduino-LF_LoRa
[docs_link]: https://github.com/leofig-rj/leofig-hass-addons/blob/master/lora2mqtt/DOCS.md
[github_leofig-rj]: https://github.com/leofig-rj
[arduino]:https://arduino.cc/
[lora]:https://www.lora-alliance.org/
[ex_usb]:https://github.com/leofig-rj/Arduino-LF_LoRa/tree/main/examples/LF_LoRa_USB_Adapter_01
[ex_01_ino]:https://github.com/leofig-rj/Arduino-LF_LoRa/tree/main/examples/LF_LoRa_Model_TEST01
[ex_01_py]:https://github.com/leofig-rj/leofig-hass-addons/blob/main/lora2mqtt/rootfs/usr/bin/models/test01.py
[ex_02_ino]:https://github.com/leofig-rj/Arduino-LF_LoRa/tree/main/examples/LF_LoRa_Model_TEST02
[ex_02_py]:https://github.com/leofig-rj/leofig-hass-addons/blob/main/lora2mqtt/rootfs/usr/bin/models/test02.py
[ex_03_ino]:https://github.com/leofig-rj/Arduino-LF_LoRa/tree/main/examples/LF_LoRa_Model_TEST03
[ex_03_py]:https://github.com/leofig-rj/leofig-hass-addons/blob/main/lora2mqtt/rootfs/usr/bin/models/test03.py
[license]:https://github.com/leofig-rj/leofig-hass-addons/blob/main/LICENSE
[mit]:https://en.wikipedia.org/wiki/MIT_License