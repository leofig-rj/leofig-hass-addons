import logging

import globals

from msgs import lora_fifo_tenta_enviar

from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH, DEVICE_CLASS_VOLTAGE, \
    DEVICE_CLASS_POWER, DEVICE_CLASS_CURRENT, DEVICE_CLASS_ENERGY, DEVICE_CLASS_RESTART, \
    DEVICE_CLASS_UPDATE, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL_INCREASING

class DevicePW01:
    def __init__(self, mac=0, addr=0, index=0):
        self.model = "PW01"
        self.mac = mac
        self.addr = addr
        self.index = index
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Sensores de elétricas"
        self.entityNames = ["Tensao", "Potencia", "Corrente", "Energia", "Energia RAM", "Aciona Rele", "Reset Energia"]
        self.entitySlugs = ["tensao", "potencia", "corrente", "energia", "energia_ram", "aciona_rele", "reset_energia"]
        self.lenEntiies = len(self.entityNames)
        self.entityValNum = [-1] * self.lenEntiies
        self.entityLastValNum= [-1] * self.lenEntiies
        self.entityValStr = ["NULL"] * self.lenEntiies
        self.entityLastValStr = ["NULL"] * self.lenEntiies

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
        
    def proc_command(self, entity, pay):

        if entity == self.entitySlugs[5]:
            lora_fifo_tenta_enviar("100", self.index)
            return True
        if entity == self.entitySlugs[6]:
            lora_fifo_tenta_enviar("110", self.index)
            return True
        return False
 
    def proc_publish(self):

        client = g_cli_mqtt

        for i in range(5):          
            if self.entityValNum[i] != self.entityLastValNum[i]:
                self.entityLastValNum[i] = self.entityValNum[i]
                aAux = "{:.1f}".format(self.entityValNum[i]/10.0)
                client.pub(f"{client.workTopic[self.index]}/{self.entitySlugs[i]}", 0, True, aAux)

    def proc_discovery(self):

        client = globals.g_cli_mqtt

        if client.send_aux_connectivity_discovery(self.index) and \
            client.send_tele_sensor_discovery(self.index, "RSSI", EC_DIAGNOSTIC, "{{ value_json.rssi }}", DEVICE_CLASS_SIGNAL_STRENGTH, "") and \
            client.send_sensor_discovery(self.index, self.entityNames[0], EC_NONE, DEVICE_CLASS_VOLTAGE, "V", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(self.index, self.entityNames[1], EC_NONE, DEVICE_CLASS_POWER, "W", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(self.index, self.entityNames[2], EC_NONE, DEVICE_CLASS_CURRENT, "A", STATE_CLASS_MEASUREMENT, True) and \
            client.send_sensor_discovery(self.index, self.entityNames[3], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            client.send_sensor_discovery(self.index, self.entityNames[4], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            client.send_button_discovery(self.index, self.entityNames[5], EC_NONE, DEVICE_CLASS_UPDATE) and \
            client.send_button_discovery(self.index, self.entityNames[6], EC_NONE, DEVICE_CLASS_RESTART):
            logging.debug("Discovery Entity PW01 OK")
            return True
        else:
            logging.debug("Discovery Entity PW01 NOT OK")
            return False


