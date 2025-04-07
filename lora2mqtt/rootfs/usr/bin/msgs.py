import time
import logging
import requests

import funcs
import globals

#from .devices import pw01

# Constantes para LFLoRa
from consts import  MSG_CHECK_OK

# Para LoRa
from consts import LORA_FIFO_LEN, LORA_TEMPO_REFRESH, LORA_NUM_TENTATIVAS_CMD, LORA_TEMPO_OUT

# Para MQTT
from consts import EC_DIAGNOSTIC, DEVICE_CLASS_RESTART, DEVICE_CLASS_SIGNAL_STRENGTH

from consts import ADDON_SLUG, UINQUE

# Variáveis globais
online = False

loraCommandTime = 0
lastMsgSent = ""
lastIdRec = 0
lastIdSent = 0
tentativasCmd = 0

loraFiFoPrimeiro = 0
loraFiFoUltimo = 0
loraFiFoMsgBuffer = [""] * LORA_FIFO_LEN
loraFiFoDestinoBuffer = [0] * LORA_FIFO_LEN
loraUltimoDestinoCmd = 0


# Configurações
url = "http://10.0.1.20:8123/api/devices"
headers = {
    "Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmZTJiZmRiZjJkNmE0YWEyOWEwY2ZiZTNhMWY4NzRkZCIsImlhdCI6MTc0NDA1MDU4OSwiZXhwIjoyMDU5NDEwNTg5fQ.mNt5-tDLeNLhL3aaf4KemmBShisffScu6JhleysQLl0",  # Substitua pelo seu token de acesso
    "Content-Type": "application/json",
}

def mqtt_filhos():
    global url, headers
    # Requisição para listar dispositivos
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        devices = response.json()
        bridge_id = f"{ADDON_SLUG}_{UINQUE}"  # Substitua pelo ID da sua Bridge
        child_device_ids = [
            device["id"] for device in devices if device.get("via_device_id") == bridge_id
        ]
        logging.info(f"IDs dos dispositivos filhos da Bridge: , {child_device_ids}")
    else:
        logging.info(f"Erro ao obter dispositivos: {response.status_code}")
    # Requisição para listar dispositivos
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        devices = response.json()
        mqtt_devices = [
            device for device in devices if "mqtt" in device.get("config_entries", [])
        ]
        for device in mqtt_devices:
            logging.info(f"ID: {device['id']} - Nome: {device['name']}")
    else:
        logging.info(f"Erro ao acessar dispositivos: {response.status_code}")

def loop_serial():
    global lastIdRec
    # Verifico se tem dado na serial
    if globals.g_serial.in_waiting > 0:
        # Pegando o dado e deixando como string
        serial_data = globals.g_serial.readline().decode('utf-8').strip()
        # Tratando o dado
        result, de, para, id, msg = globals.g_lf_lora.lora_check_msg_ini(serial_data)
        logging.debug(f"Recebido result: {result} de: {de} para: {para} msg: {msg}")
        # Trato a mensagem
        if result == MSG_CHECK_OK:
            # Preservando o ID
            lastIdRec = id
            # Tratando a msg conforme remetente
            index = funcs.get_index_from_addr(de)
            logging.debug(f"Índice do dispositivo: {index}")
            on_lora_message(msg, index)

def loop_mqtt():
    global online
    
    if not online:
        if mqtt_send_online():
            logging.debug("Discovery")
            mqtt_send_discovery_bridge()
            mqtt_send_discovery_entities()

    # Em Python, `yield` pode ser substituído por uma pausa como `time.sleep`
    time.sleep(0.01)

    if online:
        mqtt_send_com_lora()

    # Outra pausa
    time.sleep(0.01)

    if online:
        mqtt_send_entities()

def on_mqtt_message(topic, payload):

    # Converte o payload de byte para string
    #payload_char = payload.decode('utf-8')[:LFLORA_MAX_PACKET_SIZE]

    top = topic
    pay = payload

    if "/set" in top:
        set_pos = top.rfind("/set")
        entity_pos = top.rfind("/", 0, set_pos)
        if entity_pos == -1:
            logging.error(f"Na msg recebida de MQTT não encontrado /set: | {top} para {pay}")
            return
        entity = top[entity_pos + 1:set_pos]
        logging.debug(f"Set | {entity} para {pay}")
        
        # Para pegar o dispositivo que enviou o comando
        device_pos = top.rfind("/", 0, entity_pos)
        if device_pos == -1:
            logging.error(f"Na msg recebida de MQTT não encontrado o dispositivo: | {top} para {pay}")
            return
        device = top[device_pos + 1:entity_pos]
        logging.debug(f"Dispositivo {device}")

        if device == 'bridge':
            # Trata comando de Bridge
            mqtt_bridge_proc_command(entity, pay)
        else:
            # Procura nos dispositivo
            index = globals.g_devices.find_device_by_name(device)
            if index is not None:
                ram_dev = globals.g_devices.get_dev_rams()[index]
                ram_dev.slaveObj.proc_command(entity, pay, index)
            else:
                logging.debug(f"Não encontrado dispositivo {device}")
    else:
        logging.error(f"A msg recebida de MQTT não foi tratada: | {top} para {pay}")

def mqtt_bridge_proc_command(entity, pay):
    """Processa comando para Bridge recebidas do MQTT)."""
    if entity != "reset_esp":
        return
    logging.debug(f"Processando comando para Bridge {entity}: {pay}")
    # Vou tentar excluir o dispositivo indice 0
    ram_devs = globals.g_devices.get_dev_rams()
    client = globals.g_cli_mqtt
    client.send_delete_discovery_x("binary_sensor", "Com LoRa", 0)
    client.send_delete_discovery_x("sensor", "RSSI", 0)
    obj = ram_devs[0].slaveObj
    logging.info(f"Objeto {obj}")
    logging.info(f"Dominios {obj.entityDomains}")
    logging.info(f"Nmes {obj.entityNames}")
    for i in range(len(obj.entityNames)):
        logging.info(f"Entidade {i} Domínio {obj.entityDomains[i]} Nome {obj.entityNames[i]}")
#        client.send_delete_discovery_x(0, obj.entityDomains[i], obj.entityNames[i])
 

def mqtt_send_online():
    global online

    if globals.g_cli_mqtt.pub(globals.g_cli_mqtt.bridge_status_topic, 0, True, "online"):
        online = True
    else:
        logging.debug("Erro enviando status=online")
    return online

def mqtt_send_discovery_bridge():
    globals.g_cli_mqtt.send_connectivity_discovery()
    globals.g_cli_mqtt.send_bridge_button_discovery("Reset ESP", EC_DIAGNOSTIC, DEVICE_CLASS_RESTART)

def mqtt_send_discovery_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    for i in range(len(ram_devs)):
        # Publica discovery do Com LoRa e RSSI do dispositivo
        mqtt_send_aux_connectivity_discovery(i)
        mqtt_send_sensor_discovery(i, "RSSI", EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH, "", "", True)
        # Publica discovery das entidades do dispositivo (modelo)
        ram_devs[i].slaveObj.proc_discovery(i)
        logging.debug(f"Discovery Entity {i}")

def mqtt_send_com_lora():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    for i in range(len(ram_devs)):
        if ram_devs[i].loraLastCom != ram_devs[i].loraCom:
            ram_devs[i].loraLastCom = ram_devs[i].loraCom

            s_com_lora = "online" if ram_devs[i].loraCom else "offline"
            logging.debug(f"Com LoRa {i} {s_com_lora}")

            globals.g_cli_mqtt.pub(f"{globals.g_cli_mqtt.work_topics[i]}/com_lora", 0, True, s_com_lora)

def mqtt_set_rssi(index, rssi):
    # Salvo RSSI do Dispositivo na RAM
    ram_devs = globals.g_devices.get_dev_rams()
    ram_devs[index].loraRSSI = rssi

def mqtt_send_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    # Envio os estados das entidades
    for i in range(len(ram_devs)):
        if ram_devs[i].loraCom:
            # Publica RSSI do dispositivo
            if ram_devs[i].loraLastRSSI != ram_devs[i].loraRSSI:
                ram_devs[i].loraLastRSSI = ram_devs[i].loraRSSI
                mqtt_pub(i, "rssi", str(ram_devs[i].loraRSSI))
            # Publica entidades do dispositivo (modelo)
            ram_devs[i].slaveObj.proc_publish(i)

def mqtt_pub(index, slug, val):
    client = globals.g_cli_mqtt
    return client.pub(f"{client.work_topics[index]}/{slug}", 0, True, val)

def mqtt_send_aux_connectivity_discovery(index):
    client = globals.g_cli_mqtt
    return client.send_aux_connectivity_discovery(index)

def mqtt_send_tele_binary_sensor_discovery(index, name, entity_category, value_template, device_class):
    client = globals.g_cli_mqtt
    return client.send_tele_binary_sensor_discovery(index, name, entity_category, value_template, device_class)

def mqtt_send_tele_sensor_discovery(index, name, entity_category, value_template, device_class, units):
    client = globals.g_cli_mqtt
    return client.send_tele_sensor_discovery(index, name, entity_category, value_template, device_class, units)

def mqtt_send_sensor_discovery(index, name, entity_category, device_class, units, state_class, force_update):
    client = globals.g_cli_mqtt
    return client.send_sensor_discovery(index, name, entity_category, device_class, units, state_class, force_update)

def mqtt_send_binary_sensor_discovery(index, name, entity_category, device_class):
    client = globals.g_cli_mqtt
    return client.send_binary_sensor_discovery(index, name, entity_category, device_class)

def mqtt_send_button_discovery(index, name, entity_category, device_class):
    client = globals.g_cli_mqtt
    return client.send_button_discovery(index, name, entity_category, device_class)

def mqtt_send_switch_discovery(index, name, entity_category):
    client = globals.g_cli_mqtt
    return client.send_switch_discovery(index, name, entity_category)

def mqtt_send_number_discovery(index, name, entity_category, step):
    client = globals.g_cli_mqtt
    return client.send_number_discovery(index, name, entity_category, step)

def mqtt_send_light_discovery(index, name, entity_category, rgb):
    client = globals.g_cli_mqtt
    return client.send_light_discovery(index, name, entity_category, rgb)

def mqtt_send_light_switch_discovery(index, name, entity_category):
    client = globals.g_cli_mqtt
    return client.send_light_switch_discovery(index, name, entity_category)

def loop_lora():

    ram_devs = globals.g_devices.get_dev_rams()

    # Verifico Time out dos dispositivos para informar desconexão
    for i in range(len(ram_devs)):
        tempoOut = funcs.pega_delta_millis(ram_devs[i].loraTimeOut)
        if tempoOut > LORA_TEMPO_OUT:
            ram_devs[i].loraTimeOut = funcs.millis()
            ram_devs[i].loraCom = False
    
    # Verifico se a última mensagem retornou...
    if not lora_ultimo_cmd_retornou():
        return

    # Verifico se tem comando no FiFo para enviar...
    lora_fifo_verifica()

    # Solicito estado periodicamente...
    tempoLoop = funcs.pega_delta_millis(loraCommandTime)
    if tempoLoop > LORA_TEMPO_REFRESH:
        lora_fifo_tenta_enviar("000", loraUltimoDestinoCmd)
        # Defino o próximo destino para solicitar estado...
        lora_proximo_destino_cmd()

def on_lora_message(sMsg, index):
    global loraFiFoPrimeiro, loraFiFoUltimo
    logging.debug(f"Tamanho da MSG: {len(sMsg)} Índice {index}")
    
    if loraFiFoPrimeiro != loraFiFoUltimo:
        logging.info("FiFo não está vazia!")
        return
    
    # Pego o Dispositivo na RAM
    ram_dev = globals.g_devices.get_dev_rams()[index]

    # Executa a rotina no dispositivo (modelo)
    ram_dev.slaveObj.proc_rec_msg(sMsg, index)

    # Atualizo variáveis de contexto
    ram_dev.loraTimeOut = funcs.millis()
    ram_dev.loraCom = True
    if lora_pega_ultimo_destino_cmd() == index:
        lora_proximo_destino_cmd()

    return

def lora_fifo_tenta_enviar(sMsg, index):
    global loraFiFoPrimeiro, loraFiFoUltimo, loraFiFoMsgBuffer, loraFiFoDestinoBuffer
    
    if loraFiFoPrimeiro == loraFiFoUltimo:
        if lora_ultimo_cmd_retornou():
            lora_envia_mensagem_index(sMsg, index)
            return
    
    aux = (loraFiFoUltimo + 1) % LORA_FIFO_LEN
    if aux == loraFiFoPrimeiro:
        return
    
    loraFiFoMsgBuffer[loraFiFoUltimo] = sMsg
    loraFiFoDestinoBuffer[loraFiFoUltimo] = index
    loraFiFoUltimo = aux

def lora_envia_mensagem_index(sMsg, index):
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    lora_envia_mensagem(sMsg, ram_devs[index].slaveAddr)


def lora_envia_mensagem(sMsg, para):
    global loraCommandTime, tentativasCmd, lastIdSent, lastMsgSent
    
    loraCommandTime = funcs.millis()
    tentativasCmd = 0
    
    # Envio comando de solicitação de estado
    serial_data = globals.g_lf_lora.lora_add_header(sMsg, para)
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.debug(f"Enviado {serial_data}")

    lastIdSent = globals.g_lf_lora.last_sent_id()
    lastMsgSent = serial_data

def lora_reenvia_mensagem():
    global loraCommandTime, tentativasCmd
    
    loraCommandTime = funcs.millis()
    tentativasCmd += 1

    # Reenvio último comando
    serial_data = lastMsgSent
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.debug(f"Renviado {serial_data}")

def lora_ultimo_cmd_retornou():
    global lastIdRec, lastIdSent, loraCommandTime, tentativasCmd
    
    if lastIdRec == lastIdSent:
        return True
    
    if funcs.pega_delta_millis(loraCommandTime) > LORA_TEMPO_REFRESH:
        if tentativasCmd >= LORA_NUM_TENTATIVAS_CMD:
            return True
        lora_reenvia_mensagem()
    return False

def lora_fifo_verifica():
    global loraFiFoPrimeiro, loraFiFoUltimo, loraFiFoMsgBuffer, loraFiFoDestinoBuffer
    
    if loraFiFoPrimeiro != loraFiFoUltimo:
        if lora_ultimo_cmd_retornou():
            lora_envia_mensagem_index(loraFiFoMsgBuffer[loraFiFoPrimeiro], \
                                      loraFiFoDestinoBuffer[loraFiFoPrimeiro])
            loraFiFoPrimeiro = (loraFiFoPrimeiro + 1) % LORA_FIFO_LEN

def lora_proximo_destino_cmd():
    global loraUltimoDestinoCmd

    loraUltimoDestinoCmd = (loraUltimoDestinoCmd + 1) % len(globals.g_devices.get_dev_rams())

def lora_pega_ultimo_destino_cmd():
    global loraUltimoDestinoCmd
    return loraUltimoDestinoCmd

