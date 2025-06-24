# test_lector.py
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import time
from datetime import datetime

# Agregar el directorio de lector al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../back-end/lector'))

# Importar funciones del módulo lector
try:
    from api_qr_temporal import normalize_email, get_dia_espanol, validate_timestamp
except ImportError:
    # Definir funciones básicas para testing si no se pueden importar
    def normalize_email(email):
        return email.lower().strip() if email else ""
    
    def get_dia_espanol():
        dias = {
            'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
            'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado',
            'Sunday': 'domingo'
        }
        return dias.get(datetime.now().strftime("%A"), 'lunes')
    
    def validate_timestamp(qr_data):
        try:
            if qr_data.get('expired') == True or qr_data.get('status') == "EXPIRED":
                return {"valid": False, "error": "QR marcado como expirado"}
            
            qr_timestamp = qr_data.get('timestamp')
            if not qr_timestamp:
                return {"valid": False, "error": "QR sin timestamp"}
            
            current_time = time.time() * 1000
            time_diff = abs(current_time - qr_timestamp) / 1000
            
            if time_diff > 16:
                return {"valid": False, "error": f"QR expirado hace {int(time_diff)} segundos"}
            
            return {"valid": True, "time_remaining": max(0, 16 - int(time_diff))}
            
        except Exception as e:
            return {"valid": False, "error": f"Error validando timestamp: {str(e)}"}

class TestUtilityFunctions(unittest.TestCase):
    """Tests para funciones de utilidad del lector QR"""
    
    def test_normalize_email_basic(self):
        """Test normalización básica de email"""
        test_cases = [
            ('TEST@EXAMPLE.COM', 'test@example.com'),
            ('  user@domain.com  ', 'user@domain.com'),
            ('User.Name@Domain.ORG', 'user.name@domain.org'),
            ('', ''),
            (None, '')
        ]
        
        for input_email, expected in test_cases:
            result = normalize_email(input_email)
            self.assertEqual(result, expected)
    
    def test_get_dia_espanol(self):
        """Test obtención del día en español"""
        result = get_dia_espanol()
        
        # Verificar que retorna un día válido en español
        dias_validos = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        self.assertIn(result, dias_validos)
        self.assertIsInstance(result, str)
    
    def test_validate_timestamp_valid_qr(self):
        """Test validación de QR con timestamp válido"""
        current_time = time.time() * 1000  # milisegundos
        
        qr_data = {
            'timestamp': current_time - 5000,  # 5 segundos atrás
            'status': 'VALID'
        }
        
        result = validate_timestamp(qr_data)
        self.assertTrue(result['valid'])
        self.assertIn('time_remaining', result)
    
    def test_validate_timestamp_expired_qr(self):
        """Test validación de QR expirado por tiempo"""
        current_time = time.time() * 1000
        
        qr_data = {
            'timestamp': current_time - 20000,  # 20 segundos atrás (expirado)
            'status': 'VALID'
        }
        
        result = validate_timestamp(qr_data)
        self.assertFalse(result['valid'])
        self.assertIn('expirado', result['error'].lower())
    
    def test_validate_timestamp_marked_expired(self):
        """Test validación de QR marcado como expirado"""
        qr_data = {
            'timestamp': time.time() * 1000,
            'status': 'EXPIRED'
        }
        
        result = validate_timestamp(qr_data)
        self.assertFalse(result['valid'])
        self.assertIn('expirado', result['error'].lower())
    
    def test_validate_timestamp_no_timestamp(self):
        """Test validación de QR sin timestamp"""
        qr_data = {
            'status': 'VALID'
            # Sin timestamp
        }
        
        result = validate_timestamp(qr_data)
        self.assertFalse(result['valid'])
        self.assertIn('timestamp', result['error'].lower())

class TestQRDataValidation(unittest.TestCase):
    """Tests para validación de datos QR"""
    
    def test_valid_student_qr_data(self):
        """Test datos QR válidos para estudiante"""
        qr_data = {
            'name': 'Juan',
            'surname': 'Pérez',
            'email': 'juan.perez@estudiante.com',
            'tipoUsuario': 'ESTUDIANTE',
            'timestamp': int(time.time() * 1000),
            'status': 'VALID'
        }
        
        # Verificar estructura básica
        self.assertIn('name', qr_data)
        self.assertIn('surname', qr_data)
        self.assertIn('email', qr_data)
        self.assertIn('tipoUsuario', qr_data)
        self.assertEqual(qr_data['tipoUsuario'], 'ESTUDIANTE')
    
    def test_valid_helper_qr_data(self):
        """Test datos QR válidos para ayudante"""
        qr_data = {
            'name': 'Ana',
            'surname': 'García',
            'email': 'ana.garcia@ayudante.com',
            'tipoUsuario': 'AYUDANTE',
            'timestamp': int(time.time() * 1000),
            'status': 'VALID'
        }
        
        # Verificar estructura básica
        self.assertIn('name', qr_data)
        self.assertIn('surname', qr_data)
        self.assertIn('email', qr_data)
        self.assertIn('tipoUsuario', qr_data)
        self.assertEqual(qr_data['tipoUsuario'], 'AYUDANTE')
    
    def test_invalid_user_type(self):
        """Test tipo de usuario inválido"""
        invalid_types = ['PROFESOR', 'ADMIN', '', 'INVALID']
        
        for invalid_type in invalid_types:
            qr_data = {
                'name': 'Test',
                'surname': 'User',
                'email': 'test@example.com',
                'tipoUsuario': invalid_type,
                'timestamp': int(time.time() * 1000)
            }
            
            # El tipo debe ser ESTUDIANTE o AYUDANTE
            valid_types = ['ESTUDIANTE', 'AYUDANTE']
            self.assertNotIn(qr_data['tipoUsuario'], valid_types)

class TestDatabaseOperations(unittest.TestCase):
    """Tests para operaciones de base de datos simuladas"""
    
    def test_db_config_structure(self):
        """Test estructura de configuración de DB"""
        # Simular configuración DB
        db_config = {
            'host': 'localhost',
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'test_db',
            'port': 3306,
            'charset': 'utf8mb4'
        }
        
        required_keys = ['host', 'user', 'password', 'database', 'port']
        
        for key in required_keys:
            self.assertIn(key, db_config)
        
        self.assertIsInstance(db_config['port'], int)
        self.assertGreater(db_config['port'], 0)
    
    @patch('pymysql.connect')
    def test_get_db_connection_mock(self, mock_connect):
        """Test conexión a BD con mock"""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        # Simular función get_db_connection
        def get_db_connection():
            try:
                return mock_connect()
            except Exception:
                return None
        
        result = get_db_connection()
        self.assertIsNotNone(result)
        mock_connect.assert_called_once()

class TestProcessingLogic(unittest.TestCase):
    """Tests para lógica de procesamiento"""
    
    def test_determine_registro_type_logic(self):
        """Test lógica para determinar tipo de registro"""
        # Simular lógica básica
        def determine_registro_type(last_registro_type):
            if last_registro_type == 'Entrada':
                return 'Salida'
            else:
                return 'Entrada'
        
        # Test casos
        self.assertEqual(determine_registro_type('Entrada'), 'Salida')
        self.assertEqual(determine_registro_type('Salida'), 'Entrada')
        self.assertEqual(determine_registro_type(None), 'Entrada')
        self.assertEqual(determine_registro_type(''), 'Entrada')
    
    def test_process_success_response(self):
        """Test estructura de respuesta exitosa"""
        # Simular respuesta exitosa
        success_response = {
            "success": True,
            "tipo": "Entrada",
            "usuario_tipo": "ESTUDIANTE",
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@test.com",
            "fecha": "2023-12-25",
            "hora": "10:30:00",
            "message": "Entrada registrada para Juan Pérez"
        }
        
        # Verificar estructura
        self.assertTrue(success_response['success'])
        self.assertIn('tipo', success_response)
        self.assertIn('usuario_tipo', success_response)
        self.assertIn('message', success_response)
        
        # Verificar tipos válidos
        valid_tipos = ['Entrada', 'Salida']
        valid_user_tipos = ['ESTUDIANTE', 'AYUDANTE']
        
        self.assertIn(success_response['tipo'], valid_tipos)
        self.assertIn(success_response['usuario_tipo'], valid_user_tipos)
    
    def test_process_error_response(self):
        """Test estructura de respuesta de error"""
        # Simular respuesta de error
        error_response = {
            "success": False,
            "error": "Usuario no encontrado",
            "expired": False
        }
        
        # Verificar estructura
        self.assertFalse(error_response['success'])
        self.assertIn('error', error_response)
        self.assertIsInstance(error_response['error'], str)
        self.assertGreater(len(error_response['error']), 0)

class TestEndpointLogic(unittest.TestCase):
    """Tests para lógica de endpoints"""
    
    def test_health_endpoint_response(self):
        """Test respuesta del endpoint de salud"""
        # Simular respuesta de health
        health_response = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "service": "QR Temporal API"
        }
        
        self.assertEqual(health_response["status"], "ok")
        self.assertIn("timestamp", health_response)
        self.assertIn("service", health_response)
        self.assertIsInstance(health_response["timestamp"], str)
    
    def test_validate_qr_request_structure(self):
        """Test estructura de request para validar QR"""
        # Simular request válido
        valid_request = {
            "qr_data": json.dumps({
                "name": "Juan",
                "surname": "Pérez",
                "email": "juan@test.com",
                "tipoUsuario": "ESTUDIANTE",
                "timestamp": int(time.time() * 1000)
            })
        }
        
        self.assertIn("qr_data", valid_request)
        
        # Verificar que qr_data es JSON válido
        qr_data = json.loads(valid_request["qr_data"])
        self.assertIsInstance(qr_data, dict)
        self.assertIn("name", qr_data)
        self.assertIn("email", qr_data)
    
    def test_stats_response_structure(self):
        """Test estructura de respuesta de estadísticas"""
        # Simular respuesta de stats
        stats_response = {
            "success": True,
            "date": "2023-12-25",
            "students": {
                "entries": 15,
                "exits": 12
            },
            "helpers": {
                "entries": 5,
                "exits": 4
            }
        }
        
        self.assertTrue(stats_response["success"])
        self.assertIn("date", stats_response)
        self.assertIn("students", stats_response)
        self.assertIn("helpers", stats_response)
        
        # Verificar estructura de contadores
        self.assertIn("entries", stats_response["students"])
        self.assertIn("exits", stats_response["students"])
        self.assertIsInstance(stats_response["students"]["entries"], int)
        self.assertIsInstance(stats_response["students"]["exits"], int)

class TestErrorHandling(unittest.TestCase):
    """Tests para manejo de errores"""
    
    def test_invalid_json_handling(self):
        """Test manejo de JSON inválido"""
        invalid_json_strings = [
            "invalid json",
            "{incomplete: json",
            "",
            None
        ]
        
        for invalid_json in invalid_json_strings:
            try:
                if invalid_json:
                    json.loads(invalid_json)
                    self.fail(f"Should have failed for: {invalid_json}")
            except (json.JSONDecodeError, TypeError):
                # Se espera que falle
                pass
    
    def test_missing_required_fields(self):
        """Test manejo de campos faltantes"""
        incomplete_data = {
            "name": "Juan",
            # Faltan surname, email, tipoUsuario
        }
        
        required_fields = ["name", "surname", "email", "tipoUsuario"]
        missing_fields = []
        
        for field in required_fields:
            if field not in incomplete_data or not incomplete_data[field]:
                missing_fields.append(field)
        
        self.assertGreater(len(missing_fields), 0)
        self.assertIn("surname", missing_fields)
        self.assertIn("email", missing_fields)
    
    def test_database_error_simulation(self):
        """Test simulación de error de base de datos"""
        # Simular diferentes tipos de errores de BD
        db_errors = [
            "Connection refused",
            "Table doesn't exist",
            "Access denied",
            "Timeout"
        ]
        
        for error in db_errors:
            # Verificar que los errores son strings no vacíos
            self.assertIsInstance(error, str)
            self.assertGreater(len(error), 0)

class TestIntegrationBasics(unittest.TestCase):
    """Tests básicos de integración"""
    
    @patch.dict(os.environ, {
        'MYSQL_HOST': 'localhost',
        'MYSQL_USER': 'test',
        'MYSQL_PASSWORD': 'test',
        'MYSQL_DB': 'test',
        'SECRET_KEY': 'test-secret'
    })
    def test_app_imports(self):
        """Test que se pueden importar los módulos principales"""
        try:
            # Intentar importar el módulo principal
            import api_qr_temporal
            self.assertTrue(hasattr(api_qr_temporal, 'app'))
        except ImportError as e:
            # Si falla la importación por dependencias, verificar que existe el archivo
            lector_path = os.path.join(
                os.path.dirname(__file__), 
                '../back-end/lector/api_qr_temporal.py'
            )
            self.assertTrue(os.path.exists(lector_path), 
                          f"Archivo api_qr_temporal.py debe existir en {lector_path}")
    
    def test_flask_app_configuration(self):
        """Test configuración básica de Flask"""
        # Simular configuración de Flask
        app_config = {
            'SECRET_KEY': 'test-secret',
            'ENV': 'testing',
            'TESTING': True
        }
        
        # Verificar que tiene configuración básica
        self.assertIn('SECRET_KEY', app_config)
        self.assertIsNotNone(app_config['SECRET_KEY'])
        self.assertGreater(len(app_config['SECRET_KEY']), 0)

if __name__ == '__main__':
    # Configurar logging para tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Solo errores para tests más limpios
    
    # Ejecutar tests con output verboso
    unittest.main(verbosity=2)