import socket
import pyaudio
import threading
import select

# Configurações de áudio
CHUNK = 1024  # Tamanho do buffer
FORMAT = pyaudio.paInt16  # Formato de áudio
CHANNELS = 1  # Mono
RATE = 44100  # Taxa de amostragem

class VoipRoom:
	def __init__(self, LOCAL_IP="0.0.0.0", LOCAL_PORT=5000, REMOTE_IP="127.0.0.1", REMOTE_PORT=5000, input_device=None, output_device=None):
		# Configurações de rede
		self.LOCAL_IP = LOCAL_IP
		self.LOCAL_PORT = LOCAL_PORT
		self.REMOTE_IP = REMOTE_IP
		self.REMOTE_PORT = REMOTE_PORT

		# Inicialização de áudio
		self.audio = pyaudio.PyAudio()

		# Configurações de dispositivo de áudio
		input_kwargs = {"format": FORMAT, "channels": CHANNELS, "rate": RATE, "input": True, "frames_per_buffer": CHUNK}
		output_kwargs = {"format": FORMAT, "channels": CHANNELS, "rate": RATE, "output": True, "frames_per_buffer": CHUNK}
		
		if input_device is not None:
			input_kwargs["input_device_index"] = input_device
		if output_device is not None:
			output_kwargs["output_device_index"] = output_device

		# Fluxos de entrada (microfone) e saída (alto-falante)
		self.input_stream = self.audio.open(**input_kwargs)
		self.output_stream = self.audio.open(**output_kwargs)

		# Socket UDP
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind((self.LOCAL_IP, self.LOCAL_PORT))
		# timeouts curtos para permitir encerramento rápido
		self.sock.settimeout(0.2)

		# Threads para enviar e receber áudio
		self.running = True
		self.send_thread = threading.Thread(target=self.send_audio)
		self.receive_thread = threading.Thread(target=self.receive_audio)
		self.send_thread.daemon = True
		self.receive_thread.daemon = True

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
			except socket.timeout:
				# permite checar self.running periodicamente
				continue
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
		try:
			self.send_thread.join(timeout=1.0)
			self.receive_thread.join(timeout=1.0)
		except Exception:
			pass
		self.input_stream.close()
		self.output_stream.close()
		self.audio.terminate()
		self.sock.close()
		print("VoIP encerrado.")
