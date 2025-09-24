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
import logging
import sys
import threading
import webview


"""
Main sem ZeroTier: Descoberta via broadcast em todas as redes.
"""

# Inicializar configurações
settings = Settings.SettingsManager()

# ---- Logging configuration ----
try:
    base_dir = os.path.dirname(os.path.dirname(__file__))
except Exception:
    base_dir = os.getcwd()
log_file = os.path.join(base_dir, 'concord.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)

def _excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = _excepthook

# Configurar username se não existir
username = settings.get_username() or "New User"
settings.set_username(username)

# Atualiza cache de dispositivos no início e tenta reaplicar selecionados
try:
    settings.refresh_audio_device_cache()
except Exception:
    logging.exception("Falha ao atualizar cache de dispositivos de áudio")

# Configurar dispositivos de áudio se não existirem
audio_devices = settings.get_audio_devices()
if audio_devices["input"] is None or audio_devices["output"] is None:
    print("Configurando dispositivos de áudio...")
    input_devices = settings.get_cached_input_devices()
    output_devices = settings.get_cached_output_devices()
    
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
discovery = Discovery.DiscoveryService(self_id=self_id, display_name="Concord", username=username, on_update=lambda: api.publish_peers_update())
control = Discovery.ControlServer(control_port=38020)
discovery.start()
control.start()

# Simple call manager state shared with API
current_call = {"room": None}
_ui_state = {"screen": "main"}

# Volumes em porcentagem (0-100)
_input_volume_percent = 100
_output_volume_percent = 100

def api_get_volume():
    return {"input": _input_volume_percent, "output": _output_volume_percent}

def api_set_volume(inp, out):
    global _input_volume_percent, _output_volume_percent
    changed = False
    if inp is not None:
        try:
            val = int(float(inp))
            if 0 <= val <= 100:
                _input_volume_percent = val
                if current_call["room"] is not None:
                    current_call["room"].set_input_volume(val)
                changed = True
        except Exception:
            pass
    if out is not None:
        try:
            val = int(float(out))
            if 0 <= val <= 100:
                _output_volume_percent = val
                if current_call["room"] is not None:
                    current_call["room"].set_output_volume(val)
                changed = True
        except Exception:
            pass
    return changed

def api_status():
    # Pause peers list when in settings
    peers = [] if _ui_state.get("screen") == "settings" else discovery.get_peers()
    # enrich pending offer with username
    po = control.pending_offer
    if po:
        try:
            name = po.get('peer_ip')
            for p in peers:
                if p.get('ip') == po.get('peer_ip'):
                    name = p.get('username', p.get('display_name', name))
                    break
            po = dict(po)
            po['peer_username'] = name
        except Exception:
            pass
    return {
        "host": hostname,
        "interfaces": Discovery.get_local_ipv4_interfaces(),
        "peers": peers,
        "pending": bool(po),
        "pending_offer": po or None,
        "in_call": current_call["room"] is not None,
        "current_call": current_call.get("info") if current_call["room"] is not None else None,
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
        output_device=audio_devices["output"],
        input_volume=_input_volume_percent / 100.0,
        output_volume=_output_volume_percent / 100.0,
    )
    room.start()
    current_call["room"] = room
    # resolve remote username from discovery
    remote_name = ip
    try:
        for p in discovery.get_peers():
            if p.get('ip') == ip:
                remote_name = p.get('username', p.get('display_name', ip))
                break
    except Exception:
        pass
    info = {"remote_ip": ip, "local_ip": result['local_ip'], "remote_username": remote_name}
    current_call["info"] = info
    return True, info

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
        output_device=audio_devices["output"],
        input_volume=_input_volume_percent / 100.0,
        output_volume=_output_volume_percent / 100.0,
    )
    room.start()
    current_call["room"] = room
    # resolve remote username from discovery
    remote_name = accepted['peer_ip']
    try:
        for p in discovery.get_peers():
            if p.get('ip') == accepted['peer_ip']:
                remote_name = p.get('username', p.get('display_name', accepted['peer_ip']))
                break
    except Exception:
        pass
    info = {"remote_ip": accepted['peer_ip'], "local_ip": accepted['local_ip'], "remote_username": remote_name}
    current_call["info"] = info
    return True, info

def api_reject():
    return control.reject_pending()

def api_hangup():
    if current_call["room"] is None:
        return False
    try:
        current_call["room"].stop()
    finally:
        current_call["room"] = None
        current_call["info"] = None
    return True

def _sample_mic_level(device_index):
    try:
        import pyaudio, audioop
        pa = pyaudio.PyAudio()
        # Valida o índice do dispositivo antes de abrir
        try:
            if device_index is not None:
                info = pa.get_device_info_by_index(int(device_index))
                if not info or int(info.get('maxInputChannels', 0) or 0) <= 0:
                    try:
                        pa.terminate()
                    except Exception:
                        pass
                    return 0
        except Exception:
            try:
                pa.terminate()
            except Exception:
                pass
            return 0
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024,
                         input_device_index=int(device_index) if device_index is not None else None)
        try:
            data = stream.read(1024, exception_on_overflow=False)
            rms = audioop.rms(data, 2)
            level = min(100, int((rms / 32767.0) * 100))
        finally:
            try:
                stream.close()
            except Exception:
                pass
            try:
                pa.terminate()
            except Exception:
                pass
        return level
    except Exception:
        return 0

def _get_mic_level(device_index=None):
    try:
        idx = device_index
        if idx is None:
            devs = settings.get_audio_devices()
            idx = devs.get("input")
        return _sample_mic_level(idx)
    except Exception:
        return 0

def _play_test_tone(output_device_index):
    try:
        import pyaudio, math, struct
        pa = pyaudio.PyAudio()
        rate = 44100
        duration = 0.6  # seconds
        freq = 880.0
        frames = int(rate * duration)
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=rate, output=True,
                         output_device_index=int(output_device_index) if output_device_index is not None else None)
        # Follow currently selected output volume (0-100)
        try:
            vol_factor = float(_output_volume_percent) / 100.0
        except Exception:
            vol_factor = 1.0
        vol_factor = max(0.0, min(1.0, vol_factor))
        for n in range(frames):
            sample = int(0.6 * vol_factor * 32767 * math.sin(2 * math.pi * freq * (n / rate)))
            stream.write(struct.pack('<h', sample))
        try:
            stream.close()
        finally:
            pa.terminate()
        return True
    except Exception:
        return False

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
    get_volume_fn=api_get_volume,
    set_volume_fn=api_set_volume,
    devices_provider=lambda: settings.get_cached_devices(),
    set_devices_fn=lambda inp, out: (settings.set_audio_devices(inp, out) or True),
    get_username_fn=settings.get_username,
    set_username_fn=settings.set_username,
    get_mic_level_fn=_get_mic_level,
    test_output_fn=lambda out_idx: _play_test_tone(out_idx),
    get_selected_devices_fn=lambda: settings.get_audio_devices(),
    set_ui_state_fn=lambda st: _ui_state.update({"screen": str(st or "main")}),
    window_minimize_fn=lambda: (webview.windows[0].minimize() if webview.windows else False) or True,
    window_maximize_fn=lambda: (webview.windows[0].toggle_fullscreen() if webview.windows else False) or True,
    window_close_fn=lambda: (webview.windows[0].destroy() if webview.windows else False) or True,
    window_resize_fn=lambda w, h: (webview.windows[0].resize(int(w), int(h)) if (webview.windows and w and h) else False) or True,
)
api.start()

hostname = platform.node()
iface_list = Discovery.get_local_ipv4_interfaces()

def render_header(status_text):
    print("Concord - P2P VoIP")
    print(f"Host: {hostname}")
    bcasts = ", ".join([f"{i['ip']} -> {i['broadcast']} ({i['network']})" for i in iface_list])
    print(f"Broadcasts: {bcasts}")
    print(f"Status: {status_text}")
    print("")

try:
    # Launch lightweight static server for front-end after API is up
    def _serve_frontend():
        try:
            import run_front
            run_front.serve_frontend(os.path.dirname(__file__), open_browser=False)
        except Exception:
            logging.exception("Falha ao iniciar o servidor do frontend")

    # Move console UI loop to a background thread so webview can run on main thread
    def _console_loop():
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
        except Exception:
            logging.exception("Erro no loop de console")

    threading.Thread(target=_serve_frontend, daemon=True).start()
    threading.Thread(target=_console_loop, daemon=True).start()

    # Create and start webview on main thread
    try:
        webview.create_window('Concord', 'http://127.0.0.1:5173/index.html', width=1200, height=800, frameless=True)
        webview.start()
    except Exception:
        logging.exception("Falha ao abrir a janela do webview")
except KeyboardInterrupt:
    pass
finally:
    try:
        discovery.send_goodbye()
    except Exception:
        pass
    discovery.stop()
    control.stop()

