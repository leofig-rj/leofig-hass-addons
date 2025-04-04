import time
import logging
import funcs

# Definições de índices e constantes
INDEX_ELET = 0
INDEX_LUZ = 1
NUM_DESTINOS_CMD_LORA = 2
NUM_SLAVES = 2
LORA_FIFO_LEN = 10
LORA_TEMPO_REFRESH = 5000
LORA_NUM_TENTATIVAS_CMD = 3

# Endereços dos slaves LoRa
SLAVE_ELET_ADDR = 0x02
SLAVE_LUZ_ADDR = 0x03
loraSlaveAddr = [SLAVE_ELET_ADDR, SLAVE_LUZ_ADDR]

# Variáveis globais
online = False
sentDiscovery = False

lastMqttReconnect = 0
lastTeleMillis = 0

lastTensao = -1
lastPotencia = -1
lastCorrente = -1
lastEnergia = -1
lastEnergiaRam = -1
lastLoraCom = [False] * NUM_SLAVES
lastLampada1 = "NULL"
lastInput1 = "NULL"

loraCommandTime = 0
loraTimeOut = [0] * NUM_SLAVES
loraCom = [False] * NUM_SLAVES
loraRSSI = [0] * NUM_SLAVES
lastMsgSent = ""
lastIdRec = 0
lastIdSent = 0
tentativasCmd = 0
iTensao = 0
iPotencia = 0
iCorrente = 0
iEnergia = 0
iEnergiaRam = 0
sLampada1 = "NULL"
sInput1 = "NULL"

loraFiFoPrimeiro = 0
loraFiFoUltimo = 0
loraFiFoMsgBuffer = [""] * LORA_FIFO_LEN
loraFiFoDestinoBuffer = [0] * LORA_FIFO_LEN
loraUltimoDestinoCmd = 0

loraTimeOut = [0] * NUM_DESTINOS_CMD_LORA
loraCom = [False] * NUM_DESTINOS_CMD_LORA

def trata_mensagem(sMsg, index):
    global loraFiFoPrimeiro, loraFiFoUltimo
    logging.debug(f"Tamanho da MSG: {len(sMsg)} Índice {index}")
    
    if loraFiFoPrimeiro != loraFiFoUltimo:
        logging.info("FiFo não está vazia!")
        return
    
    if index == INDEX_ELET:
        trata_mensagem_gara(sMsg)
        return
    
    if index == INDEX_LUZ:
        trata_mensagem_fut(sMsg)
        return

def trata_mensagem_gara(sMsg):
    global iTensao, iPotencia, iCorrente, iEnergia, iEnergiaRam, loraUltimoDestinoCmd, loraTimeOut, loraCom
    
    if len(sMsg) != 33:
        logging.info(f"Erro no tamanho da mensagem! {len(sMsg)}")
        return
    
    partes = sMsg.split('#')
    if len(partes) != 6:
        logging.info("Erro ao dividir a mensagem!")
        return
    
    if len(partes[1]) != 4 or len(partes[2]) != 6 or len(partes[3]) != 6 or len(partes[4]) != 6 or len(partes[5]) != 6:
        logging.info("Erro no tamanho dos dados!")
        logging.info(f"P1 {partes[1]} P2 {partes[2]} P3 {partes[3]} P4 {partes[4]} P5 {partes[5]} ")
        return
    
    iTensao = int(partes[1])
    iPotencia = int(partes[2])
    iCorrente = int(partes[3])
    iEnergia = int(partes[4])
    iEnergiaRam = int(partes[5])

    logging.debug(f"Tensão: {iTensao} Potência: {iPotencia} Corrente: {iCorrente} Energia: {iEnergia} EnergiaRam: {iEnergiaRam}")
    
    loraTimeOut[INDEX_ELET] = funcs.millis()
    loraCom[INDEX_ELET] = True
    if loraUltimoDestinoCmd == INDEX_ELET:
        lora_proximo_destino_cmd()

def trata_mensagem_fut(sMsg):
    global loraUltimoDestinoCmd, sLampada1, sInput1, loraTimeOut, loraCom
    
    if len(sMsg) != 4:
        logging.info("Erro no tamanho da mensagem!")
        return
    
    partes = sMsg.split('#')
    if len(partes) != 3:
        logging.info("Erro ao dividir a mensagem!")
        return
    
    if len(partes[1]) != 1 or len(partes[2]) != 1:
        logging.info("Erro no tamanho dos dados!")
        return
    
    sLampada1 = funcs.char_to_state(partes[1])
    sInput1 = funcs.char_to_on_off(partes[2])
    
    logging.debug(f"Lâmpada1: {sLampada1} Input1: {sInput1}")
    
    loraTimeOut[INDEX_LUZ] = funcs.millis()
    loraCom[INDEX_LUZ] = True
    if loraUltimoDestinoCmd == INDEX_LUZ:
        lora_proximo_destino_cmd()

def get_index_from_addr(addr):
    return loraSlaveAddr.index(addr) if addr in loraSlaveAddr else 255

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
    lora_envia_mensagem(sMsg, loraSlaveAddr[index])


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
            lora_envia_mensagem_index(loraFiFoMsgBuffer[loraFiFoPrimeiro], loraFiFoDestinoBuffer[loraFiFoPrimeiro])
            loraFiFoPrimeiro = (loraFiFoPrimeiro + 1) % LORA_FIFO_LEN

def lora_proximo_destino_cmd():
    global loraUltimoDestinoCmd
    loraUltimoDestinoCmd = (loraUltimoDestinoCmd + 1) % NUM_DESTINOS_CMD_LORA

#def lora_proximo_destino_cmd():
#    global loraUltimoDestinoCmd
#    loraUltimoDestinoCmd += 1
#    if loraUltimoDestinoCmd >= NUM_DESTINOS_CMD_LORA:
#        loraUltimoDestinoCmd = 0

