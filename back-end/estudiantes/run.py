# run.py - Script para ejecutar el servidor de desarrollo
#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Configuración para desarrollo
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    print(f"🚀 Iniciando API en http://{host}:{port}")
    print(f"📊 Modo debug: {debug_mode}")
    print(f"🗄️  Base de datos: {os.getenv('MYSQL_DB')}")
    print("💻 Endpoints disponibles:")
    print("   - GET  /api/health")
    print("   - GET  /api/estudiantes_presentes/estudiantes")
    print("   - POST /api/estudiantes_presentes/estudiantes/<id>/presente")
    print("   - GET  /api/registros_hoy")
    print("   - GET  /api/registros_semana")
    print("   - GET  /api/registros_mes")
    print("   - POST /api/qr/validate")
    print("   - GET  /api/qr/status/<email>")
    print("=" * 50)
    
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        threaded=True
    )