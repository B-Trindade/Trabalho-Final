"""
Implementation of DNS server
"""

import random as rand
import socket
import threading
import sys
import time
import select as s
import dnslib as dns
import pickle
from utils import *

CMD_END = 'end'
CMD_LIST_SUBDOMAINS = 'ls'
CMD_LIST_HOSTS = 'lh'
TIMEOUT = 3

def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

class DNSserver():
    """
    A server must register either a Host process or a Server process:
        - a HOST will provide a pair (hostname, PID)
        - a SERVER will provide a pair (dns, PID)
    The lookup after no ENTRY is found is implemented by the RESOLVER.
    """

    def __init__(self) -> None:
        self.ip = 'localhost' # restringe para processos internos por eficiencia
        self.port = rand.randint(53000, 53999)
        
        self.domain = input('Entre com o nome do domínio (para root use "."): ')
        if self.domain != '.':
            parent_ip = 'localhost' # input('Entre com o endereço IPv4 do server pai: ')
            parent_port = input('Entre com a porta do server pai: ')
            self.parent_addr = (parent_ip, int(parent_port))
        else:
            self.parent_addr = None

        self.hosts = {}
        self.subdomains = {}

        # starts the server socket using UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        # select entry points
        self.entry_points = [self.socket, sys.stdin]

        self.lock = threading.Lock()
        pass

    def __enter__(self):
        return self

    def register_in_parent(self):
        data = RegisterMsg(TypeEnum.SERVER, self.domain)
        self.socket.sendto(pickle.dumps(data), self.parent_addr)
        try:
            self.socket.settimeout(TIMEOUT)
            data, _ = self.socket.recvfrom(1024)
            self.socket.settimeout(None)
            result = pickle.loads(data)
            if not result.success:
                print('Não foi possível registrar o server.')
                if result.error_text:
                    print(result.error_text)
                print('Encerrando execução...')
                exit()
            else:
                print(f'Server "{self.domain}" registrado com sucesso!')
        except socket.timeout:
            print('O servidor não respondeu dentro do tempo esperado. '
                'Tente novamente mais tarde.\n'
                'Encerrando execução...')
            exit()
        except Exception as e:
            print('Algo inesperado ocorreu e não foi possível registrar o host.')
            print(e)
            print('Encerrando execução...')
            exit()

    def start(self):
        print('\n===================================================')
        print(f'Server hospedado em: "{self.ip}:{self.port}".')
        print(f'Domínio: {self.domain}')
        print('===================================================\n')

        #self.socket.setblocking(False)
        try:
            if self.parent_addr is not None:
                self.register_in_parent()
            while True:
                r, w, x = s.select(self.entry_points, [], [])

                for ready in r:
                    if ready == self.socket:
                        msg, addr = self.receiveMessage()

                        if type(msg) == RegisterMsg:
                            reg = self.registerHandler(msg, addr)
                            reg.join()
                        else:
                            #TODO: treat client with response
                            pass
                    elif ready == sys.stdin:
                        cmd = input()
                        print('server> ' + cmd)
                        if cmd == CMD_END:
                            self.socket.close()
                        elif cmd == CMD_LIST_HOSTS:
                            print(self.hosts)
                        elif cmd == CMD_LIST_SUBDOMAINS:
                            print(self.subdomains)
                        #TODO: HANDLE COMMANDS
        except Exception as e:
            print('Servidor encerrado.', e)
        pass
    
    def receiveMessage(self):
        # get incoming conn's node type and return
        data, addr = self.socket.recvfrom(1024)

        data = pickle.loads(data)

        return data, addr

    @threaded
    def registerHandler(self, msg: RegisterMsg, addr):
        self.lock.acquire()
        if msg.type == TypeEnum.HOST:
            self.hosts[msg.name] = addr
            result = RegisterResultMsg(True)
            self.socket.sendto(pickle.dumps(result), addr)
        elif msg.type == TypeEnum.SERVER:
            self.subdomains[msg.name] = addr
            result = RegisterResultMsg(True)
            self.socket.sendto(pickle.dumps(result), addr)
        self.lock.release()

        print(f'Novo {msg.type.value} registrado:')
        print(f'{msg.name} => {addr}')

    def generateResponse():
        pass

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.socket.close()
        pass

    def __del__(self) -> None:
        self.socket.close()
        pass

def main():

    with DNSserver() as server:
        server.start()

if __name__ == '__main__':
    main()