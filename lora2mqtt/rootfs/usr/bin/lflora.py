import random
import string

class RegRec:
    def __init__(self, de=0, para=0, id=0):
        self.de = de
        self.para = para
        self.id = id

class LFLoraClass:
    LFLORA_MAX_PACKET_SIZE = 255

    MSG_CHECK_OK = 0
    MSG_CHECK_NOT_MASTER = 1
    MSG_CHECK_NOT_ME = 2
    MSG_CHECK_ALREADY_REC = 3
    MSG_CHECK_ERROR = 4

    def __init__(self):
        self._myAddr = 0
        self._myMasterAddr = 0
        self._lastSendId = 255
        self._regRecs = []
        self._lastRegRec = RegRec()
        self.lf_key = [
            0x20, 0x0B, 0x4C, 0x49, 0x10, 0x07, 0x48, 0x30,
            0x3B, 0x10, 0x17, 0x31, 0x42, 0x48, 0x41, 0x43,
            0x0E, 0x08, 0x08, 0x2E, 0x28, 0x3A, 0x0D, 0x35,
            0x2A, 0x15, 0x29, 0x0B, 0x10, 0x29, 0x1B, 0x0C,
            0x2E, 0x46, 0x14, 0x04, 0x06, 0x3C, 0x01, 0x42,
            0x1C, 0x1D, 0x29, 0x4D, 0x04, 0x46, 0x00, 0x01,
            0x45, 0x3A, 0x09, 0x45, 0x27, 0x12, 0x05, 0x2F,
            0x0C, 0x0D, 0x0D, 0x45, 0x03, 0x40, 0x26, 0x44,
            0x2B, 0x41, 0x28, 0x2C, 0x4A, 0x29, 0x31, 0x32,
            0x1D, 0x12, 0x1F, 0x21, 0x47, 0x1C, 0x2B, 0x23,
            0x33, 0x0B, 0x1B, 0x33, 0x1D, 0x2B, 0x29, 0x2D,
            0x33, 0x43, 0x20, 0x41, 0x46, 0x49, 0x02, 0x0A,
            0x39, 0x18, 0x3B, 0x4D, 0x08, 0x08, 0x15, 0x14,
            0x2A, 0x36, 0x33, 0x47, 0x4E, 0x38, 0x25, 0x4B,
            0x1E, 0x12, 0x47, 0x09, 0x26, 0x16, 0x32, 0x4D,
            0x22, 0x1A, 0x4E, 0x30, 0x19, 0x4C, 0x32, 0x38
        ]
        self.descCheckMsgLora = [
            "OK",
            "Não é do Master",
            "Não é para mim",
            "Msg repetida",
            "Erro na Msg"
        ]

    def set_my_addr(self, addr):
        self._myAddr = addr

    def set_my_master_addr(self, addr):
        self._myMasterAddr = addr

    def my_addr(self):
        return self._myAddr

    def my_master_addr(self):
        return self._myMasterAddr

    def lora_encode(self, input_str, length):
        out = []
        out.append(random.choice(string.printable))
        out.append(random.choice(string.printable))
        j = ord(out[0])
        d = ord(out[1]) % 7 + 1
        for i in range(length):
            if j > 127:
                j -= 128
            out.append(chr((ord(input_str[i]) // 16 + 32 + self.lf_key[j]) & 0xFF))
            out.append(chr((ord(input_str[i]) % 16 + 32 + self.lf_key[j]) & 0xFF))
            j += d
        out.append('\0')
        return ''.join(out)

    def lora_add_header(self, input_str, length, para):
        self._lastSendId += 1
        return self.lora_add_header_ret(input_str, length, para, self._lastSendId)

    def lora_add_header_ret(self, input_str, length, para, msg_id):
        # Criação do buffer auxiliar com o cabeçalho
        aux = f"{self._myAddr:02X}{para:02X}{msg_id:02X}{length + 10:04X}"
        # Completa com a mensagem de entrada
#        aux += input_str.decode('utf-8')
        aux += input_str
        # Retorna a mensagem com o cabeçalho
#        return aux.encode('utf-8')
        return aux
    
    def lora_decode(self, encoded_str, length):
        out = []
        j = ord(encoded_str[0])
        d = ord(encoded_str[1]) % 7 + 1
        l = length // 2 - 1
        for i in range(l):
            if j > 127:
                j -= 128
            a1 = ord(encoded_str[i * 2 + 2]) - 32 - self.lf_key[j]
            a2 = ord(encoded_str[i * 2 + 3]) - 32 - self.lf_key[j]
            a3 = a1 * 16 + a2
            if a3 < 32 or a3 > 126:
                return False,  ''.join(out)
            out.append(chr(a3))
            j += d
        return True, ''.join(out)

    def lora_check_msg_ini(self, input_str, length):
        out = []

        for i in range(10):
            try:
                char = input_str[i:i+1].decode('utf-8')  # Decodifica um único byte
                if char not in "0123456789ABCDEFabcdef":
                    return self.MSG_CHECK_ERROR, 0, 0, out
            except UnicodeDecodeError:
                return self.MSG_CHECK_ERROR, 0, 0, out

        de = int(input_str[0:2].decode('utf-8'), 16)
        para = int(input_str[2:4].decode('utf-8'), 16)
        id = int(input_str[4:6].decode('utf-8'), 16)
        len_in_msg = int(input_str[6:10].decode('utf-8'), 16)

        if len_in_msg != length:
            return self.MSG_CHECK_ERROR, 0, 0, out

        out = input_str[10:]
        self._lastRegRec = RegRec(de, para, id)

        index = self.find_reg_rec(de, para)
        if index == -1:
            self.add_reg_rec(de, para, id)
        else:
            if self._regRecs[index].id == id:
                return self.MSG_CHECK_ALREADY_REC, de, para, out
            self._regRecs[index].id = id

        return self.MSG_CHECK_OK, de, para, out

    def lora_check_msg_ini_old(self, input_str, length):
        out = []
        success, decoded_str = self.lora_decode(input_str, length)
        if not success:
            return self.MSG_CHECK_ERROR, 0, 0, ''.join(out)

        aux = decoded_str
        for i in range(10):
            if not aux[i].isdigit() and not aux[i].isalpha():
                return self.MSG_CHECK_ERROR, 0, 0, ''.join(out)

        de = int(aux[0:2], 16)
        para = int(aux[2:4], 16)
        id = int(aux[4:6], 16)
        len_in_msg = int(aux[6:10], 16)

        if len_in_msg != length // 2 - 1:
            return self.MSG_CHECK_ERROR, 0, 0, ''.join(out)

        out = aux[10:]
        self._lastRegRec = RegRec(de, para, id)

        index = self.find_reg_rec(de, para)
        if index == -1:
            self.add_reg_rec(de, para, id)
        else:
            if self._regRecs[index].id == id:
                return self.MSG_CHECK_ALREADY_REC, de, para, ''.join(out)
            self._regRecs[index].id = id

        return self.MSG_CHECK_OK, de, para, ''.join(out)

    def lora_check_msg(self, input_str, length):
        out = []
        result, de, para, out = self.lora_check_msg_ini(input_str, length)
        if result != self.MSG_CHECK_OK:
            return result, out
        if para != self._myAddr:
            return self.MSG_CHECK_NOT_ME, out
        if de != self._myMasterAddr:
            return self.MSG_CHECK_NOT_MASTER, out
        return self.MSG_CHECK_OK, out

    def lora_check_msg_master(self, input_str, length):
        out = []
        result, de, para, out = self.lora_check_msg_ini(input_str, length)
        if result != self.MSG_CHECK_OK:
            return result, out
        if para != self._myAddr:
            return self.MSG_CHECK_NOT_ME, out
        return self.MSG_CHECK_OK, out


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

