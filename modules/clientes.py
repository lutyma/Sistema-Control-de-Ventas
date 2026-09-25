import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos

def render_clientes():
    st.title("⚙️ Paramétricos - Gestión de Clientes")
    
    try:
        df_clientes = cargar_datos("SELECT * FROM clientes ORDER BY nombres ASC")
    except Exception:
        df_clientes = pd.DataFrame()

    col_c1, col_c2 = st.columns([1, 2])
    
    with col_c1:
        st.write("#### Registrar Nuevo Cliente")
        with st.form("form_nuevo_cliente", clear_on_submit=True):
            nombre_c = st.text_input("Nombre y Apellido*")
            telefono_c = st.text_input("Teléfono")
            doc_c = st.text_input("N° Documento / RUC")
            
            if st.form_submit_button("Guardar Cliente", type="primary"):
                if nombre_c:
                    try:
                        ejecutar_query("""
                            INSERT INTO clientes (nombres, telefono, numero_documento) 
                            VALUES (:n, :t, :d)
                        """, {"n": nombre_c, "t": telefono_c, "d": doc_c})
                        st.success(f"✅ Cliente '{nombre_c}' registrado con éxito.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar cliente: {e}")
                else:
                    st.warning("⚠️ El nombre del cliente es obligatorio.")
    
    with col_c2:
        st.write("#### Lista de Clientes Registrados")
        if not df_clientes.empty:
            st.dataframe(df_clientes, use_container_width=True)
        else:
            st.info("No hay clientes registrados aún.")