# config/database.py - Configuración de la base de datos
import mysql.connector
from flask import g, current_app
import logging

def get_db():
    """Obtiene la conexión a la base de datos"""
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB'],
                charset='utf8mb4',
                autocommit=True
            )
            g.db.ping(reconnect=True)
        except mysql.connector.Error as e:
            logging.error(f"Error conectando a la base de datos: {e}")
            raise
    return g.db

def close_db(e=None):
    """Cierra la conexión a la base de datos"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    """Inicializa la configuración de la base de datos"""
    app.teardown_appcontext(close_db)

def execute_query(query, params=None, fetch_one=False, fetch_all=True):
    """
    Ejecuta una consulta SQL de forma segura
    
    Args:
        query (str): Consulta SQL
        params (tuple): Parámetros para la consulta
        fetch_one (bool): Si debe retornar solo un registro
        fetch_all (bool): Si debe retornar todos los registros
    
    Returns:
        dict/list: Resultado de la consulta
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute(query, params or ())
        
        if query.strip().upper().startswith('SELECT'):
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
        else:
            # Para INSERT, UPDATE, DELETE
            db.commit()
            result = {
                'affected_rows': cursor.rowcount,
                'last_insert_id': cursor.lastrowid
            }
        
        return result
        
    except mysql.connector.Error as e:
        db.rollback()
        logging.error(f"Error ejecutando consulta: {e}")
        raise
    finally:
        cursor.close()