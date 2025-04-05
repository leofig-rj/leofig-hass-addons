import serial
import paho.mqtt.client as mqtt
import logging
import json
import os
import time
import getopt
import sys

import yaml

import lflora
import msgs
import devs
import funcs
import globals

from broker import LoRa2MQTTClient

from consts import MSG_CHECK_OK, ADDON_NAME, ADDON_SLUG, VERSION, UINQUE, OWNER, HA_PREFIX, LWT_MSG, LWT_QOS, \
    LWT_REATAIN, MQTT_KEEP_ALIVE, MQTT_CLIENT_ID, EC_DIAGNOSTIC, DEVICE_CLASS_RESTART

########### MAIN ############
def main(broker, port, broker_user, broker_pass):
    usb_id = "Desconhecido"

    # Carrega as opções configuradas no addon
    with open("/data/options.json") as config_file:
        options = json.load(config_file)

    max_threads = options.get("max_threads", 200)
    logging.debug(f"max_threads: {max_threads}")
    serial_obj = options.get("serial", {"port": "/dev/ttyACM0"})
    logging.debug(f"serial_obj: {serial_obj}")
    data_path = options.get("data_path", "/config/lora2mqtt")
    logging.debug(f"data_path: {data_path}")

    # Inicializa variáveis globais
    globals.devices = devs.DeviceManager()
    globals.devices.load_devices_to_ram()


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

    try:
        # Configurando conexão serial
        ser = serial.Serial(serial_obj["port"], 115200)
        ser.flush()

    except serial.SerialException as e:
        ser = None  # Define como None para evitar problemas futuros
        logging.error(f"Erro {e} na configuração serial...")

    try:
        
       if ser:
            # Envio comando de solicitação de estado da dongue
            ser.write("!000".encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
            logging.debug("Enviado comando solicita estado do adaptador")
            time.sleep(2)  # Aguarda 2 segundos
            # Verifico se tem dado na serial
            if ser.in_waiting > 0:
                # Pegando o dado e deixando como string
                serial_data = ser.readline().decode('utf-8').strip()
                # Tratando o dado
                if serial_data[0] == '!':
                    usb_id = serial_data[1:]
                    logging.debug(f"Recebeu do adaptador: {usb_id}")

            client = LoRa2MQTTClient("/dev/ttyUSB0", 
                                        broker, 
                                        port, 
                                        usb_id, 
                                        broker_user, 
                                        broker_pass) 
            
            # Torno o cliente global
            globals.client_mqtt = client
            
            lf_lora = lflora.LFLoraClass()
            lf_lora.set_my_addr(1)

            client.mqtt_connection()
            client.loop_start()  # Inicia o loop MQTT em uma thread separada
            client.send_connectivity_discovery()
            client.send_bridge_button_discovery("Reset ESP", EC_DIAGNOSTIC, DEVICE_CLASS_RESTART)

            contador = 0

            while True:
                # Verifico se tem dado na serial
                if ser.in_waiting > 0:
                    # Pegando o dado e deixando como string
                    serial_data = ser.readline().decode('utf-8').strip()
                    # Tratando o dado
                    result, de, para, msg = lf_lora.lora_check_msg_ini(serial_data)
                    logging.debug(f"Recebido result: {result} de: {de} para: {para} msg: {msg}")
                    # Trato a mensagem
                    if result == MSG_CHECK_OK:
                        # Publicando a msg limpa
                        data_to_publish = f"Dado recebido: {msg}"
                        client.send_message("lora2mqtt/dados", data_to_publish)
                        # Tratando a msg conforme remetente
                        index = funcs.get_index_from_addr(de)
                        msgs.on_lora_message(msg, index)

    
                if funcs.pega_delta_millis(msgs.loraCommandTime) > msgs.LORA_TEMPO_REFRESH:
                    msgs.loraCommandTime = int(time.time() * 1000)

                    # Envio comando de solicitação de estado
                    serial_data = lf_lora.lora_add_header("000", contador + 2)
                    ser.write(serial_data.encode('utf-8'))    # Enviar uma string (precisa ser em bytes)
                    logging.debug(f"Enviado {serial_data}")

                    contador = (contador + 1) % 2

    except Exception as e:
        logging.error(f"Erro: {e}")
    finally:
        logging.error("Encerrando aplicação LoRa2MQTT...")
        ser.close()
        client.loop_stop()
        client.disconnect()

if __name__ == '__main__':
    broker = 'localhost'
    port = 1883
    broker_user = None
    broker_pass = None
    loglevel = 'INFO'

    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]
    short_options = 'b:p:u:P'
    long_options = ['broker=', 'port=', 'user=',
                    'Pass=']
    try:
        arguments, values = getopt.getopt(
            argument_list, short_options, long_options)
    except getopt.error:
        raise ValueError('Invalid parameters!')

    for current_argument, current_value in arguments:
        if funcs.is_empty_str(current_value):
            pass
        elif current_argument in ("-b", "--broker"):
            broker = current_value
        elif current_argument in ("-p", "--port"):
            port = int(current_value)
        elif current_argument in ("-u", "--user"):
            broker_user = current_value
        elif current_argument in ("-P", "--Pass"):
            broker_pass = current_value

    # Carregar as opções do add-on
    with open('/data/options.json') as options_file:
        options = json.load(options_file)

    log_level = options.get('log_level', 'INFO').upper()

    # Configurar o logger
    logging.basicConfig(level=getattr(logging, log_level), datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] LoRa2MQTT: %(message)s', )
    
    logger = logging.getLogger(__name__)
    logger.info("Nível de logging configurado para: %s", log_level)  
    logger.debug(f"Options: {broker}, {port}, {broker_user}, {broker_pass}")
    
    main(broker, port, broker_user, broker_pass)

