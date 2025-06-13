from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import json
import time
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=os.getenv('CORS_ORIGINS', '*'))

# Configurar Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
if os.getenv('FLASK_ENV'):
    app.config['ENV'] = os.getenv('FLASK_ENV')

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DB', 'registro_qr'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """Establece conexión a la base de datos"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Error conectando a BD: {str(e)}")
        return None

def normalize_email(email):
    """Normaliza email para comparaciones"""
    return email.lower().strip() if email else ""

def get_dia_espanol():
    """Obtiene el día actual en español"""
    dias = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado',
        'Sunday': 'domingo'
    }
    return dias.get(datetime.now().strftime("%A"), 'lunes')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "QR Temporal API"
    })

@app.route('/validate-qr', methods=['POST'])
def validate_qr():
    """Endpoint principal para validar QR temporal"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Log del QR recibido
        logger.info(f"QR recibido: {data}")
        
        # Parsear datos del QR
        try:
            if isinstance(data, str):
                qr_data = json.loads(data)
            else:
                qr_data = data
        except json.JSONDecodeError:
            return jsonify({"success": False, "error": "Formato QR inválido"}), 400
        
        # Validar timestamp (QR temporal)
        validation_result = validate_timestamp(qr_data)
        if not validation_result["valid"]:
            return jsonify({
                "success": False, 
                "error": validation_result["error"],
                "expired": True
            }), 400
        
        # Extraer datos del usuario
        nombre = qr_data.get('name', '').strip()
        apellido = qr_data.get('surname', '').strip()
        email = normalize_email(qr_data.get('email', ''))
        tipo_usuario = qr_data.get('tipoUsuario', '').upper()
        
        if not all([nombre, apellido, email, tipo_usuario]):
            return jsonify({"success": False, "error": "Datos incompletos"}), 400
        
        if tipo_usuario not in ['ESTUDIANTE', 'AYUDANTE']:
            return jsonify({"success": False, "error": "Tipo de usuario inválido"}), 400
        
        # Procesar según tipo de usuario
        if tipo_usuario == 'ESTUDIANTE':
            result = process_student(nombre, apellido, email)
        else:  # AYUDANTE
            result = process_helper(nombre, apellido, email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error validando QR: {str(e)}")
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500

def validate_timestamp(qr_data):
    """Valida que el QR no haya expirado"""
    try:
        # Verificar si está explícitamente expirado
        if qr_data.get('expired') == True or qr_data.get('status') == "EXPIRED":
            return {"valid": False, "error": "QR marcado como expirado"}
        
        # Verificar timestamp
        qr_timestamp = qr_data.get('timestamp')
        if not qr_timestamp:
            return {"valid": False, "error": "QR sin timestamp"}
        
        # Calcular diferencia de tiempo
        current_time = time.time() * 1000  # ms
        time_diff = abs(current_time - qr_timestamp) / 1000  # segundos
        
        # QR válido por 16 segundos (tolerancia extra)
        if time_diff > 16:
            return {"valid": False, "error": f"QR expirado hace {int(time_diff)} segundos"}
        
        return {"valid": True, "time_remaining": max(0, 16 - int(time_diff))}
        
    except Exception as e:
        return {"valid": False, "error": f"Error validando timestamp: {str(e)}"}

def process_student(nombre, apellido, email):
    """Procesa registro de estudiante"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Sin conexión a BD"}
    
    try:
        cursor = conn.cursor()
        
        # Verificar que el estudiante existe y está activo
        cursor.execute("""
            SELECT id, nombre, apellido, email, activo 
            FROM usuarios_estudiantes 
            WHERE LOWER(email) = %s AND activo = 1
        """, (email,))
        
        estudiante = cursor.fetchone()
        if not estudiante:
            return {"success": False, "error": "Estudiante no encontrado o inactivo"}
        
        # Verificar último registro para determinar entrada/salida
        cursor.execute("""
            SELECT tipo, DATE(fecha) as fecha_reg 
            FROM EST_registros 
            WHERE email = %s 
            ORDER BY fecha DESC, hora DESC 
            LIMIT 1
        """, (email,))
        
        ultimo_registro = cursor.fetchone()
        fecha_actual = datetime.now().date()
        
        # Determinar tipo de registro
        if ultimo_registro and ultimo_registro['fecha_reg'] == fecha_actual and ultimo_registro['tipo'] == 'Entrada':
            tipo_registro = 'Salida'
        else:
            tipo_registro = 'Entrada'
        
        # Insertar registro
        now = datetime.now()
        cursor.execute("""
            INSERT INTO EST_registros 
            (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            get_dia_espanol(),
            estudiante['nombre'],
            estudiante['apellido'],
            estudiante['email'],
            tipo_registro,
            0
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "tipo": tipo_registro,
            "usuario_tipo": "ESTUDIANTE",
            "nombre": estudiante['nombre'],
            "apellido": estudiante['apellido'],
            "email": estudiante['email'],
            "fecha": now.strftime("%Y-%m-%d"),
            "hora": now.strftime("%H:%M:%S"),
            "message": f"{tipo_registro} registrada para {estudiante['nombre']} {estudiante['apellido']}"
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error procesando estudiante: {str(e)}")
        return {"success": False, "error": f"Error en BD: {str(e)}"}
    finally:
        conn.close()

def process_helper(nombre, apellido, email):
    """Procesa registro de ayudante"""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Sin conexión a BD"}
    
    try:
        cursor = conn.cursor()
        
        # Verificar que el ayudante existe y está activo
        cursor.execute("""
            SELECT id, nombre, apellido, email, activo 
            FROM usuarios_permitidos 
            WHERE LOWER(email) = %s AND activo = 1
        """, (email,))
        
        ayudante = cursor.fetchone()
        if not ayudante:
            return {"success": False, "error": "Ayudante no encontrado o inactivo"}
        
        # Verificar último registro para determinar entrada/salida
        cursor.execute("""
            SELECT tipo, DATE(fecha) as fecha_reg 
            FROM registros 
            WHERE email = %s 
            ORDER BY fecha DESC, hora DESC 
            LIMIT 1
        """, (email,))
        
        ultimo_registro = cursor.fetchone()
        fecha_actual = datetime.now().date()
        
        # Determinar tipo de registro
        if ultimo_registro and ultimo_registro['fecha_reg'] == fecha_actual and ultimo_registro['tipo'] == 'Entrada':
            tipo_registro = 'Salida'
        else:
            tipo_registro = 'Entrada'
        
        # Insertar registro
        now = datetime.now()
        cursor.execute("""
            INSERT INTO registros 
            (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            get_dia_espanol(),
            ayudante['nombre'],
            ayudante['apellido'],
            ayudante['email'],
            tipo_registro,
            0
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "tipo": tipo_registro,
            "usuario_tipo": "AYUDANTE",
            "nombre": ayudante['nombre'],
            "apellido": ayudante['apellido'],
            "email": ayudante['email'],
            "fecha": now.strftime("%Y-%m-%d"),
            "hora": now.strftime("%H:%M:%S"),
            "message": f"{tipo_registro} registrada para {ayudante['nombre']} {ayudante['apellido']}"
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error procesando ayudante: {str(e)}")
        return {"success": False, "error": f"Error en BD: {str(e)}"}
    finally:
        conn.close()

@app.route('/verify-student', methods=['POST'])
def verify_student():
    """Verificar si un estudiante existe"""
    try:
        data = request.get_json()
        email = normalize_email(data.get('email', ''))
        
        if not email:
            return jsonify({"success": False, "error": "Email requerido"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Sin conexión a BD"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nombre, apellido, email, activo 
            FROM usuarios_estudiantes 
            WHERE LOWER(email) = %s
        """, (email,))
        
        estudiante = cursor.fetchone()
        conn.close()
        
        if estudiante:
            return jsonify({
                "success": True,
                "exists": True,
                "active": bool(estudiante['activo']),
                "data": estudiante
            })
        else:
            return jsonify({
                "success": True,
                "exists": False,
                "active": False
            })
            
    except Exception as e:
        logger.error(f"Error verificando estudiante: {str(e)}")
        return jsonify({"success": False, "error": "Error interno"}), 500

@app.route('/verify-helper', methods=['POST'])
def verify_helper():
    """Verificar si un ayudante existe"""
    try:
        data = request.get_json()
        email = normalize_email(data.get('email', ''))
        
        if not email:
            return jsonify({"success": False, "error": "Email requerido"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Sin conexión a BD"}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nombre, apellido, email, activo 
            FROM usuarios_permitidos 
            WHERE LOWER(email) = %s
        """, (email,))
        
        ayudante = cursor.fetchone()
        conn.close()
        
        if ayudante:
            return jsonify({
                "success": True,
                "exists": True,
                "active": bool(ayudante['activo']),
                "data": ayudante
            })
        else:
            return jsonify({
                "success": True,
                "exists": False,
                "active": False
            })
            
    except Exception as e:
        logger.error(f"Error verificando ayudante: {str(e)}")
        return jsonify({"success": False, "error": "Error interno"}), 500

@app.route('/get-last-records', methods=['GET'])
def get_last_records():
    """Obtener últimos registros"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Sin conexión a BD"}), 500
        
        cursor = conn.cursor()
        
        # Últimos registros de estudiantes
        cursor.execute("""
            SELECT 'ESTUDIANTE' as tipo_usuario, nombre, apellido, email, fecha, hora, tipo
            FROM EST_registros 
            ORDER BY fecha DESC, hora DESC 
            LIMIT %s
        """, (limit,))
        estudiantes = cursor.fetchall()
        
        # Últimos registros de ayudantes
        cursor.execute("""
            SELECT 'AYUDANTE' as tipo_usuario, nombre, apellido, email, fecha, hora, tipo
            FROM registros 
            ORDER BY fecha DESC, hora DESC 
            LIMIT %s
        """, (limit,))
        ayudantes = cursor.fetchall()
        
        conn.close()
        
        # Combinar y ordenar por fecha/hora
        todos_registros = list(estudiantes) + list(ayudantes)
        todos_registros.sort(key=lambda x: (x['fecha'], x['hora']), reverse=True)
        
        return jsonify({
            "success": True,
            "records": todos_registros[:limit]
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo registros: {str(e)}")
        return jsonify({"success": False, "error": "Error interno"}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas del día"""
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Sin conexión a BD"}), 500
        
        cursor = conn.cursor()
        
        # Estadísticas de estudiantes
        cursor.execute("""
            SELECT COUNT(*) as total, tipo
            FROM EST_registros 
            WHERE fecha = %s 
            GROUP BY tipo
        """, (fecha_hoy,))
        est_stats = {row['tipo']: row['total'] for row in cursor.fetchall()}
        
        # Estadísticas de ayudantes
        cursor.execute("""
            SELECT COUNT(*) as total, tipo
            FROM registros 
            WHERE fecha = %s 
            GROUP BY tipo
        """, (fecha_hoy,))
        ayu_stats = {row['tipo']: row['total'] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            "success": True,
            "date": fecha_hoy,
            "students": {
                "entries": est_stats.get('Entrada', 0),
                "exits": est_stats.get('Salida', 0)
            },
            "helpers": {
                "entries": ayu_stats.get('Entrada', 0),
                "exits": ayu_stats.get('Salida', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({"success": False, "error": "Error interno"}), 500

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    print("🚀 Iniciando API QR Temporal")
    print("📊 Endpoints disponibles:")
    print("  - POST /validate-qr - Validar y registrar QR")
    print("  - POST /verify-student - Verificar estudiante")
    print("  - POST /verify-helper - Verificar ayudante")
    print("  - GET /get-last-records - Últimos registros")
    print("  - GET /stats - Estadísticas del día")
    print("  - GET /health - Estado de la API")
    print(f"🔗 API ejecutándose en http://{host}:{port}")
    
    app.run(host=host, port=port, debug=(os.getenv('FLASK_ENV') == 'development'))
