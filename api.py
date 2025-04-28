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

            # Traer usuarios activos
            cursor.execute("SELECT * FROM usuarios_permitidos WHERE activo = 1")
            usuarios = cursor.fetchall()

            resultado = []

            # Fecha de inicio de semana (lunes)
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week_str = start_of_week.strftime('%Y-%m-%d')

            for user in usuarios:
                # Traer sus horarios asignados
                cursor.execute(
                    "SELECT * FROM horarios_asignados WHERE usuario_id = %s",
                    (user['id'],)
                )
                horarios = cursor.fetchall()

                # Si no tiene horarios, “No Aplica”
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

                # Un bloque por cada horario
                for h in horarios:
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
                    if h['dia'].lower() == dia_actual_esp:
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s AND fecha = %s
                            ORDER BY hora
                        """, (user['email'], fecha_actual))
                    else:
                        cursor.execute("""
                            SELECT * FROM registros
                            WHERE email = %s
                              AND dia = %s
                              AND fecha BETWEEN %s AND %s
                            ORDER BY fecha DESC, hora
                        """, (user['email'], h['dia'], start_of_week_str, fecha_actual))

                    registros_del_dia = cursor.fetchall()

                    # --- Revisar pares entrada-salida para ver si cubren el bloque ---
                    registros_en_bloque = False
                    for i in range(0, len(registros_del_dia), 2):
                        if i + 1 < len(registros_del_dia):
                            r1 = registros_del_dia[i]
                            r2 = registros_del_dia[i+1]

                            # Entrada
                            if isinstance(r1['hora'], str):
                                t1 = datetime.strptime(r1['hora'], "%H:%M:%S").time()
                            elif isinstance(r1['hora'], timedelta):
                                secs = int(r1['hora'].total_seconds())
                                t1 = time(secs//3600, (secs%3600)//60, secs%60)
                            else:
                                t1 = r1['hora']

                            # Salida
                            if isinstance(r2['hora'], str):
                                t2 = datetime.strptime(r2['hora'], "%H:%M:%S").time()
                            elif isinstance(r2['hora'], timedelta):
                                secs = int(r2['hora'].total_seconds())
                                t2 = time(secs//3600, (secs%3600)//60, secs%60)
                            else:
                                t2 = r2['hora']

                            # Casos de cobertura
                            caso1 = (t1 <= hora_entrada_dt and t2 > hora_entrada_dt)
                            caso2 = (t1 > hora_entrada_dt and t1 < hora_salida_dt)
                            caso3 = (t2 >= hora_salida_dt and t1 < hora_salida_dt)
                            caso4 = (t1 >= hora_entrada_dt and t2 <= hora_salida_dt)
                            if caso1 or caso2 or caso3 or caso4:
                                registros_en_bloque = True
                                break

                    # --- Determinar estado según día actual o no ---
                    if h['dia'].lower() == dia_actual_esp:
                        now_t = datetime.strptime(hora_actual, "%H:%M:%S").time()
                        if registros_en_bloque:
                            if now_t < hora_entrada_dt:
                                bloque_estado = "Pendiente"
                            elif hora_entrada_dt <= now_t < hora_salida_dt:
                                bloque_estado = "Cumpliendo"
                            else:
                                bloque_estado = "Cumplido"
                                cumplidos += 1
                        else:
                            if now_t < hora_entrada_dt:
                                bloque_estado = "Pendiente"
                            elif hora_entrada_dt <= now_t < hora_salida_dt:
                                bloque_estado = "Atrasado"
                            else:
                                bloque_estado = "Ausente"
                    else:
                        if registros_en_bloque:
                            bloque_estado = "Cumplido"
                            cumplidos += 1
                        else:
                            bloque_estado = "Ausente"

                    bloques_info.append({
                        "bloque": bloque_label,
                        "estado": bloque_estado
                    })

                # Estado general
                if cumplidos == len(horarios):
                    estado_usuario = "Cumple"
                elif cumplidos > 0:
                    estado_usuario = "En Curso"
                else:
                    estado_usuario = "No Cumple"

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

    
    
# --- ENDPOINT: Ayudantes presentes (modificado) ---
@app.route('/ayudantes_presentes', methods=['GET'])
def get_ayudantes_presentes():
    try:
        conn = get_connection()
        
        with conn.cursor() as cursor:
            # Obtener directamente de la tabla de estados
            cursor.execute("""
                SELECT e.email, e.nombre, e.apellido, e.estado, 
                       e.ultima_entrada, u.foto_url
                FROM estado_usuarios e
                LEFT JOIN usuarios_permitidos u ON e.email = u.email
                WHERE e.estado = 'dentro'
            """)
            
            ayudantes_dentro = cursor.fetchall()
            
            # Formateo de datos
            for ayudante in ayudantes_dentro:
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
            HORAS_POR_DIA = 8.0

            for usuario in usuarios:
                # 2) Traer todos los registros ordenados por fecha y hora
                cursor.execute("""
                    SELECT fecha, hora 
                    FROM registros 
                    WHERE email = %s 
                    ORDER BY fecha, hora
                """, (usuario['email'],))
                todos = cursor.fetchall()

                # 3) Agrupar por día
                regs_por_dia = {}
                for reg in todos:
                    # formatear fecha a string YYYY-MM-DD
                    if isinstance(reg['fecha'], date):
                        fecha_str = reg['fecha'].strftime('%Y-%m-%d')
                    else:
                        fecha_str = str(reg['fecha'])
                    regs_por_dia.setdefault(fecha_str, []).append(reg)

                horas_totales = 0
                dias_procesados = set()

                # 4) Procesar cada día
                for fecha, regs in regs_por_dia.items():
                    # ordenar por hora
                    regs.sort(key=lambda x: x['hora'])

                    # si es impar, añado salida ficticia a las 23:59:59
                    if len(regs) % 2 != 0:
                        ultimo = regs[-1].copy()
                        ultimo['hora'] = "23:59:59"
                        regs.append(ultimo)

                    # 5) Calcular pares entrada–salida
                    for i in range(0, len(regs), 2):
                        entrada_raw = regs[i]['hora']
                        salida_raw  = regs[i+1]['hora']

                        # convertir entrada a datetime.time
                        if isinstance(entrada_raw, timedelta):
                            secs = int(entrada_raw.total_seconds())
                            hh, rem = divmod(secs, 3600)
                            mm, ss  = divmod(rem, 60)
                            entrada_t = time(hh, mm, ss)
                        elif isinstance(entrada_raw, str):
                            entrada_t = datetime.strptime(entrada_raw, "%H:%M:%S").time()
                        else:
                            entrada_t = entrada_raw

                        # convertir salida a datetime.time
                        if isinstance(salida_raw, timedelta):
                            secs = int(salida_raw.total_seconds())
                            hh, rem = divmod(secs, 3600)
                            mm, ss  = divmod(rem, 60)
                            salida_t = time(hh, mm, ss)
                        elif isinstance(salida_raw, str):
                            salida_t = datetime.strptime(salida_raw, "%H:%M:%S").time()
                        else:
                            salida_t = salida_raw

                        # combinar con fecha mínima para poder restar
                        dt_ent = datetime.combine(datetime.min.date(), entrada_t)
                        dt_sal = datetime.combine(datetime.min.date(), salida_t)

                        if dt_sal > dt_ent:
                            diff = dt_sal - dt_ent
                            horas_totales += diff.total_seconds() / 3600

                    dias_procesados.add(fecha)

                # 6) Calcular días completos
                dias_completos = horas_totales / HORAS_POR_DIA

                resultado.append({
                    "nombre": usuario['nombre'],
                    "apellido": usuario['apellido'],
                    "email": usuario['email'],
                    "dias_asistidos": round(dias_completos, 1),
                    "horas_totales": round(horas_totales, 1),
                    "dias_calendario": len(dias_procesados)
                })

        conn.close()
        return jsonify(resultado)

    except Exception as e:
        print(f"Error al obtener horas acumuladas: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT: Detalle de horas por usuario (para debugging) ---
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
@app.route('/procesar_salidas_pendientes', methods=['POST'])
def procesar_salidas_pendientes():
    try:
        # Fecha a procesar (por defecto, ahora)
        data = request.get_json() or {}
        
        conn = get_connection()
        registros_procesados = []
        
        with conn.cursor() as cursor:
            # Buscar usuarios con estado 'dentro' que no hayan registrado salida
            cursor.execute("""
                SELECT e.email, e.nombre, e.apellido, u.id as usuario_id
                FROM estado_usuarios e
                JOIN usuarios_permitidos u ON e.email = u.email
                WHERE e.estado = 'dentro'
            """)
            
            usuarios_dentro = cursor.fetchall()
            
            now = get_current_datetime()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            
            # Día de la semana en español
            dias = {
                'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
                'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
            }
            dia = dias.get(now.strftime("%A"), now.strftime("%A"))
            
            for usuario in usuarios_dentro:
                # Insertar registro de salida automático
                cursor.execute("""
                    INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, tipo, auto_generado)
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