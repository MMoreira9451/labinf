#!/usr/bin/env python3
# file: upload_sqlite_to_mysql.py

import sqlite3
import mysql.connector

# Configuración de la base de datos MySQL
MYSQL_CONFIG = {
'host': '10.53.113.96',  # Cambiar por tu IP o dominio
    'user': 'qruser',
    'password': 'tu_password_segura',
    'database': 'registro_qr'
}

# Ruta a la base de datos SQLite
SQLITE_DB_PATH = 'registro_qr.db'

def disable_foreign_key_checks(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")

def enable_foreign_key_checks(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS=1")

def transfer_table(sqlite_conn, mysql_conn, table_name):
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()

    # Obtener columnas
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    column_list = ', '.join([f"`{c}`" for c in columns])
    placeholders = ', '.join(['%s'] * len(columns))

    # Leer datos de SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    # Desactivar claves foráneas temporalmente
    disable_foreign_key_checks(mysql_cursor)
    mysql_cursor.execute(f"DELETE FROM `{table_name}`")
    enable_foreign_key_checks(mysql_cursor)
    mysql_conn.commit()

    # Insertar en MySQL
    insert_sql = f"INSERT INTO `{table_name}` ({column_list}) VALUES ({placeholders})"
    for row in rows:
        mysql_cursor.execute(insert_sql, row)

    mysql_conn.commit()
    print(f"Tabla '{table_name}' transferida: {len(rows)} filas")

def main():
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)

    # Orden correcto: primero eliminar dependientes
    tables = ['horarios_asignados', 'registros', 'usuarios_permitidos']
    for table in tables:
        transfer_table(sqlite_conn, mysql_conn, table)

    sqlite_conn.close()
    mysql_conn.close()

if __name__ == '__main__':
    main()
