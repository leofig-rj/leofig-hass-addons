# Em self.model é definido o nome do dispositivo
# O nome do arquivo dever ser o nome do dispositivo em minúsculas .py
# O nome da classe deve ter o padrão "Device" + o nome do dispositivo,
# em maiúsculas
# A classe tem que ter as variáveis : self.model, self.chip, self.ver, self.man, 
# self.desc, self.entityNames e self.entitySlugs
# E as funções: proc_rec_msg, proc_command, proc_publish e proc_discovery

import logging

from funcs import slugify, char_to_state
from msgs import lora_send_msg_usr, mqtt_pub, mqtt_send_sensor_discovery, \
                    mqtt_send_light_discovery, mqtt_send_button_discovery

from consts import EC_NONE, DEVICE_CLASS_VOLTAGE, DEVICE_CLASS_POWER, DEVICE_CLASS_CURRENT, \
    DEVICE_CLASS_ENERGY, DEVICE_CLASS_FREQUENCY, DEVICE_CLASS_RESTART,  \
    STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL_INCREASING

class DeviceTEST02:
    def __init__(self):
        self.model = "TEST02"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Sensores de elétricas"
        self.entityNames = ["Tensao", "Potencia", "Corrente", "Energia", "Frequencia", "Lampada", "Reset Energia"]
        self.entityDomains = ["sensor", "sensor", "sensor", "sensor", "sensor", "light", "button"]
        self.entityValNumFator = [0.1, 0.1, 0.001, 1, 0.1]
        self.entityValStr = []
        self.entityLastValStr = []
        self.entitySlugs = []
        self.entityValNum = []
        self.entityLastValNum= []

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

        for i in range(len(self.entityValNumFator)):
            self.entityValNum.append(-1)
            self.entityLastValNum.append(-1)

        for i in range(1):
            self.entityValStr.append("NULL")
            self.entityLastValStr.append("NULL")

    def proc_rec_msg(self, sMsg, index):
        
        if len(sMsg) != 35:
            logging.info(f"TEST02 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
        if len(partes) != 7:
            logging.info("TEST02 - Erro ao dividir a mensagem!")
            return
        
        if len(partes[1]) != 4 or len(partes[2]) != 6 or len(partes[3]) != 6 or len(partes[4]) != 6 \
            or len(partes[5]) != 6 or len(partes[6]) != 1:
            logging.info("TEST02 - Erro no tamanho dos dados!")
            logging.info(f"P1 {partes[1]} P2 {partes[2]} P3 {partes[3]} P4 {partes[4]} P5 {partes[5]} P6 {partes[6]} ")
            return
        
        self.entityValNum[0]  = int(partes[1])
        self.entityValNum[1]  = int(partes[2])
        self.entityValNum[2]  = int(partes[3])
        self.entityValNum[3]  = int(partes[4])
        self.entityValNum[4]  = int(partes[5])

        self.entityValStr[0] = char_to_state(partes[6])

        logging.debug(
            f"TEST02 - Tensão: {self.entityValNum[0]} Potência: {self.entityValNum[1]} "
            f"Corrente: {self.entityValNum[2]} Energia: {self.entityValNum[3]} "
            f"EnergiaRam: {self.entityValNum[4]} Interruptor: {self.entityValStr[0]}")
        
    def proc_command(self, entity, pay, index):

        if entity == self.entitySlugs[5]:
            if (pay.find("ON")!=-1):
                # ON -> Cmd 101
                lora_send_msg_usr("101", index)
            else:
                # OFF -> Cmd 102
                lora_send_msg_usr("102", index)
            ######  Definindo para evitar ficar mudando enquanto espera feedback
            self.entityValStr[0] = pay
        if entity == self.entitySlugs[6]:
            lora_send_msg_usr("110", index)
            return True
        return False

    def proc_publish(self, index, force):

        for i in range(len(self.entityValNumFator)):
            if (self.entityLastValNum[i] != self.entityValNum[i]) or force:
                self.entityLastValNum[i] = self.entityValNum[i]
                aAux = "{:.1f}".format(self.entityValNum[i]*self.entityValNumFator[i])
                logging.debug(f"TEST02 - entityValNum {i} {self.entitySlugs[i]} {aAux}")
                mqtt_pub(index, self.entitySlugs[i], aAux)
        if (self.entityLastValStr[0] != self.entityValStr[0]) or force:
            self.entityLastValStr[0] = self.entityValStr[0]
            logging.debug(f"TEST02 - entityValStr 0 {self.entitySlugs[5]} {self.entityValStr[0]}")
            mqtt_pub(index, self.entitySlugs[5], self.entityValStr[0])

    def proc_discovery(self, index):

        if mqtt_send_sensor_discovery(index, self.entityNames[0], EC_NONE, DEVICE_CLASS_VOLTAGE, "V", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[1], EC_NONE, DEVICE_CLASS_POWER, "W", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[2], EC_NONE, DEVICE_CLASS_CURRENT, "A", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[3], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[4], EC_NONE, DEVICE_CLASS_FREQUENCY, "Hz", STATE_CLASS_TOTAL_INCREASING, True) and \
            mqtt_send_light_discovery(index, self.entityNames[5], EC_NONE) and \
            mqtt_send_button_discovery(index, self.entityNames[6], EC_NONE, DEVICE_CLASS_RESTART):
            logging.debug(f"Discovery Entity TEST02 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Entity TEST02 NOT OK")
            return False
