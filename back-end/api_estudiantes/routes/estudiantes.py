# routes/estudiantes.py - Rutas para manejo de estudiantes
from flask import Blueprint, request, jsonify
from config.database import execute_query
from utils.validators import validate_email, validate_required_fields
from utils.helpers import format_response, handle_error
import logging

estudiantes_bp = Blueprint('estudiantes', __name__)

@estudiantes_bp.route('/estudiantes_presentes/estudiantes', methods=['GET'])
def get_estudiantes():
    """Obtiene la lista de todos los estudiantes"""
    try:
        query = """
        SELECT 
            ue.id,
            ue.nombre,
            ue.apellido,
            ue.email,
            ue.activo as estado,
            ue.TP as carrera,
            CASE 
                WHEN er.email IS NOT NULL AND DATE(er.fecha) = CURDATE() 
                THEN 1 
                ELSE 0 
            END as presente
        FROM usuarios_estudiantes ue
        LEFT JOIN (
            SELECT email, fecha, 
                   ROW_NUMBER() OVER (PARTITION BY email ORDER BY fecha DESC, hora DESC) as rn
            FROM EST_registros 
            WHERE tipo = 'Entrada'
        ) er ON ue.email = er.email AND er.rn = 1
        ORDER BY ue.apellido, ue.nombre
        """
        
        estudiantes = execute_query(query)
        
        # Formatear respuesta
        formatted_estudiantes = []
        for est in estudiantes:
            formatted_estudiantes.append({
                'id': str(est['id']),
                'nombre': est['nombre'],
                'apellido': est['apellido'],
                'rut': '',  # No hay RUT en la DB actual
                'carrera': est['carrera'] or '',
                'email': est['email'],
                'estado': 'activo' if est['estado'] else 'inactivo',
                'presente': bool(est['presente'])
            })
        
        return format_response(formatted_estudiantes)
        
    except Exception as e:
        return handle_error(e, "Error al obtener estudiantes")

@estudiantes_bp.route('/estudiantes_presentes/estudiantes/<estudiante_id>/presente', methods=['POST'])
def toggle_presente(estudiante_id):
    """Cambia el estado de presencia de un estudiante"""
    try:
        data = request.get_json()
        presente = data.get('presente', False)
        
        # Obtener datos del estudiante
        query_estudiante = "SELECT * FROM usuarios_estudiantes WHERE id = %s"
        estudiante = execute_query(query_estudiante, (estudiante_id,), fetch_one=True)
        
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Si se marca como presente, registrar entrada
        if presente:
            query_insert = """
            INSERT INTO EST_registros (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado)
            VALUES (CURDATE(), CURTIME(), DAYNAME(CURDATE()), %s, %s, %s, 'Entrada', 1)
            """
            execute_query(query_insert, (
                estudiante['nombre'],
                estudiante['apellido'],
                estudiante['email']
            ))
        else:
            # Si se marca como ausente, registrar salida
            query_insert = """
            INSERT INTO EST_registros (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado)
            VALUES (CURDATE(), CURTIME(), DAYNAME(CURDATE()), %s, %s, %s, 'Salida', 1)
            """
            execute_query(query_insert, (
                estudiante['nombre'],
                estudiante['apellido'],
                estudiante['email']
            ))
        
        return format_response({'success': True, 'presente': presente})
        
    except Exception as e:
        return handle_error(e, "Error al cambiar estado de presencia")

@estudiantes_bp.route('/estudiantes', methods=['POST'])
def create_estudiante():
    """Crea un nuevo estudiante"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['nombre', 'apellido', 'email']
        if not validate_required_fields(data, required_fields):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Validar email
        if not validate_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        # Verificar si el email ya existe
        query_exists = "SELECT id FROM usuarios_estudiantes WHERE email = %s"
        existing = execute_query(query_exists, (data['email'],), fetch_one=True)
        
        if existing:
            return jsonify({'error': 'Ya existe un estudiante con ese email'}), 409
        
        # Insertar nuevo estudiante
        query_insert = """
        INSERT INTO usuarios_estudiantes (nombre, apellido, email, activo, TP)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        result = execute_query(query_insert, (
            data['nombre'].strip(),
            data['apellido'].strip(),
            data['email'].strip().lower(),
            data.get('activo', True),
            data.get('carrera', '')
        ))
        
        return format_response({
            'id': result['last_insert_id'],
            'mensaje': 'Estudiante creado exitosamente'
        }), 201
        
    except Exception as e:
        return handle_error(e, "Error al crear estudiante")

@estudiantes_bp.route('/estudiantes/<estudiante_id>', methods=['GET'])
def get_estudiante(estudiante_id):
    """Obtiene los detalles de un estudiante específico"""
    try:
        query = """
        SELECT 
            ue.*,
            CASE 
                WHEN er.email IS NOT NULL AND DATE(er.fecha) = CURDATE() 
                THEN 1 
                ELSE 0 
            END as presente
        FROM usuarios_estudiantes ue
        LEFT JOIN (
            SELECT email, fecha,
                   ROW_NUMBER() OVER (PARTITION BY email ORDER BY fecha DESC, hora DESC) as rn
            FROM EST_registros 
            WHERE tipo = 'Entrada'
        ) er ON ue.email = er.email AND er.rn = 1
        WHERE ue.id = %s
        """
        
        estudiante = execute_query(query, (estudiante_id,), fetch_one=True)
        
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Obtener historial de registros reciente
        query_registros = """
        SELECT fecha, hora, tipo 
        FROM EST_registros 
        WHERE email = %s 
        ORDER BY fecha DESC, hora DESC 
        LIMIT 10
        """
        
        registros = execute_query(query_registros, (estudiante['email'],))
        
        response_data = {
            'id': str(estudiante['id']),
            'nombre': estudiante['nombre'],
            'apellido': estudiante['apellido'],
            'email': estudiante['email'],
            'carrera': estudiante['TP'] or '',
            'activo': bool(estudiante['activo']),
            'presente': bool(estudiante['presente']),
            'registros_recientes': [{
                'fecha': reg['fecha'].strftime('%Y-%m-%d'),
                'hora': str(reg['hora']),
                'tipo': reg['tipo']
            } for reg in registros]
        }
        
        return format_response(response_data)
        
    except Exception as e:
        return handle_error(e, "Error al obtener estudiante")

@estudiantes_bp.route('/estudiantes/<estudiante_id>', methods=['PUT'])
def update_estudiante(estudiante_id):
    """Actualiza los datos de un estudiante"""
    try:
        data = request.get_json()
        
        # Verificar que el estudiante existe
        query_exists = "SELECT id FROM usuarios_estudiantes WHERE id = %s"
        existing = execute_query(query_exists, (estudiante_id,), fetch_one=True)
        
        if not existing:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Construir consulta de actualización dinámicamente
        update_fields = []
        params = []
        
        if 'nombre' in data:
            update_fields.append("nombre = %s")
            params.append(data['nombre'].strip())
        
        if 'apellido' in data:
            update_fields.append("apellido = %s")
            params.append(data['apellido'].strip())
        
        if 'email' in data:
            if not validate_email(data['email']):
                return jsonify({'error': 'Email inválido'}), 400
            update_fields.append("email = %s")
            params.append(data['email'].strip().lower())
        
        if 'carrera' in data:
            update_fields.append("TP = %s")
            params.append(data['carrera'])
        
        if 'activo' in data:
            update_fields.append("activo = %s")
            params.append(data['activo'])
        
        if not update_fields:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        params.append(estudiante_id)
        
        query_update = f"""
        UPDATE usuarios_estudiantes 
        SET {', '.join(update_fields)}
        WHERE id = %s
        """
        
        execute_query(query_update, params)
        
        return format_response({'mensaje': 'Estudiante actualizado exitosamente'})
        
    except Exception as e:
        return handle_error(e, "Error al actualizar estudiante")

@estudiantes_bp.route('/estudiantes/<estudiante_id>', methods=['DELETE'])
def delete_estudiante(estudiante_id):
    """Elimina un estudiante (soft delete)"""
    try:
        # Verificar que el estudiante existe
        query_exists = "SELECT id FROM usuarios_estudiantes WHERE id = %s"
        existing = execute_query(query_exists, (estudiante_id,), fetch_one=True)
        
        if not existing:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Marcar como inactivo en lugar de eliminar
        query_delete = "UPDATE usuarios_estudiantes SET activo = 0 WHERE id = %s"
        execute_query(query_delete, (estudiante_id,))
        
        return format_response({'mensaje': 'Estudiante desactivado exitosamente'})
        
    except Exception as e:
        return handle_error(e, "Error al eliminar estudiante")