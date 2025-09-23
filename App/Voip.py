import socket
import pyaudio
import threading
import select
import audioop

# Configurações de áudio
CHUNK = 1024  # Tamanho do buffer
FORMAT = pyaudio.paInt16  # Formato de áudio
CHANNELS = 1  # Mono
RATE = 44100  # Taxa de amostragem

class VoipRoom:
	def __init__(self, LOCAL_IP="0.0.0.0", LOCAL_PORT=5000, REMOTE_IP="127.0.0.1", REMOTE_PORT=5000, input_device=None, output_device=None, input_volume=1.0, output_volume=1.0):
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

		# Controle de volume (0.0 a 1.0)
		self._vol_lock = threading.Lock()
		self._input_volume = max(0.0, min(1.0, float(input_volume)))
		self._output_volume = max(0.0, min(1.0, float(output_volume)))

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
				# Aplica volume de entrada
				with self._vol_lock:
					in_vol = self._input_volume
				if in_vol != 1.0:
					try:
						data = audioop.mul(data, 2, in_vol)
					except Exception:
						pass
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
				# Aplica volume de saída
				with self._vol_lock:
					out_vol = self._output_volume
				if out_vol != 1.0:
					try:
						data = audioop.mul(data, 2, out_vol)
					except Exception:
						pass
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

	# ------ Volume controls ------
	def set_input_volume(self, percent):
		try:
			value = max(0.0, min(100.0, float(percent))) / 100.0
		except Exception:
			return False
		with self._vol_lock:
			self._input_volume = value
		return True

	def set_output_volume(self, percent):
		try:
			value = max(0.0, min(100.0, float(percent))) / 100.0
		except Exception:
			return False
		with self._vol_lock:
			self._output_volume = value
		return True

	def get_volumes(self):
		with self._vol_lock:
			return {
				"input": int(round(self._input_volume * 100)),
				"output": int(round(self._output_volume * 100)),
			}
