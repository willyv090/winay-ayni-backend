import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()

try:
    conexion = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    cursor = conexion.cursor()

    cursor.execute("SELECT current_database(), current_user;")
    resultado = cursor.fetchone()

    print("Conexión exitosa a PostgreSQL")
    print(f"Base de datos: {resultado[0]}")
    print(f"Usuario: {resultado[1]}")

    cursor.close()
    conexion.close()

except Exception as error:
    print("Error al conectar con PostgreSQL:")
    print(error)