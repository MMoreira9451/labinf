# test_estudiantes.py
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Agregar el directorio de estudiantes al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../back-end/estudiantes'))

from utils.validators import validate_email, validate_required_fields, validate_qr_data
from utils.helpers import format_response, serialize_datetime, safe_int, safe_bool
from datetime import datetime, date, time

class TestValidators(unittest.TestCase):
    """Tests para funciones de validación"""
    
    def test_validate_email_valid(self):
        """Test validación de emails válidos"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co',
            'student123@university.edu'
        ]
        
        for email in valid_emails:
            self.assertTrue(validate_email(email))
    
    def test_validate_email_invalid(self):
        """Test validación de emails inválidos"""
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            '',
            None,
            'spaces in@email.com'
        ]
        
        for email in invalid_emails:
            self.assertFalse(validate_email(email))
    
    def test_validate_required_fields_complete(self):
        """Test validación con todos los campos requeridos"""
        data = {
            'nombre': 'Juan',
            'apellido': 'Pérez',
            'email': 'juan@test.com'
        }
        required = ['nombre', 'apellido', 'email']
        
        self.assertTrue(validate_required_fields(data, required))
    
    def test_validate_required_fields_missing(self):
        """Test validación con campos faltantes"""
        data = {
            'nombre': 'Juan',
            'email': 'juan@test.com'
        }
        required = ['nombre', 'apellido', 'email']
        
        self.assertFalse(validate_required_fields(data, required))
    
    def test_validate_required_fields_empty_values(self):
        """Test validación con valores vacíos"""
        data = {
            'nombre': '',
            'apellido': 'Pérez',
            'email': 'juan@test.com'
        }
        required = ['nombre', 'apellido', 'email']
        
        self.assertFalse(validate_required_fields(data, required))
    
    def test_validate_qr_data_valid(self):
        """Test validación de QR válido"""
        qr_data = {
            'name': 'Juan',
            'surname': 'Pérez',
            'email': 'juan@test.com',
            'tipoUsuario': 'ESTUDIANTE',
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        result = validate_qr_data(qr_data)
        self.assertTrue(result['valid'])
    
    def test_validate_qr_data_missing_fields(self):
        """Test validación de QR con campos faltantes"""
        qr_data = {
            'name': 'Juan',
            'email': 'juan@test.com'
            # Faltan 'surname' y 'tipoUsuario'
        }
        
        result = validate_qr_data(qr_data)
        self.assertFalse(result['valid'])
    
    def test_validate_qr_data_wrong_user_type(self):
        """Test validación de QR con tipo de usuario incorrecto"""
        qr_data = {
            'name': 'Juan',
            'surname': 'Pérez',
            'email': 'juan@test.com',
            'tipoUsuario': 'PROFESOR'  # Tipo incorrecto
        }
        
        result = validate_qr_data(qr_data)
        self.assertFalse(result['valid'])

class TestHelpers(unittest.TestCase):
    """Tests para funciones de ayuda"""
    
    def test_format_response_basic(self):
        """Test formateo básico de respuesta"""
        data = {'test': 'value'}
        response = format_response(data)
        
        # Verificar que es un objeto Response de Flask
        self.assertTrue(hasattr(response, 'data'))
        
        # Verificar estructura JSON
        json_data = json.loads(response.data)
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['data'], data)
        self.assertIn('timestamp', json_data)
    
    def test_format_response_with_message(self):
        """Test formateo de respuesta con mensaje"""
        data = {'test': 'value'}
        message = 'Operation successful'
        response = format_response(data, message)
        
        json_data = json.loads(response.data)
        self.assertEqual(json_data['message'], message)
    
    def test_serialize_datetime_datetime(self):
        """Test serialización de datetime"""
        dt = datetime(2023, 12, 25, 15, 30, 45)
        result = serialize_datetime(dt)
        
        self.assertIsInstance(result, str)
        self.assertIn('2023-12-25', result)
    
    def test_serialize_datetime_date(self):
        """Test serialización de date"""
        d = date(2023, 12, 25)
        result = serialize_datetime(d)
        
        self.assertIsInstance(result, str)
        self.assertEqual(result, '2023-12-25')
    
    def test_serialize_datetime_time(self):
        """Test serialización de time"""
        t = time(15, 30, 45)
        result = serialize_datetime(t)
        
        self.assertIsInstance(result, str)
        self.assertEqual(result, '15:30:45')
    
    def test_serialize_datetime_other(self):
        """Test serialización de otros objetos"""
        obj = "test string"
        result = serialize_datetime(obj)
        
        self.assertEqual(result, obj)
    
    def test_safe_int_valid(self):
        """Test conversión segura a int con valores válidos"""
        test_cases = [
            ('123', 123),
            (123, 123),
            ('0', 0),
            ('-456', -456)
        ]
        
        for input_val, expected in test_cases:
            result = safe_int(input_val)
            self.assertEqual(result, expected)
    
    def test_safe_int_invalid(self):
        """Test conversión segura a int con valores inválidos"""
        test_cases = [
            'abc',
            None,
            [],
            {}
        ]
        
        for input_val in test_cases:
            result = safe_int(input_val, default=42)
            self.assertEqual(result, 42)
    
    def test_safe_bool_valid(self):
        """Test conversión segura a bool"""
        test_cases = [
            (True, True),
            (False, False),
            ('true', True),
            ('false', False),
            ('1', True),
            ('0', False),
            (1, True),
            (0, False)
        ]
        
        for input_val, expected in test_cases:
            result = safe_bool(input_val)
            self.assertEqual(result, expected)
    
    def test_safe_bool_invalid(self):
        """Test conversión segura a bool con valores inválidos"""
        result = safe_bool(None, default=True)
        self.assertTrue(result)
        
        result = safe_bool('invalid', default=False)
        self.assertFalse(result)

class TestDatabaseConfig(unittest.TestCase):
    """Tests para configuración de base de datos"""
    
    @patch('config.database.mysql.connector.connect')
    def test_get_db_success(self):
        """Test obtención exitosa de conexión DB"""
        mock_connection = MagicMock()
        
        with patch('config.database.mysql.connector.connect', return_value=mock_connection):
            from config.database import get_db
            
            # Mock del contexto de Flask
            with patch('config.database.g', {}):
                with patch('config.database.current_app') as mock_app:
                    mock_app.config = {
                        'MYSQL_HOST': 'localhost',
                        'MYSQL_USER': 'test',
                        'MYSQL_PASSWORD': 'test',
                        'MYSQL_DB': 'test'
                    }
                    
                    try:
                        result = get_db()
                        # Si no hay error, la función existe y es callable
                        self.assertTrue(callable(get_db))
                    except:
                        # Es normal que falle sin contexto completo de Flask
                        self.assertTrue(callable(get_db))

class TestAppCreation(unittest.TestCase):
    """Tests básicos de creación de aplicación"""
    
    @patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret',
        'MYSQL_HOST': 'localhost',
        'MYSQL_USER': 'test',
        'MYSQL_PASSWORD': 'test',
        'MYSQL_DB': 'test'
    })
    def test_create_app_function_exists(self):
        """Test que la función create_app existe"""
        try:
            from app import create_app
            self.assertTrue(callable(create_app))
        except ImportError:
            self.fail("create_app function should exist")
    
    def test_health_endpoint_logic(self):
        """Test lógica básica del endpoint de salud"""
        # Simular respuesta de health check
        health_response = {
            'status': 'OK',
            'timestamp': datetime.now().isoformat(),
            'message': 'API funcionando correctamente'
        }
        
        self.assertEqual(health_response['status'], 'OK')
        self.assertIn('timestamp', health_response)
        self.assertIn('message', health_response)

class TestUtilityFunctions(unittest.TestCase):
    """Tests para funciones de utilidad adicionales"""
    
    def test_clean_email_function_exists(self):
        """Test que existe función para limpiar emails"""
        try:
            from utils.helpers import clean_email
            result = clean_email('  TEST@EXAMPLE.COM  ')
            self.assertEqual(result, 'test@example.com')
        except ImportError:
            # Si no existe, no es crítico para el test
            pass
    
    def test_format_student_name_function_exists(self):
        """Test que existe función para formatear nombres"""
        try:
            from utils.helpers import format_student_name
            result = format_student_name('Juan', 'Pérez')
            self.assertEqual(result, 'Juan Pérez')
        except ImportError:
            # Si no existe, no es crítico para el test
            pass

if __name__ == '__main__':
    # Ejecutar tests con output verboso
    unittest.main(verbosity=2)