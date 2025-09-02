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
                    mqtt_send_binary_sensor_discovery, mqtt_send_sensor_discovery, \
                    mqtt_send_number_discovery

from consts import EC_NONE, DEVICE_CLASS_NONE, DEVICE_CLASS_WATER, DEVICE_CLASS_TEMPERATURE, \
                    UNITS_NONE, STATE_CLASS_NONE, STATE_CLASS_TOTAL_INCREASING, \
                    STATE_CLASS_MEASUREMENT

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
                            "Input 4", "Input 5", "Input 6", \
                            "AnaIn 1", "AnaIn 2", "AnaIn 3", \
                            "AnaIn 4", "AnaOut 1",  "AnaOut 2", \
                            "Water Meter 1", "Temperature 1"]
        self.entityDomains = ["switch", "switch", "switch", \
                            "switch", "switch", "switch", \
                            "binary_sensor", "binary_sensor", "binary_sensor", \
                            "binary_sensor", "binary_sensor", "binary_sensor", \
                            "sensor", "sensor", "sensor", \
                            "sensor", "number", "number", \
                            "sensor", "sensor"]
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
        self.waterMeterNum = 1 
        self.waterMeterStates = []
        self.waterMeterLastStates = []
        self.tempNum = 1 
        self.tempStates = []
        self.tempLastStates = []

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

        for i in range(self.relayNum):
            self.relayStates.append("")
            self.relayLastStates.append("")

        for i in range(self.inputNum):
            self.inputStates.append("")
            self.inputLastStates.append("")

        for i in range(self.inAnaNum):
            self.inAnaStates.append(-1)
            self.inAnaLastStates.append(-1)

        for i in range(self.outAnaNum):
            self.outAnaStates.append(-1)
            self.outAnaLastStates.append(-1)

        for i in range(self.waterMeterNum):
            self.waterMeterStates.append(-1)
            self.waterMeterLastStates.append(-1)

        for i in range(self.tempNum):
            self.tempStates.append(-100.0)
            self.tempLastStates.append(-100.0)

    def proc_rec_msg(self, sMsg, index):

        # Mensagem recebida do dispositivo
        # A mgs tem o padrão "#rrrrr#eeeeee#iiiiiiiiiiiiiiii#oooooo"
        # Onde r = estados dos relés, e = estados das entradas,
        #      i = entradas analógicas, s = saidas analógicas
        if len(sMsg) != 50:
            logging.error(f"KC868_A6_V01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        partes = sMsg.split('#')
        if len(partes) != 7:
            logging.error("KC868_A6_V01 - Erro ao dividir a mensagem!")
            return
        ok = True
        ok = ok and len(partes[1]) == 6
        ok = ok and len(partes[2]) == 6
        ok = ok and len(partes[3]) == 16
        ok = ok and len(partes[4]) == 6
        ok = ok and len(partes[5]) == 5
        ok = ok and len(partes[6]) == 5
        if not ok:
            logging.error("KC868_A6_V01 - Erro no tamanho dos dados!")
            return
        # Presevando os dados tratados da Msg
        for i in range(self.relayNum):
            # Estado do relé no formato "ON" / "OFF"
            self.relayStates[i] = char_to_on_off(partes[1][i])
            logging.debug(f"KC868_A6_V01 - Relay {i+1}: {self.relayStates[i]}")
        for i in range(self.inputNum):
            # Estado da entrada no formato "ON" / "OFF"
            self.inputStates[i] = char_to_on_off(partes[2][i])
            logging.debug(f"KC868_A6_V01 - Input {i+1}: {self.inputStates[i]}")
        for i in range(self.inAnaNum):
            # Estado da entrada no formato inteiro
            self.inAnaStates[i] = int(partes[3][(i*4):(i*4)+4])
            logging.debug(f"KC868_A6_V01 - AnaIn {i+1}: {self.inAnaStates[i]}")
        for i in range(self.outAnaNum):
            # Estado da entrada no formato inteiro
            self.outAnaStates[i] = int(partes[4][(i*3):(i*3)+3])
            logging.debug(f"KC868_A6_V01 - AnaOut {i+1}: {self.outAnaStates[i]}")
        for i in range(self.waterMeterNum):
            # Estado da entrada no formato inteiro
            self.waterMeterStates[i] = int(partes[5][(i*5):(i*5)+5])
            logging.debug(f"KC868_A6_V01 - Water Meter {i+1}: {self.waterMeterStates[i]}")
        for i in range(self.tempNum):
            # Estado da entrada no formato float
            self.tempStates[i] = float(partes[6][(i*5):(i*5)+5])
            logging.debug(f"KC868_A6_V01 - Temperature {i+1}: {self.tempStates[i]}")
        
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
        # Testo comandos de "Saída Analógica"
        for i in range(self.outAnaNum):
            if entity == self.entitySlugs[i+16]:
                # Pegando o estado
                state = int(pay)
                logging.debug(f"KC868_A6_V01 - AnaOut {i+1} state: {state}")
                # Enviando comando para dispositivo
                lora_send_msg_usr(self.outAnaCmd[i] + f"{state:03}", index)
                #  Atualizando para evitar ficar mudando enquanto espera feedback
                self.outAnaStates[i] = state
                return True
        return False

    def proc_publish(self, index, force):

        # Publicando estados no MQTT
        for i in range(self.relayNum):
            # Só publica se houve alteração no estado ou se for forçado
            if (self.relayLastStates[i] != self.relayStates[i]) or force:
                self.relayLastStates[i] = self.relayStates[i]
                # Publicando o estado do relé no MQTT, já está no formato "ON" / "OFF"
                mqtt_pub(index, self.entitySlugs[i], self.relayStates[i])
                logging.debug(f"KC868_A6_V01 - entityVal {i} {self.entitySlugs[i]} {self.relayStates[i]}")
        for i in range(self.inputNum):
            # Só publica se houve alteração no estado ou se for forçado
            if (self.inputLastStates[i] != self.inputStates[i]) or force:
                self.inputLastStates[i] = self.inputStates[i]
                # Publicando o estado da entrada no MQTT, já está no formato "ON" / "OFF"
                mqtt_pub(index, self.entitySlugs[i+6], self.inputStates[i])
                logging.debug(f"KC868_A6_V01 - entityVal {i+6} {self.entitySlugs[i+6]} {self.inputStates[i]}")
        for i in range(self.inAnaNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.inAnaLastStates[i] != self.inAnaStates[i]) or force:
                self.inAnaLastStates[i] = self.inAnaStates[i]
                # Publicando o estado da entrada analógica no MQTT, formatando para string
                aAux = "{:.0f}".format(self.inAnaStates[i])
                mqtt_pub(index, self.entitySlugs[i+12], aAux)
                logging.debug(f"KC868_A6_V01 - entityVal {i+6} {self.entitySlugs[i+12]} {aAux}")
        for i in range(self.outAnaNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.outAnaLastStates[i] != self.outAnaStates[i]) or force:
                self.outAnaLastStates[i] = self.outAnaStates[i]
                # Publicando o estado da saida analógica no MQTT, formatando para string
                aAux = "{:.0f}".format(self.outAnaStates[i])
                mqtt_pub(index, self.entitySlugs[i+16], aAux)
                logging.debug(f"KC868_A6_V01 - entityVal {i+16} {self.entitySlugs[i+16]} {aAux}")
        for i in range(self.waterMeterNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.waterMeterLastStates[i] != self.waterMeterStates[i]) or force:
                self.waterMeterLastStates[i] = self.waterMeterStates[i]
                # Publicando o estado da medição no MQTT, formatando para string
                aAux = "{:.0f}".format(self.waterMeterStates[i])
                mqtt_pub(index, self.entitySlugs[i+18], aAux)
                logging.debug(f"KC868_A6_V01 - entityVal {i+18} {self.entitySlugs[i+18]} {aAux}")
        for i in range(self.tempNum):
            # Só publica se houve alteração no valor ou se for forçado
            if (self.tempLastStates[i] != self.tempStates[i]) or force:
                self.tempLastStates[i] = self.tempStates[i]
                # Publicando o estado da temperatura no MQTT, formatando para string
                aAux = "{:.1f}".format(self.tempStates[i])
                mqtt_pub(index, self.entitySlugs[i+19], aAux)
                logging.debug(f"KC868_A6_V01 - entityVal {i+19} {self.entitySlugs[i+19]} {aAux}")

    def proc_discovery(self, index):

        # Publicando descobrimento das entidades no MQTT
        ret = True
        for i in range(self.relayNum):
            ret = ret and mqtt_send_switch_discovery(index, self.entityNames[i], EC_NONE)
            if not ret:
                break
        if ret:
            for i in range(self.inputNum):
                ret = ret and mqtt_send_binary_sensor_discovery(index, self.entityNames[i+6], \
                                EC_NONE, DEVICE_CLASS_NONE)
                if not ret:
                    break
        if ret:
            for i in range(self.inAnaNum):
                ret = ret and mqtt_send_sensor_discovery(index, self.entityNames[i+12], EC_NONE, \
                                DEVICE_CLASS_NONE, UNITS_NONE, STATE_CLASS_NONE, True)
                if not ret:
                    break
        if ret:
            for i in range(self.outAnaNum):
                ret = ret and mqtt_send_number_discovery(index, self.entityNames[i+16], EC_NONE, \
                                0, 100, 1)
                if not ret:
                    break
        if ret:
            for i in range(self.waterMeterNum):
                ret = ret and mqtt_send_sensor_discovery(index, self.entityNames[i+18], EC_NONE, \
                                DEVICE_CLASS_WATER, "L", STATE_CLASS_TOTAL_INCREASING, True)
                if not ret:
                    break
        if ret:
            for i in range(self.tempNum):
                ret = ret and mqtt_send_sensor_discovery(index, self.entityNames[i+19], EC_NONE, \
                                DEVICE_CLASS_TEMPERATURE, "°C", STATE_CLASS_MEASUREMENT, True)
                if not ret:
                    break
        if ret:
            logging.debug(f"Discovery Device KC868_A6_V01 OK Index {index}")
            return True
        else:
            logging.debug("Discovery Device KC868_A6_V01 NOT OK")
            return False
