import logging
import devs

##### TESTE DE DeviceManager ######
# Apenas como referência não está no sistema
gerenciador = devs.DeviceManager()

# Lista todos os dispositivos
logging.debug("Dispositivos cadastrados:")
gerenciador.list_devices()

# Busca um dispositivo específico
id_para_buscar = "12345"
dispositivo = gerenciador.find_device_by_id(id_para_buscar)
if dispositivo:
    logging.debug(f"Dispositivo encontrado: {dispositivo}")
else:
    logging.debug(f"Dispositivo com ID '{id_para_buscar}' não encontrado.")

novo_dispositivo = {
    "id": "12345",
    "model": "ZX-900",
    "chip": "ESP32",
    "manufacturer": "TechCorp",
    "serial": "SN-0012345",
    "version": "1.0.0",
    "friendly_name": "Sensor de Temperatura",
    "address": 4
}

# Adicionando o novo dispositivo
gerenciador.add_device(novo_dispositivo)

# Lista todos os dispositivos
logging.debug("Dispositivos cadastrados:")
gerenciador.list_devices()

# Exclui um dispositivo
id_para_excluir = "12345"
gerenciador.delete_device_by_id(id_para_excluir)   

# Lista todos os dispositivos
logging.debug("Dispositivos cadastrados:")
gerenciador.list_devices()

# Busca um dispositivo específico
id_para_buscar = "234567890123"
dispositivo = gerenciador.find_device_by_id(id_para_buscar)
if dispositivo:
    logging.debug(f"Dispositivo encontrado: {dispositivo}")
else:
    logging.debug(f"Dispositivo com ID '{id_para_buscar}' não encontrado.")

##### FIM  - TESTE DE DeviceManager ######

