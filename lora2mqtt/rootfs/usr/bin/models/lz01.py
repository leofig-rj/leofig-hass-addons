import logging

from funcs import slugify, char_to_state, char_to_on_off
from msgs import lora_fifo_tenta_enviar, mqtt_set_rssi, mqtt_pub, mqtt_send_light_switch_discovery, \
                    mqtt_send_binary_sensor_discovery

from consts import EC_NONE

class DeviceLZ01:
    def __init__(self):
        self.model = "LZ01"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Lampada"
        self.entityNames = ["Lampada 1", "Input 1"]
        self.entityDomains = ["light", "binary_sensor"]
        self.entitySlugs = []
        self.entityValStr = []
        self.entityLastValStr = []
        self.entityRSSI = -20

        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))
            self.entityValStr.append("NULL")
            self.entityLastValStr.append("NULL")

    def proc_rec_msg(self, sMsg, index):

#        if len(sMsg) != 9:
        if len(sMsg) != 4:
            logging.info(f"LZ01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
#        if len(partes) != 4:
        if len(partes) != 3:
            logging.info("LZ01 - Erro ao dividir a mensagem!")
            return
        
#        if len(partes[1]) != 1 or len(partes[2]) != 1 or len(partes[3]) != 4:
        if len(partes[1]) != 1 or len(partes[2]) != 1:
            logging.info("LZ01 - Erro no tamanho dos dados!")
            return
        
        self.entityValStr[0] = char_to_state(partes[1])
        self.entityValStr[1] = char_to_on_off(partes[2])
#        mqtt_set_rssi(index, int(partes[3]))
        mqtt_set_rssi(index, self.entityRSSI)
        self.entityRSSI = self.entityRSSI -1
        if self.entityRSSI < -150:
            self.entityRSSI = -20
        
        logging.debug(f"LZ01 - Lâmpada1: {self.entityValStr[0]} Input1: {self.entityValStr[1]}")
            
    def proc_command(self, entity, pay, index):

        if entity == self.entitySlugs[0]:
            if (pay.find("ON")!=-1):
                # ON -> Cmd 101
                lora_fifo_tenta_enviar("101", index)
            else:
                # OFF -> Cmd 102
                lora_fifo_tenta_enviar("102", index)
            ######  Definindo para evitar ficar mudando enquanto espera feedback
            self.entityValStr[0] = pay
            return True
        return False
 
    def proc_publish(self, index, force):

        for i in range(len(self.entityNames)):
            if (self.entityLastValStr[i] != self.entityValStr[i]) or force:
                self.entityLastValStr[i] = self.entityValStr[i]
                logging.debug(f"LZ01 - entityValStr {i} {self.entitySlugs[i]} {self.entityValStr[i]}")
                mqtt_pub(index, self.entitySlugs[i], self.entityValStr[i])

    def proc_discovery(self, index):

        if mqtt_send_light_switch_discovery(index, self.entityNames[0], EC_NONE) and \
            mqtt_send_binary_sensor_discovery(index, self.entityNames[1], EC_NONE, EC_NONE):
            logging.debug(f"Discovery Entity LZ01 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Entity LZ01 NOT OK")
            return False
