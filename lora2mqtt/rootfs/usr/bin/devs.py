import os
import yaml
import logging
import importlib

import funcs
import globals

class Model:
    def __init__(self, model_name="", model_obj=None):
        self.model_name = model_name
        self.model_obj = model_obj

    def pega_obj(name):
        try:
            # Importa dinamicamente o módulo correspondente em dispositivos
            module_name = f"models.{funcs.slugify(name)}"
            module = importlib.import_module(module_name)

            # Obtém a classe com o nome esperado (DeviceXX)
            class_name = f"Device{name}"
            cls = getattr(module, class_name)

            # Crio uma instância
            obj = cls()

            return obj

        except ModuleNotFoundError:
            logging.error(f"Erro: O módulo '{name}' não foi encontrado.")
            return None
        except AttributeError:
            logging.error(f"Erro: A classe 'Dev{name}' não foi encontrada no módulo.")
            return None
        except Exception as e:
            logging.error(f"Erro inesperado: {e}") 
            return None

class DeviceRAM:
    def __init__(self, slaveIndex=0, slaveAddr=0, slaveName="", slaveSlug="", slaveMac="", slaveVer="", slaveChip="", \
                 slaveModel="", slaveMan="", slaveObj=None):
        self.slaveIndex = slaveIndex
        self.slaveAddr = slaveAddr
        self.slaveName = slaveName
        self.slaveSlug = slaveSlug
        self.slaveMac = slaveMac
        self.slaveVer = slaveVer
        self.slaveChip = slaveChip
        self.slaveModel = slaveModel
        self.slaveMan = slaveMan
        self.slaveObj = slaveObj
        self.loraTimeOut = 0
        self.loraCom = False
        self.loraRSSI = 0
        self.loraLastTimeOut = 0
        self.loraLastCom = False
        self.loraLastRSSI = -1
        logging.debug(f"Addr: {self.slaveAddr}, Name: {self.slaveName}, "
                      f"Mac: {self.slaveMac}, Vesion: {self.slaveVer}, "
                      f"Chip: {self.slaveChip}, Model: {self.slaveModel}, "
                      f"Manuf: {self.slaveMan}, Obj: {self.slaveObj}")
        
class DeviceManager:
    def __init__(self):
        self.data_path = None
        self.config_file_path = None
        self.dev_rams = []
        self.models = []

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

    def load_devices_to_ram(self):
        """Carrega todos os dispositivos cadastrados na DeviceRAM."""
        devices = self.load_devices()
        self.dev_rams.clear()
        i = 0
        if devices:
            for device in devices:
                # Vejo se friendly_name foi definido
                name = device['friendly_name']
                if funcs.is_empty_str(name):
                    name = device['id']
                # Defino o slug do nome
                slug = funcs.slugify(name)
                # Vejo se o modelo existe no sistema
                model = self.get_model(device['model'])
                obj = None
                if model:
                    obj = model.model_obj
                logging.info(f"DEVICE {device['address']} {name} {slug} {device['mac']} {obj.ver} " \
                              f"{obj.chip} {device['model']} {obj.man} {obj}")
                self.dev_rams.append(DeviceRAM(i, device['address'], name, slug, device['mac'], obj.ver, \
                                               obj.chip, device['model'], obj.man, obj))
                i = i + 1
        else:
            logging.debug("Nenhum dispositivo cadastrado.")
    
    def get_dev_rams(self):
        return self.dev_rams

    def get_model(self, modelo):
        # Procuro o modelo em self.models
        for i in range(len(self.models)):
            if self.models[i].model_name == modelo:
                return self.models[i]
        # Não achou, tento criar
        obj = Model.pega_obj(modelo)
        if obj:
            model = Model(modelo, obj)
            self.models.append(model)
            return model

        return None

    def find_device_by_name(self, name):
        """Busca um dispositivo específico pelo slug."""
        for i in range(len(self.dev_rams)):
            if name == self.dev_rams[i].slaveName:
                return i
        return None

