import sqlite3
import os
import pyaudio


class SettingsManager:

	def __init__(self, db_path="concord.db"):
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
		for i in range(audio.get_device_count()):
			info = audio.get_device_info_by_index(i)
			devices.append({
				"index": i,
				"name": info["name"],
				"max_input_channels": info["maxInputChannels"],
				"max_output_channels": info["maxOutputChannels"],
			})
		audio.terminate()
		return devices

	def get_input_devices(self):
		return [d for d in self.list_audio_devices() if d["max_input_channels"] > 0]

	def get_output_devices(self):
		return [d for d in self.list_audio_devices() if d["max_output_channels"] > 0]
