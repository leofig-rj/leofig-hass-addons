import time

import globals

# Funções Auxiliares
def last4(s):
    """
    Retorna os últimos 4 caracteres de uma string, começando do índice 8.
    """
    return s[8:]

def slugify(text):
    """Converte um texto em formato 'slug' (substitui espaços por _ e coloca tudo em minúsculas)."""
    return text.lower().replace(' ', '_')

def nome_com_lora(index):
    """Retorna o nome básico para um dispositivo LoRa."""
    return "Com LoRa"  # Pode ser expandido com nomes individuais, se necessário.

def slug_com_lora(index):
    """Retorna o nome slugificado de um dispositivo LoRa."""
    return slugify(nome_com_lora(index))

def isEmptyStr(s):
    return s == 'null' or len(s) == 0 or s.isspace()

def millis():
    return int(time.time() * 1000)

def pega_delta_millis(tempo_anterior):
    auxMillis = int(time.time() * 1000)
    if auxMillis < tempo_anterior:
        return (auxMillis + 0xFFFFFFFF) - tempo_anterior
    return auxMillis - tempo_anterior

def char_to_byte(c):
    return ord(c) - ord('0')

def char_to_on_off(c):
    return "ON" if c == '1' else "OFF"

def char_to_state(c):
    return {"state": "ON"} if c == '1' else {"state": "OFF"}

def bool_to_on_off(b):
    return "ON" if b else "OFF"

def is_empty_str(string):
    return string == ""

def get_index_from_addr(addr):
    ram_devs = globals.g_devices.get_dev_rams()
    for i in range(len(ram_devs)):
        if ram_devs[i].slaveAddr == addr:
            return i
    return 255
