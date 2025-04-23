# LoRa2MQTT Add-on

Integrating your LoRa devices with Home Assistant over MQTT

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
