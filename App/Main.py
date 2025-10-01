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

def check_and_add_firewall_rule():
    """Verifica e adiciona uma regra no Firewall do Windows para o aplicativo, se necessário."""
    if platform.system() != "Windows":
        return # Função específica para Windows

    import subprocess
    import ctypes

    rule_name = "Concord P2P"
    try:
        # Verifica se a regra já existe
        check_command = f'netsh advfirewall firewall show rule name="{rule_name}"'
        subprocess.check_output(check_command, shell=True, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        # Se o comando acima não der erro, a regra existe.
        return
    except subprocess.CalledProcessError:
        # A regra não existe, vamos criá-la.
        print(f"Regra de firewall '{rule_name}' não encontrada. Tentando criar...")
        try:
            # Verifica se o processo tem privilégios de administrador
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                print("Permissão de administrador necessária. Solicitando...")
                # Re-executa o script com privilégios de administrador
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0) # Encerra o processo atual sem privilégios

            # Adiciona a regra para o executável Python que está rodando o script
            program_path = sys.executable
            add_command = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow program="{program_path}" enable=yes'
            subprocess.check_call(add_command, shell=True)
            print(f"Regra de firewall '{rule_name}' criada com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao criar regra de firewall: {e}. Por favor, adicione manualmente uma regra de entrada para o aplicativo.")

def setup_logging():
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

class Application:
    def __init__(self):
        self.settings = Settings.SettingsManager()
        self.username = self.settings.get_username() or "New User"
        self.settings.set_username(self.username)

        self.audio_devices = {}
        self._init_audio_devices()

        self.self_id = str(uuid.uuid4())
        self.discovery = None
        self.control = None
        self.api = None

        self.current_call = {"room": None, "info": None}
        self.ui_state = {"screen": "main"}
        self.input_volume_percent = 100
        self.output_volume_percent = 100

        self.hostname = platform.node()
        self.iface_list = Discovery.get_local_ipv4_interfaces()

    def _init_audio_devices(self):
        try:
            self.settings.refresh_audio_device_cache()
        except Exception:
            logging.exception("Falha ao atualizar cache de dispositivos de áudio")

        self.audio_devices = self.settings.get_audio_devices()
        if self.audio_devices["input"] is None or self.audio_devices["output"] is None:
            print("Configurando dispositivos de áudio...")
            input_devices = self.settings.get_cached_input_devices()
            output_devices = self.settings.get_cached_output_devices()
            
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
            
            self.settings.set_audio_devices(input_device, output_device)
            self.audio_devices = self.settings.get_audio_devices()

    def _sample_mic_level(self, device_index):
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

    def _get_mic_level(self, device_index=None):
        try:
            idx = device_index
            if idx is None:
                devs = self.settings.get_audio_devices()
                idx = devs.get("input")
            return self._sample_mic_level(idx)
        except Exception:
            return 0

    def _play_test_tone(self, output_device_index):
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
                vol_factor = float(self.output_volume_percent) / 100.0
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

    def api_get_volume(self):
        return {"input": self.input_volume_percent, "output": self.output_volume_percent}

    def api_set_volume(self, inp, out):
        changed = False
        if inp is not None:
            try:
                val = int(float(inp))
                if 0 <= val <= 100:
                    self.input_volume_percent = val
                    if self.current_call["room"] is not None:
                        self.current_call["room"].set_input_volume(val)
                    changed = True
            except Exception:
                pass
        if out is not None:
            try:
                val = int(float(out))
                if 0 <= val <= 100:
                    self.output_volume_percent = val
                    if self.current_call["room"] is not None:
                        self.current_call["room"].set_output_volume(val)
                    changed = True
            except Exception:
                pass
        return changed

    def api_toggle_mute(self, mute_type, is_muted):
        """Ativa/desativa o mudo para entrada ou saída."""
        if self.current_call.get("room") is None:
            return False

        try:
            is_muted = bool(is_muted)
            if mute_type == "input":
                volume_to_set = 0 if is_muted else self.input_volume_percent
                self.current_call["room"].set_input_volume(volume_to_set)
            elif mute_type == "output":
                volume_to_set = 0 if is_muted else self.output_volume_percent
                self.current_call["room"].set_output_volume(volume_to_set)
            else:
                return False
            return True
        except Exception:
            return False

    def api_status(self):
        peers = [] if self.ui_state.get("screen") == "settings" else self.discovery.get_peers()
        po = self.control.pending_offer
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
            "host": self.hostname,
            "interfaces": Discovery.get_local_ipv4_interfaces(),
            "peers": peers,
            "pending": bool(po),
            "pending_offer": po or None,
            "in_call": self.current_call["room"] is not None,
            "current_call": self.current_call.get("info") if self.current_call["room"] is not None else None,
        }

    def api_peers(self, network_filter=None):
        all_peers = self.discovery.get_peers()
        if not network_filter or network_filter == 'all':
            return all_peers
        try:
            import ipaddress
            net = ipaddress.ip_network(network_filter, strict=False)
            return [p for p in all_peers if ipaddress.ip_address(p['ip']) in net]
        except Exception:
            return all_peers

    def api_start_call(self, ip, ctrl_port):
        if self.current_call["room"] is not None:
            return False, "Already in call"
        result = Discovery.initiate_call(ip, ctrl_port, my_username=self.username)
        if result is None:
            return False, "Peer rejected or no answer"
        room = Voip.VoipRoom(
            LOCAL_IP=result['local_ip'], 
            LOCAL_PORT=result['local_media_port'], 
            REMOTE_IP=ip, 
            REMOTE_PORT=result['remote_media_port'],
            input_device=self.audio_devices["input"],
            output_device=self.audio_devices["output"],
            input_volume=self.input_volume_percent / 100.0,
            output_volume=self.output_volume_percent / 100.0,
        )
        room.start()
        self.current_call["room"] = room
        remote_name = ip
        try:
            for p in self.discovery.get_peers():
                if p.get('ip') == ip:
                    remote_name = p.get('username', p.get('display_name', ip))
                    break
        except Exception:
            pass
        info = {"remote_ip": ip, "local_ip": result['local_ip'], "remote_username": remote_name}
        self.current_call["info"] = info
        self.api.publish_status_update()
        return True, info

    def api_accept(self):
        if self.current_call["room"] is not None:
            return False, "Already in call"
        if not self.control.pending_offer:
            return False, "No pending"
        accepted = self.control.accept_pending()
        if not accepted:
            return False, "No pending"
        room = Voip.VoipRoom(
            LOCAL_IP=accepted['local_ip'], 
            LOCAL_PORT=accepted['my_media_port'], 
            REMOTE_IP=accepted['peer_ip'], 
            REMOTE_PORT=accepted['peer_media_port'],
            input_device=self.audio_devices["input"],
            output_device=self.audio_devices["output"],
            input_volume=self.input_volume_percent / 100.0,
            output_volume=self.output_volume_percent / 100.0,
        )
        room.start()
        self.current_call["room"] = room
        remote_name = accepted['peer_ip']
        try:
            for p in self.discovery.get_peers():
                if p.get('ip') == accepted['peer_ip']:
                    remote_name = p.get('username', p.get('display_name', accepted['peer_ip']))
                    break
        except Exception:
            pass
        info = {"remote_ip": accepted['peer_ip'], "local_ip": accepted['local_ip'], "remote_username": remote_name}
        self.current_call["info"] = info
        self.api.publish_status_update()
        return True, info

    def api_reject(self):
        ok = self.control.reject_pending()
        self.api.publish_status_update()
        return ok

    def api_hangup(self):
        if self.current_call["room"] is None:
            return False
        try:
            self.current_call["room"].send_hangup_notification()
            self.current_call["room"].stop()
        finally:
            self.current_call["room"] = None
            self.current_call["info"] = None
        self.api.publish_status_update()
        return True

    def api_set_ui_state(self, state):
        self.ui_state.update({"screen": str(state or "main")})
        if state == "settings":
            try:
                logging.info("Atualizando cache de dispositivos de áudio ao entrar nas configurações...")
                self.settings.refresh_audio_device_cache()
            except Exception:
                logging.exception("Falha ao atualizar o cache de dispositivos de áudio.")

    def run(self):
        check_and_add_firewall_rule()
        setup_logging()
        sys.excepthook = _excepthook

        self.discovery = Discovery.DiscoveryService(self_id=self.self_id, display_name="Concord", username=self.username, beacon_interval=5.0, on_update=lambda: self.api.publish_peers_update())
        self.control = Discovery.ControlServer(control_port=38020, on_update=lambda: self.api.publish_status_update())

        self.api = Api.ApiServer(
            host="127.0.0.1", port=5001,
            peers_provider=self.api_peers,
            pending_provider=lambda: self.control.pending_offer,
            status_provider=self.api_status,
            start_call_fn=self.api_start_call,
            accept_fn=self.api_accept,
            reject_fn=self.api_reject,
            hangup_fn=self.api_hangup,
            trigger_discovery_fn=lambda: self.discovery.trigger_beacon() or True,
            get_volume_fn=self.api_get_volume,
            set_volume_fn=self.api_set_volume,
            toggle_mute_fn=self.api_toggle_mute,
            devices_provider=lambda: self.settings.get_cached_devices(),
            set_devices_fn=lambda inp, out: (self.settings.set_audio_devices(inp, out) or True),
            get_username_fn=self.settings.get_username,
            set_username_fn=self.settings.set_username,
            get_mic_level_fn=self._get_mic_level,
            test_output_fn=lambda out_idx: self._play_test_tone(out_idx),
            get_selected_devices_fn=lambda: self.settings.get_audio_devices(),
            set_ui_state_fn=self.api_set_ui_state,
            window_minimize_fn=lambda: (webview.windows[0].minimize() if webview.windows else False) or True,
            window_maximize_fn=lambda: (webview.windows[0].toggle_fullscreen() if webview.windows else False) or True,
            window_close_fn=lambda: (webview.windows[0].destroy() if webview.windows else False) or True,
            window_resize_fn=lambda w, h: (webview.windows[0].resize(int(w), int(h)) if (webview.windows and w and h) else False) or True,
        )

        self.api.start()
        self.discovery.start()
        self.control.start()

        try:
            def _serve_frontend():
                try:
                    import run_front
                    run_front.serve_frontend(os.path.dirname(__file__), open_browser=False)
                except Exception:
                    logging.exception("Falha ao iniciar o servidor do frontend")
            threading.Thread(target=_serve_frontend, daemon=True).start()

            webview.create_window('Concord', 'http://127.0.0.1:5173/index.html', width=1200, height=800, frameless=False)
            webview.start()
        except KeyboardInterrupt:
            pass
        except Exception:
            logging.exception("Falha ao abrir a janela do webview")
        finally:
            self.shutdown()

    def shutdown(self):
        logging.info("Encerrando a aplicação...")
        try:
            self.discovery.send_goodbye()
        except Exception:
            pass
        self.discovery.stop()
        self.control.stop()

if __name__ == "__main__":
    app = Application()
    app.run()
