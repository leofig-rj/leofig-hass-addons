import logging

from funcs import slugify
from msgs import lora_fifo_tenta_enviar, mqtt_set_rssi, mqtt_pub, mqtt_send_sensor_discovery, \
                    mqtt_send_button_discovery

from consts import EC_NONE, DEVICE_CLASS_VOLTAGE, DEVICE_CLASS_POWER, DEVICE_CLASS_CURRENT, \
    DEVICE_CLASS_ENERGY, DEVICE_CLASS_RESTART, DEVICE_CLASS_UPDATE, STATE_CLASS_MEASUREMENT, \
    STATE_CLASS_TOTAL_INCREASING

class DevicePW01:
    def __init__(self):
        self.model = "PW01"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Sensores de elétricas"
        self.entityNames = ["Tensao", "Potencia", "Corrente", "Energia", "Energia RAM", "Aciona Rele", "Reset Energia"]
        self.entityDomains = ["sensor", "sensor", "sensor", "sensor", "sensor", "button", "button"]
        self.entityValNumFator = [0.1, 0.1, 0.001, 1, 1]
        self.entitySlugs = []
        self.entityValNum = []
        self.entityLastValNum= []
        self.entityRSSI = -25

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))

        for i in range(len(self.entityValNumFator)):
            self.entityValNum.append(-1)
            self.entityLastValNum.append(-1)

    def proc_rec_msg(self, sMsg, index):
        
#        if len(sMsg) != 38:
        if len(sMsg) != 33:
            logging.info(f"PW01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
#        if len(partes) != 7:
        if len(partes) != 6:
            logging.info("PW01 - Erro ao dividir a mensagem!")
            return
        
#        if len(partes[1]) != 4 or len(partes[2]) != 6 or len(partes[3]) != 6 or len(partes[4]) != 6 or len(partes[5]) != 6 or len(partes[6]) != 4:
        if len(partes[1]) != 4 or len(partes[2]) != 6 or len(partes[3]) != 6 or len(partes[4]) != 6 or len(partes[5]) != 6:
            logging.info("PW01 - Erro no tamanho dos dados!")
            logging.info(f"P1 {partes[1]} P2 {partes[2]} P3 {partes[3]} P4 {partes[4]} P5 {partes[5]} ")
            return
        
        self.entityValNum[0]  = int(partes[1])
        self.entityValNum[1]  = int(partes[2])
        self.entityValNum[2]  = int(partes[3])
        self.entityValNum[3]  = int(partes[4])
        self.entityValNum[4]  = int(partes[5])
#        mqtt_set_rssi(index, int(partes[6]))
        mqtt_set_rssi(index, self.entityRSSI)
        self.entityRSSI = self.entityRSSI -1
        if self.entityRSSI < -150:
            self.entityRSSI = -25

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
 
    def proc_publish(self, index, force):

        for i in range(len(self.entityValNumFator)):
            if (self.entityLastValNum[i] != self.entityValNum[i]) or force:
                self.entityLastValNum[i] = self.entityValNum[i]
                aAux = "{:.1f}".format(self.entityValNum[i]*self.entityValNumFator[i])
                logging.debug(f"PW01 - entityValNum {i} {self.entitySlugs[i]} {aAux}")
                mqtt_pub(index, self.entitySlugs[i], aAux)

    def proc_discovery(self, index):

        if mqtt_send_sensor_discovery(index, self.entityNames[0], EC_NONE, DEVICE_CLASS_VOLTAGE, "V", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[1], EC_NONE, DEVICE_CLASS_POWER, "W", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[2], EC_NONE, DEVICE_CLASS_CURRENT, "A", STATE_CLASS_MEASUREMENT, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[3], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            mqtt_send_sensor_discovery(index, self.entityNames[4], EC_NONE, DEVICE_CLASS_ENERGY, "Wh", STATE_CLASS_TOTAL_INCREASING, True) and \
            mqtt_send_button_discovery(index, self.entityNames[5], EC_NONE, DEVICE_CLASS_UPDATE) and \
            mqtt_send_button_discovery(index, self.entityNames[6], EC_NONE, DEVICE_CLASS_RESTART):
            logging.debug(f"Discovery Entity PW01 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Entity PW01 NOT OK")
            return False


