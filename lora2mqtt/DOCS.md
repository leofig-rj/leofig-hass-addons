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
    port:   is serial port where the LoRa USB Adapter is connected.

data_path:  is the path to the config.yaml used to save LoRa2MQTT data.
            use default.

Example add-on configuration:

```yaml
loglevel: INFO
```

### Options: `serial`

port: /dev/ttyACM0 

### Option: `loglevel`

- `DEBUG`: Shows detailed debug information.
- `INFO`: Default informations.
- `WARNING`: Little alerts.
- `ERROR`:  Only errors.

### Options: `data_path`

