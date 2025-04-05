import logging

import msgs
import funcs
import bridge

from consts import EC_NONE, EC_DIAGNOSTIC, DEVICE_CLASS_SIGNAL_STRENGTH

class DevicePW01:
    def __init__(self, mac=0, addr=0, index=0):
        self.model = "LZ01"
        self.mac = mac
        self.addr = addr
        self.index = index
        self.chip = "ESP32"
        self.ver = "1.0.0"
        self.man = "Leonardo Figueiro"
        self.desc = "Lampada"
        self.entityNames = ["Lampada 1", "Input 1"]
        self.entitySlugs = ["lampada_1", "input_1"]
        self.lenEntiies = len(self.entityNames)
        self.entityValNum = [-1] * self.lenEntiies
        self.entityLastValNum= [-1] * self.lenEntiies
        self.entityValStr = ["NULL"] * self.lenEntiies
        self.entityLastValStr = ["NULL"] * self.lenEntiies

    def proc_rec_msg(self, sMsg):

        ram_dev = bridge.devices.get_dev_rams()[self.index]
        
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
        
        self.entityValStr[0] = funcs.char_to_state(partes[1])
        self.entityValStr[1] = funcs.char_to_on_off(partes[2])
        
        logging.debug(f"LZ01 - Lâmpada1: {self.entityValStr[0]} Input1: {self.entityValStr[1]}")
            
        ram_dev.loraTimeOut = funcs.millis()
        ram_dev.loraCom = True
        if msgs.get_loraUltimoDestinoCmd() == self.index:
            msgs.lora_proximo_destino_cmd()

    def proc_command(self, entity, pay):

        if entity == self.entitySlugs[0]:
            if (pay.indexOf("ON")!=-1):
                msgs.loraFiFoTentaEnviar("101", self.index)
            else:
                msgs.loraFiFoTentaEnviar("102", self.index)
            ######  Definindo para evitar ficar mudando enquanto espera feedback
            self.entityValStr[0] = pay
            return True
        return False
 
    def proc_publish(self):

        client = bridge.client_mqtt

        for i in range(2):          
            if self.entityValStr[i] != self.entityLastValStr[i]:
                self.entityLastValStr[i] = self.entityValStr[i]
                client.pub(f"{client.workTopic[self.index]}/{self.entitySlugs[i]}", 0, True, self.entityValStr[i])

    def proc_discovery(self):

        client = bridge.client_mqtt

        if client.sendAuxConnectivityDiscovery(self.index) and \
            client.sendTeleSensorDiscovery(self.index, "RSSI", EC_DIAGNOSTIC, "{{ value_json.rssi }}", DEVICE_CLASS_SIGNAL_STRENGTH, "") and \
            client.sendLightSwitchDiscovery(self.index, self.entityNames[0], EC_NONE) and \
            client.sendBinarySensorDiscovery(self.index, self.entityNames[1], EC_NONE, EC_NONE):
            return True
        else:
            return False
