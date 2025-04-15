import cv2
import mediapipe as mp
import numpy as np
import sqlite3
from deepface import DeepFace
from scipy.spatial.distance import cosine
import time
import os
from datetime import datetime

# Inicializar MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

# Rutas de bases de datos
FACES_DB_PATH = 'faces.db'
ATTENDANCE_DB_PATH = 'registro_qr.db'

# Conectar a la base de datos de rostros
def init_faces_db():
    conn = sqlite3.connect(FACES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT,
                    embedding BLOB,
                    embedding_size INTEGER)""")
    conn.commit()
    conn.close()
    print("Base de datos de rostros verificada.")

# Inicializar la base de datos de asistencia si no existe
def init_attendance_db():
    conn = sqlite3.connect(ATTENDANCE_DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de usuarios permitidos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios_permitidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Tabla de registros de asistencia
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        dia TEXT NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT NOT NULL,
        timestamp INTEGER DEFAULT (strftime('%s', 'now')),
        metodo TEXT DEFAULT 'facial'
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Base de datos de asistencia verificada.")
def add_metodo_column():
    """Agrega la columna 'metodo' a la tabla de registros si no existe"""
    try:
        conn = sqlite3.connect(ATTENDANCE_DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si la columna existe
        cursor.execute("PRAGMA table_info(registros)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'metodo' not in columns:
            cursor.execute("ALTER TABLE registros ADD COLUMN metodo TEXT DEFAULT 'facial'")
            conn.commit()
            print("Columna 'metodo' añadida a la tabla registros")
        
        conn.close()
    except Exception as e:
        print(f"Error al añadir columna metodo: {e}")

# Llamar a la función para añadir la columna
add_metodo_column()
# Inicializar ambas bases de datos
init_faces_db()
init_attendance_db()

def get_face_embedding(face_img):
    try:
        # Usar DeepFace para obtener embeddings con el modelo FaceNet
        embedding_obj = DeepFace.represent(face_img, model_name="Facenet512")
        # DeepFace.represent devuelve una lista con un diccionario, donde la clave 'embedding' contiene el vector
        embedding = np.array(embedding_obj[0]['embedding'])
        return embedding
    except Exception as e:
        print(f"Error al obtener embedding: {e}")
        return None

def save_face(name, email, embedding):
    if embedding is None:
        return False
    
    conn = sqlite3.connect(FACES_DB_PATH)
    cursor = conn.cursor()
    
    # Asegurar que embedding es del tipo correcto
    embedding = np.array(embedding, dtype=np.float32)
    
    cursor.execute("INSERT INTO faces (name, email, embedding, embedding_size) VALUES (?, ?, ?, ?)", 
                 (name, email, embedding.tobytes(), embedding.shape[0]))
    conn.commit()
    conn.close()
    return True

def recognize_face(embedding):
    if embedding is None:
        return "Error", None
    
    conn = sqlite3.connect(FACES_DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todos los rostros registrados
    cursor.execute("SELECT name, email, embedding, embedding_size FROM faces")
    known_faces = cursor.fetchall()
    conn.close()
    
    if not known_faces:
        print("No hay rostros registrados en la base de datos.")
        return "Desconocido", None
    
    min_dist = 1.0  # Umbral de similitud
    identity = "Desconocido"
    email = None
    
    for name, face_email, stored_embedding_bytes, stored_size in known_faces:
        # Verificar que las dimensiones coincidan
        if stored_size != embedding.shape[0]:
            continue
        
        # Convertir los bytes almacenados a un array numpy
        stored_embedding = np.frombuffer(stored_embedding_bytes, dtype=np.float32)
        
        # Realizar la comparación
        try:
            dist = cosine(embedding, stored_embedding)
            if dist < min_dist:
                min_dist = dist
                identity = name
                email = face_email
        except Exception as e:
            print(f"Error al comparar embeddings: {e}")
    
    threshold = 0.258  # Umbral de distancia para considerar una coincidencia
    if min_dist < threshold:
        print(f"Mejor coincidencia: {identity}, Email: {email}, Distancia: {min_dist:.4f}")
        return identity, email
    else:
        return "Desconocido", None

def get_user_data_from_email(email):
    """Obtiene los datos del usuario desde la base de datos de asistencia"""
    try:
        conn = sqlite3.connect(ATTENDANCE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE email = ? AND activo = 1", 
                      (email,))
        user = cursor.fetchone()
        conn.close()
        
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
    except Exception as e:
        print(f"Error al buscar usuario: {e}")
        return {"found": False}

def register_attendance(nombre, apellido, email):
    """Registra la entrada o salida en la base de datos de asistencia"""
    try:
        conn = sqlite3.connect(ATTENDANCE_DB_PATH)
        cursor = conn.cursor()
        
        # Obtener fecha y hora actual
        now = datetime.now()
        fecha = now.strftime("%Y-%m-%d")
        hora = now.strftime("%H:%M:%S")
        dia = now.strftime("%A")  # Día de la semana en inglés
        
        # Insertar registro
        cursor.execute('''
            INSERT INTO registros (fecha, hora, dia, nombre, apellido, email, metodo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fecha, hora, dia, nombre, apellido, email, 'facial'))
        
        conn.commit()
        registro_id = cursor.lastrowid
        conn.close()
        
        # Determinar si es entrada o salida
        tipo = determinar_tipo_registro(email)
        
        return {
            "success": True,
            "message": f"Registro exitoso: {nombre} {apellido}",
            "id": registro_id,
            "fecha": fecha,
            "hora": hora,
            "tipo": tipo
        }
    except Exception as e:
        print(f"Error al registrar asistencia: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def determinar_tipo_registro(email):
    """Determina si el registro es de entrada o salida basado en registros previos"""
    conn = sqlite3.connect(ATTENDANCE_DB_PATH)
    cursor = conn.cursor()
    
    # Obtener fecha actual
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Contar registros de hoy para este usuario
    cursor.execute('''
        SELECT COUNT(*) FROM registros 
        WHERE email = ? AND fecha = ?
    ''', (email, today))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    # Conteos pares (incluyendo 0) son entradas, impares son salidas
    return "Entrada" if count % 2 == 0 else "Salida"

def register_new_face(frame):
    """Registra un nuevo rostro asociado a un usuario existente"""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb_frame)
    
    if results.detections:
        detection = results.detections[0]  # Tomar la primera cara detectada
        bboxC = detection.location_data.relative_bounding_box
        h, w, _ = frame.shape
        x, y, w, h = int(bboxC.xmin * w), int(bboxC.ymin * h), int(bboxC.width * w), int(bboxC.height * h)
        face_img = frame[y:y+h, x:x+w]
        if face_img.size > 0:
            # Primero obtener el email del usuario
            email = input("Ingrese el email del usuario registrado: ")
            
            # Verificar si existe en la base de datos de asistencia
            user_data = get_user_data_from_email(email)
            
            if user_data["found"]:
                print(f"Usuario encontrado: {user_data['nombre']} {user_data['apellido']}")
                # Obtener embedding
                embedding = get_face_embedding(face_img)
                if embedding is not None:
                    # Guardar rostro con el nombre y email del usuario
                    nombre_completo = f"{user_data['nombre']} {user_data['apellido']}"
                    if save_face(nombre_completo, email, embedding):
                        print(f"Rostro de {nombre_completo} registrado correctamente.")
                        print(f"Dimensión del embedding: {embedding.shape[0]}")
                    else:
                        print("Error al registrar el rostro.")
                else:
                    print("No se pudo obtener el embedding facial.")
            else:
                print("Usuario no encontrado en la base de datos. Debe estar registrado previamente.")
        else:
            print("No se pudo extraer la imagen facial.")
    else:
        print("No se detectó ningún rostro.")

def list_registered_users():
    """Lista los usuarios permitidos para facilitar el registro de rostros"""
    try:
        conn = sqlite3.connect(ATTENDANCE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
        users = cursor.fetchall()
        conn.close()
        
        if users:
            print("\n--- Usuarios registrados en el sistema ---")
            for user in users:
                print(f"ID: {user[0]}, Nombre: {user[1]} {user[2]}, Email: {user[3]}")
        else:
            print("No hay usuarios registrados en el sistema.")
    except Exception as e:
        print(f"Error al obtener la lista de usuarios: {e}")

# Función principal - Control de acceso facial
def run_face_attendance_system():
    # Captura de video en tiempo real
    cap = cv2.VideoCapture(0)
    print("Sistema de Control de Asistencia con Reconocimiento Facial")
    print("Presione 'r' para registrar un nuevo rostro, 'l' para listar usuarios, 'q' para salir")

    # Variables para el control de acceso
    analyzing = False
    analysis_start_time = 0
    analysis_duration = 3  # segundos
    analysis_frames = []
    access_status = None
    access_display_start = 0
    access_display_duration = 3  # segundos
    recognized_person = None
    
    # Tiempo mínimo entre registros para la misma persona (en segundos)
    cooldown_time = 5
    last_recognition_time = {}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Crear una copia del frame para mostrar
        display_frame = frame.copy()
        
        # Convertir imagen a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)
        
        current_time = time.time()
        
        # Mostrar resultado de acceso si está activo
        if access_status is not None and current_time - access_display_start < access_display_duration:
            # Crear un overlay para mostrar el resultado
            overlay = display_frame.copy()
            if access_status["success"]:
                text = f"{access_status['message']} - {access_status['tipo']}"
                cv2.putText(overlay, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                # Imprimir en la consola también
                if current_time - access_display_start < 0.1:  # Para que no imprima muchas veces
                    print(f"ACCESO REGISTRADO: {text}")
            else:
                cv2.putText(overlay, f"ERROR: {access_status['message']}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                # Imprimir en la consola también
                if current_time - access_display_start < 0.1:  # Para que no imprima muchas veces
                    print(f"ERROR DE REGISTRO: {access_status['message']}")
            
            # Aplicar el overlay con transparencia
            alpha = 0.7
            cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
        elif current_time - access_display_start >= access_display_duration:
            access_status = None
            recognized_person = None
        
        # Si se detecta una cara
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)
                
                # Dibujar el rectángulo alrededor de la cara
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Si no estamos analizando ni mostrando un resultado, iniciar análisis
                if not analyzing and access_status is None:
                    analyzing = True
                    analysis_start_time = current_time
                    analysis_frames = []
                    print("Analizando rostro...")
                    cv2.putText(display_frame, "Analizando...", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # Si estamos en fase de análisis
                elif analyzing:
                    # Agregar el frame actual al análisis
                    face_img = frame[y:y+h, x:x+w]
                    if face_img.size > 0:
                        analysis_frames.append(face_img)
                    
                    # Indicar que estamos analizando
                    progress = min(int((current_time - analysis_start_time) / analysis_duration * 100), 100)
                    cv2.putText(display_frame, f"Analizando: {progress}%", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    # Si hemos analizado suficiente tiempo
                    if current_time - analysis_start_time >= analysis_duration and len(analysis_frames) > 0:
                        analyzing = False
                        
                        # Tomar el último frame para reconocimiento
                        best_face = analysis_frames[-1]
                        embedding = get_face_embedding(best_face)
                        
                        if embedding is not None:
                            identity, email = recognize_face(embedding)
                            
                            # Si reconocimos a alguien
                            if identity != "Desconocido" and identity != "Error" and email:
                                # Verificar si hay tiempo de espera para este usuario
                                if email in last_recognition_time and current_time - last_recognition_time[email] < cooldown_time:
                                    print(f"Ignorando reconocimiento de {identity} - demasiado pronto")
                                    continue
                                
                                # Obtener datos del usuario
                                user_data = get_user_data_from_email(email)
                                
                                if user_data["found"]:
                                    # Registrar asistencia
                                    registro = register_attendance(
                                        user_data["nombre"], 
                                        user_data["apellido"], 
                                        user_data["email"]
                                    )
                                    
                                    # Actualizar estado de acceso
                                    access_status = registro
                                    access_display_start = current_time
                                    recognized_person = identity
                                    last_recognition_time[email] = current_time
                                else:
                                    access_status = {
                                        "success": False,
                                        "message": f"Usuario no encontrado en sistema: {identity}"
                                    }
                                    access_display_start = current_time
                            else:
                                access_status = {
                                    "success": False,
                                    "message": "Persona no reconocida"
                                }
                                access_display_start = current_time
        else:
            # Si no hay caras en el frame, reiniciar el análisis
            if analyzing:
                analyzing = False
                print("Rostro perdido. Análisis cancelado.")
        
        # Mostrar la identidad de la persona reconocida
        if recognized_person and access_status:
            cv2.putText(display_frame, f"{recognized_person}", (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow('Control de Asistencia Facial', display_frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('r'):
            register_new_face(frame)
        elif key == ord('l'):
            list_registered_users()
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run_face_attendance_system()