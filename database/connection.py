import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# # Inicialización de la base de datos
# try:
#     DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
#     engine = create_engine(DATABASE_URL)
# except Exception as e:
#     st.error("Error: No se pudo encontrar la configuración de la base de datos en Secrets.")
#     st.stop()

# --- 1. LECTURA DE CONFIGURACIÓN ---
try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
except Exception as e:
    st.error(f"Error al leer la URL desde Secrets: {e}")
    st.stop()

# --- 2. CONEXIÓN A BASE DE DATOS (CON POOLING DE NEON) ---
try:
    engine = create_engine(
        DATABASE_URL, 
        pool_pre_ping=True, 
        pool_recycle=300
    )
except Exception as e:
    st.error(f"Error al conectar con la base de datos Neon: {e}")
    st.stop()

def ejecutar_query(query, params=None):
    """Ejecuta comandos INSERT, UPDATE, DELETE dentro de una transacción"""
    with engine.begin() as conn:
        return conn.execute(text(query), params)

def cargar_datos(query, params=None):
    """Ejecuta consultas SELECT y devuelve un DataFrame de Pandas"""
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)