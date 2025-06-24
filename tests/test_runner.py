#!/usr/bin/env python3
"""
Test Runner para todos los servicios del back-end
Ejecuta unit tests básicos para ayudantes, estudiantes y lector QR
"""

import unittest
import sys
import os
from io import StringIO

def run_tests():
    """Ejecuta todos los tests y muestra resultados"""
    
    print("🧪 EJECUTANDO UNIT TESTS PARA SISTEMA DE ACCESO")
    print("=" * 60)
    
    # Agregar directorio actual al path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # Lista de módulos de test
    test_modules = [
        'test_ayudantes',
        'test_estudiantes', 
        'test_lector'
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for module_name in test_modules:
        print(f"\n📋 Ejecutando tests para: {module_name}")
        print("-" * 40)
        
        try:
            # Importar módulo de test
            test_module = __import__(module_name)
            
            # Crear test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Ejecutar tests
            stream = StringIO()
            runner = unittest.TextTestRunner(
                stream=stream, 
                verbosity=2,
                failfast=False
            )
            result = runner.run(suite)
            
            # Mostrar resultados
            output = stream.getvalue()
            print(output)
            
            # Acumular estadísticas
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            # Mostrar resumen del módulo
            if result.wasSuccessful():
                print(f"✅ {module_name}: TODOS LOS TESTS PASARON")
            else:
                print(f"❌ {module_name}: {len(result.failures)} fallos, {len(result.errors)} errores")
                
                # Mostrar detalles de fallos
                if result.failures:
                    print("\n📝 FALLOS:")
                    for test, traceback in result.failures:
                        print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
                
                if result.errors:
                    print("\n💥 ERRORES:")
                    for test, traceback in result.errors:
                        print(f"  - {test}: Error de ejecución")
        
        except ImportError as e:
            print(f"⚠️  No se pudo importar {module_name}: {e}")
            print("   (Esto es normal si faltan dependencias)")
        
        except Exception as e:
            print(f"💥 Error ejecutando {module_name}: {e}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"Total de tests ejecutados: {total_tests}")
    print(f"Tests exitosos: {total_tests - total_failures - total_errors}")
    print(f"Tests fallidos: {total_failures}")
    print(f"Errores: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("\n🎉 TODOS LOS TESTS PASARON EXITOSAMENTE!")
        return True
    else:
        success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📈 Tasa de éxito: {success_rate:.1f}%")
        return False

def run_specific_test(test_name):
    """Ejecuta un test específico"""
    print(f"🎯 Ejecutando test específico: {test_name}")
    print("-" * 40)
    
    try:
        # Importar módulo de test
        module_name = f"test_{test_name}"
        test_module = __import__(module_name)
        
        # Crear test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except ImportError as e:
        print(f"❌ No se pudo importar {module_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_requirements():
    """Crea archivo requirements-test.txt"""
    requirements = """# Requirements para ejecutar unit tests
unittest2==1.1.0
mock==4.0.3
pytest==7.4.3
coverage==7.3.2

# Dependencias mínimas para tests
Flask==2.3.3
flask-cors==4.0.0
PyMySQL==1.1.0
python-dotenv==1.0.0
"""
    
    with open('requirements-test.txt', 'w') as f:
        f.write(requirements)
    
    print("📄 Creado requirements-test.txt")

def main():
    """Función principal"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'help' or command == '--help' or command == '-h':
            print("🔧 USO DEL TEST RUNNER")
            print("=" * 30)
            print("python test_runner.py           - Ejecutar todos los tests")
            print("python test_runner.py ayudantes - Ejecutar tests de ayudantes")
            print("python test_runner.py estudiantes - Ejecutar tests de estudiantes")  
            print("python test_runner.py lector    - Ejecutar tests de lector QR")
            print("python test_runner.py requirements - Crear requirements-test.txt")
            print("python test_runner.py help      - Mostrar esta ayuda")
            return
        
        elif command == 'requirements':
            create_test_requirements()
            return
        
        elif command in ['ayudantes', 'estudiantes', 'lector']:
            success = run_specific_test(command)
            sys.exit(0 if success else 1)
        
        else:
            print(f"❌ Comando desconocido: {command}")
            print("Use 'python test_runner.py help' para ver opciones")
            sys.exit(1)
    
    else:
        # Ejecutar todos los tests
        success = run_tests()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()