import subprocess
import json
import uuid
import os

zerotier_cli_path = os.path.join(os.getcwd(), 'zt', 'zerotier-one_x64.exe')  # Caminho relativo
zerotier_cli_path = str(zerotier_cli_path)+" -q"

class ZeroTierManager:
    """
    Gerencia a conexão com o ZeroTier e retorna o IP na rede virtual.
    """
    def __init__(self, network_id):
        self.network_id = network_id

    def join_network(self):
        """
        Conecta o dispositivo à rede ZeroTier.
        """
        #global zerotier_cli_path
        print(zerotier_cli_path)
        command = f'{zerotier_cli_path} join {self.network_id}'
        try:
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"Conectado à rede ZeroTier {self.network_id}.")
        except subprocess.CalledProcessError as e:
            print(f"Erro ao conectar à rede: {e}")

    def leave_network(self):
        """
        Remove o dispositivo da rede ZeroTier.
        """
        command = f'{zerotier_cli_path} leave {self.network_id}'
        try:
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"Removido da rede ZeroTier {self.network_id}.")
        except subprocess.CalledProcessError as e:
            print(f"Erro ao sair da rede: {e}")

    def get_ip(self):
        """
        Obtém o IP privado do cliente na rede ZeroTier.
        """
        command = f'{zerotier_cli_path} listnetworks'
        try:
            result = subprocess.run(
                command, shell=True, check=True, capture_output=True, text=True
            )
            networks = result.stdout.splitlines()
            for line in networks:
                if self.network_id in line:
                    # O IP geralmente aparece após a string da rede
                    print(line)
                    ip = line.split()[8]
                    ip = str(ip).split("/")[0]
                    print(f"IP ZeroTier: {ip}")
                    return ip
            print("Rede não encontrada ou cliente desconectado.")
            return None
        except subprocess.CalledProcessError as e:
            print(f"Erro ao obter o IP: {e}")
            return None


class RoomManager:
    """
    Gerencia as salas e associa os IPs ZeroTier a elas.
    """
    def __init__(self):
        self.rooms = {}  # Estrutura: { room_id: [ { 'client_id': id, 'ip': ip } ] }

    def create_room(self, room_id=None):
        """
        Cria uma nova sala com um ID único ou especificado.
        """
        room_id = room_id or str(uuid.uuid4())  # Gera um ID único se não for fornecido
        self.rooms[room_id] = []
        print(f"Sala criada: {room_id}")
        return room_id

    def join_room(self, room_id, client_id, ip):
        """
        Adiciona um cliente à sala.
        """
        if room_id not in self.rooms:
            print(f"Sala {room_id} não encontrada.")
            return False
        self.rooms[room_id].append({'client_id': client_id, 'ip': ip})
        print(f"Cliente {client_id} (IP: {ip}) entrou na sala {room_id}.")
        return True

    def get_peers(self, room_id, client_id):
        """
        Retorna os peers conectados na mesma sala (exceto o próprio cliente).
        """
        if room_id not in self.rooms:
            print(f"Sala {room_id} não encontrada.")
            return []
        peers = [peer for peer in self.rooms[room_id] if peer['client_id'] != client_id]
        return peers