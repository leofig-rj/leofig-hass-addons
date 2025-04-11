import time
import logging

import funcs
import globals

# Constantes para LFLoRa
from consts import  MODO_OP_CFG, MODO_OP_LOOP, FASE_NEG_INIC, MSG_CHECK_OK

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
mqttLastNomeDisp = ""


def loop_serial():
    global lastIdRec, loraLoopTime
    # Verifico se tem dado na serial
    if globals.g_serial.in_waiting > 0:
        # Pegando o dado e deixando como string
        serial_data = globals.g_serial.readline().decode('utf-8').strip()
        if globals.g_lf_lora.modo_op() == MODO_OP_LOOP:
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

        if globals.g_lf_lora.modo_op() == MODO_OP_CFG:
            if globals.g_lf_lora.on_lora_message(serial_data):
                loraLoopTime = funcs.millis()
                lora_envia_msg_cfg()

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
        device_name = top[device_pos + 1:entity_pos]
        logging.debug(f"Dispositivo {device_name}")

        if device_name == 'bridge':
            # Trata comando de Bridge
            mqtt_bridge_proc_command(entity, pay)
        else:
            # Procura nos dispositivo
            index = globals.g_devices.find_device_ram_by_name(device_name)
            if index is not None:
                ram_dev = globals.g_devices.get_dev_rams()[index]
                ram_dev.slaveObj.proc_command(entity, pay, index)
            else:
                logging.debug(f"Não encontrado dispositivo {device_name}")
    else:
        logging.error(f"A msg recebida de MQTT não foi tratada: | {top} para {pay}")

def mqtt_bridge_proc_command(entity, pay):
    """Processa comando para Bridge recebidas do MQTT)."""
    global mqttLastBridgeSelect, mqttLastNomeDisp
    ram_devs = globals.g_devices.get_dev_rams()
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
        mqttLastNomeDisp = pay
        logging.debug(f"Processando comando para dispositivos de Bridge {entity}: {pay}")
        client.pub(f"{client.bridge_topic}/nome_disp", 0, True, pay)
        return

    if entity == "excluir_disp":
        logging.debug(f"Processando comando para excluir_disp de Bridge {entity}: {pay}")
        for i in range(len(ram_devs)):
            if ram_devs[i].slaveName == mqttLastBridgeSelect:
                # Vou tentar excluir o dispositivo indice i
                client.send_delete_discovery_x(i, "binary_sensor", "Com LoRa")
                client.send_delete_discovery_x(i, "sensor", "RSSI")
                obj = ram_devs[i].slaveObj
                for j in range(len(obj.entityNames)):
                    logging.info(f"Dev Excluido {ram_devs[i].slaveName} Entidade {j} Domínio {obj.entityDomains[j]} Nome {obj.entityNames[j]}")
                    client.send_delete_discovery_x(i, obj.entityDomains[j], obj.entityNames[j])
                # Excluo da lista de slaves
                ram_devs.remove(ram_devs[i])
                # Refresco dispositivos da bridge
                mqtt_bridge_refresh()

    if entity == "renomear_disp":
        logging.debug(f"Processando comando para renomear_disp de Bridge {entity}: {pay}")
        for i in range(len(ram_devs)):
            if ram_devs[i].slaveName == mqttLastBridgeSelect:
                # Vou tentar renomear o dispositivo indice i
                ram_devs[i].slaveName = mqttLastNomeDisp
                ram_devs[i].slaveSlug = funcs.slugify(ram_devs[i].slaveName)
                # Refresco dispositivos da bridge
                mqtt_bridge_refresh()

    if entity == "modo_config":
        logging.info(f"Processando comando para modo_config de Bridge {entity}: {pay}")
        if (pay.find("ON")!=-1):
            # ON
            globals.g_lf_lora.set_modo_op(MODO_OP_CFG)
        else:
            # OFF
            globals.g_lf_lora.set_modo_op(MODO_OP_LOOP)
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
    client.send_bridge_button_discovery("Renomear Disp", EC_NONE, DEVICE_CLASS_UPDATE)
    client.send_bridge_button_discovery("Excluir Disp", EC_NONE, DEVICE_CLASS_UPDATE)
    client.send_bridge_switch_discovery("Modo Config", EC_NONE)
    status = "OFF"
    if globals.g_lf_lora.modo_op() == MODO_OP_CFG:
        status = "ON"
    client.pub(f"{client.bridge_topic}/modo_config", 0, True, status)
    mqtt_send_bridge_select_discovery()

def mqtt_send_bridge_select_discovery():
    global mqttLastBridgeSelect, mqttLastNomeDisp
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
        # Inicializo Dispositivos
        client.pub(f"{client.bridge_topic}/dispositivos", 0, True, ram_devs[0].slaveName)
        mqttLastBridgeSelect = ram_devs[0].slaveName
        # Inicializo Nome Disp
        client.pub(f"{client.bridge_topic}/nome_disp", 0, True, ram_devs[0].slaveName)
        mqttLastNomeDisp = ram_devs[0].slaveName


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

    if globals.g_lf_lora.modo_op() == MODO_OP_LOOP:
        
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

    if globals.g_lf_lora.modo_op() == MODO_OP_CFG:

        # Vejo se o tempo de loop já passou
        tempoLoop = funcs.pega_delta_millis(loraLoopTime)
        if tempoLoop > LORA_TEMPO_LOOP:
            loraLoopTime = funcs.millis()
            globals.g_lf_lora.set_fase_negocia(FASE_NEG_INIC)

        # Solicito estado periodicamente...
        tempoCmd = funcs.pega_delta_millis(loraCommandTime)
        if tempoCmd > LORA_TEMPO_CMD * 2:
            if globals.g_lf_lora.fase_negocia() == FASE_NEG_INIC:
                lora_envia_msg_cfg()
        
        
def on_lora_message(sMsg, index):
#    global loraFiFoPrimeiro, loraFiFoUltimo
    logging.debug(f"LoRa - Tamanho da MSG: {len(sMsg)} Índice {index}")
    
#    if loraFiFoPrimeiro != loraFiFoUltimo:
#        logging.info("FiFo não está vazia!")
#        return
    try:
        # Pego o Dispositivo na RAM
        ram_dev = globals.g_devices.get_dev_rams()[index]

        # Executa a rotina no dispositivo Moodelo
        ram_dev.slaveObj.proc_rec_msg(sMsg, index)

        # Atualizo variáveis de contexto do dispositivo na RAM
        ram_dev.loraTimeOut = funcs.millis()
        ram_dev.loraCom = True
        if lora_pega_ultimo_destino_cmd() == index:
            lora_proximo_destino_cmd()
    except Exception as e:
        logging.error(f"Erro: {e}")

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

def lora_envia_msg_cfg():
    global loraCommandTime
    
    loraCommandTime = funcs.millis()

    # Envio comando de configuração
    serial_data = globals.g_lf_lora.negocia_msg()
    globals.g_serial.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
    logging.info(f"CFG - Enviando: {serial_data}")

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

def disp_get_ram_addr_by_mac(mac):
    # Redireciono para a função em globals.g_devices
    return globals.g_devices.get_ram_addr_by_mac(mac)

def disp_save_slave(addr, model, mac):
    # Salvo o slave em ram_devs
    globals.g_devices.save_slave(addr, model, mac)
    # Refresco dispositivos da bridge
    mqtt_bridge_refresh()
