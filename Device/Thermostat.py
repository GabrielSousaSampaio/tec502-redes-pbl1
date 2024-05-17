import socket
import threading
import time
import os


class Thermostat:

    def __init__(self, id, broker_host='0.0.0.0', initial_temperature=20, status='off',
                 broker_tcp_port=8888, broker_udp_port=9999):

        # Atributos do Termostato

        self.id = id
        self.temperature = initial_temperature
        self.status = status

        # Host e portas (broker)
        self.broker_host = broker_host
        self.broker_tcp_port = broker_tcp_port
        self.broker_udp_port = broker_udp_port

        # Conexão com o broker TCP E UDP
        self.connect_to_broker_tcp()
        self.conncet_to_broker_udp()

        # Inicia a função para ficar enviado os status via UDP
        self.send_data_via_udp()

        # Inicia a thread para receber as menssagens via tcp
        self.receive_thread = threading.Thread(target=self.recv_tcp)
        self.receive_thread.start()

    # Função para se conectar com o broker via tcp:
    def connect_to_broker_tcp(self):
        while True:
            try:

                # Tentativa de se conectar ao servidor tcp

                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Socket tcp
                self.tcp_socket.connect((self.broker_host, self.broker_tcp_port))
                self.send_identification()

                print("Conectado!")

                break


            except socket.error as e:

                if hasattr(e, 'winerror') and e.winerror == 10061:
                    print("O Broker não está respondendo. Verifique se ele está funcionando.")
                    time.sleep(2)
                    print("Aguarde a conexão...")


                else:
                    print(f"Falha ao tentar se conectar com o Broker: {e}")

    # Função para se conectar com o broker via udp:
    def conncet_to_broker_udp(self):

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Socket UDP

    # Função para receber dados via tcp (comandos da aplicação via broker):
    def recv_tcp(self):

        while True:
            try:
                data = self.tcp_socket.recv(2048).decode('utf-8')

                if not data:
                    break

                print(f"TCP DATA: {data}")

                # Tratamento do dado:

                self.message_tratament(data)


            except ConnectionResetError:
                print("A conexão com o Broker foi perdida! Verifique se ele está funcionando.")
                self.connect_to_broker_tcp()


            except Exception as e:
                print(f"Falha no recebimento dos dados via TCP.{e}")
                time.sleep(2)

    # Função para enviar a identificação do dispositivo para o broker:
    def send_identification(self):

        try:

            self.tcp_socket.send(f'device-{self.get_id()}-{self.get_status()}-{self.get_temperature()}'.encode())


        except:
            return print("Não foi possível se conectar ao Broker!")

    # Função para enviar dados via udp:
    def send_udp(self, message):

        try:

            # Tenta enviar mensagem ao servidor via UDP
            self.udp_socket.sendto(message.encode(), (self.broker_host, self.broker_udp_port))


        except socket.error as e:

            print(f"Falha ao tentar enviar mensagem via UDP.")

    # Função para enviar os dados do dispositivo via udp:
    def send_data_via_udp(self):

        def enviar():
            while True:
                try:

                    actual_data = f"dispositive_data-{self.get_id()}-{self.get_status()}-{self.get_temperature()}"

                    self.send_udp(actual_data)
                    time.sleep(2)


                except Exception as e:

                    print(f"Falha ao tentar enviar mensagem via UDP.")

        # Thread para ficar enviando os dados do dispositivo de maneira continua
        thread = threading.Thread(target=enviar)
        thread.daemon = True
        thread.start()

    # Função para tratar os comandos enviados:
    def message_tratament(self, message):

        message_split = message.split('-')

        type = message_split[0]

        if type == 'HTTPcommand':

            command = message_split[2]

            if command == 'on':

                if (self.get_status() == 'off'):
                    self.set_status()

                    self.tcp_socket.send(bytes(f"accept-command-on-{self.get_status()}", "utf-8"))


            elif command == 'off':

                if (self.get_status() == 'on'):
                    self.set_status()

                    self.tcp_socket.send(bytes(f"accept-command-off-{self.get_status()}", "utf-8"))




            elif command == 'newtemp':

                new_temp = message_split[3]

                if new_temp:

                    try:
                        new_temp = int(new_temp)

                        self.set_temperature(new_temp)

                        print(f"Nova temperatura: {self.get_temperature()}°C.")

                        self.tcp_socket.send(bytes(f"accept-command-newtemp-{self.get_temperature()}", "utf-8"))


                    except ValueError:
                        print("Valor para Temperatura inválido.")


            else:
                print("Comando inválido")

    # Função que retorna o id:
    def get_id(self):

        return self.id

    # Função que retorna a temperatura:
    def get_temperature(self):
        return self.temperature

    # Função que retorna se o termostato está ligado ou desligado:
    def get_status(self):
        return self.status

    # Função que altera o valor da temperatura:
    def set_temperature(self, target_temperature):

        self.temperature = target_temperature

    # Função que altera o estado (ligado ou desligado) do termostato:
    def set_status(self):

        if self.status == 'off':

            self.status = 'on'


        else:
            self.status = 'off'


if __name__ == "__main__":
    BROKER_IP = os.getenv("BROKER_IP")

    id = int(input('Digite o id do dispositivo: '))
    thermostat = Thermostat(id, BROKER_IP)
