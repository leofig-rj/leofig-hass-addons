import time
import logging
import json

import funcs
import globals

#from .devices import pw01

# Constantes para LFLoRa
from consts import  MSG_CHECK_OK

# Para LoRa
from consts import LORA_FIFO_LEN, LORA_TEMPO_REFRESH, LORA_NUM_TENTATIVAS_CMD, LFLORA_MAX_PACKET_SIZE, LORA_TEMPO_OUT

# Para MQTT
from consts import  REFRESH_TELEMETRY, EC_DIAGNOSTIC, DEVICE_CLASS_RESTART

# Variáveis globais
online = False

loraCommandTime = 0
lastMsgSent = ""
lastIdRec = 0
lastIdSent = 0
tentativasCmd = 0
lastTeleMillis = 0


loraFiFoPrimeiro = 0
loraFiFoUltimo = 0
loraFiFoMsgBuffer = [""] * LORA_FIFO_LEN
loraFiFoDestinoBuffer = [0] * LORA_FIFO_LEN
loraUltimoDestinoCmd = 0

def loop_serial():
    # Verifico se tem dado na serial
    if globals.g_serial.in_waiting > 0:
        # Pegando o dado e deixando como string
        serial_data = globals.g_serial.readline().decode('utf-8').strip()
        # Tratando o dado
        result, de, para, msg = globals.g_lf_lora.lora_check_msg_ini(serial_data)
        logging.debug(f"Recebido result: {result} de: {de} para: {para} msg: {msg}")
        # Trato a mensagem
        if result == MSG_CHECK_OK:
            # Tratando a msg conforme remetente
            index = funcs.get_index_from_addr(de)
            logging.debug(f"Ïndice do dispositivo: {index}")
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
        mqtt_send_telemetry()
        mqtt_send_com_lora()

    # Outra pausa
    time.sleep(0.01)

    if online:
        mqtt_send_entities()

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

#    logging.debug("Loop LoRa - 2")
    # Verifico se tem comando no FiFo para enviar...
    lora_fifo_verifica()

#    logging.debug("Loop LoRa - 3")
    # Solicito estado periodicamente...
    tempoLoop = funcs.pega_delta_millis(loraCommandTime)
    if tempoLoop > LORA_TEMPO_REFRESH:
        logging.debug("Loop LoRa - 4")
        lora_fifo_tenta_enviar("000", loraUltimoDestinoCmd)
        logging.debug("Loop LoRa - 5")
        # Defino o próximo destino para solicitar estado...
        lora_proximo_destino_cmd()
        logging.debug("Loop LoRa - 6")

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

def mqtt_send_telemetry():
    global lastTeleMillis

    tempo_loop = funcs.pega_delta_millis(lastTeleMillis)

    if tempo_loop < REFRESH_TELEMETRY:
        return

    lastTeleMillis = funcs.millis()

    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    for i in range(len(ram_devs)):
        doc = {}  # Inicializa o dicionário (equivalente ao `JsonDocument`)
        doc["rssi"] = str(ram_devs[i].loraRSSI)
        buffer = json.dumps(doc)  # Serializa o JSON em uma string
        logging.debug(f"Telemetry {i} {buffer}")
        globals.g_cli_mqtt.pub(globals.g_cli_mqtt.tele_topics[i], 0, False, buffer)

def mqtt_send_entities():
    # Pego oo Dispositivos na RAM
    ram_devs = globals.g_devices.get_dev_rams()

    for i in range(len(ram_devs)):
        if ram_devs[i].loraCom:
            # Publica entidades do dispositivo (modelo)
            ram_devs[i].slaveObj.proc_publish(i)

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
            bridge_proc_command(entity, pay)
        else:
            # Procura nos dispositivo
            index = globals.g_devices.find_device_by_name(device)
            if index:
                ram_dev = globals.g_devices.get_dev_rams()[index]
                ram_dev.slaveObj.proc_command(entity, pay, index)
            else:
                logging.debug(f"Não encontrado dispositivo {device}")
    else:
        logging.error(f"A msg recebida de MQTT não foi tratada: | {top} para {pay}")

def on_lora_message(sMsg, index):
    global loraFiFoPrimeiro, loraFiFoUltimo
    logging.debug(f"Tamanho da MSG: {len(sMsg)} Índice {index}")
    
    if loraFiFoPrimeiro != loraFiFoUltimo:
        logging.info("FiFo não está vazia!")
        return
    
    # Pego o Dispositivo na RAM
    ram_dev = globals.g_devices.get_dev_rams()[index]

    # Executa a rotina no dispositivo (modelo)
    ram_dev.slaveObj.proc_rec_msg(sMsg)

    # Atualizo variáveis de contexto
    ram_dev.loraTimeOut = funcs.millis()
    ram_dev.loraCom = True
    if lora_pega_ultimo_destino_cmd() == index:
        lora_proximo_destino_cmd()

    return

def bridge_proc_command(entity, pay):
    """Processa comando para Bridge recebidas do MQTT)."""
    logging.debug(f"Processando comando para Bridge {entity}: {pay}")


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

    lastIdSent = globals.g_lf_lora.last_sent_id();
    lastMsgSent = sMsg

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

