import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

@st.dialog("⚠️ Confirmar Eliminación de Cliente")
def dialog_eliminar_cliente(id_cliente, nombre_cliente):
    st.warning(f"¿Está seguro de que desea eliminar al cliente **{nombre_cliente}** (ID: {id_cliente})?")
    st.error("🚨 Esta acción eliminará permanentemente al cliente de la base de datos.")

    c_conf, c_canc = st.columns(2)
    if c_conf.button("🔥 Sí, Eliminar", use_container_width=True, type="primary"):
        try:
            with engine.begin() as conn:
                try:
                    conn.execute(text("DELETE FROM clientes WHERE id_cliente = :id"), {"id": id_cliente})
                except Exception:
                    conn.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": id_cliente})
            
            st.success(f"✅ Cliente '{nombre_cliente}' eliminado correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al eliminar cliente: {e}")

    if c_canc.button("❌ Cancelar", use_container_width=True):
        st.rerun()


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
                telefono_c = st.text_input("Teléfono*")
            with col2:
                doc_c = st.text_input("N° Documento / RUC")

            if st.form_submit_button("Guardar Cliente", type="primary"):
                nom_val = nombre_c.strip()
                tel_val = telefono_c.strip()
                doc_val = doc_c.strip() if doc_c.strip() else ""

                if not nom_val:
                    st.warning("⚠️ El nombre del cliente es obligatorio.")
                elif not tel_val:
                    st.warning("⚠️ El número de teléfono es obligatorio.")
                else:
                    # Validar si el teléfono ya existe registrado
                    tel_existe = cargar_datos(
                        "SELECT 1 FROM clientes WHERE TRIM(telefono) = :t",
                        params={"t": tel_val}
                    )
                    
                    if not tel_existe.empty:
                        st.error(f"❌ El número de teléfono '{tel_val}' ya se encuentra registrado con otro cliente.")
                    else:
                        try:
                            try:
                                ejecutar_query("""
                                    INSERT INTO clientes (nombre, telefono, documento) 
                                    VALUES (:n, :t, :d)
                                """, {"n": nom_val, "t": tel_val, "d": doc_val})
                            except Exception:
                                ejecutar_query("""
                                    INSERT INTO clientes (nombres, telefono, numero_documento) 
                                    VALUES (:n, :t, :d)
                                """, {"n": nom_val, "t": tel_val, "d": doc_val})
                                
                            st.success(f"✅ Cliente '{nom_val}' registrado con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar cliente: {e}")

    # --- PESTAÑA 2: MODIFICAR CLIENTE ---
    with tab_editar:
        st.subheader("✏️ Modificar Datos de Cliente")
        if not df_clientes.empty and 'nombre' in df_clientes.columns:
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
                    e_telefono = st.text_input("Teléfono*", value=str(cliente_actual['telefono']) if pd.notnull(cliente_actual['telefono']) else "")
                with col2:
                    e_doc = st.text_input("N° Documento / RUC", value=str(cliente_actual['documento']) if pd.notnull(cliente_actual['documento']) and str(cliente_actual['documento']).lower() != 'none' else "")

                btn_actualizar_cli = st.form_submit_button("Actualizar Cliente", type="primary")

                if btn_actualizar_cli:
                    nom_edit_val = e_nombre.strip()
                    tel_edit_val = e_telefono.strip()
                    doc_edit_val = e_doc.strip() if e_doc.strip() else ""
                    id_val = int(cliente_actual['id_cliente'])

                    if not nom_edit_val:
                        st.warning("⚠️ El nombre del cliente no puede estar vacío.")
                    elif not tel_edit_val:
                        st.warning("⚠️ El número de teléfono es obligatorio.")
                    else:
                        # Verificar que el teléfono no exista en OTRO cliente diferente
                        try:
                            tel_duplicado = cargar_datos("""
                                SELECT 1 FROM clientes 
                                WHERE TRIM(telefono) = :t 
                                  AND COALESCE(id_cliente, id) != :id
                            """, params={"t": tel_edit_val, "id": id_val})
                        except Exception:
                            tel_duplicado = pd.DataFrame()

                        if not tel_duplicado.empty:
                            st.error(f"❌ El número de teléfono '{tel_edit_val}' ya pertenece a otro cliente.")
                        else:
                            try:
                                try:
                                    sql_upd = """
                                        UPDATE clientes 
                                        SET nombres = :n, telefono = :t, numero_documento = :d 
                                        WHERE id_cliente = :id
                                    """
                                    ejecutar_query(sql_upd, {"n": nom_edit_val, "t": tel_edit_val, "d": doc_edit_val, "id": id_val})
                                except Exception:
                                    sql_upd = """
                                        UPDATE clientes 
                                        SET nombre = :n, telefono = :t, documento = :d 
                                        WHERE id_cliente = :id
                                    """
                                    ejecutar_query(sql_upd, {"n": nom_edit_val, "t": tel_edit_val, "d": doc_edit_val, "id": id_val})

                                st.success(f"✅ Cliente '{nom_edit_val}' actualizado correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar cliente: {e}")
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

            # Cargar ventas activas para la restricción de eliminación
            df_v_activas = cargar_datos("SELECT id_cliente, cliente FROM ventas WHERE LOWER(TRIM(estado)) = 'activo'")

            # Renderizado en tarjetas/grilla con botón de eliminación
            for _, row_c in df_mostrar.iterrows():
                id_c = int(row_c['id_cliente']) if pd.notnull(row_c['id_cliente']) else 0
                nom_c = str(row_c['nombre']) if pd.notnull(row_c['nombre']) else "-"
                doc_c = str(row_c['documento']) if pd.notnull(row_c['documento']) and str(row_c['documento']).lower() != 'none' and str(row_c['documento']).strip() != '' else "-"
                tel_c = str(row_c['telefono']) if pd.notnull(row_c['telefono']) else "-"

                # Verificar si el cliente tiene ventas activas (por id_cliente o por nombre)
                tiene_venta_activa = False
                cant_ventas_act = 0
                if not df_v_activas.empty:
                    cond_id = (df_v_activas['id_cliente'] == id_c) if 'id_cliente' in df_v_activas.columns else False
                    cond_nom = (df_v_activas['cliente'].astype(str).str.strip().str.lower() == nom_c.strip().lower())
                    ventas_match = df_v_activas[cond_id | cond_nom]
                    cant_ventas_act = len(ventas_match)
                    tiene_venta_activa = cant_ventas_act > 0

                c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
                with c1:
                    st.write(f"**ID:** {id_c}")
                with c2:
                    st.write(f"👤 **{nom_c}**")
                with c3:
                    st.caption(f"📄 Doc: {doc_c} | 📞 Tel: {tel_c}")
                with c4:
                    if tiene_venta_activa:
                        st.button(
                            "🗑️", 
                            key=f"btn_del_cli_{id_c}", 
                            disabled=True, 
                            help=f"No se puede eliminar: tiene {cant_ventas_act} venta(s) activa(s)."
                        )
                    else:
                        if st.button("🗑️", key=f"btn_del_cli_{id_c}", help="Eliminar cliente"):
                            dialog_eliminar_cliente(id_c, nom_c)

                st.divider()
        else:
            st.info("No hay clientes registrados aún.")