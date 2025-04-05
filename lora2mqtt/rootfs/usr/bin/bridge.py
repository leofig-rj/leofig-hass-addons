import serial
import paho.mqtt.client as mqtt
import logging
import json
import os
import time
import getopt
import sys

import yaml

import lflora
import msgs
import devs
import funcs
import globals

from consts import MSG_CHECK_OK, ADDON_NAME, ADDON_SLUG, VERSION, UINQUE, OWNER, HA_PREFIX, LWT_MSG, LWT_QOS, \
    LWT_REATAIN, MQTT_KEEP_ALIVE, MQTT_CLIENT_ID, EC_DIAGNOSTIC, DEVICE_CLASS_RESTART

class LoRa2MQTTClient(mqtt.Client):
    def __init__(self, lora, broker, port, usb_id, broker_user=None, broker_pass=None):
        super().__init__(MQTT_CLIENT_ID, clean_session=True)
        self.lora = lora
        self.connected_flag = False
        self.broker_host = broker
        self.broker_port = port
        self.addon_slug = ADDON_SLUG
        self.addon_name = ADDON_NAME
        self.usb_id = usb_id
        self.ram_devs = globals.devices.get_dev_rams()
        self.num_slaves = None            # Definido em _setup_mqtt_topics
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
        self._setup_mqtt_topics()

        # Configurações de autenticação MQTT (se fornecidas)
        if broker_user and broker_pass:
            self.username_pw_set(broker_user, password=broker_pass)
        logging.debug(f"MQTT Usr {broker_user}")
        logging.debug(f"MQTT Usr {broker_pass}")

        # Configura o LWT
        self.will_set(self.lwt_topic, LWT_MSG, qos=LWT_QOS, retain=LWT_REATAIN)

        # Callback para eventos MQTT
        self.on_connect = LoRa2MQTTClient.cb_on_connect
        self.on_disconnect = LoRa2MQTTClient.cb_on_disconnect
        self.on_message = LoRa2MQTTClient.cb_on_message

        # Logging informativo
        logging.info(f"Client {MQTT_CLIENT_ID} LoRa2MQTT Created")

    def _setup_mqtt_topics(self):
        """Configura os tópicos MQTT."""
        self.num_slaves = len(self.ram_devs)
        self.bridge_topic = f"{self.addon_slug}/bridge"
        self.bridge_set_topic = f"{self.bridge_topic}/+/set"
        self.bridge_status_topic = f"{self.addon_slug}/bridge/status"
        self.todos_topic = f"{self.addon_slug}/*/+/set"
        self.lwt_topic = self.bridge_status_topic

        # Configura os tópicos para cada slave
        for i in range(self.num_slaves):
            work_topic = f"{self.addon_slug}/{self.ram_devs[i-1].slaveName}"
            tele_topic = f"{work_topic}/telemetry"
            set_topic = f"{work_topic}/+/set"
            masc_uniq_topic = f"{self.addon_slug}_{self.ram_devs[i-1].slaveMac}_%s"
            masc_disc_topic = f"{HA_PREFIX}/%s/{self.addon_slug}_{self.ram_devs[i-1].slaveMac}/%s/config"

            self.work_topics.append(work_topic)
            self.tele_topics.append(tele_topic)
            self.set_topics.append(set_topic)
            self.masc_uniq_topics.append(masc_uniq_topic)
            self.masc_disc_topics.append(masc_disc_topic)

        # Logging para verificar se os tópicos foram configurados
        logging.debug("MQTT topics successfully configured.")
        logging.debug(f"Bridge Topic: {self.bridge_topic}")
        logging.debug(f"Telemetry Topics: {self.tele_topics}")
        logging.debug(f"Set Topics: {self.set_topics}")
        logging.debug(f"Masc Disc Topics: {self.masc_disc_topics}")

    def send_message(self, topic, msg, retain=False):
        """Envia uma mensagem para um tópico MQTT."""
        try:
            logging.debug(f'Sending message "{msg}" to topic "{topic}" with retain={retain}')
            self.publish(topic, msg, qos=0, retain=retain)
        except Exception as e:
            logging.error(f"Failed to send message: {e}")

    def mqtt_connection(self):
        """Tenta conectar ao broker MQTT."""
        try:
            logging.debug(f"Connecting to MQTT broker {self.broker_host}:{self.broker_port}")
            self.connect(self.broker_host, self.broker_port, MQTT_KEEP_ALIVE)
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
        """Processa mensagens recebidas do MQTT)."""
        logging.debug(f"Processando msg do topico {message.topic}: {message.payload.decode('utf-8')}")
        msgs.on_mqtt_message(message.topic, message.payload)
    
    def proc_command(self, entity, pay):
        """Processa comando para Bridge recebidas do MQTT)."""
        logging.debug(f"Processando comando para Bridge {entity}: {pay}")

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
                "ids": [f"{self.addon_slug}_{UINQUE}"],
                "name": f"{self.addon_name} Bridge",
                "sw": VERSION,
                "hw": self.usb_id,
                "mf": OWNER,
                "mdl": "Bridge"
            }
        }
        return payload

    def common_discovery_ind(self, index):
        """
        Realiza a descoberta individual para um slave LoRa. 
        """
        payload = {
            "dev": {
                "ids": [f"{self.addon_slug}_{self.ram_devs[index].slaveMac}"],
                "cns": [["mac", self.ram_devs[index].slaveMac]],
                "name": f"{self.ram_devs[index].slaveName} {funcs.last4(self.ram_devs[index].slaveMac)}",
                "sw": self.ram_devs[index].slaveVer,
                "mf": self.ram_devs[index].slaveMan,
                "mdl": self.ram_devs[index].slaveModel
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
            "uniq_id": f"{self.addon_slug}_{UINQUE}_conectividade",
            "json_attr_t": "~/telemetry",
            "stat_t": "~/status",
            "dev_cla": "connectivity",
            "pl_on": "online",
            "pl_off": "offline"
        })

        topic = f"{HA_PREFIX}/binary_sensor/{self.addon_slug}_{UINQUE}/conectividade/config"
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_aux_connectivity_discovery(self, index):
        """
        Envia a descoberta auxiliar de conectividade para um slave LoRa.
        """
        name = "Com Lora"
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
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
        slug = funcs.slugify(name)
        payload = self.common_discovery()
        payload.update({
            "~": self.bridge_topic,
            "name": name,
            "uniq_id": f"{self.addon_slug}_{UINQUE}_{slug}",
            "avty_t": "~/status",
            "stat_t": f"~/{slug}",
            "cmd_t": f"~/{slug}/set",
        })
        if entity_category:
            payload["entity_category"] = entity_category
        if device_class:
            payload["dev_cla"] = device_class

        topic = f"{HA_PREFIX}/button/{self.addon_slug}_{UINQUE}/{slug}/config"
        payload_json = json.dumps(payload)
        return self.pub(topic, 0, True, payload_json)

    def send_delete_discovery(self, domain, name):
        """
        Envia uma mensagem para deletar descoberta.
        """
        slug = funcs.slugify(name)
        topic = f"{HA_PREFIX}/{domain}/{self.addon_slug}_{UINQUE}/{slug}/config"
        return self.pub(topic, 0, False, "")

    def send_delete_discovery_x(self, domain, name, index):
        """
        Envia uma mensagem para deletar descoberta de um slave LoRa.
        """
        slug = funcs.slugify(name)
        topic = f"{HA_PREFIX}/{domain}/{self.addon_slug}_{self.ram_devs[index].slaveMac}/{slug}/config"
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
        tempo_loop = funcs.pega_delta_millis(self.last_tele_millis)
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

########### MAIN ############
def main(broker, port, broker_user, broker_pass):
    usb_id = "Desconhecido"

    # Carrega as opções configuradas no addon
    with open("/data/options.json") as config_file:
        options = json.load(config_file)

    max_threads = options.get("max_threads", 200)
    logging.debug(f"max_threads: {max_threads}")
    serial_obj = options.get("serial", {"port": "/dev/ttyACM0"})
    logging.debug(f"serial_obj: {serial_obj}")
    data_path = options.get("data_path", "/config/lora2mqtt")
    logging.debug(f"data_path: {data_path}")

    # Inicializa variáveis globais
    globals.devices = devs.DeviceManager()
    globals.devices.load_devices_to_ram()


    # Verifica se a pasta existe
    try:
        if os.path.exists(data_path) and os.path.isdir(data_path):
            logging.debug(f"Pasta encontrada: {data_path}")
            # Listar arquivos, por exemplo:
            arquivos = os.listdir(data_path)
            logging.debug(f"Arquivos na pasta: {arquivos}")
            arquivos = [arquivo for arquivo in os.listdir(data_path) if arquivo.endswith(".py")]
            logging.debug(f"Arquivos Python encontrados: {arquivos}")
        else:
            logging.error(f"O caminho não é uma pasta válida: {data_path}")
    except PermissionError:
        logging.error("Erro: Permissão negada para acessar a pasta.")




    config_file_path = "/config/lora2mqtt/teste.yaml"

    # Verifica se o arquivo existe, caso contrário, cria um arquivo vazio
    if not os.path.exists(config_file_path):
        try:
            with open(config_file_path, "w") as arquivo_yaml:
                yaml.dump({"devices": []}, arquivo_yaml)
        except OSError as e:
            logging.error(f"Erro ao criar o arquivo: {e}")
            logging.error("Certifique-se de que o diretório possui permissões de gravação.")

    try:
        # Configurando conexão serial
        ser = serial.Serial(serial_obj["port"], 115200)
        ser.flush()

    except serial.SerialException as e:
        ser = None  # Define como None para evitar problemas futuros
        logging.error(f"Erro {e} na configuração serial...")

    try:
        
       if ser:
            # Envio comando de solicitação de estado da dongue
            ser.write("!000".encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
            logging.debug("Enviado comando solicita estado do adaptador")
            time.sleep(2)  # Aguarda 2 segundos
            # Verifico se tem dado na serial
            if ser.in_waiting > 0:
                # Pegando o dado e deixando como string
                serial_data = ser.readline().decode('utf-8').strip()
                # Tratando o dado
                if serial_data[0] == '!':
                    usb_id = serial_data[1:]
                    logging.debug(f"Recebeu do adaptador: {usb_id}")

            client = LoRa2MQTTClient("/dev/ttyUSB0", 
                                    broker, 
                                    port, 
                                    usb_id, 
                                    broker_user, 
                                    broker_pass) 
            
            # Torno o cliente global
            globals.client_mqtt = client
            
            lf_lora = lflora.LFLoraClass()
            lf_lora.set_my_addr(1)

            client.mqtt_connection()
            client.loop_start()  # Inicia o loop MQTT em uma thread separada
            client.send_connectivity_discovery()
            client.send_bridge_button_discovery("Reset ESP", EC_DIAGNOSTIC, DEVICE_CLASS_RESTART)

            contador = 0

            while True:
                # Verifico se tem dado na serial
                if ser.in_waiting > 0:
                    # Pegando o dado e deixando como string
                    serial_data = ser.readline().decode('utf-8').strip()
                    # Tratando o dado
                    result, de, para, msg = lf_lora.lora_check_msg_ini(serial_data)
                    logging.debug(f"Recebido result: {result} de: {de} para: {para} msg: {msg}")
                    # Trato a mensagem
                    if result == MSG_CHECK_OK:
                        # Publicando a msg limpa
                        data_to_publish = f"Dado recebido: {msg}"
                        client.send_message("lora2mqtt/dados", data_to_publish)
                        # Tratando a msg conforme remetente
                        index = funcs.get_index_from_addr(de)
                        msgs.on_lora_message(msg, index)

    
                if funcs.pega_delta_millis(msgs.loraCommandTime) > msgs.LORA_TEMPO_REFRESH:
                    msgs.loraCommandTime = int(time.time() * 1000)

                    # Envio comando de solicitação de estado
                    serial_data = lf_lora.lora_add_header("000", contador + 2)
                    ser.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
                    logging.debug(f"Enviado {serial_data}")

                    contador = (contador + 1) % 2

    except Exception as e:
        logging.error(f"Erro: {e}")
    finally:
        logging.error("Encerrando aplicação LoRa2MQTT...")
        ser.close()
        client.loop_stop()
        client.disconnect()

if __name__ == '__main__':
    broker = 'localhost'
    port = 1883
    broker_user = None
    broker_pass = None
    loglevel = 'INFO'

    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]
    short_options = 'b:p:u:P'
    long_options = ['broker=', 'port=', 'user=',
                    'Pass=']
    try:
        arguments, values = getopt.getopt(
            argument_list, short_options, long_options)
    except getopt.error:
        raise ValueError('Invalid parameters!')

    for current_argument, current_value in arguments:
        if funcs.is_empty_str(current_value):
            pass
        elif current_argument in ("-b", "--broker"):
            broker = current_value
        elif current_argument in ("-p", "--port"):
            port = int(current_value)
        elif current_argument in ("-u", "--user"):
            broker_user = current_value
        elif current_argument in ("-P", "--Pass"):
            broker_pass = current_value

    # Carregar as opções do add-on
    with open('/data/options.json') as options_file:
        options = json.load(options_file)

    log_level = options.get('log_level', 'INFO').upper()

    # Configurar o logger
    logging.basicConfig(level=getattr(logging, log_level), datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] LoRa2MQTT: %(message)s', )
    
    logger = logging.getLogger(__name__)
    logger.info("Nível de logging configurado para: %s", log_level)  
    logger.debug(f"Options: {broker}, {port}, {broker_user}, {broker_pass}")
    
    main(broker, port, broker_user, broker_pass)

