#import serial
import paho.mqtt.client as mqtt
import logging
import json
import constants
import time
import getopt
import sys

# Configurando conexão serial
#ser = serial.Serial('/dev/ttyUSB0', 115200)

# Configurando o cliente MQTT
#mqtt_client = mqtt.Client()
#mqtt_client.connect("broker.hivemq.com", 1883)

#try:
#    while True:
#        # Lendo dados da serial
#        serial_data = ser.readline().decode('utf-8').strip()
#        
#        # Tratando dados (exemplo simples)
#        processed_data = f"Dado recebido: {serial_data}"
#        
#        # Publicando no MQTT
#        mqtt_client.publish("meu_topico/dados", processed_data)
#        print(f"Publicado: {processed_data}")

#except KeyboardInterrupt:
#    print("Encerrando aplicação...")
#    ser.close()

class LoRa2MQTTClient(mqtt.Client):
    def __init__(self, lora, broker, port, chip_mac, lora_slave_addrs, lora_slave_names, lora_slave_macs, lora_slave_vers, lora_slave_chips, home_assistant_prefix, broker_user=None, broker_pass=None, keepalive=60, mqtt_client_id="LoRa2MQTT"):
        super().__init__(mqtt_client_id, clean_session=True)
        self.lora = lora
        self.connected_flag = False
        self.broker_host = broker
        self.broker_port = port
        self.channel = constants.CHANNEL
        self.dispname = constants.DISP_NAME
        self.chip_mac = chip_mac
        self.idhdwdisp = None
        self.lora_slave_addrs = lora_slave_addrs
        self.lora_slave_names = lora_slave_names
        self.lora_slave_macs = lora_slave_macs
        self.lora_slave_vers = lora_slave_vers
        self.lora_slave_chips = lora_slave_chips
        self.num_slaves = None
        self.home_assistant_prefix = home_assistant_prefix
        self.keepalive_mqtt = keepalive
        self.bridge_topic = None          # Definido em _setup_mqtt_topics
        self.bridge_set_topic = None      # Definido em _setup_mqtt_topics
        self.bridge_status_topic = None   # Definido em _setup_mqtt_topics
        self.todos_topic = None           # Definido em _setup_mqtt_topics
        self.work_topics = []             # Definido em _setup_mqtt_topics
        self.tele_topics = []             # Definido em _setup_mqtt_topics
        self.set_topics = []              # Definido em _setup_mqtt_topics
        self.masc_uniq_topics = []        # Definido em _setup_mqtt_topics
        self.masc_disc_topics = []        # Definido em _setup_mqtt_topics
        self.lwt_topic = None             # Definido em _setup_mqtt_topics
        self.lwt_message = "offline"  # Mensagem enviada no LWT
        self.lwt_qos = 0
        self.lwt_retain = True
        self._setup_vars()
        self._setup_mqtt_topics()

        # Configurações de autenticação MQTT (se fornecidas)
        if broker_user and broker_pass:
            self.username_pw_set(broker_user, password=broker_pass)
        logging.info(f"MQTT Usr {broker_user}")
        logging.info(f"MQTT Usr {broker_pass}")

        # Configura o LWT
        self.will_set(self.lwt_topic, self.lwt_message, qos=self.lwt_qos, retain=self.lwt_retain)

        # Callback para eventos MQTT
        self.on_connect = LoRa2MQTTClient.cb_on_connect
        self.on_disconnect = LoRa2MQTTClient.cb_on_disconnect
        self.on_message = LoRa2MQTTClient.cb_on_message

        # Logging informativo
        logging.info(f"Client {mqtt_client_id} LoRa2MQTT Created")

    def _setup_vars(self):
        """Configura os tópicos MQTT."""
        self.idhdwdisp = last4(self.chip_mac)
        logging.info(f"Chip mac {self.chip_mac}")
        logging.info(f"Slave names {self.lora_slave_names}")

    def _setup_mqtt_topics(self):
        """Configura os tópicos MQTT."""
        self.num_slaves = len(self.lora_slave_names)
        self.bridge_topic = f"{self.channel}/bridge"
        self.bridge_set_topic = f"{self.bridge_topic}/+/set"
        self.bridge_status_topic = f"{self.channel}/bridge/status"
        self.todos_topic = f"{self.channel}/*/+/set"
        self.lwt_topic = self.bridge_status_topic

        # Configura os tópicos para cada slave
        for i in range(self.num_slaves):
            work_topic = f"{self.channel}/{self.lora_slave_names[i-1]}"
            tele_topic = f"{work_topic}/telemetry"
            set_topic = f"{work_topic}/+/set"
            masc_uniq_topic = f"{self.channel}_{self.lora_slave_macs[i-1]}_%s"
            masc_disc_topic = f"{self.home_assistant_prefix}/%s/{self.channel}_{self.lora_slave_macs[i-1]}/%s/config"

            self.work_topics.append(work_topic)
            self.tele_topics.append(tele_topic)
            self.set_topics.append(set_topic)
            self.masc_uniq_topics.append(masc_uniq_topic)
            self.masc_disc_topics.append(masc_disc_topic)

        # Logging para verificar se os tópicos foram configurados
        logging.info("MQTT topics successfully configured.")
        logging.info(f"Bridge Topic: {self.bridge_topic}")
        logging.info(f"Telemetry Topics: {self.tele_topics}")
        logging.info(f"Set Topics: {self.set_topics}")
        logging.info(f"Masc Disc Topics: {self.masc_disc_topics}")

    def send_message(self, topic, msg, retain=False):
        """Envia uma mensagem para um tópico MQTT."""
        try:
            logging.info(f'Sending message "{msg}" to topic "{topic}" with retain={retain}')
            self.publish(topic, msg, qos=0, retain=retain)
        except Exception as e:
            logging.error(f"Failed to send message: {e}")

    def mqtt_connection(self):
        """Tenta conectar ao broker MQTT."""
        try:
            logging.info(f"Connecting to MQTT broker {self.broker_host}:{self.broker_port}")
            self.connect(self.broker_host, self.broker_port, self.keepalive_mqtt)
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        """Callback para mensagens recebidas."""
        try:
            payload = message.payload.decode("utf-8")
            logging.debug(f"Message received on topic {message.topic}: {payload}")
            # Processa a mensagem aqui, se necessário
            client.handle_message(message)
        except Exception as e:
            logging.error(f"Error processing received message: {e}")

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        """Callback para desconexões."""
        client.connected_flag = False
        logging.info(f"Client {client._client_id.decode('utf-8')} disconnected!")

    @classmethod
    def cb_on_connect(cls, client, userdata, flags, rc):
        """Callback para conexões."""
        if rc == 0:
            client.connected_flag = True
            logging.info(f"Client {client._client_id.decode('utf-8')} connected successfully!")
            # Publica mensagem de "online" ao conectar
            client.publish(client.lwt_topic, "online", qos=0, retain=True)
            client.on_mqtt_connect()
        else:
            logging.error(f"Connection failed with return code {rc}")

    def handle_message(self, message):
        """Processa mensagens específicas (substituir pela lógica necessária)."""
        logging.info(f"Processing message from topic {message.topic}: {message.payload.decode('utf-8')}")


    def on_mqtt_connect(self):
        """Assina os tópicos MQTT necessários ao conectar."""
        try:
            # Subscrever aos tópicos principais
            self.subscribe(self.todos_topic, qos=1)
            self.subscribe(self.bridge_set_topic, qos=1)

            # Subscrever aos tópicos dos slaves
            for i in range(self.num_slaves):
                self.subscribe(self.set_topics[i-1], qos=1)

            # Atualiza status online
            self.online = False
            logging.info("Successfully subscribed to all relevant topics.")

        except Exception as e:
            logging.error(f"Error during MQTT topic subscription: {e}")

    def common_discovery(self):
        """
        Realiza a descoberta comum para o dispositivo principal.
        """
        payload = {
            "dev": {
                "ids": [f"{self.channel}_{self.chip_mac}"],
                "cns": [["mac", self.chip_mac]],
                "name": f"{self.dispname} {self.idhdwdisp}",
                "sw": constants.VERSION,
                "mf": "Leonardo Figueiró",
                "mdl": "Chip Model"  # Substituir por informações específicas do chip, se aplicável.
            }
        }
        return payload

    def common_discovery_ind(self, index):
        """
        Realiza a descoberta individual para um slave LoRa.
        """
        payload = {
            "dev": {
                "ids": [f"{self.channel}_{self.lora_slave_macs[index]}"],
                "cns": [["mac", self.lora_slave_macs[index]]],
                "name": f"{self.lora_slave_names[index]} {last4(self.lora_slave_macs[index])}",
                "sw": self.lora_slave_vers[index],
                "mf": "Leonardo Figueiró",
                "mdl": self.lora_slave_chips[index]
            }
        }
        return payload

    def send_connectivity_discovery(self):
        """
        Envia a descoberta de conectividade para o dispositivo principal.
        """
        payload = self.common_discovery()
        payload.update({
            "~": self.bridge_topic,
            "name": "Conectividade",
            "uniq_id": f"{self.channel}_{self.chip_mac}_conectividade",
            "json_attr_t": "~/telemetry",
            "stat_t": "~/status",
            "dev_cla": "connectivity",
            "pl_on": "online",
            "pl_off": "offline"
        })

        topic = f"{self.home_assistant_prefix}/binary_sensor/{self.channel}_{self.chip_mac}/conectividade/config"
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_aux_connectivity_discovery(self, index):
        """
        Envia a descoberta auxiliar de conectividade para um slave LoRa.
        """
        name = "Com Lora"
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "json_attr_t": "~/telemetry",
            "stat_t": f"~/{slug}",
            "dev_cla": "connectivity",
            "pl_on": "online",
            "pl_off": "offline"
        })

        topic = self.masc_disc_topics[index] % ("binary_sensor", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_tele_binary_sensor_discovery(self, index, name, entity_category, value_template, device_class):
        """
        Envia a descoberta de um sensor binário de telemetria via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": "~/telemetry",
            "value_template": value_template,
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class

        topic = self.masc_disc_topics[index] % ("binary_sensor", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_tele_sensor_discovery(self, index, name, entity_category, value_template, device_class, units):
        """
        Envia a descoberta de um sensor de telemetria via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": "~/telemetry",
            "value_template": value_template,
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class
        if units:
            payload["unit_of_meas"] = units

        topic = self.masc_disc_topics[index] % ("sensor", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_sensor_discovery(self, index, name, entity_category, device_class, units, state_class, force_update):
        """
        Envia a descoberta de um sensor MQTT com estado específico.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": f"~/{slug}",
            "frc_upd": force_update,
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class
        if units:
            payload["unit_of_meas"] = units
        if state_class:
            payload["stat_cla"] = state_class

        topic = self.masc_disc_topics[index] % ("sensor", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_binary_sensor_discovery(self, index, name, entity_category, device_class):
        """
        Envia a descoberta de um sensor binário via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": f"~/{slug}",
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class

        topic = self.masc_disc_topics[index] % ("binary_sensor", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_button_discovery(self, index, name, entity_category, device_class):
        """
        Envia a descoberta de um botão via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class

        topic = self.masc_disc_topics[index] % ("button", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_switch_discovery(self, index, name, entity_category):
        """
        Envia a descoberta de um interruptor via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
            "entity_category": entity_category,
        })

        topic = self.masc_disc_topics[index] % ("switch", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_number_discovery(self, index, name, entity_category, step):
        """
        Envia a descoberta de um número via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
        })
        if step:
            payload["step"] = step
        if entity_category:
            payload["entity_category"] = entity_category

        topic = self.masc_disc_topics[index] % ("number", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_light_discovery(self, index, name, entity_category, rgb):
        """
        Envia a descoberta de luz via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "schema": "json",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
            "brightness": True,
            "rgb": rgb,
        })
        if entity_category:
            payload["entity_category"] = entity_category

        topic = self.masc_disc_topics[index] % ("light", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_light_switch_discovery(self, index, name, entity_category):
        """
        Envia a descoberta de interruptor de luz via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery_ind(index)
        payload.update({
            "~": self.work_topics[index],
            "name": name,
            "uniq_id": self.masc_uniq_topics[index] % slug,
            "avty_t": "~/com_lora",
            "schema": "json",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
            "brightness": False,
            "rgb": False,
        })
        if entity_category:
            payload["entity_category"] = entity_category

        topic = self.masc_disc_topics[index] % ("light", slug)
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_bridge_button_discovery(self, name, entity_category, device_class):
        """
        Envia a descoberta de botão para a ponte via MQTT.
        """
        slug = slugify(name)
        payload = self.common_discovery()
        payload.update({
            "~": self.bridge_topic,
            "name": name,
            "uniq_id": f"{self.channel}_{self.chip_mac}_{slug}",
            "avty_t": "~/status",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class

        topic = f"{self.home_assistant_prefix}/button/{self.channel}_{self.chip_mac}/{slug}/config"
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_delete_discovery(self, domain, name):
        """
        Envia uma mensagem para deletar descoberta.
        """
        slug = slugify(name)
        topic = f"{self.home_assistant_prefix}/{domain}/{self.channel}_{self.chip_mac}/{slug}/config"
        return self.pub(topic, 0, False, "")

    def send_delete_discovery_x(self, domain, name, index):
        """
        Envia uma mensagem para deletar descoberta de um slave LoRa.
        """
        slug = slugify(name)
        topic = f"{self.home_assistant_prefix}/{domain}/{self.channel}_{self.lora_slave_macs[index]}/{slug}/config"
        return self.pub(topic, 0, False, "")

    def send_online(self):
        """
        Envia o status online do dispositivo via MQTT.
        """
        if self.pub(self.bridge_status_topic, 0, True, "online"):
            self.online = True
        else:
            logging.error("Erro enviando status=online")

    def send_com_lora(self):
        """
        Envia o status de conectividade dos dispositivos LoRa.
        """
        for i in range(self.num_slaves):
            if self.last_lora_com[i] != self.lora_com[i]:
                self.last_lora_com[i] = self.lora_com[i]
                status = "online" if self.lora_com[i] else "offline"
                self.pub(f"{self.work_topics[i]}/com_lora", 0, True, status)

    def send_telemetry(self):
        """
        Envia telemetria dos dispositivos LoRa.
        """
        tempo_loop = self.pega_delta_millis(self.last_tele_millis)
        if tempo_loop < self.refresh_telemetry:
            return

        self.last_tele_millis = self.millis()
        for i in range(self.num_slaves):
            payload = {
                "rssi": str(self.lora_rssi[i])
            }
            payload_json = json.dumps(payload)
            self.pub(self.tele_topics[i], 0, False, payload_json)

    def pub(self, topic, qos, retain, payload):
        """
        Publica uma mensagem no MQTT com tentativas de repetição.

        Args:
            topic (str): O tópico MQTT onde a mensagem será publicada.
            qos (int): Nível de Qualidade de Serviço (QoS).
            retain (bool): Define se a mensagem deve ser retida.
            payload (str): O conteúdo da mensagem.

        Returns:
            bool: True se a mensagem for publicada com sucesso, False caso contrário.
        """
        for attempt in range(10):  # Tenta publicar a mensagem até 10 vezes
            result = self.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            time.sleep(0.025)  # Espera 25ms entre as tentativas
        return False

# Funções Auxiliares
def last4(s):
    """
    Retorna os últimos 4 caracteres de uma string, começando do índice 8.
    """
    return s[8:]

def slugify(text):
    """Converte um texto em formato 'slug' (substitui espaços por _ e coloca tudo em minúsculas)."""
    return text.lower().replace(' ', '_')

def nome_com_lora(index):
    """Retorna o nome básico para um dispositivo LoRa."""
    return "Com LoRa"  # Pode ser expandido com nomes individuais, se necessário.

def slug_com_lora(index):
    """Retorna o nome slugificado de um dispositivo LoRa."""
    return slugify(nome_com_lora(index))

def isEmptyStr(s):
    return s == 'null' or len(s) == 0 or s.isspace()

def main(broker, port, broker_user, broker_pass, chip_mac, lora_slave_addrs, lora_slave_names, lora_slave_macs, lora_slave_vers, lora_slave_chips, home_assistant_prefix, max_threads):

    if not chip_mac:
        raise ValueError('Invalid LoRa chip mac.')

    #if not lora_slave_addrs or not lora_slave_names or not lora_slave_macs or not lora_slave_vers or not lora_slave_chips:
    #    raise ValueError('Invalid arrays of slaves.')
    
    if not home_assistant_prefix:
        raise ValueError('Invalid Homeassistant Prefix.')

    if not max_threads:
        max_threads = 200

    #lora_device = "/dev/ttyUSB0"  # Dispositivo LoRa (substituir conforme necessário)

    client = LoRa2MQTTClient("/dev/ttyUSB0", 
                             broker, 
                             port, 
                             chip_mac, 
                             [2,3], 
                             ["Eletricidade", "Luz"], 
                             ["234567890123", "345678901234"], 
                             ["Ver 1.1", "Ver 2.2"], 
                             ["ESP32", "ESP8266"], 
                             home_assistant_prefix, 
                             broker_user, 
                             broker_pass, 
                             60, 
                             "LoRa2MQTT_123456")

    try:
        client.mqtt_connection()
        client.loop_start()  # Inicia o loop MQTT em uma thread separada
        client.send_connectivity_discovery()
        while True:
            # Simulação de envio de mensagens
            data_to_publish = "Mensagem do LoRa simulada"
            client.send_message("lora2mqtt/dados", data_to_publish)
            time.sleep(10)  # Intervalo entre mensagens
    except KeyboardInterrupt:
        logging.info("Encerrando aplicação LoRa2MQTT...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == '__main__':
    broker = 'localhost'
    port = 1883
    broker_user = None
    broker_pass = None
    chip_mac = None
    lora_slave_addrs = None
    lora_slave_names = None
    lora_slave_macs = None
    lora_slave_vers = None
    lora_slave_chips = None
    home_assistant_prefix = None
    max_threads = None
    loglevel = 'INFO'
    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]
    short_options = 'b:p:u:P:c:a:n:m:v:C:h:l:M'
    long_options = ['broker=', 'port=', 'user=',
                    'Pass=', 'chip=', 'addrs=',
                    'names=', 'macs=', 'vers=',
                    'Chips=','haprefix=','log_level=',
                    'Max_threads=']
    try:
        arguments, values = getopt.getopt(
            argument_list, short_options, long_options)
    except getopt.error:
        raise ValueError('Invalid parameters!')

    for current_argument, current_value in arguments:
        if isEmptyStr(current_value):
            pass
        elif current_argument in ("-b", "--broker"):
            broker = current_value
        elif current_argument in ("-p", "--port"):
            port = int(current_value)
        elif current_argument in ("-u", "--user"):
            broker_user = current_value
        elif current_argument in ("-P", "--Pass"):
            broker_pass = current_value
        elif current_argument in ("-c", "--chip"):
            chip_mac = current_value
        elif current_argument in ("-a", "--addrs"):
            lora_slave_addrs = current_value
        elif current_argument in ("-n", "--names"):
            lora_slave_names = current_value
        elif current_argument in ("-m", "--macs"):
            lora_slave_macs = current_value
        elif current_argument in ("-v", "--lvers"):
            lora_slave_vers = current_value
        elif current_argument in ("-", "--Chips"):
            lora_slave_chips = current_value
        elif current_argument in ("-h", "--haprefix"):
            home_assistant_prefix = current_value
        elif current_argument in ("-l", "--log_level"):
            loglevel = int(current_value)
        elif current_argument in ("-M", "--Max_threads"):
            max_threads = int(current_value)

    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] LoRa2MQTT: %(message)s', )

    logging.debug("Options: {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}".format(
        chip_mac, home_assistant_prefix, lora_slave_addrs, lora_slave_names, lora_slave_macs, lora_slave_vers, lora_slave_chips, broker, port, broker_user, broker_pass, loglevel, max_threads))
    main(broker, port, broker_user, broker_pass, chip_mac, lora_slave_addrs, lora_slave_names, lora_slave_macs, lora_slave_vers, lora_slave_chips, home_assistant_prefix, max_threads)
    