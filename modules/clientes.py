import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

def render_clientes():
    st.title("👤 Paramétrico - Gestión de Clientes")

    tab_nuevo, tab_editar, tab_tabla = st.tabs([
        "➕ Registrar Cliente", 
        "✏️ Modificar Cliente", 
        "📋 Lista de Clientes"
    ])

    # --- CARGA DE DATOS DE CLIENTES ---
    try:
        df_clientes = cargar_datos("""
            SELECT 
                COALESCE(id_cliente, id) as id_cliente,
                COALESCE(nombre, nombres) as nombre,
                telefono,
                COALESCE(documento, numero_documento) as documento
            FROM clientes 
            ORDER BY nombre ASC
        """)
    except Exception:
        try:
            df_clientes = cargar_datos("SELECT * FROM clientes")
            # Normalizar nombres de columnas si varían
            if 'nombres' in df_clientes.columns and 'nombre' not in df_clientes.columns:
                df_clientes.rename(columns={'nombres': 'nombre'}, inplace=True)
            if 'numero_documento' in df_clientes.columns and 'documento' not in df_clientes.columns:
                df_clientes.rename(columns={'numero_documento': 'documento'}, inplace=True)
            if 'id' in df_clientes.columns and 'id_cliente' not in df_clientes.columns:
                df_clientes.rename(columns={'id': 'id_cliente'}, inplace=True)
        except Exception:
            df_clientes = pd.DataFrame()

    # --- PESTAÑA 1: REGISTRAR CLIENTE ---
    with tab_nuevo:
        st.subheader("➕ Registrar Nuevo Cliente")
        with st.form("form_nuevo_cliente_p", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre_c = st.text_input("Nombre y Apellido*")
                telefono_c = st.text_input("Teléfono")
            with col2:
                doc_c = st.text_input("N° Documento / RUC")

            if st.form_submit_button("Guardar Cliente", type="primary"):
                if nombre_c.strip():
                    try:
                        # Intento de inserción con nombres estándar
                        try:
                            ejecutar_query("""
                                INSERT INTO clientes (nombre, telefono, documento) 
                                VALUES (:n, :t, :d)
                            """, {"n": nombre_c.strip(), "t": telefono_c.strip(), "d": doc_c.strip()})
                        except Exception:
                            ejecutar_query("""
                                INSERT INTO clientes (nombres, telefono, numero_documento) 
                                VALUES (:n, :t, :d)
                            """, {"n": nombre_c.strip(), "t": telefono_c.strip(), "d": doc_c.strip()})
                            
                        st.success(f"✅ Cliente '{nombre_c}' registrado con éxito.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar cliente: {e}")
                else:
                    st.warning("⚠️ El nombre del cliente es obligatorio.")

    # --- PESTAÑA 2: MODIFICAR CLIENTE ---
    with tab_editar:
        st.subheader("✏️ Modificar Datos de Cliente")
        if not df_clientes.empty and 'nombre' in df_clientes.columns:
            # Crear mapa para el selector: "Nombre (Tel) [ID: X]" -> fila del cliente
            dict_mapa_clientes = {}
            opciones_cli = []
            
            for _, r in df_clientes.iterrows():
                id_cli = r['id_cliente'] if 'id_cliente' in r and pd.notnull(r['id_cliente']) else None
                nom = str(r['nombre']).strip() if pd.notnull(r['nombre']) else "Sin nombre"
                tel = str(r['telefono']).strip() if 'telefono' in r and pd.notnull(r['telefono']) else ""
                
                label = f"{nom} (Tel: {tel})" if tel else nom
                if id_cli is not None:
                    label += f" - [ID: {id_cli}]"
                
                opciones_cli.append(label)
                dict_mapa_clientes[label] = r

            cli_sel_label = st.selectbox("Seleccione el Cliente a Modificar:", opciones_cli)
            cliente_actual = dict_mapa_clientes[cli_sel_label]

            with st.form("form_editar_cliente"):
                col1, col2 = st.columns(2)
                with col1:
                    e_nombre = st.text_input("Nombre y Apellido*", value=str(cliente_actual['nombre']) if pd.notnull(cliente_actual['nombre']) else "")
                    e_telefono = st.text_input("Teléfono", value=str(cliente_actual['telefono']) if pd.notnull(cliente_actual['telefono']) else "")
                with col2:
                    e_doc = st.text_input("N° Documento / RUC", value=str(cliente_actual['documento']) if pd.notnull(cliente_actual['documento']) else "")

                btn_actualizar_cli = st.form_submit_button("Actualizar Cliente", type="primary")

                if btn_actualizar_cli:
                    if e_nombre.strip():
                        try:
                            id_val = int(cliente_actual['id_cliente'])
                            
                            # Intentar actualizar según las columnas reales de la tabla
                            try:
                                sql_upd = """
                                    UPDATE clientes 
                                    SET nombres = :n, telefono = :t, numero_documento = :d 
                                    WHERE id_cliente = :id
                                """
                                ejecutar_query(sql_upd, {"n": e_nombre.strip(), "t": e_telefono.strip(), "d": e_doc.strip(), "id": id_val})
                            except Exception:
                                sql_upd = """
                                    UPDATE clientes 
                                    SET nombre = :n, telefono = :t, documento = :d 
                                    WHERE id_cliente = :id
                                """
                                ejecutar_query(sql_upd, {"n": e_nombre.strip(), "t": e_telefono.strip(), "d": e_doc.strip(), "id": id_val})

                            st.success(f"✅ Cliente '{e_nombre}' actualizado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar cliente: {e}")
                    else:
                        st.warning("⚠️ El nombre del cliente no puede estar vacío.")
        else:
            st.info("No hay clientes registrados para modificar.")

    # --- PESTAÑA 3: LISTA DE CLIENTES ---
    with tab_tabla:
        st.subheader("📋 Lista de Clientes Registrados")
        if not df_clientes.empty:
            filtro_c = st.text_input("🔍 Buscar cliente por nombre o documento:", placeholder="Ej: Juan, 123456...")
            df_mostrar = df_clientes.copy()
            
            if filtro_c:
                cond_nom = df_mostrar['nombre'].astype(str).str.contains(filtro_c, case=False, na=False)
                cond_doc = df_mostrar['documento'].astype(str).str.contains(filtro_c, case=False, na=False)
                df_mostrar = df_mostrar[cond_nom | cond_doc]

            st.write(f"Mostrando **{len(df_mostrar)}** clientes:")
            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay clientes registrados aún.")