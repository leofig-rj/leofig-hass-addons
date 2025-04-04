import os
import yaml
import logging
import json

class DeviceManager:
    def __init__(self):
        self.data_path = None
        self.config_file_path = None

        # Carrega as opções configuradas no addon
        with open("/data/options.json") as config_file:
            options = json.load(config_file)

        # Acessa o caminho configurado
        self.data_path = options.get("data_path", "/config/lora2mqtt")
        self.config_file_path = f"{self.data_path}/config.yaml"

        # Verifica se o arquivo existe, caso contrário, cria um arquivo vazio
        if not os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, "w") as arquivo_yaml:
                    yaml.dump({"devices": []}, arquivo_yaml)
            except OSError as e:
                logging.error(f"Erro ao criar o arquivo: {e}")
                logging.error("Certifique-se de que o diretório possui permissões de gravação.")


    def load_devices(self):
        """Carrega todos os dispositivos do arquivo config.yaml."""
        with open(self.config_file_path, "r") as arquivo_yaml:
            return yaml.safe_load(arquivo_yaml).get("devices", [])

    def save_devices(self, devices):
        """Salva os dispositivos no arquivo config.yaml."""
        with open(self.config_file_path, "w") as arquivo_yaml:
            yaml.dump({"devices": devices}, arquivo_yaml, default_flow_style=False)

    def add_device(self, device):
        """Adiciona um novo dispositivo ao arquivo."""
        devices = self.load_devices()
        devices.append(device)
        self.save_devices(devices)
        logging.debug(f"Dispositivo adicionado: {device}")

    def find_device_by_id(self, id_device):
        """Busca um dispositivo específico pelo ID."""
        devices = self.load_devices()
        for device in devices:
            if device["id"] == id_device:
                return device
        return None

    def delete_device_by_id(self, id_device):
        """Exclui um dispositivo específico pelo ID."""
        devices = self.load_devices()
        devices_filtered = [
            device for device in devices if device["id"] != id_device
        ]
        self.save_devices(devices_filtered)
        logging.debug(f"Dispositivo com ID '{id_device}' excluído com sucesso!")

    def list_devices(self):
        """Lista todos os dispositivos cadastrados."""
        devices = self.load_devices()
        if devices:
            for device in devices:
                logging.info(f"ID: {device['id']}, Modelo: {device['model']}, "
                      f"Chip: {device['chip']}, Fabricante: {device['manufacturer']}, "
                      f"Serial: {device['serial']}, Versão: {device['version']}, "
                      f"Nome: {device['friendly_name']}, Endereço: {device['address']}")
        else:
            logging.info("Nenhum dispositivo cadastrado.")
