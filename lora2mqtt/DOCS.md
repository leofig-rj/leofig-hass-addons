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

publishstatedelay is the delay in the standby loop.
publishstatedelayshort is the delay after a command.
publishstatedelayshort must be less than publishstatedelay.

Example add-on configuration:

```yaml
ttlockclientid: YOUR_TTLOCK_CLOUD_API_CLIENT_ID
ttlockclientsecret: YOUR_TTLOCK_CLOUD_CLIENT_SECRET
ttlockuser: YOUR_TTLOCK_CLOUD_USER
ttlockhash: YOUR_TTLOCK_CLOUD_HASH
publishstatedelay: 300
publishstatedelayshort: 30
publishbatterydelay: 3600
loglevel: INFO
maxthreads: 200
```
### Options: `ttlockclientid`,  `ttlockclientsecret`,  `ttlockuser` and `ttlockhash` 

### Option: `loglevel`

- `DEBUG`: Shows detailed debug information.
- `INFO`: Default informations.
- `WARNING`: Little alerts.
- `ERROR`:  Only errors.

### Option: `publishstatedelay` and `publishbatterydelay`

Time between two information publish in seconds.

### Option: `maxthreads`

Max number of threads for execution and the default number is 200. If you have more than 200 locks and gateway try two increase this number.
