#!/usr/bin/env python3
"""
Servidor HTTP simple que responde Hola Mundo y consume otro microservicio para GET/POST de usuarios
"""
import http.server
import socketserver
import sys
import os
import json
from datetime import datetime

import requests  # Para consumir el microservicio

PORT = 3005

# URL base del microservicio que gestiona la base de datos (configurable por variable de entorno)
MICROSERVICE_BASE_URL = os.environ.get('MICROSERVICE_URL', 'http://cu-ms-payments:3000')

def fetch_users():
    """Consume el endpoint GET /users del microservicio"""
    try:
        url = f"{MICROSERVICE_BASE_URL}/users"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Fallo al consumir {url}: {str(e)}"}

def create_user(payload):
    """Consume el endpoint POST /users del microservicio, enviando el JSON recibido"""
    try:
        url = f"{MICROSERVICE_BASE_URL}/users"
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        # Muchas APIs devuelven 201 Created; si no, manejamos genéricamente
        return resp.status_code, resp.json()
    except requests.exceptions.HTTPError as e:
        # Si el microservicio responde 4xx/5xx, propagamos el código y mensaje
        status = e.response.status_code if e.response is not None else 500
        try:
            body = e.response.json()
        except Exception:
            body = {"error": f"HTTP error {status}: {str(e)}"}
        return status, body
    except requests.exceptions.RequestException as e:
        return 500, {"error": f"Fallo al consumir {url}: {str(e)}"}

class HolaMundoHandler(http.server.SimpleHTTPRequestHandler):
    # --- Helpers ---
    def _send_text_response(self, text, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(text.encode('utf-8'))

    def _send_json_response(self, obj, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode('utf-8'))

    # --- Métodos HTTP ---
    def do_GET(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Solicitud GET recibida", file=sys.stdout)
        print(f"[{timestamp}] Path: {self.path}", file=sys.stdout)

        if self.path == '/startup':
            self._send_text_response('OK')
        elif self.path == '/liveness':
            self._send_text_response('OK')
        elif self.path == '/readiness':
            self._send_text_response('OK')
        elif self.path == '/users':
            print(f"[{timestamp}] se llamó al endpoint /users (GET -> microservicio)", file=sys.stdout)
            sys.stdout.flush()
            result = fetch_users()
            self._send_json_response(result, status=200)
        else:
            self._send_text_response('<h1>Hola Mundo desde MS1</h1>')

    def do_POST(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Solicitud POST recibida", file=sys.stdout)
        print(f"[{timestamp}] Path: {self.path}", file=sys.stdout)

        if self.path == '/users':
            # Leer el cuerpo
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length) if content_length > 0 else b''
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                self._send_json_response({"error": "JSON inválido"}, status=400)
                return

            # Validación mínima: requerir 'name', igual que el microservicio habitual
            if "name" not in data or not isinstance(data["name"], str) or not data["name"].strip():
                self._send_json_response({"error": "Debe enviar el campo 'name' (string no vacío)"}, status=400)
                return

            print(f"[{timestamp}] se llamó al endpoint /users (POST -> microservicio) payload={data}", file=sys.stdout)
            sys.stdout.flush()

            status, result = create_user(data)
            # Propagar el status que devuelve el microservicio (p.ej., 201 Created)
            self._send_json_response(result, status=status)
        else:
            self.send_response(404)
            self.end_headers()

    # Log formateado
    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}", file=sys.stdout)
        sys.stdout.flush()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), HolaMundoHandler) as httpd:
        print(f"Servidor corriendo en puerto {PORT}")
        print("Presiona Ctrl+C para detener")
        httpd.serve_forever()