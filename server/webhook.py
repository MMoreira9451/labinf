#!/usr/bin/env python3
import os
import subprocess
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import hmac
import hashlib

# 🔧 CONFIGURACIÓN
WEBHOOK_SECRET = "SECRETO"  # ← CAMBIAR POR UN SECRETO FUERTE
UPDATE_SCRIPT = "/opt/scripts/update-docker.sh" # RUTA DEL SCRIPT QUE ACTUALIZA LOS CONTENEDORES
PORT = 9000 # PUERTO DEL WEBHOOK

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/webhook/docker-update':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                print(f"📨 Webhook recibido desde {self.client_address[0]}")
                
                # Verificar firma (opcional pero recomendado)
                signature = self.headers.get('X-Hub-Signature-256')
                
                if self.verify_signature(post_data, signature):
                    print("✅ Webhook verificado correctamente")
                    
                    # Ejecutar script de actualización en background
                    def run_update():
                        try:
                            print("🔄 Ejecutando actualización...")
                            result = subprocess.run(['/bin/bash', UPDATE_SCRIPT], 
                                                  capture_output=True, text=True, timeout=300)
                            print(f"📊 Resultado: {result.returncode}")
                            if result.stdout:
                                print(f"📝 Output: {result.stdout}")
                            if result.stderr:
                                print(f"⚠️  Errors: {result.stderr}")
                        except subprocess.TimeoutExpired:
                            print("⏰ Timeout en la actualización")
                        except Exception as e:
                            print(f"❌ Error ejecutando actualización: {e}")
                    
                    # Ejecutar en hilo separado para no bloquear
                    thread = threading.Thread(target=run_update)
                    thread.daemon = True
                    thread.start()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "success", "message": "Update triggered"}
                    self.wfile.write(json.dumps(response).encode())
                    
                else:
                    print("❌ Firma inválida o faltante")
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": "Invalid signature"}
                    self.wfile.write(json.dumps(response).encode())
                    
            except Exception as e:
                print(f"❌ Error procesando webhook: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/webhook/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "service": "docker-webhook"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def verify_signature(self, payload, signature):
        if not signature:
            # Cambiar a False para requerir firma obligatoria
            return False
        
        expected = 'sha256=' + hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def log_message(self, format, *args):
        # Sobrescribir para log personalizado
        print(f"🌐 {self.client_address[0]} - {format % args}")

if __name__ == '__main__':
    try:
        server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
        print(f"🚀 Servidor webhook iniciado en puerto {PORT}")
        print(f"🔗 Endpoint: https://acceso.informaticauaint.com/webhook/docker-update")
        print(f"❤️  Health check: https://acceso.informaticauaint.com/webhook/health")
        print("🎯 Presiona Ctrl+C para detener")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
