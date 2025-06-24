# -*- coding: utf-8 -*-
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

import cv2
import mediapipe as mp
import numpy as np
import mysql.connector
from deepface import DeepFace
from scipy.spatial.distance import cosine
import time
import json
from datetime import datetime
import threading
import sys
import requests
import urllib3
from pyzbar.pyzbar import decode

# Deshabilitar warnings SSL si es necesario
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar ventana
Window.size = (800, 600)
Window.resizable = False

# Configuración de la base de datos MySQL
DB_CONFIG = {
    'host': '',
    'user': '',
    'password': '',
    'database': ''
}

# Configuracion de la API para QR
API_CONFIG = {
    'base_url': 'https://acceso.informaticauaint.com/api-lector',
    'timeout': 15,
    'verify_ssl': False,
    'headers': {
        'Content-Type': 'application/json',
        'User-Agent': 'QR-Reader-Client/1.0',
        'Accept': 'application/json'
    }
}

# Colores para la interfaz
COLORS = {
    'primary': '#3498db',
    'success': '#2ecc71',
    'error': '#e74c3c',
    'warning': '#f39c12',
    'dark_bg': '#2c3e50',
    'light_text': '#ecf0f1',
    'accent': '#9b59b6',
    'button': '#3498db',
    'entry': '#27ae60',
    'exit': '#e67e22',
    'student': '#0066CC',
    'helper': '#FF6B35',
    'facial': '#8e44ad',
    'qr_mode': '#16a085'
}

# Inicializar MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

class BackgroundLayout(BoxLayout):
    """BoxLayout con fondo personalizado"""
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

class DatabaseManager:
    """Manejador de base de datos"""
    
    @staticmethod
    def get_db_connection():
        """Obtiene una conexión a la base de datos MySQL"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except mysql.connector.Error as e:
            print(f"Error conectando a MySQL: {e}")
            return None

    @staticmethod
    def init_faces_table():
        """Crea la tabla de rostros en MySQL si no existe"""
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    embedding JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            conn.commit()
            return True
        except mysql.connector.Error as e:
            print(f"Error creando tabla faces: {e}")
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def get_face_embedding(face_img):
        """Obtiene el embedding facial usando DeepFace"""
        try:
            embedding_obj = DeepFace.represent(face_img, model_name="Facenet512")
            embedding = np.array(embedding_obj[0]['embedding'])
            return embedding
        except Exception as e:
            print(f"Error al obtener embedding: {e}")
            return None

    @staticmethod
    def save_face(name, email, embedding):
        """Guarda un rostro en la base de datos MySQL"""
        if embedding is None:
            return False
        
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            embedding_list = embedding.tolist()
            embedding_json = json.dumps(embedding_list)
            
            cursor.execute("""
                INSERT INTO faces (name, email, embedding) 
                VALUES (%s, %s, %s)
            """, (name, email, embedding_json))
            
            conn.commit()
            return True
        except mysql.connector.Error as e:
            print(f"Error guardando rostro: {e}")
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def recognize_face(embedding):
        """Reconoce un rostro comparando con la base de datos"""
        if embedding is None:
            return "Error", None
        
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return "Error", None
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, email, embedding FROM faces")
            known_faces = cursor.fetchall()
            
            if not known_faces:
                return "Desconocido", None
            
            min_dist = 1.0
            identity = "Desconocido"
            email = None
            
            for name, face_email, stored_embedding_json in known_faces:
                try:
                    stored_embedding_list = json.loads(stored_embedding_json)
                    stored_embedding = np.array(stored_embedding_list)
                    
                    if stored_embedding.shape[0] != embedding.shape[0]:
                        continue
                    
                    dist = cosine(embedding, stored_embedding)
                    if dist < min_dist:
                        min_dist = dist
                        identity = name
                        email = face_email
                except Exception as e:
                    continue
            
            threshold = 0.258
            if min_dist < threshold:
                return identity, email
            else:
                return "Desconocido", None
                
        except mysql.connector.Error as e:
            print(f"Error en reconocimiento: {e}")
            return "Error", None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def get_user_data_from_email(email):
        """Obtiene los datos del usuario desde la tabla usuarios_permitidos"""
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return {"found": False}
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nombre, apellido, email 
                FROM usuarios_permitidos 
                WHERE email = %s AND activo = 1
            """, (email,))
            
            user = cursor.fetchone()
            
            if user:
                return {
                    "id": user[0],
                    "nombre": user[1],
                    "apellido": user[2],
                    "email": user[3],
                    "found": True
                }
            else:
                return {"found": False}
        except mysql.connector.Error as e:
            print(f"Error al buscar usuario: {e}")
            return {"found": False}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def register_attendance(nombre, apellido, email, metodo='facial'):
        """Registra la entrada o salida en la tabla registros de MySQL"""
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return {"success": False, "message": "Error de conexión a la base de datos"}
        
        try:
            cursor = conn.cursor()
            
            now = datetime.now()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            dia = now.strftime("%A")
            
            # Determinar tipo de registro
            tipo = DatabaseManager.determinar_tipo_registro(email)
            
            cursor.execute("""
                INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, metodo, tipo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (fecha, hora, dia, nombre, apellido, email, metodo, tipo))
            
            conn.commit()
            registro_id = cursor.lastrowid
            
            return {
                "success": True,
                "message": f"Registro exitoso: {nombre} {apellido}",
                "id": registro_id,
                "fecha": fecha,
                "hora": hora,
                "tipo": tipo
            }
        except mysql.connector.Error as e:
            print(f"Error al registrar asistencia: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def determinar_tipo_registro(email):
        """Determina si el registro es de entrada o salida"""
        conn = DatabaseManager.get_db_connection()
        if conn is None:
            return "Entrada"
        
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute("""
                SELECT COUNT(*) FROM registros 
                WHERE email = %s AND fecha = %s
            """, (email, today))
            
            count = cursor.fetchone()[0]
            return "Entrada" if count % 2 == 0 else "Salida"
        except mysql.connector.Error as e:
            print(f"Error determinando tipo de registro: {e}")
            return "Entrada"
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

class RegisterFacePopup(Popup):
    """Popup para registrar nuevos rostros"""
    def __init__(self, face_img, callback, **kwargs):
        super(RegisterFacePopup, self).__init__(**kwargs)
        self.face_img = face_img
        self.callback = callback
        
        self.title = "Registrar Nuevo Rostro"
        self.size_hint = (0.8, 0.6)
        
        content = BackgroundLayout(orientation='vertical', spacing=10, padding=10)
        
        content.add_widget(Label(
            text="Ingrese el email del usuario:",
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(1, 0.2)
        ))
        
        self.email_input = TextInput(
            multiline=False,
            size_hint=(1, 0.3),
            hint_text="ejemplo@email.com"
        )
        content.add_widget(self.email_input)
        
        button_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.3), spacing=10)
        
        cancel_btn = Button(
            text="Cancelar",
            background_color=get_color_from_hex(COLORS['error'])
        )
        cancel_btn.bind(on_press=self.dismiss)
        
        register_btn = Button(
            text="Registrar",
            background_color=get_color_from_hex(COLORS['success'])
        )
        register_btn.bind(on_press=self.register_face)
        
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(register_btn)
        content.add_widget(button_layout)
        
        self.content = content
    
    def register_face(self, instance):
        email = self.email_input.text.strip()
        if email:
            self.callback(email, self.face_img)
            self.dismiss()

class UnifiedAccessSystem(BackgroundLayout):
    def __init__(self, **kwargs):
        super(UnifiedAccessSystem, self).__init__(bg_color=COLORS['dark_bg'], **kwargs)
        self.orientation = 'vertical'
        
        # Modo actual: 'facial' o 'qr'
        self.current_mode = 'facial'
        
        # Configuración de cámara
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(cv2.CAP_PROP_FPS, 15)
        
        # Estado del sistema
        self.is_scanning = True
        self.last_scan_time = 0
        self.scan_cooldown = 2.0
        self.api_busy = False
        
        # Variables para reconocimiento facial
        self.analyzing = False
        self.analysis_start_time = 0
        self.analysis_duration = 3
        self.analysis_frames = []
        self.last_recognition_time = {}
        self.cooldown_time = 5
        
        # Estado de acceso
        self.access_status = None
        self.access_display_start = 0
        self.access_display_duration = 3
        self.recognized_person = None
        
        # Verificar conexión API para modo QR
        self.api_connected = self.check_api_connection()
        
        # Inicializar base de datos
        if not DatabaseManager.init_faces_table():
            print("Error: No se pudo inicializar la tabla de rostros")
        
        # Configurar interfaz
        self.setup_ui()
        
        # Iniciar loop de cámara
        Clock.schedule_interval(self.update_camera, 1.0 / 15.0)
        
        print("Sistema unificado iniciado en modo facial")
    
    def check_api_connection(self):
        """Verificar conexión con la API para modo QR"""
        try:
            response = requests.get(
                API_CONFIG['base_url'] + '/health', 
                timeout=5,
                verify=API_CONFIG['verify_ssl'],
                headers=API_CONFIG['headers']
            )
            return response.status_code == 200
        except:
            return False
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Header con título y botón de modo
        header = BackgroundLayout(
            orientation='horizontal', 
            size_hint=(1, 0.1), 
            bg_color=COLORS['dark_bg']
        )
        
        self.title_label = Label(
            text="RECONOCIMIENTO FACIAL - ACTIVO",
            font_size='16sp',
            bold=True,
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(0.7, 1)
        )
        header.add_widget(self.title_label)
        
        self.mode_button = Button(
            text="CAMBIAR A QR",
            background_color=get_color_from_hex(COLORS['qr_mode']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True,
            font_size='12sp',
            size_hint=(0.3, 1)
        )
        self.mode_button.bind(on_press=self.toggle_mode)
        header.add_widget(self.mode_button)
        
        self.add_widget(header)
        
        # Layout principal
        main_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.8))
        
        # Panel izquierdo - Cámara
        left_panel = BackgroundLayout(
            orientation='vertical', 
            size_hint=(0.7, 1), 
            bg_color=COLORS['dark_bg']
        )
        
        # Vista de cámara
        self.camera_image = Image(size_hint=(1, 0.9))
        left_panel.add_widget(self.camera_image)
        
        # Botones de cámara
        camera_buttons = BoxLayout(
            orientation='horizontal', 
            size_hint=(1, 0.1), 
            spacing=5
        )
        
        self.scan_button = Button(
            text="PAUSAR",
            background_color=get_color_from_hex(COLORS['button']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True
        )
        self.scan_button.bind(on_press=self.toggle_scanning)
        
        self.register_button = Button(
            text="REGISTRAR ROSTRO",
            background_color=get_color_from_hex(COLORS['facial']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True
        )
        self.register_button.bind(on_press=self.register_face_from_camera)
        
        camera_buttons.add_widget(self.scan_button)
        camera_buttons.add_widget(self.register_button)
        left_panel.add_widget(camera_buttons)
        
        main_layout.add_widget(left_panel)
        
        # Panel derecho - Información
        right_panel = BackgroundLayout(
            orientation='vertical', 
            size_hint=(0.3, 1),
            bg_color=COLORS['dark_bg'], 
            padding=[10, 5], 
            spacing=5
        )
        
        # Estado del sistema
        self.status_label = Label(
            text="Reconocimiento Facial Activo",
            font_size='14sp',
            bold=True,
            color=get_color_from_hex(COLORS['success']),
            size_hint=(1, 0.15),
            text_size=(None, None),
            halign='center'
        )
        right_panel.add_widget(self.status_label)
        
        # Modo actual
        self.mode_label = Label(
            text="MODO: FACIAL",
            font_size='12sp',
            bold=True,
            color=get_color_from_hex(COLORS['facial']),
            size_hint=(1, 0.1)
        )
        right_panel.add_widget(self.mode_label)
        
        # Tipo de usuario detectado
        self.user_type_label = Label(
            text="",
            font_size='11sp',
            bold=True,
            color=get_color_from_hex(COLORS['accent']),
            size_hint=(1, 0.1)
        )
        right_panel.add_widget(self.user_type_label)
        
        # Información detallada
        self.info_label = Label(
            text="Listo para reconocer rostros\n\nApunte la cámara hacia su rostro\npara registrar asistencia",
            font_size='10sp',
            color=get_color_from_hex(COLORS['light_text']),
            size_hint=(1, 0.45),
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        right_panel.add_widget(self.info_label)
        
        # Estado de conexión (para modo QR)
        api_status_text = "API QR: " + ("OK" if self.api_connected else "ERROR")
        api_color = COLORS['success'] if self.api_connected else COLORS['error']
        
        self.api_status_label = Label(
            text=api_status_text,
            font_size='9sp',
            color=get_color_from_hex(api_color),
            size_hint=(1, 0.1)
        )
        right_panel.add_widget(self.api_status_label)
        
        # Botón de salir
        quit_button = Button(
            text="SALIR",
            background_color=get_color_from_hex(COLORS['error']),
            color=get_color_from_hex(COLORS['light_text']),
            bold=True,
            size_hint=(1, 0.1)
        )
        quit_button.bind(on_press=self.quit_app)
        right_panel.add_widget(quit_button)
        
        main_layout.add_widget(right_panel)
        self.add_widget(main_layout)
    
    def toggle_mode(self, instance):
        """Alternar entre modo facial y QR"""
        if self.current_mode == 'facial':
            self.current_mode = 'qr'
            self.title_label.text = "LECTOR QR - ACTIVO"
            self.mode_button.text = "CAMBIAR A FACIAL"
            self.mode_button.background_color = get_color_from_hex(COLORS['facial'])
            self.mode_label.text = "MODO: QR"
            self.mode_label.color = get_color_from_hex(COLORS['qr_mode'])
            self.register_button.disabled = True
            self.register_button.text = "MODO QR"
            
            if self.api_connected:
                self.status_label.text = "Lector QR Activo"
                self.info_label.text = "Listo para escanear códigos QR\n\nApunte la cámara hacia un\ncódigo QR válido"
            else:
                self.status_label.text = "API No Disponible"
                self.status_label.color = get_color_from_hex(COLORS['error'])
                self.info_label.text = "No hay conexión con la API\n\nEl modo QR requiere\nconexión a internet"
        else:
            self.current_mode = 'facial'
            self.title_label.text = "RECONOCIMIENTO FACIAL - ACTIVO"
            self.mode_button.text = "CAMBIAR A QR"
            self.mode_button.background_color = get_color_from_hex(COLORS['qr_mode'])
            self.mode_label.text = "MODO: FACIAL"
            self.mode_label.color = get_color_from_hex(COLORS['facial'])
            self.register_button.disabled = False
            self.register_button.text = "REGISTRAR ROSTRO"
            
            self.status_label.text = "Reconocimiento Facial Activo"
            self.status_label.color = get_color_from_hex(COLORS['success'])
            self.info_label.text = "Listo para reconocer rostros\n\nApunte la cámara hacia su rostro\npara registrar asistencia"
        
        # Resetear estados
        self.analyzing = False
        self.access_status = None
        self.recognized_person = None
        
        print(f"Modo cambiado a: {self.current_mode}")
    
    def update_camera(self, dt):
        """Actualizar frame de cámara y procesar según el modo"""
        ret, frame = self.capture.read()
        
        if ret:
            frame = cv2.flip(frame, 1)  # Espejo horizontal
            display_frame = frame.copy()
            
            current_time = time.time()
            
            # Mostrar resultado de acceso si está activo
            if self.access_status is not None and current_time - self.access_display_start < self.access_display_duration:
                self.draw_access_result(display_frame, current_time)
            elif current_time - self.access_display_start >= self.access_display_duration:
                self.access_status = None
                self.recognized_person = None
            
            if self.is_scanning and not self.api_busy:
                if self.current_mode == 'facial':
                    self.process_facial_recognition(frame, display_frame, current_time)
                elif self.current_mode == 'qr' and self.api_connected:
                    self.process_qr_detection(frame, display_frame, current_time)
            
            # Convertir frame para Kivy
            self.update_camera_display(display_frame)
    
    def process_facial_recognition(self, frame, display_frame, current_time):
        """Procesar reconocimiento facial"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)
        
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)
                
                # Dibujar rectángulo
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Manejo del análisis
                if not self.analyzing and self.access_status is None:
                    self.analyzing = True
                    self.analysis_start_time = current_time
                    self.analysis_frames = []
                    cv2.putText(display_frame, "Analizando...", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                elif self.analyzing:
                    face_img = frame[y:y+h, x:x+w]
                    if face_img.size > 0:
                        self.analysis_frames.append(face_img)
                    
                    progress = min(int((current_time - self.analysis_start_time) / self.analysis_duration * 100), 100)
                    cv2.putText(display_frame, f"Analizando: {progress}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    if current_time - self.analysis_start_time >= self.analysis_duration and len(self.analysis_frames) > 0:
                        self.analyzing = False
                        self.process_facial_analysis(current_time)
        else:
            if self.analyzing:
                self.analyzing = False
    
    def process_facial_analysis(self, current_time):
        """Procesar análisis facial en hilo separado"""
        def analyze_thread():
            try:
                best_face = self.analysis_frames[-1]
                embedding = DatabaseManager.get_face_embedding(best_face)
                
                if embedding is not None:
                    identity, email = DatabaseManager.recognize_face(embedding)
                    
                    if identity != "Desconocido" and identity != "Error" and email:
                        if email in self.last_recognition_time and current_time - self.last_recognition_time[email] < self.cooldown_time:
                            return
                        
                        user_data = DatabaseManager.get_user_data_from_email(email)
                        
                        if user_data["found"]:
                            registro = DatabaseManager.register_attendance(
                                user_data["nombre"], 
                                user_data["apellido"], 
                                user_data["email"],
                                'facial'
                            )
                            
                            Clock.schedule_once(lambda dt: self.show_access_result(registro, identity, current_time), 0)
                            self.last_recognition_time[email] = current_time
                        else:
                            Clock.schedule_once(lambda dt: self.show_access_result({
                                "success": False,
                                "message": f"Usuario no encontrado: {identity}"
                            }, identity, current_time), 0)
                    else:
                        Clock.schedule_once(lambda dt: self.show_access_result({
                            "success": False,
                            "message": "Persona no reconocida"
                        }, None, current_time), 0)
                else:
                    Clock.schedule_once(lambda dt: self.show_access_result({
                        "success": False,
                        "message": "Error al analizar rostro"
                    }, None, current_time), 0)
            except Exception as e:
                print(f"Error en análisis facial: {e}")
        
        thread = threading.Thread(target=analyze_thread)
        thread.daemon = True
        thread.start()
    
    def process_qr_detection(self, frame, display_frame, current_time):
        """Procesar detección de QR"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        qr_codes = decode(gray)
        
        for qr in qr_codes:
            # Dibujar contorno del QR
            points = qr.polygon
            if points:
                pts = []
                for point in points:
                    pts.append([point.x, point.y])
                
                pts = np.array(pts, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
            
            # Procesar QR si ha pasado el cooldown
            if current_time - self.last_scan_time > self.scan_cooldown:
                qr_data = qr.data.decode('utf-8')
                self.process_qr_async(qr_data, current_time)
                self.last_scan_time = current_time
    
    def process_qr_async(self, qr_data, scan_time):
        """Procesar QR en hilo separado"""
        if self.api_busy:
            return
        
        def process_thread():
            self.api_busy = True
            try:
                self.process_qr(qr_data, scan_time)
            finally:
                self.api_busy = False
        
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()
    
    def process_qr(self, qr_data, scan_time):
        """Enviar QR a la API para procesamiento"""
        try:
            print(f"QR detectado: {qr_data[:50]}...")
            
            # Actualizar UI
            Clock.schedule_once(lambda dt: self.update_status("Enviando..."), 0)
            
            if not self.api_connected:
                Clock.schedule_once(
                    lambda dt: self.show_access_result({
                        "success": False,
                        "message": "Sin conexión API"
                    }, None, scan_time), 0
                )
                return
            
            # Parsear QR data
            try:
                if isinstance(qr_data, str):
                    parsed_data = json.loads(qr_data)
                else:
                    parsed_data = qr_data
            except json.JSONDecodeError:
                Clock.schedule_once(
                    lambda dt: self.show_access_result({
                        "success": False,
                        "message": "Formato QR inválido"
                    }, None, scan_time), 0
                )
                return
            
            # Enviar a API
            response = requests.post(
                API_CONFIG['base_url'] + '/validate-qr',
                json=parsed_data,
                timeout=API_CONFIG['timeout'],
                verify=API_CONFIG['verify_ssl'],
                headers=API_CONFIG['headers']
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    # Construir resultado exitoso
                    nombre = result.get('nombre', '')
                    apellido = result.get('apellido', '')
                    tipo = result.get('tipo', 'Registro')
                    usuario_tipo = result.get('usuario_tipo', '')
                    message = result.get('message', 'Registro exitoso')
                    
                    access_result = {
                        "success": True,
                        "message": f"{nombre} {apellido}",
                        "tipo": tipo,
                        "usuario_tipo": usuario_tipo
                    }
                    
                    Clock.schedule_once(
                        lambda dt: self.show_access_result(access_result, f"{nombre} {apellido}", scan_time), 0
                    )
                else:
                    # Error desde API
                    error_msg = result.get('error', 'Error desconocido')
                    Clock.schedule_once(
                        lambda dt: self.show_access_result({
                            "success": False,
                            "message": error_msg
                        }, None, scan_time), 0
                    )
            else:
                # Error HTTP
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', f'Error HTTP {response.status_code}')
                except:
                    error_msg = f'Error HTTP {response.status_code}'
                
                Clock.schedule_once(
                    lambda dt: self.show_access_result({
                        "success": False,
                        "message": error_msg
                    }, None, scan_time), 0
                )
        
        except requests.exceptions.ConnectionError:
            self.api_connected = False
            Clock.schedule_once(
                lambda dt: [
                    self.show_access_result({
                        "success": False,
                        "message": "Error de conexión"
                    }, None, scan_time),
                    self.update_api_status()
                ], 0
            )
        except requests.exceptions.Timeout:
            Clock.schedule_once(
                lambda dt: self.show_access_result({
                    "success": False,
                    "message": "Tiempo agotado"
                }, None, scan_time), 0
            )
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self.show_access_result({
                    "success": False,
                    "message": f"Error: {str(e)[:20]}"
                }, None, scan_time), 0
            )
    
    def draw_access_result(self, display_frame, current_time):
        """Dibujar resultado de acceso en el frame"""
        overlay = display_frame.copy()
        
        if self.access_status["success"]:
            if self.current_mode == 'facial':
                text = f"{self.access_status['message']} - {self.access_status.get('tipo', '')}"
                color = (0, 255, 0)  # Verde
            else:  # modo QR
                text = f"{self.access_status['message']} - {self.access_status.get('tipo', '')}"
                color = (0, 255, 0)  # Verde
        else:
            text = f"ERROR: {self.access_status['message']}"
            color = (0, 0, 255)  # Rojo
        
        # Dibujar texto con fondo
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Obtener tamaño del texto
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Posición centrada
        x = (display_frame.shape[1] - text_width) // 2
        y = 60
        
        # Dibujar fondo
        cv2.rectangle(overlay, (x-10, y-text_height-10), (x+text_width+10, y+baseline+10), (0, 0, 0), -1)
        
        # Dibujar texto
        cv2.putText(overlay, text, (x, y), font, font_scale, color, thickness)
        
        # Aplicar overlay con transparencia
        alpha = 0.8
        cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
    
    def update_camera_display(self, frame):
        """Actualizar display de la cámara"""
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.camera_image.texture = texture
    
    def show_access_result(self, result, person_name, scan_time):
        """Mostrar resultado de acceso en la UI"""
        self.access_status = result
        self.access_display_start = scan_time
        self.recognized_person = person_name
        
        # Actualizar labels de estado
        if result["success"]:
            if self.current_mode == 'facial':
                status_text = f"{result.get('tipo', 'Registro')} Registrado"
                color = COLORS['entry'] if result.get('tipo') == 'Entrada' else COLORS['exit']
            else:  # modo QR
                status_text = f"{result.get('tipo', 'Registro')} QR"
                color = COLORS['entry'] if result.get('tipo') == 'Entrada' else COLORS['exit']
            
            self.status_label.text = status_text
            self.status_label.color = get_color_from_hex(color)
            
            # Tipo de usuario
            user_type = result.get('usuario_tipo', '')
            if user_type:
                type_color = COLORS['student'] if user_type == "ESTUDIANTE" else COLORS['helper']
                self.user_type_label.text = user_type
                self.user_type_label.color = get_color_from_hex(type_color)
            
            # Información detallada
            self.info_label.text = f"✓ {result['message']}\n\nTipo: {result.get('tipo', '')}\nMétodo: {self.current_mode.upper()}"
            
            print(f"ACCESO REGISTRADO: {status_text} - {result['message']}")
        else:
            self.status_label.text = "ERROR"
            self.status_label.color = get_color_from_hex(COLORS['error'])
            self.user_type_label.text = ""
            self.info_label.text = f"✗ {result['message']}\n\nIntente nuevamente\no contacte soporte"
            
            print(f"ERROR DE REGISTRO: {result['message']}")
        
        # Programar reset
        Clock.schedule_once(self.reset_status, self.access_display_duration)
    
    def reset_status(self, dt):
        """Restaurar estado inicial de la UI"""
        if self.current_mode == 'facial':
            self.status_label.text = "Reconocimiento Facial Activo" if self.is_scanning else "Pausado"
            self.info_label.text = "Listo para reconocer rostros\n\nApunte la cámara hacia su rostro\npara registrar asistencia"
        else:  # modo QR
            if self.api_connected:
                self.status_label.text = "Lector QR Activo" if self.is_scanning else "Pausado"
                self.info_label.text = "Listo para escanear códigos QR\n\nApunte la cámara hacia un\ncódigo QR válido"
            else:
                self.status_label.text = "API No Disponible"
                self.info_label.text = "No hay conexión con la API\n\nEl modo QR requiere\nconexión a internet"
        
        self.status_label.color = get_color_from_hex(COLORS['success'])
        self.user_type_label.text = ""
    
    def update_status(self, status_text):
        """Actualizar estado en UI"""
        self.status_label.text = status_text
        self.status_label.color = get_color_from_hex(COLORS['warning'])
    
    def update_api_status(self):
        """Actualizar estado de conexión API"""
        api_status_text = "API QR: " + ("OK" if self.api_connected else "ERROR")
        api_color = COLORS['success'] if self.api_connected else COLORS['error']
        self.api_status_label.text = api_status_text
        self.api_status_label.color = get_color_from_hex(api_color)
    
    def toggle_scanning(self, instance):
        """Alternar escaneo/pausa"""
        self.is_scanning = not self.is_scanning
        
        if self.is_scanning:
            self.scan_button.text = "PAUSAR"
            self.scan_button.background_color = get_color_from_hex(COLORS['button'])
            
            if self.current_mode == 'facial':
                self.status_label.text = "Reconocimiento Facial Activo"
            else:
                self.status_label.text = "Lector QR Activo" if self.api_connected else "API No Disponible"
        else:
            self.scan_button.text = "REANUDAR"
            self.scan_button.background_color = get_color_from_hex(COLORS['accent'])
            self.status_label.text = "Pausado"
            self.status_label.color = get_color_from_hex(COLORS['warning'])
        
        # Resetear estados
        self.analyzing = False
        self.access_status = None
    
    def register_face_from_camera(self, instance):
        """Registrar rostro desde la cámara actual"""
        if self.current_mode != 'facial':
            return
        
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)
            
            if results.detections:
                detection = results.detections[0]
                bboxC = detection.location_data.relative_bounding_box
                h, w, _ = frame.shape
                x, y, fw, fh = int(bboxC.xmin * w), int(bboxC.ymin * h), int(bboxC.width * w), int(bboxC.height * h)
                face_img = frame[y:y+fh, x:x+fw]
                
                if face_img.size > 0:
                    popup = RegisterFacePopup(face_img, self.register_face_callback)
                    popup.open()
                else:
                    self.show_message("Error", "No se pudo extraer la imagen facial")
            else:
                self.show_message("Error", "No se detectó ningún rostro en la imagen")
    
    def register_face_callback(self, email, face_img):
        """Callback para registrar rostro"""
        def register_thread():
            try:
                # Verificar usuario en base de datos
                user_data = DatabaseManager.get_user_data_from_email(email)
                
                if user_data["found"]:
                    # Obtener embedding
                    embedding = DatabaseManager.get_face_embedding(face_img)
                    
                    if embedding is not None:
                        # Guardar rostro
                        nombre_completo = f"{user_data['nombre']} {user_data['apellido']}"
                        
                        if DatabaseManager.save_face(nombre_completo, email, embedding):
                            Clock.schedule_once(
                                lambda dt: self.show_message(
                                    "Éxito", 
                                    f"Rostro de {nombre_completo} registrado correctamente"
                                ), 0
                            )
                        else:
                            Clock.schedule_once(
                                lambda dt: self.show_message("Error", "No se pudo guardar el rostro"), 0
                            )
                    else:
                        Clock.schedule_once(
                            lambda dt: self.show_message("Error", "No se pudo procesar el rostro"), 0
                        )
                else:
                    Clock.schedule_once(
                        lambda dt: self.show_message(
                            "Error", 
                            "Usuario no encontrado. Debe estar registrado previamente en el sistema"
                        ), 0
                    )
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: self.show_message("Error", f"Error inesperado: {str(e)}"), 0
                )
        
        thread = threading.Thread(target=register_thread)
        thread.daemon = True
        thread.start()
    
    def show_message(self, title, message):
        """Mostrar mensaje popup"""
        content = BackgroundLayout(orientation='vertical', padding=10)
        
        content.add_widget(Label(
            text=message,
            color=get_color_from_hex(COLORS['light_text']),
            text_size=(300, None),
            halign='center'
        ))
        
        close_btn = Button(
            text="Cerrar",
            size_hint=(1, 0.3),
            background_color=get_color_from_hex(COLORS['button'])
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.6, 0.4)
        )
        
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def quit_app(self, instance):
        """Cerrar aplicación"""
        print("Cerrando sistema unificado...")
        if self.capture:
            self.capture.release()
        
        Clock.unschedule(self.update_camera)
        Clock.unschedule(self.reset_status)
        App.get_running_app().stop()
        sys.exit(0)

class UnifiedAccessApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex(COLORS['dark_bg'])
        return UnifiedAccessSystem()

if __name__ == '__main__':
    try:
        print("=== SISTEMA UNIFICADO DE CONTROL DE ACCESO ===")
        print("Funcionalidades:")
        print("- Reconocimiento facial con base de datos local")
        print("- Lectura de códigos QR con API remota")
        print("- Interfaz gráfica unificada")
        print("- Registro de asistencia automático")
        print("=" * 50)
        
        UnifiedAccessApp().run()
    except Exception as e:
        print(f"Error crítico en la aplicación: {e}")
        sys.exit(1)
