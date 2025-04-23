# LoRa2MQTT
> Integrate LoRa devices with Home Assistant via MQTT.

![Project Stage][project-stage-shield]![Maintenance][maintenance-shield]

Integrate [LoRa][lora] devices using [Arduino][arduino] library [LF_Lora][github_LF_LoRa] to Home Assistant via MQTT.

<img src="https://raw.githubusercontent.com/leofig-rj/leofig-hass-addons/main/lora2mqtt/pictures/LoRa2MQTT logo.png"/>

## Configuration

1. Read the [DOCS][docs_link].

## Release History

* 0.0.1
    * Starting work

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

## License

This libary is [licensed](LICENSE) under the [MIT Licence](https://en.wikipedia.org/wiki/MIT_License).

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