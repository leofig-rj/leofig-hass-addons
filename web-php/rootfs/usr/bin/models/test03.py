# Em self.model é definido o nome do dispositivo
# O nome do arquivo dever ser o nome do dispositivo em minúsculas .py
# O nome da classe deve ter o padrão "Device" + o nome do dispositivo,
# em maiúsculas
# A classe tem que ter as variáveis : self.model, self.chip, self.ver, self.man, 
# self.desc, self.entityNames e self.entitySlugs
# E as funções: proc_rec_msg, proc_command, proc_publish e proc_discovery

import logging

from funcs import slugify, char_to_on_off, pay2Light, light2Pay
from msgs import lora_send_msg_usr, mqtt_pub, mqtt_send_light_discovery, \
                    mqtt_send_binary_sensor_discovery

from consts import EC_NONE

class DeviceTEST03:
    def __init__(self):
        self.model = "TEST03"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Teste de LF_LoRa 03"
        self.entityNames = ["Lampada", "Entrada Discreta"]
        self.entityDomains = ["light", "binary_sensor"]
        self.entitySlugs = []
        self.lampadaState = None
        self.lampadaLastState = None
        self.lampadaBrig = None
        self.lampadaLastBrig = None
        self.lampadaRed = None
        self.lampadaLastRed = None
        self.lampadaGreen = None
        self.lampadaLastGreen = None
        self.lampadaBlue = None
        self.lampadaLastBlue = None
        self.entradaState = None
        self.entradaLastState = None

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

    def proc_rec_msg(self, sMsg, index):

        # Mensagem recebida do dispositivo
        # A mgs tem o padrão "#l#BBB#rrr#ggg#bbb#e"
        # Onde l = estado da lâmpada, BBB = brilho, rrr = vermelho, ggg = verde,
        # bbb = azul, e = estado da entrada
        if len(sMsg) != 20:
            logging.error(f"TEST03 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
        if len(partes) != 7:
            logging.error("TEST03 - Erro ao dividir a mensagem!")
            return
        
        if len(partes[1]) != 1 or len(partes[2]) != 3 or len(partes[3]) != 3 or \
            len(partes[4]) != 3 or len(partes[5]) != 3 or len(partes[6]) != 1:
            logging.error("TEST03 - Erro no tamanho dos dados!")
            return
        
        # Presevando os dados tratados da Msg
        # Estado da lâmpada no formato "ON" / "OFF"
        self.lampadaState = char_to_on_off(partes[1])
        # Estado do brilho é inteiro
        self.lampadaBrig = int(partes[2])
        # Estado do vermelho é inteiro
        self.lampadaRed = int(partes[3])
        # Estado do verde é inteiro
        self.lampadaGreen = int(partes[4])
        # Estado do azul é inteiro
        self.lampadaBlue = int(partes[5])
        # Estado da entrada no formato "ON" / "OFF"
        self.entradaState = char_to_on_off(partes[6])
        
        logging.debug(f"TEST03 - Lâmpada: {self.lampadaState}-{self.lampadaBrig}-" \
            f"{self.lampadaRed}-{self.lampadaGreen}-{self.lampadaBlue}" \
            f" Entrada Discreta: {self.entradaState}")
            
    def proc_command(self, entity, pay, index):

        # Comando recebidos do MQTT
        # Só tem comando de "Lampada", índice 0
        if entity == self.entitySlugs[0]:
            # Pegando o estado e o brilho da lâmpada
            state, brightness, r, g, b = pay2Light(pay)
            logging.debug(f"TEST03 - state: {state} brightness: {brightness} red: {r} green: {g} blue: {b}")
            if state == "ON":
                # ON -> Cmd 101
                dispCmd = "101"
                # se tiver brilho no comando do MQTT, acrescenta
                if brightness is not None:
                    dispCmd = dispCmd + f"{brightness:03}"
                # se tiver cor no comando do MQTT, acrescenta
                else:
                    if (r is not None) and (g is not None) and (b is not None):
                        dispCmd = dispCmd + f"{r:03}{g:03}{b:03}"
                # Enviando comando para dispositivo
                lora_send_msg_usr(dispCmd, index)
            else:
                # OFF -> Cmd 102
                # Enviando comando para dispositivo
                lora_send_msg_usr("102", index)

            #  Atualizando para evitar ficar mudando enquanto espera feedback
            self.lampadaState = state
            self.lampadaBrig = brightness

            return True
        return False

    def proc_publish(self, index, force):

        # Publicando estados no MQTT
        # Só publica se houve alteração no valor ou se for forçado
        if (self.lampadaLastState != self.lampadaState) or \
            (self.lampadaLastBrig != self.lampadaBrig ) or \
            (self.lampadaLastRed != self.lampadaRed ) or \
            (self.lampadaLastGreen != self.lampadaGreen ) or \
            (self.lampadaLastBlue != self.lampadaBlue ) or force:
            self.lampadaLastState = self.lampadaState
            self.lampadaLastBrig = self.lampadaBrig
            self.lampadaLastRed = self.lampadaRed
            self.lampadaLastGreen = self.lampadaGreen
            self.lampadaLastBlue = self.lampadaBlue
            # Criando a string no formato json
            val = None
            if self.lampadaState == "ON":
                # Quando ligado o estado e o brilho e a cor são publicados
                val = light2Pay(self.lampadaState, self.lampadaBrig, \
                        self.lampadaRed, self.lampadaGreen, self.lampadaBlue)
            else:
                # Quando desligado somente o estado é publicado
                val = light2Pay(self.lampadaState)
            # Publicando o estado completo da lâmpada no MQTT (formato string json)
            mqtt_pub(index, self.entitySlugs[0], val)
            logging.debug(f"TEST03 - entityVal {0} {self.entitySlugs[0]} {val}")

        # Só publica se houve alteração no valor ou se for forçado
        if (self.entradaLastState != self.entradaState) or force:
            self.entradaLastState = self.entradaState
            # Publicando o estado da entrada no MQTT, já está no formato "ON" / "OFF"
            mqtt_pub(index, self.entitySlugs[1], self.entradaState)
            logging.debug(f"TEST03 - entityVal {1} {self.entitySlugs[1]} {self.entradaState}")

    def proc_discovery(self, index):

        # Publicando descobrimento das entidades no MQTT
        if mqtt_send_light_discovery(index, self.entityNames[0], EC_NONE, True, True) and \
            mqtt_send_binary_sensor_discovery(index, self.entityNames[1], EC_NONE, EC_NONE):
            logging.debug(f"Discovery Device TEST03 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Device TEST03 NOT OK")
            return False
