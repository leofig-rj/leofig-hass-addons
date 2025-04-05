import os
import yaml
import logging

import funcs
import globals
import pw01
import lz01

class DeviceRamManager:
    def __init__(self):
        # Inicializa a lista vazia
        self.list = []

    def add(self, item):
        """Adiciona um novo item à lista."""
        self.list.append(item)
        print(f"Item '{item}' adicionado!")

    def delete(self, item):
        """Exclui um item específico da lista."""
        if item in self.list:
            self.list.remove(item)
            print(f"Item '{item}' excluído!")
        else:
            print(f"Item '{item}' não encontrado na lista.")

    def listar(self):
        """Lista todos os itens da lista."""
        if self.list:
            print("Itens na lista:")
            for i, item in enumerate(self.list, 1):
                print(f"{i}. {item}")
        else:
            print("A lista está vazia.")

    def buscar(self, item):
        """Busca um item específico na lista."""
        if item in self.list:
            print(f"Item '{item}' encontrado!")
            return item
        else:
            print(f"Item '{item}' não encontrado.")
            return None
    def clear(self):
        """Remove todos os itens da lista."""
        self.list.clear()
        print("A lista foi limpa com sucesso!")

class DeviceRAM:
    def __init__(self, slaveIndex=0, slaveAddr=0, slaveName="", slaveMac="", slaveVer="", slaveChip="", slaveModel="", slaveMan=""):
        self.slaveIndex = slaveIndex
        self.slaveAddr = slaveAddr
        self.slaveName = slaveName
        self.slaveMac = slaveMac
        self.slaveVer = slaveVer
        self.slaveChip = slaveChip
        self.slaveModel = slaveModel
        self.slaveMan = slaveMan
        self.slaveObj = None
        self.loraTimeOut = 0
        self.loraCom = False
        self.loraRSSI = 0
        self.loraLastTimeOut = 0
        self.loraLastCom = False
        if self.slaveIndex == 0:
            self.slaveObj = pw01.DevicePW01(self.slaveMac, self.slaveAddr, self.slaveIndex)
        if self.slaveIndex == 1:
            self.slaveObj = lz01.DevicePW01(self.slaveMac, self.slaveAddr, self.slaveIndex)
        logging.debug(f"Addr: {self.slaveAddr}, Name: {self.slaveName}, "
                      f"Mac: {self.slaveMac}, Vesion: {self.slaveVer}, "
                      f"Chip: {self.slaveChip}, Model: {self.slaveModel}, "
                      f"Manuf: {self.slaveMan}")
        
    def find_device_by_slug(self, slug_rec):
        """Busca um dispositivo específico pelo slug."""
        for i in range[len(self.slaveName)]:
            slug = funcs.slugify(self.slaveName[i])
            if slug == slug_rec:
                return i
        return None

class DeviceManager:
    def __init__(self):
        self.data_path = None
        self.config_file_path = None
        self.dev_rams = []

        # Acessa o caminho configurado
        self.data_path = globals.g_data_path
        self.config_file_path = f"{self.data_path}/config.yaml"

        # Verifica se o arquivo existe, caso contrário, cria um arquivo vazio
        if not os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, "w") as arquivo_yaml:
                    yaml.dump({"devices": []}, arquivo_yaml)
                self.load_devices_to_ram

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
                logging.debug(f"ID: {device['id']}, Modelo: {device['model']}, "
                      f"Chip: {device['chip']}, Fabricante: {device['manufacturer']}, "
                      f"Serial: {device['serial']}, Versão: {device['version']}, "
                      f"Nome: {device['friendly_name']}, Endereço: {device['address']}")
        else:
            logging.debug("Nenhum dispositivo cadastrado.")

    def load_devices_to_ram(self):
        """Carrega todos os dispositivos cadastrados na DeviceRAM."""
        devices = self.load_devices()
        self.dev_rams.clear()
        i = 0
        if devices:
            for device in devices:
                name = device['friendly_name']
                if funcs.is_empty_str(name):
                    name = device['id']
                self.dev_rams.append(DeviceRAM(i, device['address'], name, device['id'], device['version'], \
                                               device['chip'], device['model'], device['manufacturer']))
                i = i + 1
        else:
            logging.debug("Nenhum dispositivo cadastrado.")
    
    def get_dev_rams(self):
        return self.dev_rams
