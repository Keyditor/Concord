import http.server
import socketserver
import threading
import webbrowser
import os
import time


class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
	def log_message(self, format, *args):
		pass


def serve_frontend(directory: str, port: int = 5173):
	os.chdir(directory)
	handler = SilentHTTPRequestHandler
	httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
	thread = threading.Thread(target=httpd.serve_forever)
	thread.daemon = True
	thread.start()
	# open browser
	url = f"http://127.0.0.1:{port}/index.html"
	try:
		webbrowser.open(url)
	except Exception:
		pass
	return httpd


if __name__ == "__main__":
	# Run as standalone for testing
	server = serve_frontend(os.path.dirname(__file__))
	print("Frontend disponível em http://127.0.0.1:5173/index.html")
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		server.shutdown()
		server.server_close()
		print("Frontend encerrado")


