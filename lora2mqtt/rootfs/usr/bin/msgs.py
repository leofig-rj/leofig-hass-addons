import time
import logging

import funcs
import devs
import bridge

#from .devices import pw01

from consts import LORA_FIFO_LEN, LORA_TEMPO_REFRESH, LORA_NUM_TENTATIVAS_CMD, LFLORA_MAX_PACKET_SIZE

# Variáveis globais
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

def on_mqtt_message(topic, payload):

    # Converte o payload de byte para string
    payload_char = payload.decode('utf-8')[:LFLORA_MAX_PACKET_SIZE]

    top = topic
    pay = payload_char

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
            # Trata comandoa de Bridge
            bridge_proc_command(entity, pay)
        else:
            # Procura nos dispositivo
            index = devs.DeviceRAM.find_device_by_slug(device)
            if index:
                ram_dev = bridge.devices.get_dev_rams()[index]
                ram_dev.proc_command(entity, pay)
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
    
    ram_dev = bridge.devices.get_dev_rams()[index]
    ram_dev.slaveObj.proc_rec_msg(sMsg)
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
    lora_envia_mensagem(sMsg, bridge.devices.ram_devs()[index]["slaveAddr"])


def lora_envia_mensagem(sMsg, para):
    global loraCommandTime, tentativasCmd, lastIdSent, lastMsgSent
    
    loraCommandTime = int(time.time() * 1000)
    tentativasCmd = 0
    
    lora_data = f"{sMsg}:{para}"
    lastIdSent = hash(lora_data) % 256  # Simulação de ID único
    lastMsgSent = lora_data

def lora_reenvia_mensagem():
    global loraCommandTime, tentativasCmd
    
    loraCommandTime = int(time.time() * 1000)
    tentativasCmd += 1

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

    loraUltimoDestinoCmd = (loraUltimoDestinoCmd + 1) % len(bridge.devices.get_dev_rams())

def get_loraUltimoDestinoCmd():
    global loraUltimoDestinoCmd
    return loraUltimoDestinoCmd

