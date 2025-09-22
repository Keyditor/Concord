import threading
from flask import Flask, request, jsonify


class ApiServer:

	def __init__(self, host, port, peers_provider, pending_provider, status_provider, start_call_fn, accept_fn, reject_fn, hangup_fn):
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
		self._register_routes()

	def _register_routes(self):
		app = self._app

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
				return jsonify({"error": info or "Call failed"}), 409
			return jsonify(info)

		@app.post('/accept')
		def accept():
			ok, info = self._accept()
			if not ok:
				return jsonify({"error": info or "No pending call"}), 409
			return jsonify(info)

		@app.post('/reject')
		def reject():
			ok = self._reject()
			if not ok:
				return jsonify({"error": "No pending call"}), 409
			return jsonify({"ok": True})

		@app.post('/hangup')
		def hangup():
			ok = self._hangup()
			return jsonify({"ok": bool(ok)})

	def start(self):
		self._thread.start()

	def _run(self):
		# debug=False, use_reloader=False for thread mode
		self._app.run(host=self.host, port=self.port, debug=False, use_reloader=False)


