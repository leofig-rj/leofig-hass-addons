# Em self.model é definido o nome do dispositivo
# O nome do arquivo dever ser o nome do dispositivo em minúsculas .py
# O nome da classe deve ter o padrão "Device" + o nome do dispositivo,
# em maiúsculas
# A classe tem que ter as variáveis : self.model, self.chip, self.ver, self.man, 
# self.desc, self.entityNames e self.entitySlugs
# E as funções: proc_rec_msg, proc_command, proc_publish e proc_discovery

import logging

from funcs import slugify, char_to_on_off
from msgs import lora_send_msg_usr, mqtt_pub, mqtt_send_switch_discovery, \
                    mqtt_send_binary_sensor_discovery

from consts import EC_NONE

class DeviceKC868_A6_V01:
    def __init__(self):
        self.model = "KC868_A6_V01"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "LF_LoRa para KC868_A6 Ver 01"
        self.entityNames = ["Relay 1", "Relay 2", "Relay 3", \
                            "Relay 4", "Relay 5", "Relay 6", \
                            "Input 1", "Input 2", "Input 3", \
                            "Input 4", "Input 5", "Input 6"]
        self.entityDomains = ["switch", "switch", "switch", \
                            "switch", "switch", "switch", \
                            "binary_sensor", "binary_sensor", "binary_sensor", \
                            "binary_sensor", "binary_sensor", "binary_sensor"]
        self.entitySlugs = []
        self.relayNum = 6 
        self.relayStates = [] 
        self.relayLastStates = []
        self.relayCmdOn = ["110", "111", "112", "113", "114", "115"] 
        self.relayCmdOff = ["120", "121", "122", "123", "124", "125"] 
        self.inputNum = 6 
        self.inputStates = []
        self.inputLastStates = []
        self.inAnaNum = 4 
        self.inAnaStates = []
        self.inAnaLastStates = []
        self.outAnaNum = 2 
        self.outAnaStates = []
        self.outAnaLastStates = []
        self.outAnaCmd = ["150", "151"] 

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

        for i in range(self.relayNum):
            self.relayStates.append("")
            self.relayLastStates.append("")

        for i in range(self.inputNum):
            self.inputStates.append("")
            self.inputLastStates.append("")

    def proc_rec_msg(self, sMsg, index):

        # Mensagem recebida do dispositivo
        # A mgs tem o padrão "#rrrrr#eeeeee#iiiiiiiiiiiiiiii#oooooo"
        # Onde r = estados dos relés, e = estados das entradas,
        #      i = entradas analógicas, s = saidas analógicas
        if len(sMsg) != 38:
            logging.error(f"KC868_A6_V01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
        if len(partes) != 5:
            logging.error("KC868_A6_V01 - Erro ao dividir a mensagem!")
            return
        
        ok = True
        ok = ok and len(partes[1]) == 6
        ok = ok and len(partes[2]) == 6
        ok = ok and len(partes[3]) == 16
        ok = ok and len(partes[4]) == 6
        if not ok:
            logging.error("KC868_A6_V01 - Erro no tamanho dos dados!")
            return

#        logging.error(f"KC868_A6_V01 - AnaIn: {partes[3]}")
#        logging.error(f"KC868_A6_V01 - AnaOut: {partes[4]}")

        # Presevando os dados tratados da Msg
        for i in range(self.relayNum):
            # Estado do relé no formato "ON" / "OFF"
            logging.debug(f"KC868_A6_V01 - Relay {i+1}: {char_to_on_off(partes[1][i])}")
            self.relayStates[i] = char_to_on_off(partes[1][i])
        for i in range(self.inputNum):
            # Estado da entrada no formato "ON" / "OFF"
            logging.debug(f"KC868_A6_V01 - Input {i+1}: {char_to_on_off(partes[2][i])}")
            self.inputStates[i] = char_to_on_off(partes[2][i])
        
    def proc_command(self, entity, pay, index):

        # Comando recebidos do MQTT
        # Testo comandos de "Relé"
        for i in range(self.relayNum):
            if entity == self.entitySlugs[i]:
                # Pegando o estado
                state = pay
                logging.debug(f"KC868_A6_V01 - Realay {i+1} state: {state}")
                if state == "ON":
                    # Enviando comando para dispositivo
                    lora_send_msg_usr(self.relayCmdOn[i], index)
                else:
                    # Enviando comando para dispositivo
                    lora_send_msg_usr(self.relayCmdOff[i], index)
                #  Atualizando para evitar ficar mudando enquanto espera feedback
                self.relayStates[i] = state
                return True
        return False

    def proc_publish(self, index, force):

        # Publicando estados no MQTT
        for i in range(self.relayNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.relayLastStates[i] != self.relayStates[i]) or force:
                self.relayLastStates[i] = self.relayStates[i]
                # Publicando o estado do relé no MQTT, já está no formato "ON" / "OFF"
                mqtt_pub(index, self.entitySlugs[i], self.relayStates[i])
                logging.debug(f"KC868_A6_V01 - entityVal {i} {self.entitySlugs[i]} {self.relayStates[i]}")

        for i in range(self.inputNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.inputLastStates[i] != self.inputStates[i]) or force:
                self.inputLastStates[i] = self.inputStates[i]
                # Publicando o estado da entrada no MQTT, já está no formato "ON" / "OFF"
                mqtt_pub(index, self.entitySlugs[i+6], self.inputStates[i])
                logging.debug(f"KC868_A6_V01 - entityVal {i+6} {self.entitySlugs[i+6]} {self.inputStates[i]}")

    def proc_discovery(self, index):

        # Publicando descobrimento das entidades no MQTT
        ret = True
        for i in range(self.relayNum):
            ret = ret and mqtt_send_switch_discovery(index, self.entityNames[i], EC_NONE)
            if not ret:
                break
        if ret:
            for i in range(self.inputNum):
                ret = ret and mqtt_send_binary_sensor_discovery(index, self.entityNames[i+6], EC_NONE, EC_NONE)
                if not ret:
                    break
        if ret:
            logging.debug(f"Discovery Device KC868_A6_V01 OK Index {index}")
            return True
        else:
            logging.debug("Discovery Device KC868_A6_V01 NOT OK")
            return False
