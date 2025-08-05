import logging

import msgs

from consts import MODE_OP_PAIRING, MODE_OP_LOOP, STEP_NEG_INIC, STEP_NEG_CFG, CMD_NEGOCIA_INIC, \
    MSG_CHECK_OK, MSG_CHECK_NOT_ME, MSG_CHECK_ALREADY_REC, MSG_CHECK_ERROR

class RegRec:
    def __init__(self, de=0, para=0, id=0):
        self.de = de
        self.para = para
        self.id = id

class LFLoraClass:

    def __init__(self, net_id, addr):
        self._netId = net_id
        self._myAddr = addr
        self._lastSendId = 255
        self._lastSendIdUsr = 127
        self._regRecs = []
        self._lastRegRec = RegRec()
        self._modoOp = MODE_OP_LOOP
        self._lastModoOp = -1  # Valor indevido para enviar na primeira vez
        self._faseNegocia = STEP_NEG_INIC
        self._negociaMsg = ""
        self._negociaDe = ""
        self._negociaMac = ""
        self._negociaModelo = ""
        self._negociaAddrSlave = ""
        self._slaveAddr = 3

    def set_modo_op(self, modo):
        self._modoOp = modo

        pairingStatus = "OFF"
        if self._modoOp == MODE_OP_PAIRING:
            self._negociaMsg = CMD_NEGOCIA_INIC
            self._faseNegocia = STEP_NEG_INIC
            msgs.lora_reset_pairing_time()
            pairingStatus = "ON"

        msgs.mqtt_send_pairing_mode(pairingStatus)

    def modo_op(self):
        return self._modoOp

    def fase_negocia(self):
        return self._faseNegocia

    def set_fase_negocia(self, fase):
        self._faseNegocia = fase
        if self._faseNegocia == STEP_NEG_INIC:
            self._negociaMsg = CMD_NEGOCIA_INIC

    def negocia_msg(self):
        return self._negociaMsg

    def last_reg_rec(self):
        return self._lastRegRec

    def lora_get_next_id(self):
        self._lastSendId = self._lastSendId + 1
        if self._lastSendId > 63:
            self._lastSendId = 1
        return self._lastSendId

    def lora_get_next_id_usr(self):
        self._lastSendIdUsr = self._lastSendIdUsr + 1
        if self._lastSendIdUsr > 127:
            self._lastSendIdUsr = 64
        return self._lastSendIdUsr

    def lora_add_header_id(self, input_str, para, msg_id):
        # Criação do buffer auxiliar com o cabeçalho
        aux = f"#{self._netId:02X}{self._myAddr:02X}{para:02X}{msg_id:02X}{len(input_str) + 12:04X}"
        # Completa com a mensagem de entrada
        aux += input_str
        # Retorna a mensagem com o cabeçalho
        return aux
    
    def lora_check_msg_ini(self, input_str):
        out = ""

        if input_str[0] != '#':
            return MSG_CHECK_ERROR, 0, 0, 0, 0, out

        for i in range(16):
            try:
                char = input_str[i+1:i+2]
                if char not in "-0123456789ABCDEFabcdef":
                    return MSG_CHECK_ERROR, 0, 0, 0, 0, out
            except UnicodeDecodeError:
                return MSG_CHECK_ERROR, 0, 0, 0, 0, out

        rssi = int(input_str[1:5], 10)
        net = int(input_str[5:7], 16)
        de = int(input_str[7:9], 16)
        para = int(input_str[9:11], 16)
        id = int(input_str[11:13], 16)
        len_in_msg = int(input_str[13:17], 16)

        if net != self._netId:
            return MSG_CHECK_ERROR, 0, 0, 0, 0, out

        # input_str tem cinco caracteres a mais (#rssi)
        if len_in_msg != len(input_str) - 5:
            return MSG_CHECK_ERROR, 0, 0, 0, 0, out

        out = input_str[17:]

        self._lastRegRec = RegRec(de, para, id)

        index = self.find_reg_rec(de, para)
        if index == -1:
            self.add_reg_rec(de, para, id)
        else:
            if self._regRecs[index].id == id:
                return MSG_CHECK_ALREADY_REC, de, para, id, rssi, out
            self._regRecs[index].id = id

        return MSG_CHECK_OK, de, para, id, rssi, out

    def lora_check_msg(self, input_str, length):
        out = []
        result, de, para, id, rssi, out = self.lora_check_msg_ini(input_str, length)
        if result != MSG_CHECK_OK:
            return result, out
        if para != self._myAddr:
            return MSG_CHECK_NOT_ME, out
        return MSG_CHECK_OK, out

    def add_reg_rec(self, de, para, id):
        self._regRecs.append(RegRec(de, para, id))

    def find_reg_rec(self, de, para):
        for i, rec in enumerate(self._regRecs):
            if rec.de == de and rec.para == para:
                return i
        return -1

    def remove_reg_rec(self, index):
        if index < 0 or index >= len(self._regRecs):
            return

        # Remove o registro no índice especificado
        self._regRecs.pop(index)

    def clear_reg_recs(self):
        self._regRecs.clear()  # Limpa a lista de registros

    def is_mode_op_to_send(self):
        if self._lastModoOp != self._modoOp:
            self._lastModoOp = self._modoOp
            return True
        return False

    def on_lora_pairing_message(self, msg):
        logging.debug(f"CFG - MSG: {msg} Len: {len(msg)}")
        if msg[0] != '!':
            return False
        if msg[7] != '!':
            return False
        if msg[14] != '!':
            return False
        if msg[18] != '!':
            return False
        para = msg[1:7]
        de = msg[8:14]
        cmd = msg[15:18]
        logging.debug(f"CFG - De: {de} Para: {para} Cmd: {cmd}")

        if self._faseNegocia == STEP_NEG_INIC:
            if (len(msg)) < 34:
                return False
            if msg[31] != '!':
                return False
            if para != "FFFFFF":
                return False
            if cmd != "100":
                return False
            self._negociaDe = de
            self._negociaMac = msg[19:31]
            self._negociaModelo = msg[32:]
            logging.debug(f"CFG - MAC: {self._negociaMac} Modelo: {self._negociaModelo}")
            logging.info(f"CFG - Receiving from MAC: {self._negociaMac} Modelo: {self._negociaModelo}")
            # Verificando se modelo existe no sistema
            if msgs.disp_check_model(self._negociaModelo):
                self._negociaAddrSlave = msgs.disp_get_ram_dev_addr_by_mac(self._negociaMac)
                self._negociaMsg = f"!{self._negociaDe}!FFFFFF!101!{self._netId:03}!{self._myAddr:03}!{self._negociaAddrSlave:03}"
                logging.debug(f"CFG - Resposta CFG: {self._negociaMsg}")
                logging.info(f"CFG - Responding to MAC: {self._negociaMac} Modelo: {self._negociaModelo}")
                self.set_fase_negocia(STEP_NEG_CFG)
                return True
            logging.info(f"CFG - Model: {self._negociaModelo} not OK, check model config file!")
            msgs.mqtt_send_bridge_info(f"Model not OK: {self._negociaModelo}")
            return False
  
        if self._faseNegocia == STEP_NEG_CFG:
            logging.debug(f"CFG 1 - modelo: {self._negociaModelo} mac: {self._negociaMac} slaveAddr: {self._negociaAddrSlave:03}")
            logging.info(f"CFG - Receiving confirmation from MAC: {self._negociaMac} Modelo: {self._negociaModelo}")
            if (len(msg)) != 30:
                return False
            if msg[22] != '!':
                return False
            if msg[26] != '!':
                return False
            if para != "FFFFFF":
                return False
            if de != self._negociaDe:
                return False
            if cmd != "101":
                return False
            netId = msg[19:22]
            masterAddr = msg[23:26]
            slaveAddr = msg[27:30]
            if netId != f"{self._netId:03}":
                return False
            if masterAddr != f"{self._myAddr:03}":
                return False
            if slaveAddr != f"{self._negociaAddrSlave:03}":
                return False
            # Salvando o Slave, se não existir, cria
            msgs.disp_save_ram_dev(self._negociaAddrSlave, self._negociaModelo, self._negociaMac)
            self.set_fase_negocia(STEP_NEG_INIC)
            logging.info(f"CFG - Setting model: {self._negociaModelo} mac: {self._negociaMac} addr: {self._negociaAddrSlave:03}")
            msgs.mqtt_send_bridge_info(f"Connected MAC: {self._negociaMac}")
            return True
        return False
