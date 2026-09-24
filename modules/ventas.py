import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

def generar_link_whatsapp(vendedor_operacion, cuota_nro, venta_id, producto, cliente):
    nro_destino = "595972989099" 
    mensaje = (
        f"✅ *NOTIFICACIÓN DE COBRO*\n\n"
        f"👤 *Cobrado por:* {vendedor_operacion}\n"
        f"🤝 *Cliente:* {cliente}\n"
        f"📦 *Producto:* {producto}\n"
        f"🔢 *Cuota N°:* {cuota_nro}\n"
        f"📄 *Venta #:* {venta_id}\n"
        f"⏰ *Fecha:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{nro_destino}?text={mensaje_encoded}"

def render_ventas():
    # --- BARRA LATERAL: REGISTRO ---
    st.sidebar.header("🆕 Registrar Nueva Venta")
    with st.sidebar.form("form_registro", clear_on_submit=True):
        producto = st.text_input("Producto*")
        cliente = st.text_input("Cliente*")
        vendedor = st.text_input("Vendedor*")
        precio = st.number_input("Precio Total*", min_value=0.0, format="%.2f")
        cantidad_cuotas = st.number_input("Cantidad de Cuotas*", min_value=1, step=1)
        monto_cuota_input = st.number_input("Monto por Cuota*", min_value=0.0, format="%.2f")
        comision = st.number_input("Comisión*", min_value=0.0, format="%.2f")
        
        tipo_pago = st.selectbox("Tipo de Pago*", ["Mensual con entrega", "Mensual sin entrega", "Semanal"])
        estado_input = st.selectbox("Estado*", ["Activo", "Cancelado"])
        
        btn_crear = st.form_submit_button("Generar Venta y Cronograma")
        
        if btn_crear:
            if producto and cliente and vendedor and precio > 0 and cantidad_cuotas > 0:
                try:
                    with engine.begin() as conn:
                        sql_venta = text("""
                            INSERT INTO ventas (producto, cliente, vendedor, precio, total_cuota, monto_cuota, comision, tipo_pago, estado, fecha_creacion)
                            VALUES (:p, :c, :vend, :pre, :tcuo, :mcuo, :com, :tpago, :est, :fecha)
                            RETURNING id_producto
                        """)
                        fecha_actual = datetime.now()
                        res = conn.execute(sql_venta, {
                            "p": producto, "c": cliente, "vend": vendedor, "pre": precio, 
                            "tcuo": cantidad_cuotas, "mcuo": monto_cuota_input, 
                            "com": comision, "tpago": tipo_pago, "est": estado_input, "fecha": fecha_actual
                        })
                        nuevo_id = res.fetchone()[0]

                        sql_cuota = text("""
                            INSERT INTO detalle_ventas (producto_id, item_cuota, monto_cuota, monto_pago, saldo_cuota, estado, fecha_vencimiento, fecha_pago)
                            VALUES (:id_p, :item, :monto, :pago, :saldo, :est_c, :fv, :fp)
                        """)

                        for i in range(1, int(cantidad_cuotas) + 1):
                            vencimiento = None
                            pago = None
                            monto_pagado = 0
                            saldo = monto_cuota_input
                            estado_cuota = "Activo"

                            if tipo_pago == "Mensual con entrega":
                                vencimiento = fecha_actual + relativedelta(months=(i-1))
                                if i == 1:
                                    pago = fecha_actual
                                    monto_pagado = monto_cuota_input
                                    saldo = 0
                                    estado_cuota = "Cancelado"
                                    vencimiento = fecha_actual
                            elif tipo_pago == "Mensual sin entrega":
                                vencimiento = fecha_actual + relativedelta(months=i)
                            elif tipo_pago == "Semanal":
                                dias_al_domingo = (6 - fecha_actual.weekday()) % 7
                                primer_domingo = fecha_actual + timedelta(days=dias_al_domingo)
                                vencimiento = primer_domingo + timedelta(weeks=(i-1))

                            conn.execute(sql_cuota, {
                                "id_p": nuevo_id, "item": i, "monto": monto_cuota_input,
                                "pago": monto_pagado, "saldo": saldo, "est_c": estado_cuota,
                                "fv": vencimiento, "fp": pago
                            })

                    st.sidebar.success(f"✅ Venta #{nuevo_id} y cronograma {tipo_pago} generados.")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
            else:
                st.sidebar.warning("⚠️ Por favor rellene todos los campos obligatorios (*).")

    # --- CUERPO PRINCIPAL DE VENTAS ---
    st.title("📊 Sistema de Control de Ventas e Ingresos")

    tab_lista, tab_detalles, tab_editar, tab_editar_detalles = st.tabs([
        "📋 Listado de Ventas", "🔍 Ver Detalles de Cuotas", "✏️ Modificar Venta", "💳 Modificar Cuota"
    ])

    df_v = cargar_datos("SELECT * FROM ventas ORDER BY id_producto DESC")

    # --- PESTAÑA 1: LISTADO GENERAL ---
    with tab_lista:
        st.subheader("📋 Historial de Ventas")
        if not df_v.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_nombre = st.text_input("🔍 Buscar por producto:", placeholder="Ej: HONOR X7D...")
            with col_f2:
                filtro_cliente = st.text_input("👤 Buscar por cliente:", placeholder="Ej: Juan Pérez...")
            
            df_display = df_v.copy()
            if filtro_nombre:
                df_display = df_display[df_display['producto'].str.contains(filtro_nombre, case=False, na=False)]
            if filtro_cliente:
                df_display = df_display[df_display['cliente'].str.contains(filtro_cliente, case=False, na=False)]

            if 'fecha_ultimo_pago' in df_display.columns:
                df_display['fecha_ultimo_pago'] = pd.to_datetime(df_display['fecha_ultimo_pago'], errors='coerce')

            columnas_enteras = ["cuota", "total_cuota"]
            for col in columnas_enteras:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).astype(int)

            formatos = {}
            cols_dinero = ["monto_total", "precio", "monto_cuota", "comision"]
            for col in cols_dinero:
                if col in df_display.columns:
                    formatos[col] = "{:,.2f}"
            for col in columnas_enteras:
                if col in df_display.columns:
                    formatos[col] = "{:d}"
            if 'fecha_ultimo_pago' in df_display.columns:
                formatos['fecha_ultimo_pago'] = lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else "-"

            st.write(f"Mostrando {len(df_display)} registros:")
            st.dataframe(df_display.style.format(formatos, na_rep="-"), use_container_width=True)
        else:
            st.info("No hay ventas registradas aún.")

    # --- PESTAÑA 2: DETALLES DE CUOTAS ---
    with tab_detalles:
        st.subheader("🔍 Consulta de Detalles y Cobros")
        if not df_v.empty:
            id_sel = st.selectbox("Seleccione ID de Venta:", df_v['id_producto'], key="det_sel")
            df_d = cargar_datos("SELECT * FROM detalle_ventas WHERE producto_id = :id_p ORDER BY item_cuota ASC", params={"id_p": int(id_sel)})
            
            if not df_d.empty:
                st.write(f"### Detalles de la Venta #{id_sel}")
                columnas_num = ["saldo_cuota", "monto_pago", "monto_cuota"]
                for col in columnas_num:
                    if col in df_d.columns:
                        df_d[col] = pd.to_numeric(df_d[col], errors='coerce').fillna(0.0)

                formatos_d = {col: "{:,.2f}" for col in columnas_num if col in df_d.columns}
                st.dataframe(df_d.style.format(formatos_d), use_container_width=True)

                st.divider()
                st.write("#### ⚡ Acciones Rápidas")

                for index, fila in df_d.iterrows():
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        st.write(f"Cuota N° {int(fila['item_cuota'])} - Vence: {fila['fecha_vencimiento']} - Estado: **{fila['estado']}**")
                    
                    with col_btn:
                        esta_activo = str(fila['estado']).strip().capitalize() == "Activo"
                        if st.button(f"Pagar Cuota {int(fila['item_cuota'])}", key=f"btn_pagar_{id_sel}_{fila['item_cuota']}", disabled=not esta_activo):
                            datos_venta = df_v[df_v['id_producto'] == id_sel].iloc[0]
                            st.session_state.cuota_a_pagar = {
                                "id_p": id_sel,
                                "item": fila['item_cuota'],
                                "monto": fila['monto_cuota'],
                                "producto": datos_venta['producto'],
                                "cliente": datos_venta['cliente']
                            }

                if "cuota_a_pagar" in st.session_state:
                    info = st.session_state.cuota_a_pagar
                    
                    @st.dialog("¿Confirmar pago de cuota?")
                    def confirmar_pago():
                        if "pago_exitoso" not in st.session_state:
                            st.session_state.pago_exitoso = False

                        if not st.session_state.pago_exitoso:
                            st.warning(f"Se registrará el pago de la Cuota {int(info['item'])} para la Venta #{info['id_p']}.")
                            c_si, c_no = st.columns(2)
                            
                            if c_si.button("SÍ, confirmar", use_container_width=True, type="primary"):
                                try:
                                    ahora = datetime.now()
                                    with engine.begin() as conn:
                                        conn.execute(text("""
                                            UPDATE detalle_ventas SET monto_pago = monto_cuota, saldo_cuota = 0, 
                                            estado = 'Cancelado', fecha_pago = :hoy 
                                            WHERE producto_id = :id_p AND item_cuota = :item
                                        """), {"hoy": ahora, "id_p": info['id_p'], "item": info['item']})
                                        
                                        conn.execute(text("""
                                            UPDATE ventas SET cuota = COALESCE(cuota, 0) + 1, fecha_ultimo_pago = :hoy 
                                            WHERE id_producto = :id_p
                                        """), {"hoy": ahora, "id_p": info['id_p']})
                                        
                                        conn.execute(text("""
                                            UPDATE ventas SET estado = 'Cancelado' 
                                            WHERE id_producto = :id_p AND cuota >= total_cuota
                                        """), {"id_p": info['id_p']})

                                    st.session_state.pago_exitoso = True
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al procesar el pago: {e}")
                            
                            if c_no.button("NO, cancelar", use_container_width=True):
                                del st.session_state.cuota_a_pagar
                                st.rerun()
                        else:
                            st.success(f"✅ ¡Pago procesado con éxito por {st.session_state.usuario_actual}!")
                            link = generar_link_whatsapp(
                                st.session_state.usuario_actual, 
                                int(info['item']), 
                                info['id_p'],
                                info['producto'],
                                info['cliente']
                            )
                            st.markdown(f"""
                                <a href="{link}" target="_blank" style="text-decoration: none;">
                                    <div style="background-color: #25D366; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;">
                                        📲 Enviar Comprobante por WhatsApp
                                    </div>
                                </a>
                            """, unsafe_allow_html=True)
                            
                            st.info("Una vez enviado el mensaje, presiona el botón de abajo para actualizar la lista.")
                            if st.button("Finalizar y cerrar", use_container_width=True):
                                del st.session_state.cuota_a_pagar
                                del st.session_state.pago_exitoso
                                st.rerun()

                    confirmar_pago()

    # --- PESTAÑA 3: EDICIÓN DE DATOS ---
    with tab_editar:
        st.subheader("✏️ Modificar Información de Venta")
        if not df_v.empty:
            id_edit = st.selectbox("Elija el ID del producto a editar:", df_v['id_producto'], key="edit_sel")
            fila_actual = df_v[df_v['id_producto'] == id_edit].iloc[0]
            obs_actual = str(fila_actual['observacion']) if 'observacion' in fila_actual and pd.notnull(fila_actual['observacion']) else ""
            
            with st.form("form_edicion"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_prod = st.text_input("Producto", value=fila_actual['producto'])
                    nuevo_clie = st.text_input("Cliente", value=fila_actual['cliente'])
                    nuevo_precio = st.number_input("Precio", value=float(fila_actual['precio'] if fila_actual['precio'] else 0))
                
                with col2:
                    nueva_cuota = st.number_input("Cuota", value=int(fila_actual['cuota']) if pd.notnull(fila_actual['cuota']) else 0, step=1)
                    opciones_est = ["Activo", "Cancelado"]
                    est_db = str(fila_actual['estado']).strip().capitalize()
                    try:
                        idx_est = [opt.lower() for opt in opciones_est].index(est_db.lower())
                    except:
                        idx_est = 0
                    nuevo_est = st.selectbox("Estado", opciones_est, index=idx_est)

                nueva_obs = st.text_input("Observación", value=obs_actual, max_chars=50, help="Máximo 50 caracteres")

                if st.form_submit_button("Guardar Cambios"):
                    sql_update = """
                        UPDATE ventas 
                        SET producto=:p, cliente=:c, precio=:pre, cuota=:cuo, estado=:e, observacion=:obs
                        WHERE id_producto=:id
                    """
                    ejecutar_query(sql_update, {
                        "p": nuevo_prod, "c": nuevo_clie, "pre": nuevo_precio, 
                        "cuo": nueva_cuota, "e": nuevo_est, "obs": nueva_obs, "id": id_edit
                    })
                    st.success(f"✅ Venta #{id_edit} actualizada correctamente")
                    st.rerun()

    # --- PESTAÑA 4: EDICIÓN DE DETALLES (CUOTAS) ---
    with tab_editar_detalles:
        st.subheader("💳 Modificar Detalle de Cuota Individual")
        if not df_v.empty:
            id_venta_sel = st.selectbox("Seleccione ID de Venta:", df_v['id_producto'], key="edit_det_v")
            df_cuotas = cargar_datos("SELECT * FROM detalle_ventas WHERE producto_id = :id_p ORDER BY item_cuota ASC", params={"id_p": int(id_venta_sel)})
            
            if not df_cuotas.empty:
                id_cuota_sel = st.selectbox("Seleccione el N° de Cuota a editar:", df_cuotas['item_cuota'], key="edit_cuota_sel")
                fila_cuota = df_cuotas[df_cuotas['item_cuota'] == id_cuota_sel].iloc[0]
                
                with st.form("form_edicion_cuota"):
                    c1, c2 = st.columns(2)
                    with c1:
                        monto_c = st.number_input("Monto Cuota", value=float(fila_cuota['monto_cuota']))
                        pago_c = st.number_input("Monto Pago", value=float(fila_cuota['monto_pago'] if fila_cuota['monto_pago'] else 0))
                        f_venc = st.date_input("Fecha de Vencimiento", value=pd.to_datetime(fila_cuota['fecha_vencimiento']).date() if pd.notnull(fila_cuota['fecha_vencimiento']) else datetime.now().date())
                    
                    with c2:
                        saldo_c = st.number_input("Saldo Cuota", value=float(fila_cuota['saldo_cuota']))
                        f_pago = st.date_input("Fecha de Pago", value=pd.to_datetime(fila_cuota['fecha_pago']).date() if pd.notnull(fila_cuota['fecha_pago']) else None)
                        opciones_est_c = ["Activo", "Cancelado"]
                        est_c_db = str(fila_cuota['estado']).strip().capitalize()
                        idx_c = opciones_est_c.index(est_c_db) if est_c_db in opciones_est_c else 0
                        nuevo_est_c = st.selectbox("Estado Cuota", opciones_est_c, index=idx_c)

                    if st.form_submit_button("Actualizar Cuota"):
                        sql_upd_det = """
                            UPDATE detalle_ventas 
                            SET monto_cuota=:m, monto_pago=:p, saldo_cuota=:s, 
                                estado=:e, fecha_pago=:fp, fecha_vencimiento=:fv
                            WHERE producto_id=:id_p AND item_cuota=:item
                        """
                        ejecutar_query(sql_upd_det, {
                            "m": monto_c, "p": pago_c, "s": saldo_c, "e": nuevo_est_c, 
                            "fp": f_pago, "fv": f_venc, "id_p": id_venta_sel, "item": id_cuota_sel
                        })
                        st.success(f"✅ Cuota {id_cuota_sel} actualizada con fechas.")
                        st.rerun()