import socket
import pyaudio
import threading

# Configurações de áudio
CHUNK = 1024  # Tamanho do buffer
FORMAT = pyaudio.paInt16  # Formato de áudio
CHANNELS = 1  # Mono
RATE = 44100  # Taxa de amostragem

class VoipRoom:
    def __init__(self, LOCAL_IP="0.0.0.0", LOCAL_PORT=5000, REMOTE_IP="127.0.0.1", REMOTE_PORT=5000):
        # Configurações de rede
        self.LOCAL_IP = LOCAL_IP
        self.LOCAL_PORT = LOCAL_PORT
        self.REMOTE_IP = REMOTE_IP
        self.REMOTE_PORT = REMOTE_PORT

        # Inicialização de áudio
        self.audio = pyaudio.PyAudio()

        # Fluxos de entrada (microfone) e saída (alto-falante)
        self.input_stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        self.output_stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

        # Socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.LOCAL_IP, self.LOCAL_PORT))

        # Threads para enviar e receber áudio
        self.running = True
        self.send_thread = threading.Thread(target=self.send_audio)
        self.receive_thread = threading.Thread(target=self.receive_audio)

    # Função para enviar áudio
    def send_audio(self):
        while self.running:
            try:
                # Captura áudio do microfone
                data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                # Envia para o IP e porta remotos
                self.sock.sendto(data, (self.REMOTE_IP, self.REMOTE_PORT))
            except Exception as e:
                print(f"Erro no envio de áudio: {e}")

    # Função para receber áudio
    def receive_audio(self):
        while self.running:
            try:
                # Recebe dados UDP
                data, addr = self.sock.recvfrom(CHUNK * 2)  # O buffer pode ser ajustado
                # Reproduz o áudio recebido
                self.output_stream.write(data)
            except Exception as e:
                print(f"Erro ao receber áudio: {e}")

    # Função para iniciar as threads
    def start(self):
        self.send_thread.start()
        self.receive_thread.start()
        print(f"VoIP iniciado. Recebendo em {self.LOCAL_IP}:{self.LOCAL_PORT} e enviando para {self.REMOTE_IP}:{self.REMOTE_PORT}.")

    # Função para parar as threads e liberar recursos
    def stop(self):
        self.running = False
        self.send_thread.join()
        self.receive_thread.join()
        self.input_stream.close()
        self.output_stream.close()
        self.audio.terminate()
        self.sock.close()
        print("VoIP encerrado.")
