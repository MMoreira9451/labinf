import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.modalview import ModalView
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import cv2
from pyzbar.pyzbar import decode
import json
import time
from datetime import datetime, timedelta
import pymysql
import unicodedata
import sys

# Definir colores para la interfaz
COLORS = {
    'primary': '#3498db',      # Azul principal
    'success': '#2ecc71',      # Verde para éxito
    'error': '#e74c3c',        # Rojo para error
    'warning': '#f39c12',      # Amarillo para advertencia
    'dark_bg': '#2c3e50',      # Fondo oscuro
    'light_text': '#ecf0f1',   # Texto claro
    'dark_text': '#34495e',    # Texto oscuro
    'accent': '#9b59b6',       # Color de acento
    'inactive': '#95a5a6',     # Color inactivo
    'button': '#3498db',       # Color de botón
    'entry': '#27ae60',        # Color para entrada
    'exit': '#e67e22'          # Color para salida
}

class BackgroundLayout(BoxLayout):
    """Un BoxLayout con un fondo de color"""
    def __init__(self, bg_color=COLORS['dark_bg'], **kwargs):
        super(BackgroundLayout, self).__init__(**kwargs)
        self.bg_color = get_color_from_hex(bg_color)
        
        with self.canvas.before:
            Color(*self.bg_color)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
    
    def _update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class LectorQR(BackgroundLayout):
    def __init__(self, **kwargs):
        super(LectorQR, self).__init__(bg_color=COLORS['dark_bg'], **kwargs)
        self.orientation = 'vertical'
        
        # Configuración de la cámara
        self.capture = cv2.VideoCapture(0)
        self.capture.set(3, 640)  # Ancho
        self.capture.set(4, 480)  # Alto
        
        # Estado del lector
        self.is_scanning = True
        self.last_scan_time = 0
        self.scan_cooldown = 5  # Segundos entre escaneos
        
        # Configuración de la base de datos MySQL
        self.db_config = {
            'host': '10.0.3.54',
            'user': 'mm',
            'password': 'Gin160306',
            'database': 'registro_qr',
            'port': 3306,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        # Crear la interfaz de usuario
        self.setup_ui()
        
        # Iniciar la actualización de la cámara
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # 30 FPS
    
    def get_db_connection(self):
        """Establece y retorna una conexión a la base de datos MySQL"""
        try:
            conn = pymysql.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"Error de conexión a MySQL: {str(e)}")
            return None
    
    def normalize_text(self, text):
        """Normaliza el texto para comparaciones"""
        if text is None:
            return ""

        # Ensure we're working with unicode strings
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = text.decode('latin-1')
                except UnicodeDecodeError:
                    text = text.decode('utf-8', errors='ignore')

        # Clean up encoding artifacts without re-encoding
        text = text.replace('ﾃｭ', 'í')
        text = text.replace('ﾃｱ', 'ñ')
        text = text.replace('ﾃ³', 'ó')
        text = text.replace('ﾃ¡', 'á')
        text = text.replace('ﾃ©', 'é')
        text = text.replace('ﾃｺ', 'ú')

        # Then proceed with normalization
        text = text.lower()
    
        # Use unicodedata to remove accents but avoid re-encoding issues
        normalized = ''
        for c in unicodedata.normalize('NFD', text):
            if unicodedata.category(c) != 'Mn':
                normalized += c
    
        # Handle ñ specifically
        normalized = normalized.replace('ñ', 'n')
    
        # Remove non-alphanumeric characters
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
    
        return normalized
    
    def setup_ui(self):
        # Título
        title_box = BackgroundLayout(size_hint=(1, 0.1), bg_color=COLORS['primary'])
        self.title_label = Label(
            text="Lector de QR - Control de Acceso", 
            font_size='24sp',
            bold=True,
            color=get_color_from_hex(COLORS['light_text'])
        )
        title_box.add_widget(self.title_label)
        self.add_widget(title_box)
        
        # Vista de la cámara con marco
        camera_container = BackgroundLayout(size_hint=(1, 0.7), bg_color=COLORS['dark_bg'])
        camera_inner = BoxLayout(padding=10)
        self.image = Image(size_hint=(1, 1))
        camera_inner.add_widget(self.image)
        camera_container.add_widget(camera_inner)
        self.add_widget(camera_container)
        
        # Área de estado con degradado
        status_box = BackgroundLayout(size_hint=(1, 0.1), bg_color=COLORS['dark_bg'], padding=[10, 5])
        self.status_label = Label(
            text="Escanea un código QR",
            font_size='18sp',
            bold=True,
            color=get_color_from_hex(COLORS['light_text'])
        )
        status_box.add_widget(self.status_label)
        self.add_widget(status_box)
        
        # Botones
        button_box = BackgroundLayout(size_hint=(1, 0.1), bg_color=COLORS['dark_bg'], padding=[10, 5], spacing=10)
        
        self.toggle_button = Button(
            text="Pausar",
            background_color=get_color_from_hex(COLORS['button']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True,
            size_hint=(0.5, 1)
        )
        self.toggle_button.bind(on_press=self.toggle_scanning)
        
        self.quit_button = Button(
            text="Salir",
            background_color=get_color_from_hex(COLORS['error']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True,
            size_hint=(0.5, 1)
        )
        self.quit_button.bind(on_press=self.quit_app)
        
        button_box.add_widget(self.toggle_button)
        button_box.add_widget(self.quit_button)
        self.add_widget(button_box)
    
    def update(self, dt):
        # Capturar frame de la cámara
        ret, frame = self.capture.read()
        
        if ret:
            # Voltear horizontalmente para una vista de espejo
            frame = cv2.flip(frame, 1)
            
            # Procesar para encontrar códigos QR si el escáner está activo
            if self.is_scanning:
                # Convertir a escala de grises para mejor detección
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                qr_codes = decode(gray)
                
                current_time = time.time()
                
                for qr in qr_codes:
                    # Dibujar rectángulo alrededor del QR
                    points = qr.polygon
                    if points:
                        pts = []
                        for point in points:
                            pts.append([point.x, point.y])
                        
                        import numpy as np
                        pts = np.array(pts, np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
                    
                    # Procesar datos del QR si ha pasado suficiente tiempo desde el último escaneo
                    if current_time - self.last_scan_time > self.scan_cooldown:
                        data = qr.data.decode('utf-8')
                        self.verificar_usuario(data)
                        self.last_scan_time = current_time
            
            # Convertir para mostrar en Kivy
            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture
    
    def verificar_usuario(self, data):
        try:
            # Add logging for raw data
            print(f"Raw QR data: {data}")
    
            try:
                # Try to decode with utf-8 first
                user_data = json.loads(data)
            
                # Log the parsed data
                print(f"Parsed QR data: {user_data}")
            
                # Clean up the string values to handle encoding issues
                for key in ['name', 'surname', 'email']:
                    if key in user_data:
                        # Clean up potential encoding issues
                        try:
                            cleaned_value = user_data[key].encode('utf-8').decode('utf-8')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                                cleaned_value = user_data[key].encode('utf-8', errors='replace').decode('utf-8', errors='replace')

                        user_data[key] = cleaned_value.strip()
            
                # Log the cleaned data
                print(f"Cleaned QR data: {user_data}")
            
                # Verify if QR is expired
                if user_data.get('expired') == True or user_data.get('status') == "EXPIRED":
                    self.mostrar_resultado(False, "QR expirado", "El código QR ha expirado")
                    return
            
                # If we get here, verify the data with the database
                self.status_label.text = "Verificando usuario..."
            
                # Extract user data
                nombre = user_data.get('name', '')
                apellido = user_data.get('surname', '')
                email = user_data.get('email', '')
            
                # Log the extracted data before normalization
                print(f"Before normalization - Nombre: {nombre}, Apellido: {apellido}, Email: {email}")
            
                # Verify user in database
                resultado = self.verificar_usuario_db(nombre, apellido, email)
            
                # Show result
                if resultado["success"]:
                    tipo_registro = resultado.get("tipo", "Registro")
                    self.mostrar_resultado(True, f"{tipo_registro} registrado", resultado["message"])
                else:
                    self.mostrar_resultado(False, "Error", resultado["error"])
            
            except json.JSONDecodeError:
                # If QR contains "Expirado" as plain text
                if "Expirado" in data:
                    self.mostrar_resultado(False, "QR expirado", "El código QR ha expirado")
                else:
                    self.mostrar_resultado(False, "Formato inválido", "El QR no tiene un formato JSON válido")
    
        except Exception as e:
            print(f"Error processing QR: {str(e)}")
            self.mostrar_resultado(False, "Error", f"Error al procesar el QR: {str(e)}")
    
    def verificar_usuario_db(self, nombre, apellido, email):
        conn = None
        try:
            # Connect to database
            conn = self.get_db_connection()
            if not conn:
                return {"success": False, "error": "No se pudo conectar a la base de datos"}
            
            cursor = conn.cursor()
    
            # Normalize user data from QR
            norm_nombre = self.normalize_text(nombre)
            norm_apellido = self.normalize_text(apellido)
            norm_email = self.normalize_text(email)
    
            # Add logs for debugging
            print(f"QR Data after normalization - Nombre: {norm_nombre}, Apellido: {norm_apellido}, Email: {norm_email}")
    
            # Check if user is allowed
            cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
            all_permitted_users = cursor.fetchall()
    
            is_permitted = False
            matching_user = None
    
            for user in all_permitted_users:
                # En MySQL con DictCursor, user es un diccionario
                db_id = user['id']
                db_nombre = user['nombre']
                db_apellido = user['apellido']
                db_email = user['email']
        
                # Normalize database data
                norm_db_nombre = self.normalize_text(db_nombre)
                norm_db_apellido = self.normalize_text(db_apellido)
                norm_db_email = self.normalize_text(db_email)
        
                # Print for debugging
                print(f"DB User - ID: {db_id}, Nombre: {norm_db_nombre}, Apellido: {norm_db_apellido}, Email: {norm_db_email}")
        
                # Email is the most reliable identifier, try that first
                if norm_db_email == norm_email:
                    is_permitted = True
                    matching_user = user
                    break
        
                # If email doesn't match exactly, try with name and surname
                elif (norm_db_nombre == norm_nombre and norm_db_apellido == norm_apellido):
                    is_permitted = True
                    matching_user = user
                    break
            
                # Even more relaxed matching - if both name and email partially match
                elif (norm_db_email.find(norm_email) != -1 or norm_email.find(norm_db_email) != -1) and \
                     (norm_db_nombre.find(norm_nombre) != -1 or norm_nombre.find(norm_db_nombre) != -1):
                    is_permitted = True
                    matching_user = user
                    break
    
            if not is_permitted:
                if conn:
                    conn.close()
                return {"success": False, "error": "Usuario no permitido"}
    
            # If user is allowed, use DB data for registration
            db_id = matching_user['id']
            db_nombre = matching_user['nombre']
            db_apellido = matching_user['apellido']
            db_email = matching_user['email']
    
            # Register entry/exit
            now = datetime.now()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            dia = now.strftime("%A").lower()  # Día en inglés
            
            # Traducir día a español si es necesario
            dias_traduccion = {
                'monday': 'lunes', 
                'tuesday': 'martes', 
                'wednesday': 'miércoles',
                'thursday': 'jueves', 
                'friday': 'viernes', 
                'saturday': 'sábado', 
                'sunday': 'domingo'
            }
            dia_esp = dias_traduccion.get(dia, dia)
    
            # Verificar qué columnas existen en la tabla registros
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'registros' 
                AND (COLUMN_NAME = 'metodo' OR COLUMN_NAME = 'tipo')
            """, (self.db_config['database'],))
            
            column_info = cursor.fetchone()
            tipo_column_name = column_info['COLUMN_NAME'] if column_info else None
            
            # Verificar si existe la columna timestamp
            cursor.execute("""
                SELECT COUNT(*) as exists_column 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'registros' 
                AND COLUMN_NAME = 'timestamp'
            """, (self.db_config['database'],))
            
            timestamp_exists = cursor.fetchone()['exists_column'] > 0
    
            # Determinar si es entrada o salida
            if tipo_column_name == 'tipo':
                cursor.execute('''
                    SELECT tipo FROM registros 
                    WHERE email = %s AND fecha = %s 
                    ORDER BY id DESC LIMIT 1
                ''', (db_email, fecha))
                ultimo_registro = cursor.fetchone()
                tipo = "Salida" if (ultimo_registro and ultimo_registro['tipo'] == "Entrada") else "Entrada"
            elif tipo_column_name == 'metodo':
                cursor.execute('''
                    SELECT metodo FROM registros 
                    WHERE email = %s AND fecha = %s 
                    ORDER BY id DESC LIMIT 1
                ''', (db_email, fecha))
                ultimo_registro = cursor.fetchone()
                tipo = "Salida" if (ultimo_registro and ultimo_registro['metodo'] == "Entrada") else "Entrada"
            else:
                # Si no existe ninguna de esas columnas, alternamos basado en el número de registros
                cursor.execute('''
                    SELECT COUNT(*) as count_registros
                    FROM registros 
                    WHERE email = %s AND fecha = %s
                ''', (db_email, fecha))
                count_result = cursor.fetchone()
                tipo = "Salida" if (count_result and count_result['count_registros'] % 2 == 1) else "Entrada"
            
            # Inserción en la base de datos teniendo en cuenta las columnas disponibles
            try:
                if tipo_column_name and timestamp_exists:
                    # Tenemos ambas columnas (tipo/metodo y timestamp)
                    cursor.execute(f'''
                        INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, {tipo_column_name}, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (fecha, hora, dia_esp, db_nombre, db_apellido, db_email, tipo, now))
                elif tipo_column_name:
                    # Solo tenemos tipo/metodo pero no timestamp
                    cursor.execute(f'''
                        INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, {tipo_column_name})
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (fecha, hora, dia_esp, db_nombre, db_apellido, db_email, tipo))
                elif timestamp_exists:
                    # Solo tenemos timestamp pero no tipo/metodo
                    cursor.execute('''
                        INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (fecha, hora, dia_esp, db_nombre, db_apellido, db_email, now))
                else:
                    # No tenemos ninguna columna adicional
                    cursor.execute('''
                        INSERT INTO registros (fecha, hora, dia, nombre, apellido, email)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (fecha, hora, dia_esp, db_nombre, db_apellido, db_email))
                
                # Si no tenemos la columna tipo/metodo, intentamos crearla
                if not tipo_column_name:
                    try:
                        cursor.execute("""
                            ALTER TABLE registros 
                            ADD COLUMN metodo VARCHAR(20) DEFAULT 'Entrada'
                        """)
                        conn.commit()
                        print("Columna 'metodo' agregada a la tabla registros")
                    except Exception as alter_err:
                        print(f"No se pudo agregar la columna 'metodo': {str(alter_err)}")
                        conn.rollback()
                
                # Si no tenemos la columna timestamp, intentamos crearla
                if not timestamp_exists:
                    try:
                        cursor.execute("""
                            ALTER TABLE registros 
                            ADD COLUMN timestamp DATETIME NULL
                        """)
                        conn.commit()
                        print("Columna 'timestamp' agregada a la tabla registros")
                    except Exception as alter_err:
                        print(f"No se pudo agregar la columna 'timestamp': {str(alter_err)}")
                        conn.rollback()
                
            except Exception as e:
                # Si ocurre cualquier error, intentamos la inserción básica
                print(f"Error en inserción: {str(e)}")
                cursor.execute('''
                    INSERT INTO registros (fecha, hora, dia, nombre, apellido, email)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (fecha, hora, dia_esp, db_nombre, db_apellido, db_email))
    
            conn.commit()
            registro_id = cursor.lastrowid
            
            # Verificar horario (opcional)
            horario_ok, msg_horario = self.verificar_horario(db_email, dia_esp, hora)
            mensaje = f"{db_nombre} {db_apellido}\nFecha: {fecha} | Hora: {hora}"
            if horario_ok:
                mensaje += "\n✓ " + msg_horario
            else:
                mensaje += "\n⚠ " + msg_horario
            
            if conn:
                conn.close()
    
            return {
                "success": True,
                "message": mensaje,
                "id": registro_id,
                "fecha": fecha,
                "hora": hora,
                "tipo": tipo
            }
    
        except Exception as e:
            print(f"Database error: {str(e)}")
            if conn:
                conn.close()
            return {"success": False, "error": f"Error en base de datos: {str(e)}"}
    
    def verificar_horario(self, email, dia_semana, hora_actual):
        conn = None
        try:
            conn = self.get_db_connection()
            if not conn:
                return False, "No se pudo conectar a la base de datos"
                
            cursor = conn.cursor()
            
            # Buscar los bloques de horario para este usuario en este día
            cursor.execute("""
                SELECT h.hora_entrada, h.hora_salida 
                FROM horarios_asignados h
                JOIN usuarios_permitidos u ON h.usuario_id = u.id
                WHERE u.email = %s AND LOWER(h.dia) = %s
                ORDER BY h.hora_entrada
            """, (email, dia_semana.lower()))
            
            bloques = cursor.fetchall()
            
            if not bloques:
                if conn:
                    conn.close()
                return False, "No tiene horario asignado para hoy"
            
            # Convertir hora actual a objeto datetime para comparar
            hora_dt = datetime.strptime(hora_actual, "%H:%M:%S").time()
            
            # Verificar si la hora actual está dentro de algún bloque
            for bloque in bloques:
                hora_entrada = datetime.strptime(bloque['hora_entrada'], "%H:%M:%S").time()
                hora_salida = datetime.strptime(bloque['hora_salida'], "%H:%M:%S").time()
                
                if hora_entrada <= hora_dt <= hora_salida:
                    if conn:
                        conn.close()
                    return True, f"Dentro del horario ({bloque['hora_entrada']} - {bloque['hora_salida']})"
            
            # Si llegamos aquí, no está en ningún bloque
            # Encontrar el bloque más cercano
            bloques_dt = [(datetime.strptime(bloque['hora_entrada'], "%H:%M:%S").time(), 
                           datetime.strptime(bloque['hora_salida'], "%H:%M:%S").time()) for bloque in bloques]
            
            # Ordenar por proximidad
            bloques_dt.sort(key=lambda b: 
                abs((datetime.combine(datetime.today(), hora_dt) - 
                     datetime.combine(datetime.today(), b[0])).total_seconds()))
            
            proximo = bloques_dt[0]
            if conn:
                conn.close()
            return False, f"Fuera de horario. Bloque más cercano: {proximo[0].strftime('%H:%M:%S')} - {proximo[1].strftime('%H:%M:%S')}"
            
        except Exception as e:
            print(f"Error verificando horario: {str(e)}")
            if conn:
                conn.close()
            return False, f"Error al verificar horario: {str(e)}"
    
    def mostrar_resultado(self, success, title, message):
        # Crear una vista modal para mostrar el resultado
        modal = ModalView(size_hint=(0.8, 0.4), auto_dismiss=True)
        content = BackgroundLayout(orientation='vertical', padding=20, spacing=10, 
                                 bg_color=COLORS['entry'] if title.startswith("Entrada") else 
                                          COLORS['exit'] if title.startswith("Salida") else
                                          COLORS['success'] if success else COLORS['error'])
        
        # Icono de éxito o error
        icon_text = "➡️" if title.startswith("Entrada") else "⬅️" if title.startswith("Salida") else "✓" if success else "✗"
        icon_label = Label(
            text=icon_text,
            font_size='40sp',
            bold=True,
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(1, 0.2)
        )
        
        # Título
        title_label = Label(
            text=title,
            font_size='22sp',
            bold=True,
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(1, 0.3)
        )
        
        # Mensaje
        msg_label = Label(
            text=message,
            font_size='18sp',
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(1, 0.5),
            halign='center'
        )
        msg_label.bind(size=msg_label.setter('text_size'))
        
        # Añadir widgets al layout
        content.add_widget(icon_label)
        content.add_widget(title_label)
        content.add_widget(msg_label)
        
        # Configurar color de fondo según resultado
        if title.startswith("Entrada"):
            entry_color = get_color_from_hex(COLORS['entry'])
            modal.background_color = [entry_color[0], entry_color[1], entry_color[2], 0.95]
        elif title.startswith("Salida"):
            exit_color = get_color_from_hex(COLORS['exit'])
            modal.background_color = [exit_color[0], exit_color[1], exit_color[2], 0.95]
        elif success:
            success_color = get_color_from_hex(COLORS['success'])
            modal.background_color = [success_color[0], success_color[1], success_color[2], 0.95]
        else:
            error_color = get_color_from_hex(COLORS['error'])
            modal.background_color = [error_color[0], error_color[1], error_color[2], 0.95]
        
        # Mostrar el modal
        modal.add_widget(content)
        modal.open()
        
        # Programar cierre automático después de 5 segundos
        Clock.schedule_once(lambda dt: modal.dismiss(), 5)
        
        # Cambiar el texto del status
        if success:
            self.status_label.text = f"¡{title}!"
            if title.startswith("Entrada"):
                self.status_label.color = get_color_from_hex(COLORS['entry'])
            elif title.startswith("Salida"):
                self.status_label.color = get_color_from_hex(COLORS['exit'])
            else:
                self.status_label.color = get_color_from_hex(COLORS['success'])
        else:
            self.status_label.text = f"Error: {title}"
            self.status_label.color = get_color_from_hex(COLORS['error'])
        
        # Restaurar color después de un tiempo
        Clock.schedule_once(self.reset_status_color, 6)  # 6 segundos para que el mensaje se vea después del cierre del modal
    
    def reset_status_color(self, dt):
        self.status_label.text = "Escanea un código QR"
        self.status_label.color = get_color_from_hex(COLORS['light_text'])
    
    def toggle_scanning(self, instance):
        self.is_scanning = not self.is_scanning
        if self.is_scanning:
            self.toggle_button.text = "Pausar"
            self.toggle_button.background_color = get_color_from_hex(COLORS['button'])
            self.status_label.text = "Escanea un código QR"
        else:
            self.toggle_button.text = "Reanudar"
            self.toggle_button.background_color = get_color_from_hex(COLORS['accent'])
            self.status_label.text = "Escáner en pausa"
    
    def quit_app(self, instance):
       # Liberar la cámara
       self.capture.release()
       # Desactivar cualquier Clock Schedule
       Clock.unschedule(self.update)
       Clock.unschedule(self.reset_status_color)
       # Salir de la aplicación
       App.get_running_app().stop()
       # Para evitar el error al cerrar, forzamos la salida
       sys.exit(0)

class LectorQRApp(App):
   def build(self):
       # Configurar los colores de la ventana
       Window.clearcolor = get_color_from_hex(COLORS['dark_bg'])
       return LectorQR()

if __name__ == '__main__':
   try:
       LectorQRApp().run()
   except Exception as e:
       print(f"Error en la aplicación: {str(e)}")
       # Para asegurar que la app se cierre completamente
       sys.exit(0)