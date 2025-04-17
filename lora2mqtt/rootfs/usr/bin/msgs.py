import time
import logging

import funcs
import globals

# Constantes para LFLoRa
from consts import  MODE_OP_CFG, MODE_OP_LOOP, STEP_NEG_INIC, MSG_CHECK_OK

# Para LoRa
from consts import LORA_FIFO_LEN, LORA_NUM_ATTEMPTS_CMD, LORA_TIME_CMD, LORA_TIME_OUT, LORA_TEMPO_LOOP

# Para MQTT
from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_NONE, DEVICE_CLASS_SIGNAL_STRENGTH, DEVICE_CLASS_UPDATE, \
                    UNITS_NONE, STATE_CLASS_NONE

# Variáveis globais
online = False

loraCommandTime = 0
loraLoopTime = 0
lastMsgSent = ""
lastIdRec = 0
lastIdSent = 0
attemptsCmd = 0

loraFiFoFirst = 0
loraFiFoLast = 0
loraFiFoMsgBuffer = [""] * LORA_FIFO_LEN
loraFiFoTargetBuffer = [0] * LORA_FIFO_LEN
loraLastTargetCmd = 0

mqttLastBridgeSelect = ""
mqttLastNameDisp = ""


def loop_serial():
    global lastIdRec, loraLoopTime
    # Verifico se tem dado na serial
    if globals.g_serial.in_waiting > 0:
        # Pegando o dado e deixando como string
        serial_data = globals.g_serial.readline().decode('utf-8').strip()
        if globals.g_lf_lora.modo_op() == MODE_OP_LOOP:
            # Tratando o dado
            result, de, para, id, rssi, msg = globals.g_lf_lora.lora_check_msg_ini(serial_data)
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
                on_lora_message(msg, rssi, index)

        if globals.g_lf_lora.modo_op() == MODE_OP_CFG:
            if globals.g_lf_lora.on_lora_message(serial_data):
                loraLoopTime = funcs.millis()
                lora_send_msg_cfg()

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
        mqtt_send_com_lora(False)

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
        device_name = top[device_pos + 1:entity_pos]
        logging.debug(f"Dispositivo {device_name}")

        if device_name == 'bridge':
            # Trata comando de Bridge
            mqtt_bridge_proc_command(entity, pay)
        else:
            # Procura nos dispositivo
            index = globals.g_devices.find_ram_dev_by_name(device_name)
            if index is not None:
                ram_dev = globals.g_devices.get_ram_devs()[index]
                ram_dev.slaveObj.proc_command(entity, pay, index)
            else:
                logging.debug(f"Não encontrado dispositivo {device_name}")
    else:
        logging.error(f"A msg recebida de MQTT não foi tratada: | {top} para {pay}")

def mqtt_bridge_proc_command(entity, pay):
    """Processa comando para Bridge recebidas do MQTT)."""
    global mqttLastBridgeSelect, mqttLastNameDisp
    ram_devs = globals.g_devices.get_ram_devs()
    client = globals.g_cli_mqtt
    if entity == "dispositivos":
        mqttLastBridgeSelect = pay
        logging.debug(f"Processando comando para dispositivos de Bridge {entity}: {pay}")
        # Select = pay
        client.pub(f"{client.bridge_topic}/dispositivos", 0, True, pay)
        # Nome Disp = pay
        client.pub(f"{client.bridge_topic}/nome_disp", 0, True, pay)
        return

    if entity == "nome_disp":
        mqttLastNameDisp = pay
        logging.debug(f"Processando comando para dispositivos de Bridge {entity}: {pay}")
        client.pub(f"{client.bridge_topic}/nome_disp", 0, True, pay)
        return

    if entity == "excluir_disp":
        logging.debug(f"Processando comando para excluir_disp de Bridge {entity}: {pay}")
        for i in range(len(ram_devs)):
            if ram_devs[i].slaveName == mqttLastBridgeSelect:
                toDel = mqttLastBridgeSelect
                # Excluindo o dispositivo indice i
                client.send_delete_discovery_x(i, "binary_sensor", "Com LoRa")
                client.send_delete_discovery_x(i, "sensor", "RSSI")
                obj = ram_devs[i].slaveObj
                for j in range(len(obj.entityNames)):
                    logging.info(f"Dev Deleted {ram_devs[i].slaveName} Entity {j} Domain{obj.entityDomains[j]} Name {obj.entityNames[j]}")
                    client.send_delete_discovery_x(i, obj.entityDomains[j], obj.entityNames[j])
                # Excluindo da lista de slaves na RAM e no arquivo config.yaml
                globals.g_devices.delete_ram_dev(i)
                # Refrescando dispositivos da bridge
                mqtt_bridge_refresh()
                mqtt_send_bridge_info(f"Deleted: {toDel}")

    if entity == "renomear_disp":
        logging.debug(f"Processando comando para renomear_disp de Bridge {entity}: {pay}")
        for i in range(len(ram_devs)):
            if ram_devs[i].slaveName == mqttLastBridgeSelect:
                fromRen = mqttLastBridgeSelect
                toRen = mqttLastNameDisp
                # Excluindo o discovery do dispositivo indice i
                client.send_delete_discovery_x(i, "binary_sensor", "Com LoRa")
                client.send_delete_discovery_x(i, "sensor", "RSSI")
                obj = ram_devs[i].slaveObj
                for j in range(len(obj.entityNames)):
                    client.send_delete_discovery_x(i, obj.entityDomains[j], obj.entityNames[j])
                # Renomeaando o dispositivo indice i
                globals.g_devices.rename_ram_dev(i, mqttLastNameDisp)
                # Refrescando dispositivos da bridge
                mqtt_bridge_refresh()
                # Enviando os estados das entidades forçados
                for i in range(len(ram_devs)):
                    # Publicando Com LoRa
                    mqtt_send_com_lora(True)
                    # Publicando RSSI do dispositivo
                    mqtt_pub(i, "rssi", str(ram_devs[i].loraRSSI))
                    # Publicando entidades do dispositivo (modelo)
                    ram_devs[i].slaveObj.proc_publish(i, True)
                mqtt_send_bridge_info(f"Renamed: {fromRen} to {toRen}")


    if entity == "modo_config":
        logging.info(f"Changing Operation Mode to: {pay}")
        mqtt_send_bridge_info(f"Config Mode: {pay}")
        if (pay.find("ON")!=-1):
            # ON
            globals.g_lf_lora.set_modo_op(MODE_OP_CFG)
        else:
            # OFF
            globals.g_lf_lora.set_modo_op(MODE_OP_LOOP)
        client.pub(f"{client.bridge_topic}/modo_config", 0, True, pay)

def mqtt_bridge_refresh():
    """Refresco o dicovery de select."""
    client = globals.g_cli_mqtt
    # Refresco os tópicos
    client.setup_mqtt_topics()
    # Assino os tópicos 
    client.on_mqtt_connect()
    # Refresco o select de dispositivos
    mqtt_send_bridge_select_discovery()
    # Refresco o discovery de entidades (dispositivos)
    mqtt_send_discovery_entities()


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
    client.send_bridge_text_discovery("Nome Disp", EC_NONE)
    client.send_bridge_button_discovery("Renomear Disp", EC_NONE, DEVICE_CLASS_NONE, "mdi:rename")
    client.send_bridge_button_discovery("Excluir Disp", EC_NONE, DEVICE_CLASS_NONE, "mdi:delete-forever-outline")
    client.send_bridge_switch_discovery("Modo Config", EC_NONE, "mdi:connection")
    status = "OFF"
    if globals.g_lf_lora.modo_op() == MODE_OP_CFG:
        status = "ON"
    client.pub(f"{client.bridge_topic}/modo_config", 0, True, status)
    client.send_bridge_sensor_discovery("Info", EC_NONE, DEVICE_CLASS_NONE, UNITS_NONE, STATE_CLASS_NONE, "mdi:information-slab-box-outline")
    mqtt_send_bridge_info("Idle")
    mqtt_send_bridge_select_discovery()

def mqtt_send_bridge_select_discovery():
    global mqttLastBridgeSelect, mqttLastNameDisp
    # Inicializo o último da memória
    mqttLastBridgeSelect = ""
    # Pego os Dispositivos na RAM
    ram_devs = globals.g_devices.get_ram_devs()
    # Crio lista com nomes dos dispositivos
    devs = []
    for i in range(len(ram_devs)):
        devs.append(ram_devs[i].slaveName)
    client = globals.g_cli_mqtt
    client.send_bridge_select_discovery("Dispositivos", EC_NONE, devs)
    if len(ram_devs) > 0:
        # Inicializo Dispositivos
        client.pub(f"{client.bridge_topic}/dispositivos", 0, True, ram_devs[0].slaveName)
        mqttLastBridgeSelect = ram_devs[0].slaveName
        # Inicializo Nome Disp
        client.pub(f"{client.bridge_topic}/nome_disp", 0, True, ram_devs[0].slaveName)
        mqttLastNameDisp = ram_devs[0].slaveName

def mqtt_send_bridge_info(info):
    client = globals.g_cli_mqtt
    client.pub(f"{client.bridge_topic}/info", 0, True, info)

def mqtt_send_discovery_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_ram_devs()

    if len(ram_devs) == 0:
        return

    for i in range(len(ram_devs)):
        # Publica discovery do Com LoRa e RSSI do dispositivo
        mqtt_send_aux_connectivity_discovery(i)
        mqtt_send_sensor_discovery(i, "RSSI", EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH, "", "", True)
        # Publica discovery das entidades do dispositivo (modelo)
        ram_devs[i].slaveObj.proc_discovery(i)
        logging.debug(f"Discovery Entity {i}")

def mqtt_send_com_lora(force):
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_ram_devs()

    for i in range(len(ram_devs)):
        if (ram_devs[i].loraLastCom != ram_devs[i].loraCom) or force:
            ram_devs[i].loraLastCom = ram_devs[i].loraCom

            s_com_lora = "online" if ram_devs[i].loraCom else "offline"
            logging.debug(f"Com LoRa {i} {s_com_lora}")

            globals.g_cli_mqtt.pub(f"{globals.g_cli_mqtt.work_topics[i]}/com_lora", 0, True, s_com_lora)

def mqtt_send_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_ram_devs()

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
            ram_devs[i].slaveObj.proc_publish(i, False)

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

def mqtt_send_light_discovery(index, name, entity_category, brightness, rgb):
    client = globals.g_cli_mqtt
    return client.send_light_discovery(index, name, entity_category, brightness, rgb)

def mqtt_send_light_switch_discovery(index, name, entity_category):
    client = globals.g_cli_mqtt
    return client.send_light_switch_discovery(index, name, entity_category)

def loop_lora():
    global loraCommandTime, loraLoopTime, loraLastTargetCmd

    if globals.g_lf_lora.modo_op() == MODE_OP_LOOP:
        
        ram_devs = globals.g_devices.get_ram_devs()

        if len(ram_devs) == 0:
            return

        # Verifico Time out dos dispositivos para informar desconexão
        for i in range(len(ram_devs)):
            timeOut = funcs.get_delta_millis(ram_devs[i].loraTimeOut)
            if timeOut > LORA_TIME_OUT:
                ram_devs[i].loraTimeOut = funcs.millis()
                ram_devs[i].loraCom = False
        
        # Verifico se a última mensagem retornou...
        if not lora_last_cmd_returned():
            return

        # Verifico se tem comando no FiFo para enviar...
        lora_fifo_check()

        # Vejo se o tempo de loop já passou
        timeLoop = funcs.get_delta_millis(loraLoopTime)
        if timeLoop <= LORA_TEMPO_LOOP:
            return

        # Solicito estado periodicamente...
        timeCmd = funcs.get_delta_millis(loraCommandTime)
        if timeCmd > LORA_TIME_CMD:
            lora_fifo_try_to_send("000", loraLastTargetCmd)
            # Defino o próximo destino para solicitar estado...
            lora_next_target_cmd()

    if globals.g_lf_lora.modo_op() == MODE_OP_CFG:

        # Vejo se o tempo de loop já passou
        timeLoop = funcs.get_delta_millis(loraLoopTime)
        if timeLoop > LORA_TEMPO_LOOP:
            loraLoopTime = funcs.millis()
            globals.g_lf_lora.set_fase_negocia(STEP_NEG_INIC)

        # Solicito estado periodicamente...
        timeCmd = funcs.get_delta_millis(loraCommandTime)
        if timeCmd > LORA_TIME_CMD * 2:
            if globals.g_lf_lora.fase_negocia() == STEP_NEG_INIC:
                lora_send_msg_cfg()
        
        
def on_lora_message(sMsg, rssi, index):
#    global loraFiFoFirst, loraFiFoLast
    logging.debug(f"LoRa - Tamanho da MSG: {len(sMsg)} Índice {index}")
    
    try:
        # Pego o Dispositivo na RAM
        ram_dev = globals.g_devices.get_ram_devs()[index]

        # Executa a rotina no dispositivo Moodelo
        ram_dev.slaveObj.proc_rec_msg(sMsg, index)

        # Atualizo variáveis de contexto do dispositivo na RAM
        ram_dev.loraRSSI = rssi
        ram_dev.loraTimeOut = funcs.millis()
        ram_dev.loraCom = True
        if lora_get_last_target_cmd() == index:
            lora_next_target_cmd()
    except Exception as e:
        logging.error(f"Erro: {e}")

def lora_fifo_try_to_send(sMsg, index):
    global loraFiFoFirst, loraFiFoLast, loraFiFoMsgBuffer, loraFiFoTargetBuffer
    
    if loraFiFoFirst == loraFiFoLast:
        if lora_last_cmd_returned():
            lora_send_msg_index(sMsg, index)
            return
    
    aux = (loraFiFoLast + 1) % LORA_FIFO_LEN
    if aux == loraFiFoFirst:
        return
    
    loraFiFoMsgBuffer[loraFiFoLast] = sMsg
    loraFiFoTargetBuffer[loraFiFoLast] = index
    loraFiFoLast = aux

def lora_send_msg_index(sMsg, index):
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_ram_devs()

    lora_send_msg(sMsg, ram_devs[index].slaveAddr)


def lora_send_msg(sMsg, para):
    global loraCommandTime, attemptsCmd, lastIdSent, lastMsgSent
    
    loraCommandTime = funcs.millis()
    attemptsCmd = 0
    
    # Envio comando de solicitação de estado
    serial_data = globals.g_lf_lora.lora_add_header(sMsg, para)
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.debug(f"Enviado {serial_data}")

    lastIdSent = globals.g_lf_lora.last_sent_id()
    lastMsgSent = serial_data

def lora_resend_msg():
    global loraCommandTime, attemptsCmd
    
    loraCommandTime = funcs.millis()
    attemptsCmd += 1

    # Reenvio último comando
    serial_data = lastMsgSent
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.debug(f"Renviado {serial_data}")

def lora_send_msg_cfg():
    global loraCommandTime
    
    loraCommandTime = funcs.millis()

    # Envio comando de configuração
    serial_data = globals.g_lf_lora.negocia_msg()
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.debug(f"CFG - Enviando: {serial_data}")

def lora_last_cmd_returned():
    global lastIdRec, lastIdSent, loraCommandTime, attemptsCmd
    
    if lastIdRec == lastIdSent:
        return True
    
    if funcs.get_delta_millis(loraCommandTime) > LORA_TIME_CMD:
        if attemptsCmd >= LORA_NUM_ATTEMPTS_CMD:
            return True
        lora_resend_msg()
    return False

def lora_fifo_check():
    global loraFiFoFirst, loraFiFoLast, loraFiFoMsgBuffer, loraFiFoTargetBuffer
    
    if loraFiFoFirst != loraFiFoLast:
        if lora_last_cmd_returned():
            lora_send_msg_index(loraFiFoMsgBuffer[loraFiFoFirst], \
                                      loraFiFoTargetBuffer[loraFiFoFirst])
            loraFiFoFirst = (loraFiFoFirst + 1) % LORA_FIFO_LEN

def lora_next_target_cmd():
    global loraLastTargetCmd, loraLoopTime

    loraLastTargetCmd = (loraLastTargetCmd + 1)
    if loraLastTargetCmd >= len(globals.g_devices.get_ram_devs()):
        loraLastTargetCmd = 0
        loraLoopTime = funcs.millis()

def lora_get_last_target_cmd():
    global loraLastTargetCmd
    return loraLastTargetCmd

def disp_get_ram_dev_addr_by_mac(mac):
    # Redireciono para a função em globals.g_devices
    return globals.g_devices.get_ram_dev_addr_by_mac(mac)

def disp_save_ram_dev(addr, model, mac):
    # Salvo o slave em ram_devs
    globals.g_devices.save_ram_dev(addr, model, mac)
    # Refresco dispositivos da bridge
    mqtt_bridge_refresh()

def disp_check_model(model):
    if globals.g_devices.get_model(model) is not None:
        return True
    return False
