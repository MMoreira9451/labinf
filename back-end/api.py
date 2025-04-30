import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from datetime import datetime, timedelta, date
import json
import ssl  # Importamos el módulo SSL
import pytz  # Agregamos pytz para manejo de timezone
from datetime import datetime, timedelta, date, time 

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
            # Asegúrate de incluir explícitamente el campo 'tipo'
            cursor.execute("""
                SELECT id, fecha, hora, dia, nombre, apellido, email, tipo
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
    
# --- ENDPOINT: Insertar nuevo registro (modificado) ---
@app.route('/registros', methods=['POST'])
def add_registro():
    data = request.get_json()
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Obtener fecha y hora actuales
            now = get_current_datetime()
            fecha = data.get('fecha', now.strftime("%Y-%m-%d"))
            hora = data.get('hora', now.strftime("%H:%M:%S"))
            timestamp_value = data.get('timestamp', None)

            if timestamp_value:
    # Si timestamp_value es un número y parece ser en milisegundos (más de 11 dígitos)
                if isinstance(timestamp_value, int) and timestamp_value > 1e11:
                    timestamp = datetime.fromtimestamp(timestamp_value / 1000)
                elif isinstance(timestamp_value, str) and timestamp_value.isdigit() and len(timestamp_value) > 11:
                    timestamp = datetime.fromtimestamp(int(timestamp_value) / 1000)
                else:
        # Si ya es formato datetime o ISO string
                    try:
                        timestamp = datetime.fromisoformat(timestamp_value)
                    except Exception:
                        timestamp = now
            else:
                timestamp = now

            
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
                day_name = now.strftime("%A")
                dia = dias.get(day_name, day_name)
            
            email = data['email']
            
            # NUEVO: Determinar si es entrada o salida consultando la tabla de estados
            cursor.execute("SELECT estado FROM estado_usuarios WHERE email = %s", (email,))
            estado_actual = cursor.fetchone()
            
            if estado_actual and estado_actual['estado'] == 'dentro':
                tipo = 'Salida'
                nuevo_estado = 'fuera'
            else:
                tipo = 'Entrada'
                nuevo_estado = 'dentro'
            
            # Insertar registro
            query = """
                INSERT INTO registros 
                (fecha, hora, dia, nombre, apellido, email, tipo, timestamp) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                fecha,
                hora,
                dia,
                data['nombre'],
                data['apellido'],
                email,
                tipo,
                timestamp
            ))
            
            # Actualizar el estado del usuario
            cursor.execute("""
                INSERT INTO estado_usuarios (email, nombre, apellido, estado, 
                    ultima_entrada, ultima_salida)
                VALUES (%s, %s, %s, %s, 
                    CASE WHEN %s = 'dentro' THEN NOW() ELSE NULL END,
                    CASE WHEN %s = 'fuera' THEN NOW() ELSE NULL END)
                ON DUPLICATE KEY UPDATE 
                    estado = %s, 
                    ultima_entrada = CASE WHEN %s = 'dentro' THEN NOW() ELSE ultima_entrada END,
                    ultima_salida = CASE WHEN %s = 'fuera' THEN NOW() ELSE ultima_salida END
            """, (
                email, data['nombre'], data['apellido'], nuevo_estado, 
                nuevo_estado, nuevo_estado,
                nuevo_estado, nuevo_estado, nuevo_estado
            ))
            
            conn.commit()
            registro_id = cursor.lastrowid
        conn.close()
        return jsonify({
            "message": "Registro agregado correctamente", 
            "id": registro_id,
            "tipo": tipo,
            "estado": nuevo_estado
        })
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

@app.route('/cumplimiento', methods=['GET'])
def get_cumplimiento():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Mapa de días inglés -> español
            dias_traduccion = {
                'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miércoles',
                'thursday': 'jueves', 'friday': 'viernes',
                'saturday': 'sábado', 'sunday': 'domingo'
            }

            # Fecha y hora actual
            now = get_current_datetime()
            dia_actual = now.strftime('%A').lower()
            dia_actual_esp = dias_traduccion.get(dia_actual, dia_actual)
            hora_actual = now.strftime('%H:%M:%S')
            fecha_actual = now.strftime('%Y-%m-%d')

            print(f"[DEBUG] Iniciando cálculo de cumplimiento. Fecha: {fecha_actual}, Día: {dia_actual_esp}")

            # Traer usuarios activos
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()

            resultado = []

            # Fecha de inicio de semana (lunes)
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week_str = start_of_week.strftime('%Y-%m-%d')

            for user in usuarios:
                print(f"[DEBUG] Procesando usuario: {user['nombre']} {user['apellido']} ({user['email']})")
                
                # Traer sus horarios asignados
                cursor.execute(
                    "SELECT * FROM horarios_asignados WHERE usuario_id = %s",
                    (user['id'],)
                )
                horarios = cursor.fetchall()

                # Si no tiene horarios, "No Aplica"
                if not horarios:
                    resultado.append({
                        "nombre": user['nombre'],
                        "apellido": user['apellido'],
                        "email":   user['email'],
                        "estado":  "No Aplica",
                        "bloques": [],
                        "bloques_info": []
                    })
                    continue

                bloques = []
                bloques_info = []
                cumplidos = 0
                incompletos = 0
                ausentes = 0
                pendientes = 0

                # Un bloque por cada horario
                for h in horarios:
                    print(f"[DEBUG] Procesando bloque: {h['dia']} {h['hora_entrada']}-{h['hora_salida']}")
                    
                    bloque_label = f"{h['dia']} {h['hora_entrada']}-{h['hora_salida']}"
                    bloques.append(bloque_label)

                    # Default
                    bloque_estado = "Ausente"

                    # --- Convertir hora_entrada a datetime.time ---
                    raw = h['hora_entrada']
                    if isinstance(raw, timedelta):
                        secs = int(raw.total_seconds())
                        hh = secs // 3600
                        mm = (secs % 3600) // 60
                        ss = secs % 60
                        hora_entrada_dt = time(hh, mm, ss)
                    elif isinstance(raw, str):
                        hora_entrada_dt = datetime.strptime(raw, "%H:%M:%S").time()
                    else:
                        hora_entrada_dt = raw  # ya es time

                    # --- Convertir hora_salida a datetime.time ---
                    raw = h['hora_salida']
                    if isinstance(raw, timedelta):
                        secs = int(raw.total_seconds())
                        hh = secs // 3600
                        mm = (secs % 3600) // 60
                        ss = secs % 60
                        hora_salida_dt = time(hh, mm, ss)
                    elif isinstance(raw, str):
                        hora_salida_dt = datetime.strptime(raw, "%H:%M:%S").time()
                    else:
                        hora_salida_dt = raw

                    # --- Obtener registros de ese día o semana ---
                    dia_horario = h['dia'].lower()
                    dia_en_espanol = dias_traduccion.get(dia_horario, dia_horario)
                    
                    print(f"[DEBUG] Día actual: {dia_actual_esp}, Día del bloque: {dia_horario} / {dia_en_espanol}")

                    if dia_en_espanol == dia_actual_esp:
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s AND fecha = %s
                            ORDER BY hora
                        """, (user['email'], fecha_actual))
                    else:
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s
                              AND (LOWER(dia) = %s OR LOWER(dia) = %s)
                              AND fecha BETWEEN %s AND %s
                            ORDER BY fecha DESC, hora
                        """, (user['email'], dia_en_espanol, dia_horario, start_of_week_str, fecha_actual))

                    registros_del_dia = cursor.fetchall()
                    print(f"[DEBUG] Registros encontrados para el día: {len(registros_del_dia)}")

                    # --- Revisar registros de entrada y salida para determinar estado del bloque ---
                    cumplio_bloque = False
                    incompleto_bloque = False
                    
                    # Separar registros por tipo
                    entradas = [r for r in registros_del_dia if r['tipo'] == 'Entrada']
                    salidas = [r for r in registros_del_dia if r['tipo'] == 'Salida']
                    
                    print(f"[DEBUG] Entradas: {len(entradas)}, Salidas: {len(salidas)}")
                    
                    # Verificar si hay al menos una entrada y una salida
                    if entradas and salidas:
                        for entrada in entradas:
                            # Procesar hora de entrada
                            if isinstance(entrada['hora'], str):
                                t_entrada = datetime.strptime(entrada['hora'], "%H:%M:%S").time()
                            elif isinstance(entrada['hora'], timedelta):
                                secs = int(entrada['hora'].total_seconds())
                                t_entrada = time(secs//3600, (secs%3600)//60, secs%60)
                            else:
                                t_entrada = entrada['hora']
                            
                            print(f"[DEBUG] Procesando entrada id:{entrada['id']} hora:{t_entrada}")
                            
                            for salida in salidas:
                                # Solo considerar salidas posteriores a esta entrada
                                if salida['id'] > entrada['id']:
                                    # Procesar hora de salida
                                    if isinstance(salida['hora'], str):
                                        t_salida = datetime.strptime(salida['hora'], "%H:%M:%S").time()
                                    elif isinstance(salida['hora'], timedelta):
                                        secs = int(salida['hora'].total_seconds())
                                        t_salida = time(secs//3600, (secs%3600)//60, secs%60)
                                    else:
                                        t_salida = salida['hora']
                                    
                                    print(f"[DEBUG] Comparando con salida id:{salida['id']} hora:{t_salida}")
                                    
                                    # Verificar si cumplió el bloque completo
                                    # Caso 1: Entró a tiempo/antes y salió a tiempo/después
                                    if (t_entrada <= hora_entrada_dt and t_salida >= hora_salida_dt):
                                        cumplio_bloque = True
                                        print(f"[DEBUG] CUMPLIDO! Entrada a tiempo/antes y salida a tiempo/después")
                                        break
                                    
                                    # Caso 2: Entró tarde pero salió a tiempo/después
                                    elif (t_entrada > hora_entrada_dt and t_entrada < hora_salida_dt and t_salida >= hora_salida_dt):
                                        incompleto_bloque = True
                                        print(f"[DEBUG] INCOMPLETO - Entrada tarde, salida a tiempo/después")
                                    
                                    # Caso 3: Entró a tiempo/antes pero salió antes de terminar
                                    elif (t_entrada <= hora_entrada_dt and t_salida < hora_salida_dt):
                                        incompleto_bloque = True
                                        print(f"[DEBUG] INCOMPLETO - Entrada a tiempo/antes, salida temprana")
                                    
                                    # Caso parcial: al menos estuvo parte del bloque
                                    elif (t_entrada < hora_salida_dt and t_salida > hora_entrada_dt):
                                        incompleto_bloque = True
                                        print(f"[DEBUG] INCOMPLETO - Presencia parcial en el bloque")
                            
                            # Si ya encontró cumplimiento completo, salir del bucle
                            if cumplio_bloque:
                                break

                    # --- Determinar estado según día actual o no ---
                    if dia_en_espanol == dia_actual_esp:
                        now_t = datetime.strptime(hora_actual, "%H:%M:%S").time()
                        
                        if cumplio_bloque:
                            bloque_estado = "Cumplido"
                            cumplidos += 1
                        elif incompleto_bloque:
                            bloque_estado = "Incompleto"
                            incompletos += 1
                        elif now_t < hora_entrada_dt:
                            bloque_estado = "Pendiente"
                            pendientes += 1
                        elif now_t >= hora_entrada_dt and now_t < hora_salida_dt:
                            # Si está en el rango del bloque ahora pero no ha marcado
                            bloque_estado = "Atrasado"
                            incompletos += 1
                        else:
                            # Si ya pasó la hora y no marcó
                            bloque_estado = "Ausente"
                            ausentes += 1
                    else:
                        # Para días anteriores de la semana
                        if cumplio_bloque:
                            bloque_estado = "Cumplido"
                            cumplidos += 1
                        elif incompleto_bloque:
                            bloque_estado = "Incompleto"
                            incompletos += 1
                        else:
                            bloque_estado = "Ausente"
                            ausentes += 1

                    print(f"[DEBUG] Estado bloque: {bloque_estado} (Cumplido: {cumplio_bloque}, Incompleto: {incompleto_bloque})")
                    
                    bloques_info.append({
                        "bloque": bloque_label,
                        "estado": bloque_estado
                    })

                # Estado general del usuario para la semana según tus criterios
                print(f"[DEBUG] Usuario {user['email']} - Cumplidos: {cumplidos}, Incompletos: {incompletos}, Ausentes: {ausentes}, Pendientes: {pendientes}")
                
                if len(horarios) == 0:
                    estado_usuario = "No Aplica"
                elif pendientes > 0 and ausentes == 0 and incompletos == 0:
                    # Si solo tiene pendientes y quizás cumplidos
                    estado_usuario = "Pendiente"
                elif cumplidos == len(horarios):
                    # Si cumplió todos
                    estado_usuario = "Cumple"
                elif ausentes == len(horarios):
                    # Si no asistió a ninguno
                    estado_usuario = "Ausente"
                elif incompletos > 0 or (cumplidos > 0 and ausentes > 0):
                    # Si tiene incompletos o una mezcla de cumplidos y ausentes (REGLA IMPORTANTE)
                    estado_usuario = "Incompleto"
                else:
                    estado_usuario = "No Cumple"
                
                print(f"[DEBUG] Estado final usuario: {estado_usuario}")

                resultado.append({
                    "nombre": user['nombre'],
                    "apellido": user['apellido'],
                    "email": user['email'],
                    "estado": estado_usuario,
                    "bloques": bloques,
                    "bloques_info": bloques_info
                })

        conn.close()
        return jsonify(resultado)

    except Exception as e:
        print(f"Error en cumplimiento: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/diagnostico_cumplimiento/<email>', methods=['GET'])
def diagnostico_cumplimiento(email):
    try:
        conn = get_connection()
        resultado = {}
        
        with conn.cursor() as cursor:
            # Mapa de días inglés -> español
            dias_traduccion = {
                'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miércoles',
                'thursday': 'jueves', 'friday': 'viernes',
                'saturday': 'sábado', 'sunday': 'domingo'
            }
            
            # Obtener información del usuario
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            
            if not usuario:
                return jsonify({"error": "Usuario no encontrado"}), 404
            
            resultado["usuario"] = {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "apellido": usuario["apellido"],
                "email": usuario["email"]
            }
            
            # Obtener horarios asignados
            cursor.execute("SELECT * FROM horarios_asignados WHERE usuario_id = %s", (usuario["id"],))
            horarios = cursor.fetchall()
            
            # Formato para los horarios
            resultado["horarios"] = []
            for h in horarios:
                # Convertir a formatos legibles
                hora_entrada = format_hora(h["hora_entrada"])
                hora_salida = format_hora(h["hora_salida"])
                
                # Incluir traducción del día si está en inglés
                dia_original = h["dia"]
                dia_lower = dia_original.lower()
                dia_traducido = dias_traduccion.get(dia_lower, dia_lower)
                
                resultado["horarios"].append({
                    "dia": dia_original,
                    "dia_traducido": dia_traducido,
                    "hora_entrada": hora_entrada,
                    "hora_salida": hora_salida
                })
            
            # Fecha y hora actual
            now = get_current_datetime()
            dia_actual = now.strftime('%A').lower()
            dia_actual_esp = dias_traduccion.get(dia_actual, dia_actual)
            fecha_actual = now.strftime('%Y-%m-%d')
            hora_actual = now.strftime('%H:%M:%S')
            
            resultado["fecha_actual"] = fecha_actual
            resultado["hora_actual"] = hora_actual
            resultado["dia_actual"] = dia_actual
            resultado["dia_actual_esp"] = dia_actual_esp
            
            # Fecha de inicio de semana
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week_str = start_of_week.strftime('%Y-%m-%d')
            resultado["inicio_semana"] = start_of_week_str
            
            # Registros de la semana
            cursor.execute("""
                SELECT * FROM registros
                WHERE email = %s AND fecha BETWEEN %s AND %s
                ORDER BY fecha, hora
            """, (email, start_of_week_str, fecha_actual))
            
            registros = cursor.fetchall()
            
            # Formato para registros
            resultado["registros"] = []
            for r in registros:
                resultado["registros"].append({
                    "id": r["id"],
                    "fecha": str(r["fecha"]),
                    "dia": r["dia"],
                    "hora": format_hora(r["hora"]),
                    "tipo": r["tipo"]
                })
            
            # Ahora analizar el cumplimiento de cada bloque
            resultado["analisis_bloques"] = []
            
            for h in horarios:
                bloque_info = {
                    "dia": h["dia"],
                    "hora_entrada": format_hora(h["hora_entrada"]),
                    "hora_salida": format_hora(h["hora_salida"]),
                }
                
                # Convertir horas a datetime.time para comparación
                hora_entrada_dt = convert_to_time(h["hora_entrada"])
                hora_salida_dt = convert_to_time(h["hora_salida"])
                
                # Filtrar registros para este día
                dia_horario = h["dia"].lower()
                dia_en_espanol = dias_traduccion.get(dia_horario, dia_horario)
                
                # Registros que coinciden con este día
                registros_del_dia = [
                    r for r in registros 
                    if r["dia"].lower() == dia_horario or r["dia"].lower() == dia_en_espanol
                ]
                
                bloque_info["registros_encontrados"] = len(registros_del_dia)
                
                # Separar por tipo
                entradas = [r for r in registros_del_dia if r['tipo'] == 'Entrada']
                salidas = [r for r in registros_del_dia if r['tipo'] == 'Salida']
                
                bloque_info["entradas"] = len(entradas)
                bloque_info["salidas"] = len(salidas)
                
                # Analizar cumplimiento
                cumplio_bloque = False
                incompleto_bloque = False
                razon = "Sin registros suficientes"
                
                if entradas and salidas:
                    for entrada in entradas:
                        t_entrada = convert_to_time(entrada["hora"])
                        
                        for salida in salidas:
                            if salida["id"] > entrada["id"]:
                                t_salida = convert_to_time(salida["hora"])
                                
                                # Verificar cumplimiento según criterios
                                if t_entrada <= hora_entrada_dt and t_salida >= hora_salida_dt:
                                    cumplio_bloque = True
                                    razon = "Entrada a tiempo/antes y salida a tiempo/después"
                                    break
                                elif t_entrada > hora_entrada_dt and t_entrada < hora_salida_dt and t_salida >= hora_salida_dt:
                                    incompleto_bloque = True
                                    razon = "Entrada tarde y salida a tiempo/después"
                                elif t_entrada <= hora_entrada_dt and t_salida < hora_salida_dt:
                                    incompleto_bloque = True
                                    razon = "Entrada a tiempo/antes y salida temprana"
                                elif t_entrada < hora_salida_dt and t_salida > hora_entrada_dt:
                                    incompleto_bloque = True
                                    razon = "Presencia parcial en el bloque"
                        
                        if cumplio_bloque:
                            break
                
                # Determinar estado
                now_t = convert_to_time(hora_actual)
                
                if dia_en_espanol == dia_actual_esp:
                    if cumplio_bloque:
                        estado = "Cumplido"
                    elif incompleto_bloque:
                        estado = "Incompleto"
                    elif now_t < hora_entrada_dt:
                        estado = "Pendiente"
                        razon = "El bloque aún no ha comenzado"
                    elif now_t >= hora_entrada_dt and now_t < hora_salida_dt:
                        estado = "Atrasado"
                        razon = "El bloque está en curso pero no hay registro de entrada"
                    else:
                        estado = "Ausente"
                        razon = "El bloque ya pasó y no hubo asistencia completa"
                else:
                    if cumplio_bloque:
                        estado = "Cumplido"
                    elif incompleto_bloque:
                        estado = "Incompleto"
                    else:
                        estado = "Ausente"
                        razon = "No hay registros válidos para este bloque"
                
                bloque_info["estado"] = estado
                bloque_info["razon"] = razon
                bloque_info["cumplio"] = cumplio_bloque
                bloque_info["incompleto"] = incompleto_bloque
                
                resultado["analisis_bloques"].append(bloque_info)
        
        conn.close()
        return jsonify(resultado)
    
    except Exception as e:
        print(f"Error en diagnóstico cumplimiento: {e}")
        return jsonify({"error": str(e)}), 500

# Función auxiliar para formatear horas
def format_hora(hora_value):
    if isinstance(hora_value, time):
        return hora_value.strftime("%H:%M:%S")
    elif isinstance(hora_value, timedelta):
        secs = int(hora_value.total_seconds())
        hh, rem = divmod(secs, 3600)
        mm, ss = divmod(rem, 60)
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    elif isinstance(hora_value, str):
        return hora_value
    else:
        return str(hora_value)

# Función auxiliar para convertir a time
def convert_to_time(hora_value):
    if isinstance(hora_value, time):
        return hora_value
    elif isinstance(hora_value, timedelta):
        secs = int(hora_value.total_seconds())
        hh, rem = divmod(secs, 3600)
        mm, ss = divmod(rem, 60)
        return time(hh, mm, ss)
    elif isinstance(hora_value, str):
        try:
            return datetime.strptime(hora_value, "%H:%M:%S").time()
        except ValueError:
            # Intenta con otros formatos si el estándar falla
            try:
                return datetime.strptime(hora_value, "%H:%M").time()
            except ValueError:
                # Si todo falla, devuelve tiempo por defecto
                return time(0, 0, 0)
    else:
        # Último recurso, intenta convertir a string y luego parsear
        try:
            return datetime.strptime(str(hora_value), "%H:%M:%S").time()
        except:
            return time(0, 0, 0)
    
# Endpoint modificado: Ayudantes presentes
@app.route('/ayudantes_presentes', methods=['GET'])
def get_ayudantes_presentes():
    try:
        conn = get_connection()
        
        with conn.cursor() as cursor:
            # Obtenemos la fecha actual
            now = get_current_datetime()
            today = now.strftime('%Y-%m-%d')
            
            # NUEVA IMPLEMENTACIÓN: Buscar ayudantes basados solo en la tabla registros
            # Lógica: Un ayudante está presente si su último registro del día es de tipo 'Entrada'
            cursor.execute("""
                SELECT r.email, r.nombre, r.apellido, r.hora as ultima_entrada, u.foto_url
                FROM registros r
                JOIN (
                    -- Subconsulta para obtener el ID del último registro de cada usuario en el día actual
                    SELECT email, MAX(id) as last_id
                    FROM registros
                    WHERE fecha = %s
                    GROUP BY email
                ) as ultimos
                ON r.id = ultimos.last_id
                LEFT JOIN usuarios_permitidos u ON r.email = u.email
                WHERE r.fecha = %s
                AND r.tipo = 'Entrada'  -- Solo considerar como presentes a quienes su último registro sea Entrada
                ORDER BY r.hora DESC
            """, (today, today))
            
            ayudantes_dentro = cursor.fetchall()
            
            # Formateo de datos
            for ayudante in ayudantes_dentro:
                # Añadir estado explícitamente como 'dentro' para mantener compatibilidad con el frontend
                ayudante['estado'] = 'dentro'
                
                # Convertir tipos de datos
                for key, value in list(ayudante.items()):
                    if isinstance(value, (datetime, date)):
                        ayudante[key] = value.isoformat()
                    elif isinstance(value, timedelta):
                        ayudante[key] = str(value)
        
        conn.close()
        return jsonify(ayudantes_dentro)
    except Exception as e:
        print(f"Error al obtener ayudantes presentes: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

# --- ENDPOINT: Horas acumuladas CORREGIDO ---
# --- ENDPOINT: Horas acumuladas OPTIMIZADO ---
@app.route('/horas_acumuladas', methods=['GET'])
def get_horas_acumuladas():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1) Traer usuarios activos
            cursor.execute("""
                SELECT id, nombre, apellido, email 
                FROM usuarios_permitidos 
                WHERE activo = 1
            """)
            usuarios = cursor.fetchall()

            resultado = []

            for usuario in usuarios:
                # 2) Traer todos los registros ordenados por fecha y hora
                cursor.execute("""
                    SELECT id, fecha, hora, tipo 
                    FROM registros 
                    WHERE email = %s 
                    ORDER BY fecha, hora
                """, (usuario['email'],))
                registros = cursor.fetchall()
                
                # Inicializar variables para el cálculo
                horas_totales = 0
                dias_calendario = set()  # Para contar días únicos con asistencia
                ultimo_registro = None
                entradas_sin_salida = []
                
                # 3) Procesar los registros para hacer pares entrada-salida
                for registro in registros:
                    # Añadir a días con asistencia
                    if isinstance(registro['fecha'], date):
                        fecha_str = registro['fecha'].isoformat()
                    else:
                        fecha_str = str(registro['fecha'])
                    
                    dias_calendario.add(fecha_str)
                    
                    # Procesar según el tipo de registro
                    if registro['tipo'] == 'Entrada':
                        # Guardar esta entrada para emparejarla después
                        entradas_sin_salida.append(registro)
                    
                    elif registro['tipo'] == 'Salida' and entradas_sin_salida:
                        # Tomar la entrada más reciente que no tenga salida
                        entrada = entradas_sin_salida.pop(0)
                        
                        # Convertir ambos registros a datetime.time para poder calcular la diferencia
                        entrada_time = convert_to_time(entrada['hora'])
                        salida_time = convert_to_time(registro['hora'])
                        
                        # Verificar que la entrada y salida sean del mismo día
                        entrada_fecha = entrada['fecha'].isoformat() if isinstance(entrada['fecha'], date) else str(entrada['fecha'])
                        salida_fecha = registro['fecha'].isoformat() if isinstance(registro['fecha'], date) else str(registro['fecha'])
                        
                        if entrada_fecha == salida_fecha:
                            # Calcular la diferencia de tiempo en horas
                            if salida_time > entrada_time:  # Mismo día
                                dt_entrada = datetime.combine(date.min, entrada_time)
                                dt_salida = datetime.combine(date.min, salida_time)
                                diff = dt_salida - dt_entrada
                                horas_totales += diff.total_seconds() / 3600
                
                # 4) Calcular estadísticas finales
                dias_asistidos = horas_totales / 8.0  # 8 horas = 1 día completo
                
                resultado.append({
                    "nombre": usuario['nombre'],
                    "apellido": usuario['apellido'],
                    "email": usuario['email'],
                    "dias_asistidos": round(dias_asistidos, 1),
                    "horas_totales": round(horas_totales, 1),
                    "dias_calendario": len(dias_calendario)
                })

        conn.close()
        return jsonify(resultado)

    except Exception as e:
        print(f"Error al obtener horas acumuladas: {e}")
        return jsonify({"error": str(e)}), 500

# Función auxiliar para convertir diversos formatos de hora a datetime.time
def convert_to_time(hora_value):
    if isinstance(hora_value, time):
        return hora_value
    elif isinstance(hora_value, timedelta):
        secs = int(hora_value.total_seconds())
        hh, rem = divmod(secs, 3600)
        mm, ss = divmod(rem, 60)
        return time(hh, mm, ss)
    elif isinstance(hora_value, str):
        try:
            return datetime.strptime(hora_value, "%H:%M:%S").time()
        except ValueError:
            # Intenta con otros formatos si el estándar falla
            try:
                return datetime.strptime(hora_value, "%H:%M").time()
            except ValueError:
                # Si todo falla, devuelve tiempo por defecto
                return time(0, 0, 0)
    else:
        # Último recurso, intenta convertir a string y luego parsear
        try:
            return datetime.strptime(str(hora_value), "%H:%M:%S").time()
        except:
            return time(0, 0, 0)
        

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
                elif isinstance(reg['hora'], timedelta):
                    # Convertir timedelta a string en formato HH:MM:SS
                    seconds = reg['hora'].total_seconds()
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    hora_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
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
                            # Convertir a horas decimales - CÓDIGO CORREGIDO
                            # Aseguramos que entrada y salida sean strings
                            if not isinstance(entrada, str):
                                # Convertir a string si no lo es
                                if isinstance(entrada, timedelta):
                                    seconds = entrada.total_seconds()
                                    hours = int(seconds // 3600)
                                    minutes = int((seconds % 3600) // 60)
                                    secs = int(seconds % 60)
                                    entrada = f"{hours:02d}:{minutes:02d}:{secs:02d}"
                                else:
                                    entrada = str(entrada)
                                    
                            if not isinstance(salida, str):
                                # Convertir a string si no lo es
                                if isinstance(salida, timedelta):
                                    seconds = salida.total_seconds()
                                    hours = int(seconds // 3600)
                                    minutes = int((seconds % 3600) // 60)
                                    secs = int(seconds % 60)
                                    salida = f"{hours:02d}:{minutes:02d}:{secs:02d}"
                                else:
                                    salida = str(salida)
                            
                            # Ahora que tenemos strings, convertir a datetime
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
    
# --- PROCESO: Cierre automático modificado ---
# --- ENDPOINT: Procesar salidas pendientes mejorado ---
@app.route('/procesar_salidas_pendientes', methods=['POST'])
def procesar_salidas_pendientes():
    try:
        conn = get_connection()
        registros_procesados = []
        
        with conn.cursor() as cursor:
            # Obtener fecha y hora actual
            now = get_current_datetime()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            
            # Día de la semana en español
            dias = {
                'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
                'Thursday': 'jueves', 'Friday': 'viernes', 
                'Saturday': 'sábado', 'Sunday': 'domingo'
            }
            dia = dias.get(now.strftime("%A"), now.strftime("%A"))
            
            # 1. Buscar usuarios que tienen registros de entrada sin salida correspondiente HOY
            cursor.execute("""
                SELECT u.email, u.nombre, u.apellido, MAX(r.id) as ultimo_id, MAX(r.hora) as ultima_hora
                FROM usuarios_permitidos u
                JOIN registros r ON u.email = r.email
                WHERE r.fecha = %s AND r.tipo = 'Entrada'
                AND NOT EXISTS (
                    SELECT 1 FROM registros r2 
                    WHERE r2.email = r.email 
                    AND r2.fecha = r.fecha 
                    AND r2.tipo = 'Salida'
                    AND r2.id > r.id
                )
                GROUP BY u.email, u.nombre, u.apellido
            """, (fecha,))
            
            usuarios_sin_salida = cursor.fetchall()
            
            # 2. También buscar usuarios con estado 'dentro' en la tabla estado_usuarios como respaldo
            cursor.execute("""
                SELECT e.email, e.nombre, e.apellido
                FROM estado_usuarios e
                JOIN usuarios_permitidos u ON e.email = u.email
                WHERE e.estado = 'dentro'
                AND NOT EXISTS (
                    SELECT 1 FROM registros r 
                    WHERE r.email = e.email 
                    AND r.fecha = %s
                    AND r.tipo = 'Salida'
                )
            """, (fecha,))
            
            usuarios_dentro = cursor.fetchall()
            
            # Combinar ambos conjuntos de usuarios
            emails_procesados = set()
            todos_usuarios = []
            
            # Primero añadir usuarios con registros de entrada sin salida
            for usuario in usuarios_sin_salida:
                if usuario['email'] not in emails_procesados:
                    todos_usuarios.append(usuario)
                    emails_procesados.add(usuario['email'])
            
            # Luego añadir usuarios con estado 'dentro' sin registro de salida
            for usuario in usuarios_dentro:
                if usuario['email'] not in emails_procesados:
                    todos_usuarios.append(usuario)
                    emails_procesados.add(usuario['email'])
            
            # Procesar cada usuario
            for usuario in todos_usuarios:
                # Insertar registro de salida automático
                cursor.execute("""
                    INSERT INTO registros 
                    (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    fecha,
                    hora,
                    dia,
                    usuario['nombre'],
                    usuario['apellido'],
                    usuario['email'],
                    'Salida',
                    True  # Marcar como auto-generado
                ))
                
                # Actualizar estado a 'fuera'
                cursor.execute("""
                    UPDATE estado_usuarios 
                    SET estado = 'fuera', ultima_salida = NOW()
                    WHERE email = %s
                """, (usuario['email'],))
                
                registros_procesados.append({
                    'email': usuario['email'],
                    'nombre': usuario['nombre'],
                    'apellido': usuario['apellido'],
                    'fecha': fecha,
                    'hora': hora
                })
            
            # Confirmar los cambios
            conn.commit()
            
        conn.close()
        
        return jsonify({
            'fecha_procesada': fecha,
            'registros_creados': len(registros_procesados),
            'detalle': registros_procesados
        })
    
    except Exception as e:
        print(f"Error al procesar salidas pendientes: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Gestión del estado de usuarios ---
@app.route('/estado_usuarios', methods=['GET'])
def get_estados_usuarios():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, u.foto_url
                FROM estado_usuarios e
                LEFT JOIN usuarios_permitidos u ON e.email = u.email
                ORDER BY e.updated_at DESC
            """)
            estados = cursor.fetchall()
            
            # Convertir datetime a strings
            for estado in estados:
                for key, value in estado.items():
                    if isinstance(value, datetime):
                        estado[key] = value.isoformat()
        
        conn.close()
        return jsonify(estados)
    except Exception as e:
        print(f"Error obteniendo estados de usuarios: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Actualizar estado de un usuario ---
@app.route('/estado_usuario/<email>', methods=['PUT'])
def update_estado_usuario(email):
    try:
        data = request.get_json()
        estado = data.get('estado', 'fuera')
        
        conn = get_connection()
        with conn.cursor() as cursor:
            # Verificar si el usuario ya existe en la tabla
            cursor.execute("SELECT * FROM estado_usuarios WHERE email = %s", (email,))
            existente = cursor.fetchone()
            
            if existente:
                # Actualizar el registro existente
                cursor.execute("""
                    UPDATE estado_usuarios 
                    SET estado = %s, 
                        ultima_entrada = CASE WHEN %s = 'dentro' THEN NOW() ELSE ultima_entrada END,
                        ultima_salida = CASE WHEN %s = 'fuera' THEN NOW() ELSE ultima_salida END
                    WHERE email = %s
                """, (estado, estado, estado, email))
            else:
                # Buscar información del usuario
                cursor.execute("SELECT nombre, apellido FROM usuarios_permitidos WHERE email = %s", (email,))
                usuario = cursor.fetchone()
                if not usuario:
                    return jsonify({"error": "Usuario no encontrado"}), 404
                
                # Crear un nuevo registro
                cursor.execute("""
                    INSERT INTO estado_usuarios (email, nombre, apellido, estado, 
                        ultima_entrada, ultima_salida)
                    VALUES (%s, %s, %s, %s, 
                        CASE WHEN %s = 'dentro' THEN NOW() ELSE NULL END,
                        CASE WHEN %s = 'fuera' THEN NOW() ELSE NULL END)
                """, (email, usuario['nombre'], usuario['apellido'], estado, estado, estado))
            
            conn.commit()
        conn.close()
        return jsonify({"message": f"Estado de usuario actualizado a '{estado}'"})
    except Exception as e:
        print(f"Error actualizando estado de usuario: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- TAREA PROGRAMADA: Configurar para ejecutar automáticamente ---
# --- PROCESO: Configurar cierre automático ---
def configurar_tarea_cierre_diario():
    """
    Configura una tarea programada que se ejecutará diariamente a las 11:59 PM
    para cerrar los registros sin salida del día.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    import requests
    
    def ejecutar_cierre_diario():
        try:
            # URL correcta del servidor de producción
            server_url = 'https://acceso.informaticauaint.com'
            
            # Llamar al endpoint de procesar salidas pendientes
            response = requests.post(
                f'{server_url}/api/procesar_salidas_pendientes',
                json={},
                verify=True  # En producción, verificar los certificados
            )
            
            if response.status_code == 200:
                print(f"Cierre diario ejecutado con éxito: {response.json()}")
            else:
                print(f"Error en cierre diario: {response.text}")
        
        except Exception as e:
            print(f"Error al ejecutar cierre diario: {str(e)}")
    
    # Crear el scheduler
    scheduler = BackgroundScheduler()
    
    # Programar la tarea para ejecutarse TODOS los días a las 23:59 (11:59 PM)
    scheduler.add_job(ejecutar_cierre_diario, 'cron', hour=23, minute=59)
    
    # Iniciar el scheduler
    scheduler.start()
    
    print("Tarea de cierre diario programada para ejecutarse a las 23:59 (11:59 PM)")


    # Endpoint para reiniciar estados de cumplimiento semanalmente
@app.route('/reiniciar_cumplimiento', methods=['POST'])
def reiniciar_cumplimiento():
    try:
        conn = get_connection()
        
        # Fecha actual
        now = get_current_datetime()
        fecha_actual = now.strftime('%Y-%m-%d')
        
        # 1. Crear tabla de historial si no existe
        with conn.cursor() as cursor:
            # Crear tabla para historial si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_cumplimiento (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT,
                    email VARCHAR(255),
                    nombre VARCHAR(100),
                    apellido VARCHAR(100),
                    semana_inicio DATE,
                    semana_fin DATE,
                    estado VARCHAR(50),
                    cumplidos INT,
                    incompletos INT,
                    ausentes INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
        # 2. Obtener cumplimiento actual para guardar en historial
        with conn.cursor() as cursor:
            # Fecha de inicio de semana (lunes) y fin (domingo)
            dias_atras = now.weekday()  # 0 es lunes, 6 es domingo
            inicio_semana = now - timedelta(days=dias_atras)
            fin_semana = inicio_semana + timedelta(days=6)
            
            inicio_semana_str = inicio_semana.strftime('%Y-%m-%d')
            fin_semana_str = fin_semana.strftime('%Y-%m-%d')
            
            # Obtener usuarios activos y sus horarios
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()
            
            historial_insertado = 0
            
            for user in usuarios:
                # Calcular cumplimiento actual para este usuario
                cursor.execute(
                    "SELECT * FROM horarios_asignados WHERE usuario_id = %s",
                    (user['id'],)
                )
                horarios = cursor.fetchall()
                
                # Si no tiene horarios, continuamos con el siguiente
                if not horarios:
                    continue
                
                # Obtener los registros de esta semana
                cursor.execute("""
                    SELECT * FROM registros 
                    WHERE email = %s AND fecha BETWEEN %s AND %s
                    ORDER BY fecha, hora
                """, (user['email'], inicio_semana_str, fecha_actual))
                
                registros_semana = cursor.fetchall()
                
                # Contar estados
                cumplidos = 0
                incompletos = 0
                ausentes = 0
                
                # Procesamiento simplificado para conteo
                for h in horarios:
                    # Tomar día de la semana del horario
                    dia_semana = h['dia'].lower()
                    
                    # Verificar si hay registros para este día y horario
                    cumplio_bloque = False
                    incompleto_bloque = False
                    
                    # Filtrar registros por día de la semana
                    registros_dia = [r for r in registros_semana if r['dia'].lower() == dia_semana]
                    
                    # Obtener horas de entrada y salida para este bloque
                    hora_entrada = h['hora_entrada']
                    hora_salida = h['hora_salida']
                    
                    # Convertir a datetime.time para comparación
                    if isinstance(hora_entrada, timedelta):
                        secs = int(hora_entrada.total_seconds())
                        hora_entrada_dt = time(secs//3600, (secs%3600)//60, secs%60)
                    elif isinstance(hora_entrada, str):
                        hora_entrada_dt = datetime.strptime(hora_entrada, "%H:%M:%S").time()
                    else:
                        hora_entrada_dt = hora_entrada
                    
                    if isinstance(hora_salida, timedelta):
                        secs = int(hora_salida.total_seconds())
                        hora_salida_dt = time(secs//3600, (secs%3600)//60, secs%60)
                    elif isinstance(hora_salida, str):
                        hora_salida_dt = datetime.strptime(hora_salida, "%H:%M:%S").time()
                    else:
                        hora_salida_dt = hora_salida
                    
                    # Verificar cumplimiento simplificado para historial
                    entradas = [r for r in registros_dia if r['tipo'] == 'Entrada']
                    salidas = [r for r in registros_dia if r['tipo'] == 'Salida']
                    
                    if entradas and salidas:
                        for entrada in entradas:
                            # Hora entrada
                            if isinstance(entrada['hora'], str):
                                t_entrada = datetime.strptime(entrada['hora'], "%H:%M:%S").time()
                            elif isinstance(entrada['hora'], timedelta):
                                secs = int(entrada['hora'].total_seconds())
                                t_entrada = time(secs//3600, (secs%3600)//60, secs%60)
                            else:
                                t_entrada = entrada['hora']
                            
                            for salida in salidas:
                                if salida['id'] > entrada['id']:
                                    # Hora salida
                                    if isinstance(salida['hora'], str):
                                        t_salida = datetime.strptime(salida['hora'], "%H:%M:%S").time()
                                    elif isinstance(salida['hora'], timedelta):
                                        secs = int(salida['hora'].total_seconds())
                                        t_salida = time(secs//3600, (secs%3600)//60, secs%60)
                                    else:
                                        t_salida = salida['hora']
                                    
                                    # Verificar cumplimiento
                                    if t_entrada <= hora_entrada_dt and t_salida >= hora_salida_dt:
                                        cumplio_bloque = True
                                        break
                                    elif ((t_entrada > hora_entrada_dt and t_entrada < hora_salida_dt and t_salida >= hora_salida_dt) or
                                          (t_entrada <= hora_entrada_dt and t_salida < hora_salida_dt) or
                                          (t_entrada < hora_salida_dt and t_salida > hora_entrada_dt)):
                                        incompleto_bloque = True
                            
                            if cumplio_bloque:
                                break
                    
                    # Incrementar contadores
                    if cumplio_bloque:
                        cumplidos += 1
                    elif incompleto_bloque:
                        incompletos += 1
                    else:
                        ausentes += 1
                
                # Determinar estado general para el historial
                if len(horarios) == 0:
                    estado = "No Aplica"
                elif cumplidos == len(horarios):
                    estado = "Cumple"
                elif ausentes == len(horarios):
                    estado = "Ausente"
                elif incompletos > 0 or (cumplidos > 0 and ausentes > 0):
                    estado = "Incompleto"
                else:
                    estado = "No Cumple"
                
                # Guardar en historial
                cursor.execute("""
                    INSERT INTO historial_cumplimiento
                    (usuario_id, email, nombre, apellido, semana_inicio, semana_fin, 
                     estado, cumplidos, incompletos, ausentes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user['id'],
                    user['email'],
                    user['nombre'],
                    user['apellido'],
                    inicio_semana_str,
                    fin_semana_str,
                    estado,
                    cumplidos,
                    incompletos,
                    ausentes
                ))
                
                historial_insertado += 1
            
            conn.commit()
        
        # 3. Reiniciar el estado de los bloques (opcional - esto depende de la lógica actual)
        # Este paso no es necesario si el cumplimiento se calcula en tiempo real
        # Pero podemos añadir una bandera para indicar el inicio de una nueva semana
        
        with conn.cursor() as cursor:
            # Establecer alguna marca para indicar nuevo inicio de semana
            # Por ejemplo, una tabla de configuración del sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sistema_config (
                    clave VARCHAR(50) PRIMARY KEY,
                    valor TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Actualizar la fecha de último reinicio
            cursor.execute("""
                INSERT INTO sistema_config (clave, valor) 
                VALUES ('ultimo_reinicio_cumplimiento', %s)
                ON DUPLICATE KEY UPDATE valor = %s
            """, (fecha_actual, fecha_actual))
            
            conn.commit()
        
        conn.close()
        
        return jsonify({
            "mensaje": "Reinicio de cumplimiento semanal completado",
            "fecha_reinicio": fecha_actual,
            "registros_historial": historial_insertado
        })
        
    except Exception as e:
        print(f"Error en reinicio de cumplimiento: {e}")
        return jsonify({"error": str(e)}), 500

# --- Endpoint para obtener historial de cumplimiento ---
@app.route('/historial_cumplimiento/<email>', methods=['GET'])
def get_historial_cumplimiento(email):
    try:
        conn = get_connection()
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM historial_cumplimiento
                WHERE email = %s
                ORDER BY semana_inicio DESC
            """, (email,))
            
            historial = cursor.fetchall()
            
            # Formatear fechas
            for item in historial:
                for key, value in item.items():
                    if isinstance(value, (datetime, date)):
                        item[key] = value.isoformat()
        
        conn.close()
        return jsonify(historial)
        
    except Exception as e:
        print(f"Error al obtener historial de cumplimiento: {e}")
        return jsonify({"error": str(e)}), 500

# --- Programar tarea semanal de reinicio ---
def configurar_reinicio_semanal():
    """
    Configura una tarea programada para reiniciar los estados de cumplimiento
    cada semana (por ejemplo, los domingos a la medianoche).
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    import requests
    
    def ejecutar_reinicio_semanal():
        try:
            # Llamar al endpoint de reinicio
            response = requests.post(
                'https://localhost:5000/reiniciar_cumplimiento',
                json={},
                verify=False  # Para desarrollo local
            )
            
            if response.status_code == 200:
                print(f"Reinicio semanal de cumplimiento ejecutado: {response.json()}")
            else:
                print(f"Error en reinicio semanal: {response.text}")
        
        except Exception as e:
            print(f"Error al ejecutar reinicio semanal: {str(e)}")
    
    # Crear el scheduler
    scheduler = BackgroundScheduler()
    
    # Programar la tarea para ejecutarse los domingos a las 23:55
    scheduler.add_job(ejecutar_reinicio_semanal, 'cron', day_of_week='sun', hour=23, minute=55)
    
    # Iniciar el scheduler
    scheduler.start()
    
    print("Tarea de reinicio semanal programada para los domingos a las 23:55")

# Modificar la sección principal para incluir ambas tareas programadas
if __name__ == '__main__':
    # Definir la URL del servidor para el cierre automático
    SERVER_URL = 'https://acceso.informaticauaint.com'
    
    # Intentar configurar las tareas programadas (requiere apscheduler)
    try:
        import apscheduler
        configurar_tarea_cierre_diario()
        configurar_reinicio_semanal()  # Mantener el reinicio semanal
        print("Tareas programadas configuradas correctamente:")
        print(f"- Cierre automático: diariamente a las 23:59 (11:59 PM)")
        print(f"- Reinicio semanal: domingos a las 23:55")
        print(f"- URL para el cierre automático: {SERVER_URL}/api/procesar_salidas_pendientes")
    except ImportError:
        print("ADVERTENCIA: No se pudieron configurar las tareas programadas.")
        print("Instale 'apscheduler' con: pip install apscheduler")
        print("O ejecute manualmente los endpoints /procesar_salidas_pendientes y /reiniciar_cumplimiento")
    
    # Definir rutas a los certificados
    # Opción 1: Rutas absolutas
    cert_path = 'certificate.pem'  # Actualiza esta ruta
    key_path = 'privatekey.pem'  # Actualiza esta ruta
    
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
    
    print(f"Iniciando servidor HTTPS en 10.0.3.54:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=context)