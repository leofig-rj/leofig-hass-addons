import os
import yaml
import logging
import json

class DispositivoManager:
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
                    yaml.dump({"dispositivos": []}, arquivo_yaml)
            except OSError as e:
                logging.info(f"Erro ao criar o arquivo: {e}")
                logging.info("Certifique-se de que o diretório possui permissões de gravação.")


    def carregar_dispositivos(self):
        """Carrega todos os dispositivos do arquivo config.yaml."""
        with open(self.config_file_path, "r") as arquivo_yaml:
            return yaml.safe_load(arquivo_yaml).get("dispositivos", [])

    def salvar_dispositivos(self, dispositivos):
        """Salva os dispositivos no arquivo config.yaml."""
        with open(self.config_file_path, "w") as arquivo_yaml:
            yaml.dump({"dispositivos": dispositivos}, arquivo_yaml, default_flow_style=False)

    def adicionar_dispositivo(self, dispositivo):
        """Adiciona um novo dispositivo ao arquivo."""
        dispositivos = self.carregar_dispositivos()
        dispositivos.append(dispositivo)
        self.salvar_dispositivos(dispositivos)
        logging.info(f"Dispositivo adicionado: {dispositivo}")

    def buscar_dispositivo_por_id(self, id_dispositivo):
        """Busca um dispositivo específico pelo ID."""
        dispositivos = self.carregar_dispositivos()
        for dispositivo in dispositivos:
            if dispositivo["id"] == id_dispositivo:
                return dispositivo
        return None

    def excluir_dispositivo_por_id(self, id_dispositivo):
        """Exclui um dispositivo específico pelo ID."""
        dispositivos = self.carregar_dispositivos()
        dispositivos_filtrados = [
            dispositivo for dispositivo in dispositivos if dispositivo["id"] != id_dispositivo
        ]
        self.salvar_dispositivos(dispositivos_filtrados)
        logging.info(f"Dispositivo com ID '{id_dispositivo}' excluído com sucesso!")

    def listar_dispositivos(self):
        """Lista todos os dispositivos cadastrados."""
        dispositivos = self.carregar_dispositivos()
        if dispositivos:
            for dispositivo in dispositivos:
                logging.info(f"ID: {dispositivo['id']}, Modelo: {dispositivo['modelo']}, "
                      f"Fabricante: {dispositivo['fabricante']}, Serial: {dispositivo['serial']}")
        else:
            logging.info("Nenhum dispositivo cadastrado.")
