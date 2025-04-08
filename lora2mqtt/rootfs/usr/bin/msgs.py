import time
import logging

import funcs
import globals

# Constantes para LFLoRa
from consts import  MSG_CHECK_OK

# Para LoRa
from consts import LORA_FIFO_LEN, LORA_NUM_TENTATIVAS_CMD, LORA_TEMPO_CMD, LORA_TEMPO_OUT, LORA_TEMPO_LOOP

# Para MQTT
from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH, DEVICE_CLASS_UPDATE

# Variáveis globais
online = False

loraCommandTime = 0
loraLoopTime = 0
lastMsgSent = ""
lastIdRec = 0
lastIdSent = 0
tentativasCmd = 0

loraFiFoPrimeiro = 0
loraFiFoUltimo = 0
loraFiFoMsgBuffer = [""] * LORA_FIFO_LEN
loraFiFoDestinoBuffer = [0] * LORA_FIFO_LEN
loraUltimoDestinoCmd = 0

mqttLastBridgeSelect = ""


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
            if index is None:
                return
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
    global mqttLastBridgeSelect
    ram_devs = globals.g_devices.get_dev_rams()
    client = globals.g_cli_mqtt
    if entity == "dispositivos":
        mqttLastBridgeSelect = pay
        logging.info(f"Processando comando para Bridge {entity}: {pay}")
        client.pub(f"{client.bridge_topic}/{entity}/status", 0, True, pay)
        return
    if entity == "excluir_disp":
        logging.info(f"Processando comando para Bridge {entity}: {pay}")
        for i in range(len(ram_devs)):
            if ram_devs[i].slaveName == mqttLastBridgeSelect:
                # Vou tentar excluir o dispositivo indice i
                client.send_delete_discovery_x(i, "binary_sensor", "Com LoRa")
                client.send_delete_discovery_x(i, "sensor", "RSSI")
                obj = ram_devs[i].slaveObj
                for j in range(len(obj.entityNames)):
                    logging.info(f"Dev {ram_devs[i].slaveName} Entidade {j} Domínio {obj.entityDomains[j]} Nome {obj.entityNames[j]}")
                    client.send_delete_discovery_x(i, obj.entityDomains[j], obj.entityNames[j])
                # Excluo da lista de slaves
                ram_devs.remove(ram_devs[i])
                # Refresco o select de dispositivos
                mqtt_send_bridge_select_discovery()
                # Refresco os tópicos de cliente
                client.setup_mqtt_topics()

def mqtt_send_online():
    global online

    if globals.g_cli_mqtt.pub(globals.g_cli_mqtt.bridge_status_topic, 0, True, "online"):
        online = True
    else:
        logging.debug("Erro enviando status=online")
    return online

def mqtt_send_discovery_bridge():
    client = globals.g_cli_mqtt
    client.send_connectivity_discovery()
    client.send_bridge_button_discovery("Excluir Disp", EC_NONE, DEVICE_CLASS_UPDATE)
    mqtt_send_bridge_select_discovery()

def mqtt_send_bridge_select_discovery():
    global mqttLastBridgeSelect
    # Inicializo o último da memória
    mqttLastBridgeSelect = ""
    # Pego os Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()
    # Crio lista com nomes dos dispositivos
    devs = []
    for i in range(len(ram_devs)):
        devs.append(ram_devs[i].slaveName)
    client = globals.g_cli_mqtt
    client.send_bridge_select_discovery("Dispositivos", EC_NONE, devs)
    if len(ram_devs) > 0:
        client.pub(f"{client.bridge_topic}/dispositivos/status", 0, True, ram_devs[0].slaveName)
        mqttLastBridgeSelect = ram_devs[0].slaveName


def mqtt_send_discovery_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    if len(ram_devs) == 0:
        return

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

    if len(ram_devs) == 0:
        return

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
    global loraCommandTime, loraLoopTime, loraUltimoDestinoCmd

    ram_devs = globals.g_devices.get_dev_rams()

    if len(ram_devs) == 0:
        return

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

    # Vejo se o tempo de loop já passou
    tempoLoop = funcs.pega_delta_millis(loraLoopTime)
    if tempoLoop <= LORA_TEMPO_LOOP:
        return

    # Solicito estado periodicamente...
    tempoCmd = funcs.pega_delta_millis(loraCommandTime)
    if tempoCmd > LORA_TEMPO_CMD:
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
    
    if funcs.pega_delta_millis(loraCommandTime) > LORA_TEMPO_CMD:
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
    global loraUltimoDestinoCmd, loraLoopTime

    loraUltimoDestinoCmd = (loraUltimoDestinoCmd + 1)
    if loraUltimoDestinoCmd >= len(globals.g_devices.get_dev_rams()):
        loraUltimoDestinoCmd = 0
        loraLoopTime = funcs.millis()

def lora_pega_ultimo_destino_cmd():
    global loraUltimoDestinoCmd
    return loraUltimoDestinoCmd

