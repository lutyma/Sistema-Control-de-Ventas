import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

@st.dialog("⚠️ Confirmar Eliminación de Vendedor")
def dialog_eliminar_vendedor(id_vendedor, nombre_vendedor):
    st.warning(f"¿Está seguro de que desea eliminar al vendedor **{nombre_vendedor}** (ID: {id_vendedor})?")
    st.error("🚨 Esta acción eliminará permanentemente al vendedor de la base de datos.")

    c_conf, c_canc = st.columns(2)
    if c_conf.button("🔥 Sí, Eliminar", use_container_width=True, type="primary"):
        try:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM vendedores WHERE id_vendedor = :id"), {"id": id_vendedor})
            
            st.success(f"✅ Vendedor '{nombre_vendedor}' eliminado correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al eliminar vendedor: {e}")

    if c_canc.button("❌ Cancelar", use_container_width=True):
        st.rerun()


def render_vendedores():
    st.title("👔 Paramétrico - Gestión de Vendedores")

    tab_nuevo, tab_editar, tab_tabla = st.tabs([
        "➕ Registrar Vendedor", 
        "✏️ Modificar Vendedor", 
        "📋 Lista de Vendedores"
    ])

    # --- CARGA DE DATOS DE VENDEDORES ---
    try:
        df_vendedores = cargar_datos("SELECT * FROM vendedores ORDER BY nombre ASC")
    except Exception:
        df_vendedores = pd.DataFrame()

    # --- PESTAÑA 1: REGISTRAR VENDEDOR ---
    with tab_nuevo:
        st.subheader("➕ Registrar Nuevo Vendedor")
        with st.form("form_nuevo_vendedor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre_v = st.text_input("Nombre y Apellido*")
                telefono_v = st.text_input("Teléfono*")
            with col2:
                doc_v = st.text_input("N° Documento / CI")
                estado_v = st.selectbox("Estado*", ["Activo", "Inactivo"])

            if st.form_submit_button("Guardar Vendedor", type="primary"):
                nom_val = nombre_v.strip()
                tel_val = telefono_v.strip()
                doc_val = doc_v.strip() if doc_v.strip() else ""

                if not nom_val:
                    st.warning("⚠️ El nombre del vendedor es obligatorio.")
                elif not tel_val:
                    st.warning("⚠️ El número de teléfono es obligatorio.")
                else:
                    try:
                        ejecutar_query("""
                            INSERT INTO vendedores (nombre, telefono, documento, estado) 
                            VALUES (:n, :t, :d, :e)
                        """, {"n": nom_val, "t": tel_val, "d": doc_val, "e": estado_v})
                        
                        st.success(f"✅ Vendedor '{nom_val}' registrado con éxito.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar vendedor: {e}")

    # --- PESTAÑA 2: MODIFICAR VENDEDOR ---
    with tab_editar:
        st.subheader("✏️ Modificar Datos de Vendedor")
        if not df_vendedores.empty:
            mapa_vendedores = {f"{r['nombre']} (Tel: {r['telefono']}) - [ID: {r['id_vendedor']}]": r for _, r in df_vendedores.iterrows()}
            v_sel_label = st.selectbox("Seleccione el Vendedor a Modificar:", list(mapa_vendedores.keys()))
            vendedor_actual = mapa_vendedores[v_sel_label]

            with st.form("form_editar_vendedor"):
                col1, col2 = st.columns(2)
                with col1:
                    e_nombre = st.text_input("Nombre y Apellido*", value=str(vendedor_actual['nombre']))
                    e_telefono = st.text_input("Teléfono*", value=str(vendedor_actual['telefono']))
                with col2:
                    e_doc = st.text_input("N° Documento", value=str(vendedor_actual['documento']) if pd.notnull(vendedor_actual['documento']) else "")
                    opts_est = ["Activo", "Inactivo"]
                    idx_est = opts_est.index(vendedor_actual['estado']) if 'estado' in vendedor_actual and vendedor_actual['estado'] in opts_est else 0
                    e_estado = st.selectbox("Estado", opts_est, index=idx_est)

                if st.form_submit_button("Actualizar Vendedor", type="primary"):
                    id_v = int(vendedor_actual['id_vendedor'])
                    try:
                        sql_upd = """
                            UPDATE vendedores 
                            SET nombre = :n, telefono = :t, documento = :d, estado = :e 
                            WHERE id_vendedor = :id
                        """
                        ejecutar_query(sql_upd, {"n": e_nombre.strip(), "t": e_telefono.strip(), "d": e_doc.strip(), "e": e_estado, "id": id_v})
                        st.success(f"✅ Vendedor '{e_nombre}' actualizado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar vendedor: {e}")
        else:
            st.info("No hay vendedores registrados para modificar.")

    # --- PESTAÑA 3: LISTA DE VENDEDORES ---
    with tab_tabla:
        st.subheader("📋 Lista de Vendedores Registrados")
        if not df_vendedores.empty:
            df_v_activas = cargar_datos("SELECT id_vendedor, vendedor FROM ventas WHERE LOWER(TRIM(estado)) = 'activo'")

            for _, row_v in df_vendedores.iterrows():
                id_v = int(row_v['id_vendedor'])
                nom_v = str(row_v['nombre'])
                doc_v = str(row_v['documento']) if pd.notnull(row_v['documento']) and str(row_v['documento']).strip() != '' else "-"
                tel_v = str(row_v['telefono'])
                est_v = str(row_v.get('estado', 'Activo'))

                # Verificar si el vendedor tiene ventas activas
                tiene_venta_activa = False
                cant_ventas_act = 0
                if not df_v_activas.empty:
                    cond_id = (df_v_activas['id_vendedor'] == id_v) if 'id_vendedor' in df_v_activas.columns else False
                    cond_nom = (df_v_activas['vendedor'].astype(str).str.strip().str.lower() == nom_v.strip().lower())
                    ventas_match = df_v_activas[cond_id | cond_nom]
                    cant_ventas_act = len(ventas_match)
                    tiene_venta_activa = cant_ventas_act > 0

                c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
                with c1:
                    st.write(f"**ID:** {id_v}")
                with c2:
                    st.write(f"👔 **{nom_v}**")
                with c3:
                    st.caption(f"📄 Doc: {doc_v} | 📞 Tel: {tel_v} | Estado: {est_v}")
                with c4:
                    if tiene_venta_activa:
                        st.button(
                            "🗑️", 
                            key=f"btn_del_vend_{id_v}", 
                            disabled=True, 
                            help=f"No se puede eliminar: tiene {cant_ventas_act} venta(s) activa(s)."
                        )
                    else:
                        if st.button("🗑️", key=f"btn_del_vend_{id_v}", help="Eliminar vendedor"):
                            dialog_eliminar_vendedor(id_v, nom_v)

                st.divider()
        else:
            st.info("No hay vendedores registrados aún.")