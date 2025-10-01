import socket
import threading
import json
import time
import random
import ipaddress
import psutil


class PeerRegistry:

	def __init__(self, self_id):
		self.self_id = self_id
		self._peers = {}
		self._lock = threading.Lock()

	def upsert_peer(self, peer_id, ip, control_port, display_name, username=None):
		if peer_id == self.self_id:
			return
		with self._lock:
			self._peers[peer_id] = {
				"id": peer_id,
				"ip": ip,
				"control_port": control_port,
				"display_name": display_name,
				"username": username or display_name,
				"last_seen": time.time(),
			}

	def list_active(self, max_age_seconds=15.0):
		now = time.time()
		with self._lock:
			return [p for p in self._peers.values() if now - p["last_seen"] <= max_age_seconds]


def get_local_ipv4_interfaces():
	interfaces = []
	for if_name, addrs in psutil.net_if_addrs().items():
		for addr in addrs:
			if addr.family == socket.AF_INET:
				ip = addr.address
				netmask = addr.netmask or "255.255.255.0"
				try:
					network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
					broadcast = str(network.broadcast_address)
				except Exception:
					try:
						broadcast = addr.broadcast or "255.255.255.255"
					except Exception:
						broadcast = "255.255.255.255"
				interfaces.append({
					"name": if_name,
					"ip": ip,
					"netmask": netmask,
					"broadcast": broadcast,
					"network": str(ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)),
				})
	return interfaces


def select_local_ip_for_peer(peer_ip):
	peer = ipaddress.IPv4Address(peer_ip)
	for iface in get_local_ipv4_interfaces():
		try:
			if peer in ipaddress.IPv4Network(iface["network"], strict=False):
				return iface["ip"]
		except Exception:
			continue
	# fallback: first non-loopback
	for iface in get_local_ipv4_interfaces():
		if not iface["ip"].startswith("127."):
			return iface["ip"]
	return "127.0.0.1"


class DiscoveryService:

	def __init__(self, self_id, display_name="Concord", username=None, broadcast_port=37020, control_port=38020, beacon_interval=1.0, on_update=None):
		self.self_id = self_id
		self.display_name = display_name
		self.username = username or display_name
		self.broadcast_port = broadcast_port
		self.control_port = control_port
		self.beacon_interval = beacon_interval
		self.registry = PeerRegistry(self_id)
		self._on_update = on_update
		self._running = False
		self._beacon_thread = threading.Thread(target=self._beacon_loop)
		self._listen_thread = threading.Thread(target=self._listen_loop)
		self._beacon_thread.daemon = True
		self._listen_thread.daemon = True

	def start(self):
		self._running = True
		self._beacon_thread.start()
		self._listen_thread.start()

	def stop(self):
		self._running = False
		try:
			self._beacon_thread.join(timeout=1.0)
			self._listen_thread.join(timeout=1.0)
		except Exception:
			pass

	def get_peers(self):
		return self.registry.list_active()

	def _beacon_loop(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.settimeout(0.5)
		
		while self._running:
			try:
				interfaces = get_local_ipv4_interfaces()
				payload = {
					"type": "BEACON", "id": self.self_id, "name": self.display_name,
					"username": self.username, "control_port": self.control_port,
					"nets": [i["network"] for i in interfaces],
				}
				message = json.dumps(payload).encode("utf-8")
				for iface in interfaces:
					bcast = iface["broadcast"] or "255.255.255.255"
					sock.sendto(message, (bcast, self.broadcast_port))
				time.sleep(self.beacon_interval)
			except Exception:
				time.sleep(self.beacon_interval)
		sock.close()

	def send_goodbye(self):
		# Send a one-shot BYE to notify peers we are going offline
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			payload = {
				"type": "BYE",
				"id": self.self_id,
			}
			msg = json.dumps(payload).encode("utf-8")
			for iface in get_local_ipv4_interfaces():
				bcast = iface["broadcast"] or "255.255.255.255"
				sock.sendto(msg, (bcast, self.broadcast_port))
			sock.close()
		except Exception:
			pass

	def _listen_loop(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.bind(("", self.broadcast_port))
		sock.settimeout(0.5)
		while self._running:
			try:
				data, addr = sock.recvfrom(2048)
				peer_ip = addr[0]
				try:
					msg = json.loads(data.decode("utf-8"))
					if msg.get("type") == "BEACON" and "id" in msg and "control_port" in msg:
						# determine shared network for grouping
						shared = None
						my_nets = {i["network"] for i in get_local_ipv4_interfaces()}
						for net in msg.get("nets", []):
							if net in my_nets:
								shared = net
								break
						self.registry.upsert_peer(msg["id"], peer_ip, int(msg["control_port"]), msg.get("name", "Concord"), msg.get("username"))
						if self._on_update:
							try:
								self._on_update()
							except Exception:
								pass
					elif msg.get("type") == "BYE" and "id" in msg:
						# Remove peer from registry on goodbye
						with self.registry._lock:
							self.registry._peers.pop(msg["id"], None)
						if self._on_update:
							try:
								self._on_update()
							except Exception:
								pass
						# annotate grouping by network (optional: stored externally)
				except Exception:
					pass
			except Exception:
				# ignora erros transitórios
				continue
		sock.close()


def find_free_udp_port(bind_ip):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind((bind_ip, 0))
	port = s.getsockname()[1]
	s.close()
	return port


class ControlServer:

	def __init__(self, control_port, on_update=None):
		self.control_port = control_port
		self._running = False
		self._thread = threading.Thread(target=self._serve)
		self._thread.daemon = True
		self.pending_offer = None
		self._on_update = on_update
		self._lock = threading.Lock()

	def start(self):
		self._running = True
		self._thread.start()

	def stop(self):
		self._running = False
		try:
			self._thread.join(timeout=1.0)
		except Exception:
			pass

	def _serve(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(("", self.control_port))
		sock.settimeout(0.5)
		while self._running:
			try:
				data, addr = sock.recvfrom(2048)
				peer_ip, peer_port = addr
				try:
					msg = json.loads(data.decode("utf-8"))
					if msg.get("type") == "OFFER" and "caller_media_port" in msg:
						# armazenar oferta para ação do usuário (aceitar/recusar)
						local_ip = select_local_ip_for_peer(peer_ip)
						with self._lock:
							self.pending_offer = {
								"peer_ip": peer_ip,
								"peer_addr": addr,
								"peer_media_port": int(msg["caller_media_port"]),
								"local_ip": local_ip,
							}
						try:
							# Enviar resposta de "RINGING" para indicar que recebeu a chamada
							ringing_response = {"type": "RINGING"}
							sock.sendto(json.dumps(ringing_response).encode("utf-8"), addr)
							# Notificar que o estado mudou (nova oferta pendente)
							if self._on_update:
								self._on_update()
						except Exception:
							pass
				except Exception:
					pass
			except Exception:
				# ignora erros transitórios
				continue
		sock.close()

	def accept_pending(self):
		with self._lock:
			if not self.pending_offer:
				return None
			# abrir socket efêmero/porta para mídia
			local_ip = self.pending_offer["local_ip"]
			my_media_port = find_free_udp_port(local_ip)
			response = {
				"type": "ACCEPT",
				"callee_media_port": my_media_port,
			}
			# enviar resposta
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.sendto(json.dumps(response).encode("utf-8"), self.pending_offer["peer_addr"])
			sock.close()
			accepted = {
				"peer_ip": self.pending_offer["peer_ip"],
				"peer_media_port": self.pending_offer["peer_media_port"],
				"my_media_port": my_media_port,
				"local_ip": local_ip,
			}
			self.pending_offer = None
		if self._on_update:
			self._on_update()
		return accepted

	def reject_pending(self):
		with self._lock:
			if not self.pending_offer:
				return False
			rej = {"type": "REJECT"}
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.sendto(json.dumps(rej).encode("utf-8"), self.pending_offer["peer_addr"])
			sock.close()
			self.pending_offer = None
		if self._on_update:
			self._on_update()
		return True


def initiate_call(peer_ip, peer_control_port, timeout_seconds=10.0):
	ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ctrl_sock.settimeout(1.0)
	local_ip = select_local_ip_for_peer(peer_ip)
	my_media_port = find_free_udp_port(local_ip)
	offer = {
		"type": "OFFER",
		"caller_media_port": my_media_port,
	}
	deadline = time.time() + timeout_seconds
	response = None
	ringing_received = False
	last_send = 0
	
	while time.time() < deadline and response is None:
		try:
			# Enviar oferta apenas uma vez por segundo
			if not ringing_received or (time.time() - last_send) > 1.0:
				ctrl_sock.sendto(json.dumps(offer).encode("utf-8"), (peer_ip, peer_control_port))
				last_send = time.time()
			
			data, _ = ctrl_sock.recvfrom(2048)
			msg = json.loads(data.decode("utf-8"))
			
			if msg.get("type") == "RINGING":
				ringing_received = True
				print("Chamando... aguardando resposta...")
			elif msg.get("type") == "ACCEPT" and "callee_media_port" in msg:
				response = int(msg["callee_media_port"])
			elif msg.get("type") == "REJECT":
				ctrl_sock.close()
				return None
		except socket.timeout:
			continue
		except Exception:
			break
	ctrl_sock.close()
	if response is None:
		return None
	return {
		"local_media_port": my_media_port,
		"local_ip": local_ip,
		"remote_media_port": response,
	}
