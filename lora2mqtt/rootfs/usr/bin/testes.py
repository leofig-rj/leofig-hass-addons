import logging
import devs
import os
import json

import yaml

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

#####  TESTES DE ACESSO A PASTAS DO HA

# Carrega as opções configuradas no addon
with open("/data/options.json") as config_file:
    options = json.load(config_file)


data_path = options.get("data_path", "/config/lora2mqtt")
logging.debug(f"data_path: {data_path}")


# Verifica se a pasta existe
try:
    if os.path.exists(data_path) and os.path.isdir(data_path):
        logging.debug(f"Pasta encontrada: {data_path}")
        # Listar arquivos, por exemplo:
        arquivos = os.listdir(data_path)
        logging.debug(f"Arquivos na pasta: {arquivos}")
        arquivos = [arquivo for arquivo in os.listdir(data_path) if arquivo.endswith(".py")]
        logging.debug(f"Arquivos Python encontrados: {arquivos}")
    else:
        logging.error(f"O caminho não é uma pasta válida: {data_path}")
except PermissionError:
    logging.error("Erro: Permissão negada para acessar a pasta.")




config_file_path = "/config/lora2mqtt/teste.yaml"

# Verifica se o arquivo existe, caso contrário, cria um arquivo vazio
if not os.path.exists(config_file_path):
    try:
        with open(config_file_path, "w") as arquivo_yaml:
            yaml.dump({"devices": []}, arquivo_yaml)
    except OSError as e:
        logging.error(f"Erro ao criar o arquivo: {e}")
        logging.error("Certifique-se de que o diretório possui permissões de gravação.")

