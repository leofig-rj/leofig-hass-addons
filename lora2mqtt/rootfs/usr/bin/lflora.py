from consts import MSG_CHECK_OK, MSG_CHECK_NOT_ME, MSG_CHECK_ALREADY_REC, MSG_CHECK_ERROR

class RegRec:
    def __init__(self, de=0, para=0, id=0):
        self.de = de
        self.para = para
        self.id = id

class LFLoraClass:

    def __init__(self):
        self._myAddr = 0
        self._lastSendId = 255
        self._regRecs = []
        self._lastRegRec = RegRec()

    def set_my_addr(self, addr):
        self._myAddr = addr

    def my_addr(self):
        return self._myAddr

    def last_reg_rec(self):
        return self._lastRegRec

    def lora_add_header(self, input_str, para):
        self._lastSendId = (self._lastSendId + 1) % 256 
        return self.lora_add_header_to(input_str, para, self._lastSendId)

    def lora_add_header_to(self, input_str, para, msg_id):
        # Criação do buffer auxiliar com o cabeçalho
        aux = f"#{self._myAddr:02X}{para:02X}{msg_id:02X}{len(input_str) + 10:04X}"
        # Completa com a mensagem de entrada
        aux += input_str
        # Retorna a mensagem com o cabeçalho
        return aux
    
    def lora_check_msg_ini(self, input_str):
        out = ""

        if input_str[0] != '#':
            return MSG_CHECK_ERROR, 0, 0, out

        for i in range(10):
            try:
                char = input_str[i+1:i+2]
                if char not in "0123456789ABCDEFabcdef":
                    return MSG_CHECK_ERROR, 0, 0, out
            except UnicodeDecodeError:
                return MSG_CHECK_ERROR, 0, 0, out

        de = int(input_str[1:3], 16)
        para = int(input_str[3:5], 16)
        id = int(input_str[5:7], 16)
        len_in_msg = int(input_str[7:11], 16)

        # input_str tem um caracter a maias (o # no início)
        if len_in_msg != len(input_str) - 1:
            return MSG_CHECK_ERROR, 0, 0, out

        out = input_str[11:]

        self._lastRegRec = RegRec(de, para, id)

        index = self.find_reg_rec(de, para)
        if index == -1:
            self.add_reg_rec(de, para, id)
        else:
            if self._regRecs[index].id == id:
                return MSG_CHECK_ALREADY_REC, de, para, out
            self._regRecs[index].id = id

        return MSG_CHECK_OK, de, para, out

    def lora_check_msg(self, input_str, length):
        out = []
        result, de, para, out = self.lora_check_msg_ini(input_str, length)
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
