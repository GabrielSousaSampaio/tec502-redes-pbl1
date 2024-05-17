import socket
import threading
import time
import queue
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import *


class Broker:


   def __init__(self, host = '0.0.0.0', port_tcp = 8888, port_udp = 9999, flask_port = 5001):


       # Host e portas
       self.host = host
       self.port_tcp = port_tcp
       self.port_udp = port_udp
       self.flask_port = flask_port


       # Lista de dispositivos
       self.devices_list = []


       # Inicilizando filas para organizar menssagens
       self.udp_queue = queue.Queue()
       self.http_queue = queue.Queue()


       # Iniciando o Flask
       self.app = Flask(__name__)
       CORS(self.app)
       self.setup_flask_routes()


       # Socket TCP
       self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # SOCK_STREAM = TCP / Via que apenas aceita a comunicação
       self.bind_tcp()


       # Socket UDP
       self.socket_udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  # SOCK_DGRAM = UDP / Via que apenas aceita a comunicação
       self.bind_udp()


       self.essencial_threads()


   #Função que tenta fazer uma ligação via tcp:
   def bind_tcp(self):


       #Tento fazer uma ligação:


       try:
           self.socket_tcp.bind((self.host, self.port_tcp))
           self.socket_tcp.listen(5)   #Recebe até 5 conexões
           return


       except Exception as e:


           return print('Não foi possível iniciar a ligação via tcp.')




   # Função que tenta fazer uma ligação via udp:
   def bind_udp(self):


       try:
           self.socket_udp.bind((self.host, self.port_udp))
           return


       except Exception as e:
           return print('Não foi possível iniciar a ligação via udp.')




   # Função que aceita as conexões via tcp:
   def start_tcp_connection(self):


       #Sempre aceitando novas conexoes:


       while True:
           client_socket, client_address = self.socket_tcp.accept()


           # Indentifica se a conexão advém de um dispositivo
           self.identification(client_socket, client_address)


           # Inicia uma thread para recebimento de dados via tcp
           tcp_thread = threading.Thread(target=self.handle_tcp, args=(client_socket, client_address), daemon=True)
           tcp_thread.start()




   # Inicia uma thread para recebimento de dados via udp:
   def start_udp_connection(self):


       # O broker continua a ouvir mensagens UDP


       udp_thread = threading.Thread(target=self.handle_udp, args=(), daemon=True)
       udp_thread.start()




   # Função para identificação do cliente conectado:
   def identification(self, client_socket, client_address):


       print(f"Nova conexão: {client_address}")


       identification_msg = client_socket.recv(2048).decode('utf-8').strip()


       if identification_msg[:6] == "client":


           print(f"{client_address} é um cliente.")




       elif identification_msg[:6] == "device":


           print(f"{client_address} é um dispositivo termostato.")


           self.device_register(client_socket, client_address, identification_msg[7:])


       else:
           print(f"Não consegui identificar a conexão de {client_address}. Mensagem de identificação: {identification_msg}")
           client_socket.close()
           return  # Encerra a conexão se a identificação for desconhecida




   # Verifica continuamente se o dispositivo ainda está conectado:
   def device_confirm_conncetion(self):


       while True:


           for disp in self.devices_list:


               try:


                   disp['socket'].send(bytes("CONNECTION CONFIRMATION", 'utf-8')) # Menssagem de verificação para o dispositivo


               except Exception as e:


                   print(f"Conexão encerrada com o dispositivo: {disp['id']} > ({disp['ip']}:{disp['port']})")


                   self.devices_list.remove(disp) # Removo ele da lista de dispositivos




           time.sleep(10)  # Verificar a conexão a cada 10 segundos




   # Recebe menssagens via udp:
   def handle_udp(self):


       while True:


           try:
               data, address = self.socket_udp.recvfrom(2048)


               self.udp_queue.put((data.decode('utf-8'), address))


           except Exception as e:


               print(f"Falha ao receber mensagem via udp.")
               break


   # Recebe menssagens via tcp:
   def handle_tcp(self,client_socket, client_address):




       while True:
           try:
               # Recebe uma mensagem
               msg = client_socket.recv(2048).decode('utf-8').strip()
               print(msg)


           except Exception as e:
               if hasattr(e, 'winerror') and e.winerror == 10054:


                   print("Dispositivo desconectado!")
                   self.device_delete(self.find_device_pos_by_socket(client_socket))




               else:
                   print("Não foi possível se conectar ao Broker!")
               break


       # Fecha a conexão


       client_socket.close()
       print(f"Connection with {client_address} closed.")




   # Tratamento/interpretação dos dados enviados pelo dispositivo:
   def udp_messages_tratament(self):


       while True:


           if not self.udp_queue.empty(): # Se houver algo na fila


               # Dado e o endereço gaurdados na fila


               data, address = self.udp_queue.get()


               # Interpretando o dado


               data_split = data.split('-')


               type = data_split[0]
               id = int(data_split[1])
               state = data_split[2]
               temperature = data_split[3]


               if type == "dispositive_data":


                   for disp in self.devices_list:


                       if disp["ip"] == address[0] and disp['id'] == int(id):


                           disp["state"] = state
                           disp["temperature"] = temperature


   # Tratamento/interpretação dos comandos enviados pela aplicação:
   def process_http_command(self):


       while True:


           if not self.http_queue.empty(): # Se houver algo na fila


               # Protocolo com dados do dispositivo e do comando enviado
               protocol = self.http_queue.get()


               # Interpretando o protocolo


               type = protocol[0]
               id = int(protocol[1])
               ip = protocol[2]
               command = protocol[4]
               temperature = int(protocol[5])


               # Enviar a mensagem para os dispositivos TCP conectados


               for disp in self.devices_list:


                   if type == "HTTPcommand":


                       if disp["ip"] == ip and disp['id'] == id:


                           msg = f"HTTPcommand-{id}-{command}-{temperature}"


                           disp["socket"].send(msg.encode())






   # Função para a execução das principais threads:
   def essencial_threads(self):




       # Inicia uma thread para armazenar as mensagens Udp em uma Fila
       self.udp_thread = threading.Thread(target=self.handle_udp)
       self.udp_thread.start()


       # Iniciando o servidor Flask em uma thread separada
       self.start_flask_thread = threading.Thread(target=self.start_flask, daemon=True)
       self.start_flask_thread.start()


       # Inicia um thread para confirmar conexões do dispositivo
       self.device_confirm_conn = threading.Thread(target=self.device_confirm_conncetion, daemon=True)
       self.device_confirm_conn.start()


       # Inicia uma thread para tratar as mensagens UDP
       self.udp_messages_trat = threading.Thread(target=self.udp_messages_tratament, daemon=True)
       self.udp_messages_trat.start()


       # Inicia uma thread para tratar os comandos HTTP
       self.process_http_command = threading.Thread(target=self.process_http_command, daemon=True)
       self.process_http_command.start()




   #### Funções voltadas para a manipulação dos dispositivos




   # Função que registra um novo dispositivo
   def device_register(self, client_socket, client_address, inf):
       list_info = inf.split("-")


       device = {


           "id": int(list_info[0]),
           "ip": client_address[0],
           "port": client_address[1],
           "socket": client_socket,
           "state": list_info[1],
           "temperature": list_info[2]
       }


       self.devices_list.append(device)
       print(self.devices_list)




   # Função que encontra posição de um dispositivo pelo socket
   def find_device_pos_by_socket(self, socket):


       for disp in self.devices_list:


          if disp['socket'] == socket:
              return self.devices_list.index(disp)




   # Função que remove um dispositivo pela posição
   def device_delete(self, pos):


       del self.devices_list[pos]
       print("Dispositivo removido com sucesso!")






   ### Função para designar as rotas para a API
   def setup_flask_routes(self):




       # Função que retorna a lista com os dispositivos
       @self.app.route('/get-devices', methods=['GET'])
       def get_devices():


           try:
               dev_list = []


               for device in self.devices_list:


                   dev = {


                       "id": device["id"],
                       "ip": device["ip"],
                       "port": device["port"],
                       "state": device["state"],
                       "temperature": device["temperature"]


                   }


                   dev_list.append(dev)


               return jsonify({"success": True, "devices": dev_list}), 200


           except Exception as e:


               return jsonify({"success": False, "message": str(e)}), 500




       # Função para envio de comandos
       @self.app.route("/send-command", methods=["POST"])


       def send_command():


           try:
               data = request.json
               message = data.get("message")


               if message is None:
                   return jsonify({"success": False, "message": "Comando não recebido."}), 400


               command_split = message.split("-")




               # Coloca a mensagem na fila de mensagens HTTP
               self.http_queue.put(command_split)


               type= command_split[0]
               command = command_split[4]


               if type == "HTTPcommand":


                   if command != "on" and command != "off" and command != "newtemp":
                       return jsonify({"success": False, "message": "Comando inválido"}), 400
                   else:
                       return jsonify({"success": True, "message": "Comando enviado com sucesso."}), 200


           except Exception as e:


               return jsonify({"success": False, "message": str(e)}), 500


   #Função para startar o servidor flask
   def start_flask(self):
       self.app.run(host='0.0.0.0', port=self.flask_port)


def main():


   broker = Broker()
   broker.start_tcp_connection()
   broker.start_udp_connection()




if __name__ == '__main__':


   main()
