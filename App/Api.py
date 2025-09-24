import threading
import logging
from flask import Flask, request, jsonify



class ApiServer:

	def __init__(self, host, port, peers_provider, pending_provider, status_provider, start_call_fn, accept_fn, reject_fn, hangup_fn, get_volume_fn=None, set_volume_fn=None, devices_provider=None, set_devices_fn=None, get_username_fn=None, set_username_fn=None, get_mic_level_fn=None, test_output_fn=None, get_selected_devices_fn=None, set_ui_state_fn=None, window_minimize_fn=None, window_maximize_fn=None, window_close_fn=None, window_resize_fn=None):
		self.host = host
		self.port = port
		self._thread = threading.Thread(target=self._run)
		self._thread.daemon = True
		self._app = Flask(__name__)
		self._peers_provider = peers_provider
		self._pending_provider = pending_provider
		self._status_provider = status_provider
		self._start_call = start_call_fn
		self._accept = accept_fn
		self._reject = reject_fn
		self._hangup = hangup_fn
		self._get_volume = get_volume_fn or (lambda: {"input": 100, "output": 100})
		self._set_volume = set_volume_fn or (lambda *_args, **_kwargs: False)
		self._devices_provider = devices_provider or (lambda: {"input": [], "output": []})
		self._set_devices = set_devices_fn or (lambda *_: False)
		self._get_username = get_username_fn or (lambda: "New User")
		self._set_username = set_username_fn or (lambda _u: False)
		self._get_mic_level = get_mic_level_fn or (lambda: 0)
		self._test_output = test_output_fn or (lambda *_: False)
		self._get_selected_devices = get_selected_devices_fn or (lambda: {"input": None, "output": None})
		self._set_ui_state = set_ui_state_fn or (lambda _s: None)
		self._window_minimize = window_minimize_fn or (lambda: False)
		self._window_maximize = window_maximize_fn or (lambda: False)
		self._window_close = window_close_fn or (lambda: False)
		self._window_resize = window_resize_fn or (lambda *_: False)
		self._register_routes()

	def _register_routes(self):
		app = self._app

		@app.after_request
		def add_cors_headers(response):
			response.headers['Access-Control-Allow-Origin'] = '*'
			response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
			response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
			return response

		@app.get('/status')
		def status():
			return jsonify(self._status_provider())

		@app.get('/peers')
		def peers():
			return jsonify(self._peers_provider())

		@app.post('/call')
		def call():
			data = request.get_json(silent=True) or {}
			peer_ip = data.get('ip')
			control_port = int(data.get('control_port', 38020))
			if not peer_ip:
				return jsonify({"error": "Missing ip"}), 400
			ok, info = self._start_call(peer_ip, control_port)
			if not ok:
				logging.error("API /call failed: %s", info)
				return jsonify({"error": info or "Call failed"}), 409
			return jsonify(info)

		@app.route('/call', methods=['OPTIONS'])
		def call_options():
			return ('', 204)

		@app.post('/accept')
		def accept():
			ok, info = self._accept()
			if not ok:
				logging.error("API /accept failed: %s", info)
				return jsonify({"error": info or "No pending call"}), 409
			return jsonify(info)

		@app.route('/accept', methods=['OPTIONS'])
		def accept_options():
			return ('', 204)

		@app.post('/reject')
		def reject():
			ok = self._reject()
			if not ok:
				logging.error("API /reject failed: no pending call")
				return jsonify({"error": "No pending call"}), 409
			return jsonify({"ok": True})

		@app.route('/reject', methods=['OPTIONS'])
		def reject_options():
			return ('', 204)

		@app.post('/hangup')
		def hangup():
			ok = self._hangup()
			return jsonify({"ok": bool(ok)})

		@app.route('/hangup', methods=['OPTIONS'])
		def hangup_options():
			return ('', 204)

		@app.get('/volume')
		def volume_get():
			return jsonify(self._get_volume())

		@app.post('/volume')
		def volume_set():
			data = request.get_json(silent=True) or {}
			inp = data.get('input')
			out = data.get('output')
			ok = self._set_volume(inp, out)
			if not ok:
				return jsonify({"error": "Invalid volume payload"}), 400
			return jsonify(self._get_volume())

		@app.route('/volume', methods=['OPTIONS'])
		def volume_options():
			return ('', 204)

		@app.get('/devices')
		def list_devices():
			return jsonify(self._devices_provider())

		@app.get('/audio-devices')
		def get_selected_devices():
			return jsonify(self._get_selected_devices())

		@app.post('/ui-state')
		def set_ui_state():
			data = request.get_json(silent=True) or {}
			state = data.get('state')
			self._set_ui_state(state)
			return jsonify({"ok": True})

		@app.post('/window/minimize')
		def window_minimize():
			return jsonify({"ok": bool(self._window_minimize())})

		@app.post('/window/maximize')
		def window_maximize():
			return jsonify({"ok": bool(self._window_maximize())})

		@app.post('/window/close')
		def window_close():
			return jsonify({"ok": bool(self._window_close())})

		@app.post('/window/resize')
		def window_resize():
			data = request.get_json(silent=True) or {}
			w = data.get('width')
			h = data.get('height')
			return jsonify({"ok": bool(self._window_resize(w, h))})

		@app.get('/mic-level')
		def mic_level():
			try:
				# optional device override via query param
				inp = request.args.get('input')
				level = int(self._get_mic_level(None if inp is None else int(inp)))
				level = max(0, min(100, level))
				return jsonify({"level": level})
			except Exception:
				return jsonify({"level": 0})

		@app.post('/test-output')
		def test_output():
			data = request.get_json(silent=True) or {}
			out = data.get('output')
			ok = self._test_output(out)
			return jsonify({"ok": bool(ok)})

		@app.route('/test-output', methods=['OPTIONS'])
		def test_output_options():
			return ('', 204)

		@app.post('/audio-devices')
		def set_devices():
			data = request.get_json(silent=True) or {}
			inp = data.get('input')
			out = data.get('output')
			ok = self._set_devices(inp, out)
			if not ok:
				return jsonify({"error": "Invalid devices"}), 400
			return jsonify({"ok": True})

		@app.route('/audio-devices', methods=['OPTIONS'])
		def set_devices_options():
			return ('', 204)

		@app.get('/user')
		def get_user():
			return jsonify({"username": self._get_username()})

		@app.post('/user')
		def set_user():
			data = request.get_json(silent=True) or {}
			username = data.get('username')
			if not username or not isinstance(username, str):
				return jsonify({"error": "Invalid username"}), 400
			ok = self._set_username(username)
			return jsonify({"ok": bool(ok)})

		@app.route('/user', methods=['OPTIONS'])
		def user_options():
			return ('', 204)

	def start(self):
		self._thread.start()

	def _run(self):
		# debug=False, use_reloader=False for thread mode
		self._app.run(host=self.host, port=self.port, debug=False, use_reloader=False)


