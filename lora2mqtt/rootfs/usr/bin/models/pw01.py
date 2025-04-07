import logging

import globals

from funcs import slugify
from msgs import lora_fifo_tenta_enviar

from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH, DEVICE_CLASS_VOLTAGE, \
    DEVICE_CLASS_POWER, DEVICE_CLASS_CURRENT, DEVICE_CLASS_ENERGY, DEVICE_CLASS_RESTART, \
    DEVICE_CLASS_UPDATE, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL_INCREASING

class DevicePW01:
    def __init__(self):
        self.model = "PW01"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Sensores de elétricas"
        self.entityNames = ["Tensao", "Potencia", "Corrente", "Energia", "Energia RAM", "Aciona Rele", "Reset Energia"]
        self.entityValNumFator = [0.1, 0.1, 0.001, 1, 1]
        self.entitySlugs = []
        self.entityValNum = []
        self.entityLastValNum= []

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

        for i in range(len(self.entityValNumFator)):
            self.entityValNum.append(-1)
            self.entityLastValNum.append(-1)

    def proc_rec_msg(self, sMsg):
        
        if len(sMsg) != 33:
            logging.info(f"PW01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
        if len(partes) != 6:
            logging.info("PW01 - Erro ao dividir a mensagem!")
            return
        
        if len(partes[1]) != 4 or len(partes[2]) != 6 or len(partes[3]) != 6 or len(partes[4]) != 6 or len(partes[5]) != 6:
            logging.info("PW01 - Erro no tamanho dos dados!")
            logging.info(f"P1 {partes[1]} P2 {partes[2]} P3 {partes[3]} P4 {partes[4]} P5 {partes[5]} ")
            return
        
        self.entityValNum[0]  = int(partes[1])
        self.entityValNum[1]  = int(partes[2])
        self.entityValNum[2]  = int(partes[3])
        self.entityValNum[3]  = int(partes[4])
        self.entityValNum[4]  = int(partes[5])

        logging.debug(
            f"PW01 - Tensão: {self.entityValNum[0]} Potência: {self.entityValNum[1]} "
            f"Corrente: {self.entityValNum[2]} Energia: {self.entityValNum[3]} "
            f"EnergiaRam: {self.entityValNum[4]}")
        
    def proc_command(self, entity, pay, index):

        if entity == self.entitySlugs[5]:
            lora_fifo_tenta_enviar("100", index)
            return True
        if entity == self.entitySlugs[6]:
            lora_fifo_tenta_enviar("110", index)
            return True
        return False
 
    def proc_publish(self, index):

        client = globals.g_cli_mqtt

        for i in range(len(self.entityValNumFator)):
            if self.entityLastValNum[i] != self.entityValNum[i]:
                self.entityLastValNum[i] = self.entityValNum[i]
                aAux = "{:.1f}".format(self.entityValNum[i]*self.entityValNumFator[i])
                logging.debug(f"PW01 - entityValNum {i} {self.entitySlugs[i]} {aAux}")
                client.pub(f"{client.work_topics[index]}/{self.entitySlugs[i]}", 0, True, aAux)

    def proc_discovery(self, index):

        client = globals.g_cli_mqtt

        if client.send_aux_connectivity_discovery(index) and \
            client.send_tele_sensor_discovery(index, "RSSI", EC_DIAGNOSTIC, "{{ value_json.rssi }}", DEVICE_CLASS_SIGNAL_STRENGTH, "") and \
            client.send_sensor_discovery(index, self.entityNames[0], EC_NONE, DEVICE_CLASS_VOLTAGE, "V", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(index, self.entityNames[1], EC_NONE, DEVICE_CLASS_POWER, "W", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(index, self.entityNames[2], EC_NONE, DEVICE_CLASS_CURRENT, "A", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(index, self.entityNames[3], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            client.send_sensor_discovery(index, self.entityNames[4], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            client.send_button_discovery(index, self.entityNames[5], EC_NONE, DEVICE_CLASS_UPDATE) and \
            client.send_button_discovery(index, self.entityNames[6], EC_NONE, DEVICE_CLASS_RESTART):
            logging.debug(f"Discovery Entity PW01 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Entity PW01 NOT OK")
            return False


