import logging

import globals

from funcs import slugify, char_to_state, char_to_on_off
from msgs import lora_fifo_tenta_enviar

from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH

class DeviceLZ01:
    def __init__(self, addr=0):
        self.model = "LZ01"
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Lampada"
        self.entityAddr = addr
        self.entityNames = ["Lampada 1", "Input 1"]
        self.entitySlugs = []
        self.entityValNum = []
        self.entityLastValNum= []
        self.entityValStr = []
        self.entityLastValStr = []
        self._setup_lists()

    def _setup_lists(self):
        logging.debug(f"LZ01 - Preenchendo listas! {len(self.entityNames)}")
        for i in range(len(self.entityNames)):
            self.entitySlugs.append(slugify(self.entityNames[i]))
            self.entityValNum.append(-1)
            self.entityLastValNum.append(-1)
            self.entityValStr.append("NULL")
            self.entityLastValStr.append("NULL")
        logging.debug(f"LZ01 - Resultado listas! {self.entitySlugs}")

    def proc_rec_msg(self, sMsg):

        if len(sMsg) != 4:
            logging.info(f"LZ01 - Erro no tamanho da mensagem! {len(sMsg)}")
            return
        
        partes = sMsg.split('#')
        if len(partes) != 3:
            logging.info("LZ01 - Erro ao dividir a mensagem!")
            return
        
        if len(partes[1]) != 1 or len(partes[2]) != 1:
            logging.info("LZ01 - Erro no tamanho dos dados!")
            return
        
        self.entityValStr[0] = char_to_state(partes[1])
        self.entityValStr[1] = char_to_on_off(partes[2])
        
        logging.debug(f"LZ01 - Lâmpada1: {self.entityValStr[0]} Input1: {self.entityValStr[1]}")
            
    def proc_command(self, entity, pay, index):

        if entity == self.entitySlugs[0]:
            if (pay.indexOf("ON")!=-1):
                lora_fifo_tenta_enviar("101", index)
            else:
                lora_fifo_tenta_enviar("102", index)
            ######  Definindo para evitar ficar mudando enquanto espera feedback
            self.entityValStr[0] = pay
            return True
        return False
 
    def proc_publish(self, index):

        client = globals.g_cli_mqtt

        for i in range(2):
            if self.entityLastValStr[i] != self.entityValStr[i]:
                self.entityLastValStr[i] = self.entityValStr[i]
                logging.debug(f"LZ01 - entityValStr {i} {self.entitySlugs[i]} {self.entityValStr[i]}")
                client.pub(f"{client.work_topics[index]}/{self.entitySlugs[i]}", 0, True, self.entityValStr[i])

    def proc_discovery(self, index):

        client = globals.g_cli_mqtt

        if client.send_aux_connectivity_discovery(index) and \
            client.send_tele_sensor_discovery(index, "RSSI", EC_DIAGNOSTIC, "{{ value_json.rssi }}", DEVICE_CLASS_SIGNAL_STRENGTH, "") and \
            client.send_light_switch_discovery(index, self.entityNames[0], EC_NONE) and \
            client.send_binary_sensor_discovery(index, self.entityNames[1], EC_NONE, EC_NONE):
            logging.debug(f"Discovery Entity LZ01 OK Índex {index}")
            return True
        else:
            logging.debug("Discovery Entity LZ01 NOT OK")
            return False
