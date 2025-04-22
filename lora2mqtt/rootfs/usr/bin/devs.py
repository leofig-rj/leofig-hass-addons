import shutil
import os
import yaml
import time
import logging
import importlib

import funcs
import globals

# Pegando o objeto do modelo se existir o arquivo de definição do odelo e se estiver dentro do padão
def get_model_obj(name):
    try:
        # Importa dinamicamente o módulo correspondente em dispositivos (internos)
        module_name = f"models.{funcs.slugify(name)}"
        module = importlib.import_module(module_name)

        # Obtém a classe com o nome esperado (DeviceXX)
        class_name = f"Device{name}"
        cls = getattr(module, class_name)

        # Crio uma instância
        model_obj = cls()

        return model_obj

    except ModuleNotFoundError:

        try:
            # Importa dinamicamente o módulo correspondente em dispositivos (do usuário)
            module_name = f"models_import.{funcs.slugify(name)}"
            module = importlib.import_module(module_name)

            # Obtém a classe com o nome esperado (DeviceXX)
            class_name = f"Device{name}"
            cls = getattr(module, class_name)

            # Crio uma instância
            model_obj = cls()

            return model_obj

        except ModuleNotFoundError:
            logging.error(f"Erro: O módulo '{name}' não foi encontrado.")
            return None
        except AttributeError:
            logging.error(f"Erro: A classe 'Dev{name}' não foi encontrada no módulo.")
            return None
        except Exception as e:
            logging.error(f"Erro inesperado: {e}") 
            return None
    except AttributeError:
        logging.error(f"Erro: A classe 'Dev{name}' não foi encontrada no módulo.")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado: {e}") 
        return None

class DeviceRAM:
    def __init__(self, slaveAddr=0, slaveName="", slaveSlug="", slaveMac="", slaveVer="", slaveChip="", \
                 slaveModel="", slaveMan="", slaveObj=None):
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

        # Acessando o caminho do arquivo config.yaml com os dispositivos
        self.data_path = globals.g_data_path
        self.config_file_path = f"{self.data_path}/config.yaml"

        # Verificando se a pasta raiz do addon existe, caso contrário, cria a pasta
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

        # Verificando se a pasta dos modelos do usuário existe, caso contrário, cria a pasta
        usrs_models_path = f"{self.data_path}/models"
        if not os.path.exists(usrs_models_path):
            os.makedirs(usrs_models_path)

        # Verificando se o arquivo de configuração existe, caso contrário, cria um arquivo vazio
        if not os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, "w") as arquivo_yaml:
                    yaml.dump({"devices": []}, arquivo_yaml)
                self.load_devices_to_ram

            except OSError as e:
                logging.error(f"Erro ao criar o arquivo: {e}")
                logging.error("Certifique-se de que o diretório possui permissões de gravação.")

        # Copiando os arquivos de modelos do usuário. Definindo o caminho da pasta de destino
        addon_models_path = "/usr/bin/models_import"

        # Certificando-se de que a pasta de destino existe, caso contrário, criar
        if not os.path.exists(addon_models_path):
            os.makedirs(addon_models_path)

        # Copiaando os arquivos da pasta de omodelos do usr para a pasta de destino
        for arquivo in os.listdir(usrs_models_path):
            caminho_arquivo_origem = os.path.join(usrs_models_path, arquivo)
            
            # Verificando se é um arquivo antes de copiar (ignora pastas)
            if os.path.isfile(caminho_arquivo_origem):
                shutil.copy(caminho_arquivo_origem, addon_models_path)
                logging.info(f"File {arquivo} copied to the AddOn")


    def load_devices(self):
        """Carrega todos os dispositivos do arquivo config.yaml."""
        with open(self.config_file_path, "r") as arquivo_yaml:
            return yaml.safe_load(arquivo_yaml).get("devices", [])

    def save_devices(self, devices):
        """Salva os dispositivos no arquivo config.yaml."""
        with open(self.config_file_path, "w") as arquivo_yaml:
            yaml.dump({"devices": devices}, arquivo_yaml, default_flow_style=False)

    def add_device(self, addr, name, mac, model):
        """Adiciona um novo dispositivo ao arquivo."""
        device = {
            "address": addr,
            "name": name,
            "mac": mac,
            "model": model
            }
        devices = self.load_devices()
        devices.append(device)
        self.save_devices(devices)
        logging.debug(f"Dispositivo adicionado: {device}")

    def find_device_by_mac(self, mac):
        """Busca um dispositivo específico pelo MAC."""
        devices = self.load_devices()
        for device in devices:
            if device["mac"] == mac:
                return device
        return None

    def delete_device_by_mac(self, mac):
        """Exclui um dispositivo específico pelo MAC."""
        devices = self.load_devices()
        devices_filtered = [
            device for device in devices if device["mac"] != mac
        ]
        self.save_devices(devices_filtered)
        logging.debug(f"Dispositivo com MAC '{mac}' excluído com sucesso!")

    def load_devices_to_ram(self):
        """Carrega todos os dispositivos cadastrados na DeviceRAM."""
        devices = self.load_devices()
        self.dev_rams.clear()
        if devices:
            for device in devices:
                # Vejo se name foi definido
                name = device['name']
                if funcs.is_empty_str(name):
                    name = device['mac']
                # Defino o slug do nome
                slug = funcs.slugify(name)
                # Vejo se o modelo existe no sistema
                obj = get_model_obj(device['model'])
                if obj is not None:
                    logging.info(f"DEVICE {device['address']} {name} {slug} {device['mac']} {obj.ver} " \
                                f"{obj.chip} {device['model']} {obj.man} {obj}")
                    self.dev_rams.append(DeviceRAM(device['address'], name, slug, device['mac'], obj.ver, \
                                                obj.chip, device['model'], obj.man, obj))
                else:
                    logging.debug(f"Arquivo de definição do modelo {device['model']} não OK")
        else:
            logging.debug("Nenhum dispositivo cadastrado.")
    
    def get_ram_devs(self):
        return self.dev_rams

    def find_ram_dev_by_name(self, name):
        """Busca um dispositivo da RAM específico pelo nome."""
        for i in range(len(self.dev_rams)):
            if name == self.dev_rams[i].slaveName:
                return i
        return None

    def find_ram_dev_by_mac(self, mac):
        """Busca um dispositivo da RAM específico pelo mac."""
        for i in range(len(self.dev_rams)):
            if mac == self.dev_rams[i].slaveMac:
                return i
        return None

    def get_next_ram_dev_addr(self):
        """Pega o próxiom endereço de Slave."""
        addr = 2
        i = 0
        j = len(self.dev_rams)
        while i < j:
            if addr == self.dev_rams[i].slaveAddr:
                addr = addr + 1
                i = 0
            else:
                i += 1    
        return addr

    def get_ram_dev_addr_by_mac(self, mac):
        """Pega o endereço do Slave com Mac."""
        addr = 0
        for i in range(len(self.dev_rams)):
            if mac == self.dev_rams[i].slaveMac:
                addr = self.dev_rams[i].slaveAddr
                break
        if addr == 0:
            addr = self.get_next_ram_dev_addr()
        return addr

    def delete_ram_dev(self, index):
        # Excluo da lista de slaves
        mac = self.dev_rams[index].slaveMac
        # Excluo na RAM
        self.dev_rams.remove(self.dev_rams[index])
        # Excluo no config.yaml
        self.delete_device_by_mac(mac)

    def rename_ram_dev(self, index, name):
        # Pego o addr, mac e model
        addr = self.dev_rams[index].slaveAddr
        mac = self.dev_rams[index].slaveMac
        model = self.dev_rams[index].slaveModel
        # Renomeio na RAM
        self.dev_rams[index].slaveName = name
        self.dev_rams[index].slaveSlug = funcs.slugify(name)
        # Excluo no config.yaml
        self.delete_device_by_mac(mac)
        # Excluo com novo nome no config.yaml
        self.add_device(addr, name, mac, model)

    def save_ram_dev(self, addr, model, mac):
        index = self.find_ram_dev_by_mac(mac)
        if index is not None:
            ram_dev = self.dev_rams[index]
            ram_dev.slaveAddr = addr
            # Vejo se o modelo existe no sistema
            obj = get_model_obj(model)
            if obj is not None:
                ram_dev.slaveAddr = addr
                ram_dev.slaveModel = model
                ram_dev.slaveObj = obj
                # Excluo no arquivo config.yaml
                self.delete_device_by_mac(mac)
                # Crio com nova configuração no arquivo config.yaml
                self.add_device(addr, ram_dev.slaveName, mac, model)
                return
            logging.debug(f"Arquivo de definição do modelo {model} não OK")
            return
        # Defino o nome como mac
        name = mac
        # Defino o slug do nome
        slug = funcs.slugify(name)
        # Vejo se o modelo existe no sistema
        obj = get_model_obj(model)
        if obj is not None:
            index = len(self.dev_rams)
            self.dev_rams.append(DeviceRAM(addr, name, slug, mac, obj.ver, obj.chip, model, obj.man, obj))
            # Crio no arquivo config.yaml
            self.add_device(addr, name, mac, model)
            logging.info(f"DEVICE {index} {addr} {name} {slug} {mac} {obj.ver} {obj.chip} {model} {obj.man} {obj}")
            time.sleep(0.1)
            return
        logging.debug(f"Arquivo de definição do modelo {model} não OK")
