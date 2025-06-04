# app.py - Archivo principal de la aplicación Flask
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# Importar blueprints
from routes.estudiantes import estudiantes_bp
from routes.registros import registros_bp
from routes.qr import qr_bp
from config.database import init_db, close_db

# Cargar variables de entorno
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'registro_qr')
    
    # Habilitar CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Inicializar base de datos
    init_db(app)
    
    # Registrar blueprints
    app.register_blueprint(estudiantes_bp, url_prefix='/api')
    app.register_blueprint(registros_bp, url_prefix='/api')
    app.register_blueprint(qr_bp, url_prefix='/api')
    
    # Ruta de salud
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'OK',
            'timestamp': datetime.now().isoformat(),
            'message': 'API funcionando correctamente'
        })
    
    # Manejador de errores
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint no encontrado'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Error interno del servidor'}), 500
    
    # Cerrar conexión DB al finalizar
    @app.teardown_appcontext
    def close_db_connection(error):
        close_db()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )