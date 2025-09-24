import sqlite3
import os
import pyaudio


class SettingsManager:

	def __init__(self, db_path="concord.db"):
		# Ensure DB path is absolute and anchored to project root, not CWD
		if not os.path.isabs(db_path):
			project_root = os.path.dirname(os.path.dirname(__file__))
			self.db_path = os.path.abspath(os.path.join(project_root, db_path))
		else:
			self.db_path = db_path
		self._init_db()

	def _init_db(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS user_settings (
				id INTEGER PRIMARY KEY,
				username TEXT,
				input_device_index INTEGER,
				output_device_index INTEGER,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		""")
		# Tabela de cache de dispositivos de áudio
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS audio_devices (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				kind TEXT NOT NULL,              -- 'input' ou 'output'
				position INTEGER NOT NULL,        -- posição na lista exibida (0..N-1)
				pa_index INTEGER NOT NULL,        -- índice real do PyAudio
				name TEXT NOT NULL,
				max_channels INTEGER NOT NULL,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		""")
		conn.commit()
		conn.close()

	def get_username(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute("SELECT username FROM user_settings WHERE id = 1")
		result = cursor.fetchone()
		conn.close()
		return result[0] if result else None

	def set_username(self, username):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		# First check if record exists
		cursor.execute("SELECT id FROM user_settings WHERE id = 1")
		exists = cursor.fetchone()
		
		if exists:
			# Update existing record
			cursor.execute("""
				UPDATE user_settings 
				SET username = ?, updated_at = CURRENT_TIMESTAMP
				WHERE id = 1
			""", (username,))
		else:
			# Insert new record
			cursor.execute("""
				INSERT INTO user_settings (id, username, updated_at)
				VALUES (1, ?, CURRENT_TIMESTAMP)
			""", (username,))
		conn.commit()
		conn.close()

	def get_audio_devices(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute("SELECT input_device_index, output_device_index FROM user_settings WHERE id = 1")
		result = cursor.fetchone()
		conn.close()
		if result:
			return {"input": result[0], "output": result[1]}
		return {"input": None, "output": None}

	def set_audio_devices(self, input_index, output_index):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		# First check if record exists
		cursor.execute("SELECT id FROM user_settings WHERE id = 1")
		exists = cursor.fetchone()
		
		if exists:
			# Update existing record
			cursor.execute("""
				UPDATE user_settings 
				SET input_device_index = ?, output_device_index = ?, updated_at = CURRENT_TIMESTAMP
				WHERE id = 1
			""", (input_index, output_index))
		else:
			# Insert new record with default username
			cursor.execute("""
				INSERT INTO user_settings (id, username, input_device_index, output_device_index, updated_at)
				VALUES (1, 'User', ?, ?, CURRENT_TIMESTAMP)
			""", (input_index, output_index))
		conn.commit()
		conn.close()

	def list_audio_devices(self):
		audio = pyaudio.PyAudio()
		devices = []
		try:
			# Use apenas dispositivos do Host API padrão para evitar duplicatas, quando disponível
			try:
				default_host_api = audio.get_default_host_api_info().get("index")
			except Exception:
				default_host_api = None
			seen_names = set()
			for i in range(audio.get_device_count()):
				try:
					info = audio.get_device_info_by_index(i)
				except Exception:
					# Pula entradas problemáticas em vez de falhar toda a listagem
					continue
				# Filtra por Host API padrão
				if default_host_api is not None and info.get("hostApi") != default_host_api:
					continue
				# Ignora dispositivos de loopback do WASAPI (quando presentes)
				if info.get("isLoopbackDevice") == 1 or "loopback" in str(info.get("name", "")).lower():
					continue
				# Deduplica por nome (case-insensitive)
				name_key = str(info.get("name", "")).strip().lower()
				if name_key in seen_names:
					continue
				seen_names.add(name_key)
				devices.append({
					"index": i,
					"name": info.get("name", f"Device {i}"),
					"max_input_channels": int(info.get("maxInputChannels", 0) or 0),
					"max_output_channels": int(info.get("maxOutputChannels", 0) or 0),
				})
		finally:
			audio.terminate()
		return devices

	def get_input_devices(self):
		return [d for d in self.list_audio_devices() if d["max_input_channels"] > 0]

	def get_output_devices(self):
		return [d for d in self.list_audio_devices() if d["max_output_channels"] > 0]

	def refresh_audio_device_cache(self):
		"""Escaneia dispositivos e atualiza o cache em tabela dedicada."""
		inputs = self.get_input_devices()
		outputs = self.get_output_devices()
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		# Limpa cache anterior
		cursor.execute("DELETE FROM audio_devices")
		# Insere inputs
		for pos, dev in enumerate(inputs):
			cursor.execute(
				"""
				INSERT INTO audio_devices (kind, position, pa_index, name, max_channels, updated_at)
				VALUES ('input', ?, ?, ?, ?, CURRENT_TIMESTAMP)
				""",
				(pos, int(dev["index"]), str(dev["name"]), int(dev.get("max_input_channels", 0)))
			)
		# Insere outputs
		for pos, dev in enumerate(outputs):
			cursor.execute(
				"""
				INSERT INTO audio_devices (kind, position, pa_index, name, max_channels, updated_at)
				VALUES ('output', ?, ?, ?, ?, CURRENT_TIMESTAMP)
				""",
				(pos, int(dev["index"]), str(dev["name"]), int(dev.get("max_output_channels", 0)))
			)
		conn.commit()
		conn.close()

	def get_cached_devices(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute("SELECT position, pa_index, name, max_channels FROM audio_devices WHERE kind='input' ORDER BY position ASC")
		inputs = [{"index": r[1], "name": r[2], "max_input_channels": r[3], "position": r[0]} for r in cursor.fetchall()]
		cursor.execute("SELECT position, pa_index, name, max_channels FROM audio_devices WHERE kind='output' ORDER BY position ASC")
		outputs = [{"index": r[1], "name": r[2], "max_output_channels": r[3], "position": r[0]} for r in cursor.fetchall()]
		conn.close()
		return {"input": inputs, "output": outputs}

	def get_cached_input_devices(self):
		return self.get_cached_devices()["input"]

	def get_cached_output_devices(self):
		return self.get_cached_devices()["output"]
