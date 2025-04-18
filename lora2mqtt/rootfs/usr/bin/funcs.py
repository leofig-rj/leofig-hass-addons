import time
import json

import globals

from consts import LORA_COM_NAME

# Funções Auxiliares
def last4(s):
    """
    Retorna os últimos 4 caracteres de uma string, começando do índice 8.
    """
    return s[8:]

def slugify(text):
    """Converte um texto em formato 'slug' (substitui espaços por _ e coloca tudo em minúsculas)."""
    return text.lower().replace(' ', '_')

def name_com_lora(index):
    """Retorna o nome básico para um dispositivo LoRa."""
    return LORA_COM_NAME

def slug_com_lora(index):
    """Retorna o nome slugificado de um dispositivo LoRa."""
    return slugify(name_com_lora(index))

def millis():
    return int(time.time() * 1000)

def get_delta_millis(tempo_anterior):
    auxMillis = int(time.time() * 1000)
    if auxMillis < tempo_anterior:
        return (auxMillis + 0xFFFFFFFF) - tempo_anterior
    return auxMillis - tempo_anterior

def char_to_byte(c):
    return ord(c) - ord('0')

def char_to_on_off(c):
    return "ON" if c == '1' else "OFF"

def char_to_state(c):
    ret = {"state": "OFF"}
    if c == '1':
        ret = {"state": "ON"}
    return json.dumps(ret)       # Serializa o JSON em uma string

def light2Pay(state, brightness=None, r=None, g=None, b=None):
    data = {}
    data["state"] = state
    if brightness is not None:
        data["brightness"] = brightness
    if (r is not None) and (g is not None) and (b is not None):
        data["color"] = {"r": r, "g": g, "b": b}
    return json.dumps(data)       # Serializa o JSON em uma string

def pay2Light(pay):
    data = json.loads(pay)
    state = data.get('state')
    brightness = data.get('brightness')
    color = data.get('color')
    r = None
    g = None
    b = None
    if color is not None:
        r = color.get('r')
        g = color.get('g')
        b = color.get('b')
    return state, brightness, r, g, b

def bool_to_on_off(b):
    return "ON" if b else "OFF"

def is_empty_str(string):
    return string == ""

def get_index_from_addr(addr):
    ram_devs = globals.g_devices.get_ram_devs()
    if len(ram_devs)==0:
        return None
    for i in range(len(ram_devs)):
        if ram_devs[i].slaveAddr == addr:
            return i
    return None
