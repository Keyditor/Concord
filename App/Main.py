### Corpo do programa.
### Concord - Voice Chat

import json
import Voip
import Discovery
import Api
import Settings
import os
import uuid
import socket
import platform
import msvcrt
import time


"""
Main sem ZeroTier: Descoberta via broadcast em todas as redes.
"""

# Inicializar configurações
settings = Settings.SettingsManager()

# Configurar username se não existir
username = settings.get_username()
if not username:
    print("Primeira execução - configure seu username:")
    username = input("Username: ").strip() or "User"
    settings.set_username(username)

# Configurar dispositivos de áudio se não existirem
audio_devices = settings.get_audio_devices()
if audio_devices["input"] is None or audio_devices["output"] is None:
    print("Configurando dispositivos de áudio...")
    input_devices = settings.get_input_devices()
    output_devices = settings.get_output_devices()
    
    print("Dispositivos de entrada disponíveis:")
    for i, dev in enumerate(input_devices):
        print(f"{i}) {dev['name']}")
    try:
        input_idx = int(input("Selecione dispositivo de entrada (número): "))
        input_device = input_devices[input_idx]["index"]
    except (ValueError, IndexError):
        input_device = None
    
    print("Dispositivos de saída disponíveis:")
    for i, dev in enumerate(output_devices):
        print(f"{i}) {dev['name']}")
    try:
        output_idx = int(input("Selecione dispositivo de saída (número): "))
        output_device = output_devices[output_idx]["index"]
    except (ValueError, IndexError):
        output_device = None
    
    settings.set_audio_devices(input_device, output_device)
    audio_devices = settings.get_audio_devices()

# Descoberta de peers via broadcast multi-interface e negociação de portas
self_id = str(uuid.uuid4())
discovery = Discovery.DiscoveryService(self_id=self_id, display_name="Concord", username=username)
control = Discovery.ControlServer(control_port=38020)
discovery.start()
control.start()

# Simple call manager state shared with API
current_call = {"room": None}

def api_status():
    peers = discovery.get_peers()
    return {
        "host": hostname,
        "interfaces": Discovery.get_local_ipv4_interfaces(),
        "peers": peers,
        "pending": bool(control.pending_offer),
        "in_call": current_call["room"] is not None,
    }

def api_peers():
    return discovery.get_peers()

def api_start_call(ip, ctrl_port):
    if current_call["room"] is not None:
        return False, "Already in call"
    result = Discovery.initiate_call(ip, ctrl_port)
    if result is None:
        return False, "Peer rejected or no answer"
    room = Voip.VoipRoom(
        LOCAL_IP=result['local_ip'], 
        LOCAL_PORT=result['local_media_port'], 
        REMOTE_IP=ip, 
        REMOTE_PORT=result['remote_media_port'],
        input_device=audio_devices["input"],
        output_device=audio_devices["output"]
    )
    room.start()
    current_call["room"] = room
    return True, {"remote_ip": ip, "local_ip": result['local_ip']}

def api_accept():
    if current_call["room"] is not None:
        return False, "Already in call"
    if not control.pending_offer:
        return False, "No pending"
    accepted = control.accept_pending()
    if not accepted:
        return False, "No pending"
    room = Voip.VoipRoom(
        LOCAL_IP=accepted['local_ip'], 
        LOCAL_PORT=accepted['my_media_port'], 
        REMOTE_IP=accepted['peer_ip'], 
        REMOTE_PORT=accepted['peer_media_port'],
        input_device=audio_devices["input"],
        output_device=audio_devices["output"]
    )
    room.start()
    current_call["room"] = room
    return True, {"remote_ip": accepted['peer_ip'], "local_ip": accepted['local_ip']}

def api_reject():
    return control.reject_pending()

def api_hangup():
    if current_call["room"] is None:
        return False
    try:
        current_call["room"].stop()
    finally:
        current_call["room"] = None
    return True

api = Api.ApiServer(
    host="127.0.0.1",
    port=5001,
    peers_provider=api_peers,
    pending_provider=lambda: control.pending_offer,
    status_provider=api_status,
    start_call_fn=api_start_call,
    accept_fn=api_accept,
    reject_fn=api_reject,
    hangup_fn=api_hangup,
)
api.start()

hostname = platform.node()
iface_list = Discovery.get_local_ipv4_interfaces()

def render_header(status_text):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Concord - P2P VoIP")
    print(f"Host: {hostname}")
    bcasts = ", ".join([f"{i['ip']} -> {i['broadcast']} ({i['network']})" for i in iface_list])
    print(f"Broadcasts: {bcasts}")
    print(f"Status: {status_text}")
    print("")

try:
    current_room = None
    input_buffer = ""
    last_render = 0.0
    awaiting_answer = False
    peers = []
    
    while True:
        now = time.time()
        if now - last_render >= 5.0:
            peers = discovery.get_peers()
            render_header("Buscando peers...")
            if peers:
                print("Peers encontrados:")
                for idx, p in enumerate(peers):
                    username = p.get('username', p['display_name'])
                    print(f"{idx}) {username} - {p['ip']}")
                print("")
                print(f"Conectar a peer (número): {input_buffer}")
            else:
                print("Nenhum peer encontrado")
            
            # Mostrar chamada recebida independente de haver peers
            if control.pending_offer and not awaiting_answer:
                po = control.pending_offer
                print("")
                print(f"Chamada recebida de {po['peer_ip']} (porta {po['peer_media_port']}). Aceitar? [Y/N]")
                awaiting_answer = True
            last_render = now

        # Non-blocking keyboard input (Windows)
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if awaiting_answer:
                if ch.lower() == 'y':
                    accepted = control.accept_pending()
                    awaiting_answer = False
                    if accepted:
                        room = Voip.VoipRoom(
                            LOCAL_IP=accepted['local_ip'], 
                            LOCAL_PORT=accepted['my_media_port'], 
                            REMOTE_IP=accepted['peer_ip'], 
                            REMOTE_PORT=accepted['peer_media_port'],
                            input_device=audio_devices["input"],
                            output_device=audio_devices["output"]
                        )
                        room.start()
                        print("Conectado. Pressione ENTER para encerrar a chamada.")
                        input()  # aqui pode bloquear durante a chamada
                        room.stop()
                        input_buffer = ""
                        last_render = 0
                elif ch.lower() == 'n':
                    control.reject_pending()
                    awaiting_answer = False
                    last_render = 0
                continue

            if ch in ('\r', '\n'):
                if input_buffer.strip() != "" and peers:
                    try:
                        sel = int(input_buffer)
                        target = peers[sel]
                        render_header(f"Chamando {target['ip']}...")
                        result = Discovery.initiate_call(target['ip'], target['control_port'])
                        if result is None:
                            print("Sem resposta ou recusado pelo peer.")
                            time.sleep(1.5)
                        else:
                            room = Voip.VoipRoom(
                                LOCAL_IP=result['local_ip'], 
                                LOCAL_PORT=result['local_media_port'], 
                                REMOTE_IP=target['ip'], 
                                REMOTE_PORT=result['remote_media_port'],
                                input_device=audio_devices["input"],
                                output_device=audio_devices["output"]
                            )
                            room.start()
                            print("Conectado. Pressione ENTER para encerrar a chamada.")
                            input()
                            room.stop()
                    except (ValueError, IndexError):
                        pass
                input_buffer = ""
                last_render = 0
            elif ch == '\x08':  # backspace
                input_buffer = input_buffer[:-1]
                last_render = 0
            elif ch.isdigit():
                input_buffer += ch
                last_render = 0

        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    discovery.stop()
    control.stop()

