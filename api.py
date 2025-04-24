import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from datetime import datetime, timedelta, date
import json
import ssl  # Importamos el módulo SSL
import pytz  # Agregamos pytz para manejo de timezone

app = Flask(__name__)
CORS(app)

# Define your timezone - ajusta esto a tu zona horaria
TIMEZONE = pytz.timezone('America/Santiago')

# Custom function to get current time in the correct timezone
def get_current_datetime():
    return datetime.now(pytz.utc).astimezone(TIMEZONE)

# Clase para manejar la serialización de objetos datetime y timedelta
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            # Convertir timedelta a segundos
            return str(obj)
        return super().default(obj)

# Configurar Flask para usar nuestro encoder personalizado
from flask.json.provider import JSONProvider

class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)
    
    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)

# --- CONFIGURACIÓN DE CONEXIÓN ---
DB_CONFIG = {
    'host': '10.0.3.54',  # Actualizado a la nueva IP
    'user': 'mm',
    'password': 'Gin160306',
    'database': 'registro_qr',
    'port': 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**DB_CONFIG)

# --- ENDPOINT: Obtener todos los registros ---
@app.route('/registros', methods=['GET'])
def get_registros():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM registros ORDER BY fecha DESC, hora DESC")
            registros = cursor.fetchall()
            
            # Convertir manualmente cualquier valor problemático
            for reg in registros:
                for key, value in reg.items():
                    # Convertir datetime a string si es necesario
                    if isinstance(value, datetime):
                        reg[key] = value.isoformat()
                    # Convertir timedelta a string si es necesario
                    elif isinstance(value, timedelta):
                        reg[key] = str(value)
        
        conn.close()
        return jsonify(registros)
    except Exception as e:
        print(f"Error en get_registros: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Registros de Hoy ---
@app.route('/registros_hoy', methods=['GET'])
def get_registros_hoy():
    try:
        conn = get_connection()
        # Usar la función timezone-aware para obtener la fecha actual
        today = get_current_datetime().strftime('%Y-%m-%d')
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, fecha, hora, dia, nombre, apellido, email
                FROM registros 
                WHERE fecha = %s 
                ORDER BY hora DESC
            """, (today,))
            registros = cursor.fetchall()
            
            # Convertir manualmente cualquier objeto date a string
            serializable_registros = []
            for reg in registros:
                serializable_reg = {}
                for key, value in reg.items():
                    # Convertir objetos date a string
                    if isinstance(value, datetime):
                        serializable_reg[key] = value.isoformat()
                    elif isinstance(value, timedelta):
                        serializable_reg[key] = str(value)
                    # También manejar el tipo date específicamente
                    elif hasattr(value, 'isoformat') and callable(value.isoformat):
                        serializable_reg[key] = value.isoformat()
                    else:
                        serializable_reg[key] = value
                serializable_registros.append(serializable_reg)
            
        conn.close()
        # Asegurarnos de que siempre devolvemos una lista, incluso vacía
        return jsonify(serializable_registros if serializable_registros else [])
    except Exception as e:
        print(f"Error al obtener registros de hoy: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
# --- ENDPOINT: Insertar nuevo registro ---
@app.route('/registros', methods=['POST'])
def add_registro():
    data = request.get_json()
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Obtener fecha y hora actuales si no se proporcionan
            now = get_current_datetime()
            fecha = data.get('fecha', now.strftime("%Y-%m-%d"))
            hora = data.get('hora', now.strftime("%H:%M:%S"))
            
            # Mapeo de días de la semana (inglés -> español)
            dias = {
                'Monday': 'lunes',
                'Tuesday': 'martes',
                'Wednesday': 'miércoles',
                'Thursday': 'jueves',
                'Friday': 'viernes',
                'Saturday': 'sábado',
                'Sunday': 'domingo'
            }
            
            # Obtener día de la semana en español
            if 'dia' in data and data['dia']:
                dia = data['dia']
            else:
                day_name = now.strftime("%A")  # Nombre del día en inglés
                dia = dias.get(day_name, day_name)  # Traducir a español
            
            query = "INSERT INTO registros (fecha, hora, dia, nombre, apellido, email) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (
                fecha,
                hora,
                dia,
                data['nombre'],
                data['apellido'],
                data['email']
            ))
            conn.commit()
            registro_id = cursor.lastrowid
        conn.close()
        return jsonify({"message": "Registro agregado correctamente", "id": registro_id})
    except Exception as e:
        print(f"Error al añadir registro: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Lista de usuarios permitidos ---
@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()
        conn.close()
        return jsonify(usuarios)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Horarios asignados ---
@app.route('/horarios', methods=['GET'])
def get_horarios():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT h.id, h.usuario_id, u.nombre, u.apellido, u.email, h.dia, h.hora_entrada, h.hora_salida
                FROM horarios_asignados h
                JOIN usuarios_permitidos u ON h.usuario_id = u.id
            """
            cursor.execute(query)
            horarios = cursor.fetchall()
        conn.close()
        return jsonify(horarios)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Cumplimiento CORREGIDO ---
@app.route('/cumplimiento', methods=['GET'])
def get_cumplimiento():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Preparar diccionario de traducción de días una sola vez
            dias_traduccion = {
                'monday': 'lunes', 
                'tuesday': 'martes', 
                'wednesday': 'miércoles',
                'thursday': 'jueves', 
                'friday': 'viernes', 
                'saturday': 'sábado', 
                'sunday': 'domingo'
            }
            
            # Obtener información de fecha actual con la zona horaria correcta
            now = get_current_datetime()
            dia_actual = now.strftime('%A').lower()  # Día en inglés: 'monday', 'tuesday', etc.
            dia_actual_esp = dias_traduccion.get(dia_actual, dia_actual)
            hora_actual = now.strftime('%H:%M:%S')
            fecha_actual = now.strftime('%Y-%m-%d')
            
            # Obtener usuarios activos
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()

            cumplimiento = []

            for user in usuarios:
                cursor.execute("SELECT * FROM horarios_asignados WHERE usuario_id = %s", (user['id'],))
                horarios = cursor.fetchall()

                if not horarios:
                    cumplimiento.append({
                        "nombre": user['nombre'],
                        "apellido": user['apellido'],
                        "email": user['email'],
                        "estado": "No Aplica",
                        "bloques": [],
                        "bloques_info": []
                    })
                    continue

                bloques = []
                cumplidos = 0
                bloques_info = []  # Lista para almacenar información detallada de cada bloque

                for h in horarios:
                    bloque = f"{h['dia']} {h['hora_entrada']}-{h['hora_salida']}"
                    bloques.append(bloque)
                    
                    # Determinar estado del bloque
                    bloque_estado = "Ausente"  # Estado por defecto
                    
                    # CAMBIO: Obtener todos los registros del día para este bloque
                    if h['dia'].lower() == dia_actual_esp:
                        # Para el día actual, verificamos en la fecha actual
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s AND fecha = %s
                            ORDER BY hora
                        """, (user['email'], fecha_actual))
                    else:
                        # Para otros días, obtenemos registros históricos (de las últimas 2 semanas)
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s AND dia = %s AND fecha >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
                            ORDER BY fecha DESC, hora
                        """, (user['email'], h['dia']))
                    
                    registros_del_dia = cursor.fetchall()
                    
                    # Convertir horas de bloque a objetos datetime para comparación
                    hora_entrada_dt = datetime.strptime(h['hora_entrada'], "%H:%M:%S").time()
                    hora_salida_dt = datetime.strptime(h['hora_salida'], "%H:%M:%S").time()
                    
                    # CAMBIO: Considerar cumplido si hay registros que cruzan el bloque
                    if registros_del_dia:
                        # Verificar si algún registro está dentro del bloque o lo cubre
                        registros_en_bloque = False
                        
                        # Para cada par de registros (entrada-salida)
                        for i in range(0, len(registros_del_dia), 2):
                            if i + 1 < len(registros_del_dia):  # Asegurarse de que hay un par
                                # Obtener tiempos de entrada y salida
                                reg_entrada = registros_del_dia[i]
                                reg_salida = registros_del_dia[i + 1]
                                
                                # Convertir a objetos time
                                if isinstance(reg_entrada['hora'], str):
                                    reg_entrada_time = datetime.strptime(reg_entrada['hora'], "%H:%M:%S").time()
                                else:
                                    reg_entrada_time = reg_entrada['hora']
                                    
                                if isinstance(reg_salida['hora'], str):
                                    reg_salida_time = datetime.strptime(reg_salida['hora'], "%H:%M:%S").time()
                                else:
                                    reg_salida_time = reg_salida['hora']
                                
                                # CAMBIO PRINCIPAL: Verificar si la entrada-salida cubre el bloque
                                # Caso 1: Entrada antes del inicio y salida después del inicio
                                caso1 = reg_entrada_time <= hora_entrada_dt and reg_salida_time > hora_entrada_dt
                                
                                # Caso 2: Entrada después del inicio pero antes del fin
                                caso2 = (reg_entrada_time > hora_entrada_dt and 
                                         reg_entrada_time < hora_salida_dt)
                                
                                # Caso 3: Salida después del fin pero entrada antes del fin
                                caso3 = reg_salida_time >= hora_salida_dt and reg_entrada_time < hora_salida_dt
                                
                                # Caso 4: Completamente dentro del bloque
                                caso4 = (reg_entrada_time >= hora_entrada_dt and 
                                         reg_salida_time <= hora_salida_dt)
                                
                                # Si cualquier caso es cierto, el bloque está cubierto
                                if caso1 or caso2 or caso3 or caso4:
                                    registros_en_bloque = True
                                    break
                        
                        # Si es el día actual y la hora actual está dentro del bloque
                        if h['dia'].lower() == dia_actual_esp:
                            hora_actual_dt = datetime.strptime(hora_actual, "%H:%M:%S").time()
                            
                            if registros_en_bloque:
                                # Ya hay registros que cubren el bloque
                                if hora_actual_dt < hora_entrada_dt:
                                    bloque_estado = "Pendiente"
                                elif hora_entrada_dt <= hora_actual_dt < hora_salida_dt:
                                    bloque_estado = "Cumpliendo"
                                else:  # hora_actual >= hora_salida
                                    bloque_estado = "Cumplido"
                                    cumplidos += 1
                            else:
                                # No hay registros que cubran el bloque
                                if hora_actual_dt < hora_entrada_dt:
                                    bloque_estado = "Pendiente"
                                elif hora_entrada_dt <= hora_actual_dt < hora_salida_dt:
                                    bloque_estado = "Atrasado"
                                else:
                                    bloque_estado = "Ausente"
                        else:
                            # No es el día actual
                            if registros_en_bloque:
                                bloque_estado = "Cumplido"
                                cumplidos += 1
                            else:
                                bloque_estado = "Ausente"
                    else:
                        # No hay registros para este día/bloque
                        if h['dia'].lower() == dia_actual_esp:
                            hora_actual_dt = datetime.strptime(hora_actual, "%H:%M:%S").time()
                            if hora_actual_dt < hora_entrada_dt:
                                bloque_estado = "Pendiente"
                            elif hora_actual_dt >= hora_entrada_dt and hora_actual_dt < hora_salida_dt:
                                bloque_estado = "Atrasado"
                            else:
                                bloque_estado = "Ausente"
                        else:
                            bloque_estado = "Ausente"
                            
                    # Añadir información de este bloque a la lista
                    bloques_info.append({
                        "bloque": bloque,
                        "estado": bloque_estado
                    })

                # Determinar estado general
                if cumplidos == len(horarios):
                    estado = "Cumple"
                elif cumplidos > 0:
                    estado = "En Curso"
                else:
                    # Verificar si hay bloques pendientes (solo para el día actual)
                    pendientes = sum(1 for b in bloques_info if b["estado"] == "Pendiente")
                    cumpliendo = sum(1 for b in bloques_info if b["estado"] == "Cumpliendo")
                    
                    if pendientes > 0 or cumpliendo > 0:
                        estado = "En Curso"
                    else:
                        estado = "No Cumple"

                # Añadir entrada al resultado
                cumplimiento.append({
                    "nombre": user['nombre'],
                    "apellido": user['apellido'],
                    "email": user['email'],
                    "estado": estado,
                    "bloques": bloques,
                    "bloques_info": bloques_info  # Incluir información detallada de cada bloque
                })

        conn.close()
        return jsonify(cumplimiento)
    except Exception as e:
        print(f"Error en cumplimiento: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Ayudantes presentes ---
@app.route('/ayudantes_presentes', methods=['GET'])
def get_ayudantes_presentes():
    try:
        conn = get_connection()
        # Usar la función timezone-aware para obtener la fecha actual
        today = get_current_datetime().strftime('%Y-%m-%d')
        
        with conn.cursor() as cursor:
            # Obtenemos todos los registros de hoy ordenados por email y hora
            cursor.execute("""
                SELECT r.id, r.email, r.nombre, r.apellido, r.hora, r.fecha
                FROM registros r
                WHERE r.fecha = %s
                ORDER BY r.email, r.hora
            """, (today,))
            
            todos_registros = cursor.fetchall()
            
            # Procesamos los registros para determinar quién está dentro
            ayudantes_presentes = {}
            for registro in todos_registros:
                email = registro['email']
                
                # Si es un número par de entradas para este email, está dentro
                # Si es impar, está fuera
                if email in ayudantes_presentes:
                    # Ya existe, así que esta entrada podría ser una salida
                    ayudantes_presentes[email]['dentro'] = not ayudantes_presentes[email]['dentro']
                    ayudantes_presentes[email]['ultima_hora'] = registro['hora']
                else:
                    # Primera entrada del día
                    ayudantes_presentes[email] = {
                        'nombre': registro['nombre'],
                        'apellido': registro['apellido'],
                        'email': email,
                        'ultima_entrada': registro['hora'],
                        'ultima_hora': registro['hora'],
                        'dentro': True  # Primera entrada implica que está dentro
                    }
            
            # Filtramos solo aquellos que están dentro (última marca fue de entrada)
            ayudantes_dentro = []
            for email, datos in ayudantes_presentes.items():
                if datos['dentro']:
                    # Formatear la hora para mostrarla mejor
                    try:
                        if isinstance(datos['ultima_entrada'], str):
                            hora_str = datos['ultima_entrada']
                        else:
                            hora_str = datos['ultima_entrada'].strftime('%H:%M:%S')
                        
                        datos['ultima_entrada'] = hora_str
                    except:
                        # Si hay algún error al formatear, dejamos la hora como está
                        pass
                    
                    # Eliminamos la bandera 'dentro' que ya no necesitamos
                    del datos['dentro']
                    del datos['ultima_hora']
                    
                    ayudantes_dentro.append(datos)
            
            # Obtener fotos de perfil si existen
            for ayudante in ayudantes_dentro:
                try:
                    cursor.execute("SELECT foto_url FROM usuarios_permitidos WHERE email = %s LIMIT 1", (ayudante['email'],))
                    foto = cursor.fetchone()
                    if foto and 'foto_url' in foto and foto['foto_url']:
                        ayudante['foto_url'] = foto['foto_url']
                    else:
                        ayudante['foto_url'] = None
                except:
                    # Si hay algún error, simplemente no incluimos foto
                    ayudante['foto_url'] = None
            
        conn.close()
        
        # Convertimos cualquier objeto no serializable a string
        for ayudante in ayudantes_dentro:
            for key, value in list(ayudante.items()):
                if isinstance(value, (datetime, date)):
                    ayudante[key] = value.isoformat()
                elif isinstance(value, timedelta):
                    ayudante[key] = str(value)
                elif hasattr(value, 'isoformat') and callable(getattr(value, 'isoformat')):
                    ayudante[key] = value.isoformat()
        
        return jsonify(ayudantes_dentro)
    except Exception as e:
        print(f"Error al obtener ayudantes presentes: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Horas acumuladas CORREGIDO ---
@app.route('/horas_acumuladas', methods=['GET'])
def get_horas_acumuladas():
    try:
        conn = get_connection()
        
        with conn.cursor() as cursor:
            # Obtener usuarios activos
            cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()
            
            resultado = []
            
            # Definir cuántas horas equivalen a un día completo (por ejemplo, 8 horas = 1 día)
            HORAS_POR_DIA = 8
            
            for usuario in usuarios:
                # Obtener todos los registros ordenados por fecha y hora
                cursor.execute("""
                    SELECT fecha, hora, id
                    FROM registros
                    WHERE email = %s
                    ORDER BY fecha, hora
                """, (usuario['email'],))
                
                todos_registros = cursor.fetchall()
                
                # Procesamiento mejorado de horas
                horas_totales = 0
                dias_procesados = set()
                
                # Agrupar registros por día para procesar pares entrada-salida
                registros_por_dia = {}
                for reg in todos_registros:
                    fecha_str = str(reg['fecha'])
                    if fecha_str not in registros_por_dia:
                        registros_por_dia[fecha_str] = []
                    registros_por_dia[fecha_str].append(reg)
                
                # Procesar cada día
                for fecha, registros_dia in registros_por_dia.items():
                    # Ordenar registros por hora
                    registros_dia.sort(key=lambda x: x['hora'])
                    
                    # Si hay un número impar de registros, asumimos que falta un registro de salida
                    # CAMBIO: En lugar de eliminar el último registro, creamos un registro de salida ficticio al final del día
                    if len(registros_dia) % 2 != 0 and len(registros_dia) > 0:
                        # Crear registro ficticio de salida
                        ultimo_registro = registros_dia[-1].copy()  # Copiamos para no modificar el original
                        if isinstance(ultimo_registro['hora'], str):
                            hora_salida = "23:59:59"
                        else:
                            try:
                                hora_salida = datetime.strptime("23:59:59", "%H:%M:%S").time()
                            except:
                                hora_salida = "23:59:59"  # Si falla la conversión, usar string
                        
                        ultimo_registro['hora'] = hora_salida
                        ultimo_registro['ficticio'] = True  # Marcar como ficticio
                        registros_dia.append(ultimo_registro)
                    
                    # Procesar pares de entrada-salida
                    horas_dia = 0
                    for i in range(0, len(registros_dia), 2):
                        if i + 1 < len(registros_dia):  # Asegurarnos de que hay un par completo
                            try:
                                entrada_reg = registros_dia[i]
                                salida_reg = registros_dia[i + 1]
                                
                                # Convertir a objetos datetime para cálculo
                                if isinstance(entrada_reg['hora'], str):
                                    entrada_hora = datetime.strptime(entrada_reg['hora'], '%H:%M:%S')
                                else:
                                    entrada_hora = entrada_reg['hora']
                                    
                                if isinstance(salida_reg['hora'], str):
                                    salida_hora = datetime.strptime(salida_reg['hora'], '%H:%M:%S')
                                else:
                                    salida_hora = salida_reg['hora']
                                
                                # Verificar que la salida es posterior a la entrada
                                if hasattr(salida_hora, 'hour') and hasattr(entrada_hora, 'hour'):
                                    # Convertir a horas del día para comparación
                                    entrada_horas = entrada_hora.hour + entrada_hora.minute/60 + entrada_hora.second/3600
                                    salida_horas = salida_hora.hour + salida_hora.minute/60 + salida_hora.second/3600
                                    
                                    if salida_horas > entrada_horas:
                                        horas_bloque = salida_horas - entrada_horas
                                        horas_dia += horas_bloque
                                        print(f"Usuario {usuario['email']} - Fecha {fecha} - Entrada {entrada_horas} - Salida {salida_horas} - Horas {horas_bloque}")
                            except Exception as e:
                                print(f"Error procesando par entrada-salida: {str(e)}")
                                continue
                    
                    # Sumar las horas de este día al total
                    dias_procesados.add(fecha)
                    horas_totales += horas_dia
                
                # Calcular días completos en función de las horas trabajadas
                dias_completos = horas_totales / HORAS_POR_DIA
                
                # Agregar datos del usuario al resultado
                resultado.append({
                    "nombre": usuario['nombre'],
                    "apellido": usuario['apellido'],
                    "email": usuario['email'],
                    "dias_asistidos": round(dias_completos, 1),  # Días completos calculados por horas
                    "horas_totales": round(horas_totales, 1),    # Horas totales redondeadas a 1 decimal
                    "dias_calendario": len(dias_procesados)      # Número de días distintos con registros
                })
                
        conn.close()
        return jsonify(resultado if resultado else [])
    except Exception as e:
        print(f"Error al obtener horas acumuladas: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Detalle de horas por usuario (para debugging) ---
@app.route('/horas_detalle/<email>', methods=['GET'])
def get_horas_detalle(email):
    try:
        conn = get_connection()
        
        with conn.cursor() as cursor:
            # Verificar que el usuario existe
            cursor.execute("SELECT nombre, apellido FROM usuarios_permitidos WHERE email = %s AND activo = 1", (email,))
            usuario = cursor.fetchone()
            
            if not usuario:
                return jsonify({"error": "Usuario no encontrado o inactivo"}), 404
            
            # Obtener todos los registros ordenados por fecha y hora
            cursor.execute("""
                SELECT fecha, hora, id
                FROM registros
                WHERE email = %s
                ORDER BY fecha, hora
            """, (email,))
            
            todos_registros = cursor.fetchall()
            
            # Procesar los registros para mostrar el detalle
            detalle_por_dia = {}
            
            for reg in todos_registros:
                fecha_str = str(reg['fecha'])
                
                # Convertir hora a formato estandarizado
                if isinstance(reg['hora'], str):
                    hora_str = reg['hora']
                else:
                    try:
                        hora_str = reg['hora'].strftime('%H:%M:%S')
                    except:
                        hora_str = str(reg['hora'])
                
                # Agregar al diccionario de días
                if fecha_str not in detalle_por_dia:
                    detalle_por_dia[fecha_str] = []
                
                detalle_por_dia[fecha_str].append({
                    "id": reg['id'],
                    "hora": hora_str
                })
            
            # Calcular horas por día
            resumen_dias = []
            horas_totales = 0
            
            for fecha, registros in detalle_por_dia.items():
                # Ordenar registros por hora
                registros.sort(key=lambda x: x['hora'])
                
                # CAMBIO: Manejar registros impares agregando uno ficticio al final
                reg_procesados = registros.copy()
                if len(reg_procesados) % 2 != 0 and len(reg_procesados) > 0:
                    ultimo_registro = reg_procesados[-1].copy()
                    ultimo_registro["hora"] = "23:59:59"
                    ultimo_registro["ficticio"] = True
                    reg_procesados.append(ultimo_registro)
                
                # Calcular pares entrada-salida
                pares = []
                horas_dia = 0
                
                for i in range(0, len(reg_procesados), 2):
                    if i + 1 < len(reg_procesados):  # Hay un par completo
                        entrada = reg_procesados[i]['hora']
                        salida = reg_procesados[i + 1]['hora']
                        es_ficticio = reg_procesados[i + 1].get('ficticio', False)
                        
                        try:
                            # Convertir a horas decimales
                            entrada_dt = datetime.strptime(entrada, '%H:%M:%S')
                            salida_dt = datetime.strptime(salida, '%H:%M:%S')
                            
                            entrada_decimal = entrada_dt.hour + entrada_dt.minute/60 + entrada_dt.second/3600
                            salida_decimal = salida_dt.hour + salida_dt.minute/60 + salida_dt.second/3600
                            
                            if salida_decimal > entrada_decimal:
                                horas = salida_decimal - entrada_decimal
                                horas_dia += horas
                                
                                pares.append({
                                    "entrada": entrada,
                                    "salida": salida,
                                    "horas": round(horas, 2),
                                    "es_ficticio": es_ficticio
                                })
                        except Exception as e:
                            print(f"Error calculando horas para par: {str(e)}")
                
                # Agregar resumen del día
                resumen_dias.append({
                    "fecha": fecha,
                    "registros_totales": len(registros),
                    "pares_completos": len(pares),
                    "registros": registros,
                    "pares": pares,
                    "horas_dia": round(horas_dia, 2)
                })
                
                horas_totales += horas_dia
            
            # Definir horas por día completo
            HORAS_POR_DIA = 8
            dias_completos = horas_totales / HORAS_POR_DIA
            
            # Preparar resultado final
            resultado = {
                "nombre": usuario['nombre'],
                "apellido": usuario['apellido'],
                "email": email,
                "dias_calendario": len(detalle_por_dia),  # Días naturales con registros
                "dias_completos": round(dias_completos, 2),  # Días equivalentes basados en horas
                "horas_totales": round(horas_totales, 2),
                "detalle_dias": resumen_dias
            }
            
        conn.close()
        return jsonify(resultado)
    except Exception as e:
        print(f"Error al obtener detalle de horas: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- PROCESO: Cierre automático de registros sin salida ---
@app.route('/procesar_salidas_pendientes', methods=['POST'])
def procesar_salidas_pendientes():
    """
    Procesa todos los registros de entrada sin su correspondiente registro de salida
    para el día anterior (o para una fecha específica si se proporciona).
    
    Se puede llamar de forma manual o mediante un proceso programado (cron job).
    """
    try:
        # Obtener fecha a procesar (por defecto, día anterior)
        data = request.get_json() or {}
        fecha_procesar = data.get('fecha')
        
        if not fecha_procesar:
            # Si no se proporciona fecha, usar el día anterior
            ayer = get_current_datetime() - timedelta(days=1)
            fecha_procesar = ayer.strftime('%Y-%m-%d')
        
        # Obtener hora de salida (por defecto, 23:59:59)
        hora_salida = data.get('hora_salida', '23:59:59')
        
        conn = get_connection()
        registros_procesados = []
        
        with conn.cursor() as cursor:
            # Primero, obtener todos los usuarios que registraron entrada ese día
            cursor.execute("""
                SELECT DISTINCT email, nombre, apellido, dia
                FROM registros
                WHERE fecha = %s
            """, (fecha_procesar,))
            
            usuarios = cursor.fetchall()
            
            for usuario in usuarios:
                email = usuario['email']
                
                # Obtener todos los registros de este usuario para esa fecha, ordenados por hora
                cursor.execute("""
                    SELECT id, hora
                    FROM registros
                    WHERE email = %s AND fecha = %s
                    ORDER BY hora
                """, (email, fecha_procesar))
                
                registros_usuario = cursor.fetchall()
                
                # Si hay un número impar de registros, agregar un registro de salida
                if len(registros_usuario) % 2 != 0:
                    # Obtener día de la semana
                    dia = usuario['dia']
                    
                    # Insertar registro de salida automático
                    cursor.execute("""
                        INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, auto_generado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        fecha_procesar,
                        hora_salida,
                        dia,
                        usuario['nombre'],
                        usuario['apellido'],
                        email,
                        True  # Marcar como auto-generado
                    ))
                    
                    # Guardar información del registro procesado
                    registros_procesados.append({
                        'email': email,
                        'nombre': usuario['nombre'],
                        'apellido': usuario['apellido'],
                        'fecha': fecha_procesar,
                        'hora_entrada': registros_usuario[-1]['hora'],
                        'hora_salida': hora_salida
                    })
            
            # Confirmar los cambios en la base de datos
            conn.commit()
            
        conn.close()
        
        # Devolver resultados
        return jsonify({
            'fecha_procesada': fecha_procesar,
            'registros_creados': len(registros_procesados),
            'detalle': registros_procesados
        })
    
    except Exception as e:
        print(f"Error al procesar salidas pendientes: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- TAREA PROGRAMADA: Configurar para ejecutar automáticamente ---
def configurar_tarea_cierre_diario():
    """
    Configura una tarea programada que se ejecutará diariamente para cerrar
    los registros sin salida del día anterior.
    
    Esta función debe ser llamada al iniciar la aplicación.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    import requests
    
    def ejecutar_cierre_diario():
        try:
            # Llamar al endpoint de procesar salidas pendientes
            response = requests.post(
                'https://localhost:5000/procesar_salidas_pendientes',
                json={},
                verify=False  # Para desarrollo local. En producción, usar certificados apropiados
            )
            
            if response.status_code == 200:
                print(f"Cierre diario ejecutado con éxito: {response.json()}")
            else:
                print(f"Error en cierre diario: {response.text}")
        
        except Exception as e:
            print(f"Error al ejecutar cierre diario: {str(e)}")
    
    # Crear el scheduler
    scheduler = BackgroundScheduler()
    
    # Programar la tarea para ejecutarse todos los días a las 23:55
    scheduler.add_job(ejecutar_cierre_diario, 'cron', hour=23, minute=55)
    
    # Iniciar el scheduler
    scheduler.start()
    
    print("Tarea de cierre diario programada para ejecutarse a las 23:55")

# Modificar la sección principal para incluir la configuración de la tarea programada
if __name__ == '__main__':
    # Intentar configurar la tarea programada (requiere apscheduler)
    try:
        import apscheduler
        configurar_tarea_cierre_diario()
    except ImportError:
        print("ADVERTENCIA: No se pudo configurar la tarea programada.")
        print("Instale 'apscheduler' con: pip install apscheduler")
        print("O ejecute manualmente el endpoint /procesar_salidas_pendientes")
    
    # Definir rutas a los certificados
    # Opción 1: Rutas absolutas
    cert_path = 'certificate.pem'  # Actualiza esta ruta
    key_path = 'privatekey.pem'    # Actualiza esta ruta
    
    # Opción 2: Rutas relativas al directorio del script
    # cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificate.pem')
    # key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'privatekey.pem')
    
    # Verificar que los archivos de certificado existen
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"Error: Certificados no encontrados en las rutas especificadas")
        print(f"Certificado: {cert_path}")
        print(f"Clave privada: {key_path}")
        print("Verifica las rutas o mueve los certificados a estas ubicaciones")
        exit(1)
    else:
        print(f"Certificados encontrados correctamente")
    
    # Configurar contexto SSL
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        
        # Configuraciones de seguridad recomendadas
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Deshabilitar protocolos inseguros
        
        print("Contexto SSL configurado correctamente")
    except Exception as e:
        print(f"Error al configurar el contexto SSL: {str(e)}")
        exit(1)
    
    print("Iniciando servidor HTTPS en 10.0.3.54:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=context)