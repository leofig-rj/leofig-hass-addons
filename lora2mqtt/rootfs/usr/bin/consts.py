# Constantes de configuração do AddOn
ADDON_SLUG = "lora2mqtt"
ADDON_NAME = "LoRa2MQTT"
VERSION = "0.0.1"
UNIQUE = "290146823516"
OWNER = "Leonardo Figueiró"
HA_PREFIX = "homeassistant"

# Constantes para Modos de Operação
MODE_OP_LOOP = 0
MODE_OP_PAIRING = 1

# Constantes para Fases de Negociação de novo Slave
STEP_NEG_INIC = 0
STEP_NEG_CFG = 1

# Constantes para LFLoRa
LFLORA_MAX_PACKET_SIZE = 255
MSG_CHECK_OK = 0
MSG_CHECK_NOT_MASTER = 1
MSG_CHECK_NOT_ME = 2
MSG_CHECK_ALREADY_REC = 3
MSG_CHECK_ERROR = 4
CMD_GET_USB_MODEL = "!000000!FFFFFF!000"
CMD_NEGOCIA_INIC = "!000000!FFFFFF!100"

# Constantes para mensagens
LORA_FIFO_LEN = 10
LORA_LOOP_TIME = 5000
LORA_PAIRING_TIME = 60000
LORA_NUM_ATTEMPTS_CMD = 3
LORA_TIME_OUT = 60000
LORA_TIME_CMD = 2000

##### Constantes para MQTT
# Constantes de uso geral
BUF_MQTT_MSG_LEN = 512
LORA_COM_NAME = "Com LoRa"

# Constantes para inicialização
MQTT_KEEP_ALIVE = 60
MQTT_CLIENT_ID = "LoRa2MQTT_123456"

# Constantes para LWT
LWT_MSG = "offline"      # Mensagem enviada no LWT
LWT_QOS = 0
LWT_REATAIN = True

# Constantes para Discovery
EC_DIAGNOSTIC = "diagnostic"
EC_CONFIG = "config"
EC_NONE = ""

# Constantes para Device Class
DEVICE_CLASS_NONE = ""

# Para Button
DEVICE_CLASS_RESTART = "RESTART"
DEVICE_CLASS_UPDATE = "UPDATE"
DEVICE_CLASS_IDENTIFY = "IDENTIFY"

# Para Sensor
DEVICE_CLASS_DURATION = "DURATION"
DEVICE_CLASS_ENUM = "ENUM"
DEVICE_CLASS_TEMPERATURE = "TEMPERATURE"
DEVICE_CLASS_SIGNAL_STRENGTH = "SIGNAL_STRENGTH"
DEVICE_CLASS_WATER = "WATER"
DEVICE_CLASS_VOLTAGE = "VOLTAGE"
DEVICE_CLASS_POWER = "POWER"
DEVICE_CLASS_CURRENT = "CURRENT"
DEVICE_CLASS_ENERGY = "ENERGY"
DEVICE_CLASS_FREQUENCY = "FREQUENCY"

# Constantes para Binary Sensor
DEVICE_CLASS_CONNECTIVITY = "CONNECTIVITY"
DEVICE_CLASS_PROBLEM = "PROBLEM"
DEVICE_CLASS_RUNNING = "RUNNING"
DEVICE_CLASS_DOOR = "DOOR"

# Constantes para Units
UNITS_NONE = ""

# Constantes para State Class
STATE_CLASS_NONE = ""
STATE_CLASS_MEASUREMENT = "MEASUREMENT"
STATE_CLASS_TOTAL_INCREASING = "TOTAL_INCREASING"
STATE_CLASS_TOTAL = "TOTAL"
