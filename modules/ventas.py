import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

# --- FUNCIONES DE LIMPIEZA DE ESTADO AL CERRAR MODALES ---
def limpiar_modal_ver():
    st.session_state.pop("ver_venta_id", None)

def limpiar_modal_pago():
    st.session_state.pop("pago_rapido_datos", None)
    st.session_state.pop("cobro_rapido_exitoso", None)
    st.session_state.pop("monto_cobrado_hoy", None)
    st.session_state.pop("num_cuota_cobrada", None)

def limpiar_modal_eliminar():
    st.session_state.pop("eliminar_venta_datos", None)


def generar_link_whatsapp(vendedor_operacion, cuota_nro, venta_id, producto, cliente, monto_pagado_hoy=None):
    nro_destino = "595972989099" 
    txt_monto = f" (Gs. {monto_pagado_hoy:,.0f})" if monto_pagado_hoy else ""
    mensaje = (
        f"✅ *NOTIFICACIÓN DE COBRO*\n\n"
        f"👤 *Cobrado por:* {vendedor_operacion}\n"
        f"🤝 *Cliente:* {cliente}\n"
        f"📦 *Producto:* {producto}\n"
        f"🔢 *Cuota N°:* {cuota_nro}{txt_monto}\n"
        f"📄 *Venta #:* {venta_id}\n"
        f"⏰ *Fecha:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{nro_destino}?text={mensaje_encoded}"


# --- DIÁLOGO 1: VISUALIZACIÓN COMPLETA DE VENTA Y CRONOGRAMA ---
@st.dialog("📄 Detalle General de la Venta", width="large")
def dialog_ver_venta_completa(id_venta):
    df_v_sel = cargar_datos("SELECT * FROM ventas WHERE venta_id = :id_v", params={"id_v": int(id_venta)})
    
    if df_v_sel.empty:
        st.error("No se encontraron los datos de esta venta.")
        if st.button("Cerrar", use_container_width=True):
            limpiar_modal_ver()
            st.rerun()
        return

    v_data = df_v_sel.iloc[0]
    
    st.subheader(f"Venta #{id_venta} - {v_data['producto']}")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"👤 **Cliente:** {v_data['cliente']}")
        st.markdown(f"👔 **Vendedor:** {v_data.get('vendedor', '-')}")
        st.markdown(f"📅 **Fecha Venta:** {pd.to_datetime(v_data.get('fecha_creacion')).strftime('%d/%m/%Y %H:%M') if pd.notnull(v_data.get('fecha_creacion')) else '-'}")
    
    with c2:
        precio_val = float(v_data['precio']) if pd.notnull(v_data['precio']) else 0.0
        comision_val = float(v_data.get('comision', 0)) if pd.notnull(v_data.get('comision')) else 0.0
        st.markdown(f"💰 **Precio Total:** Gs. {precio_val:,.0f}")
        st.markdown(f"💵 **Comisión:** Gs. {comision_val:,.0f}")
        st.markdown(f"💳 **Tipo de Pago:** {v_data.get('tipo_pago', '-')}")

    with c3:
        cuota_p = int(v_data['cuota']) if pd.notnull(v_data['cuota']) else 0
        tot_c = int(v_data['total_cuota']) if pd.notnull(v_data['total_cuota']) else 1
        st.markdown(f"🔢 **Cuotas Pagadas:** {cuota_p} / {tot_c}")
        st.markdown(f"📌 **Estado:** `{v_data['estado']}`")
        if 'observacion' in v_data and pd.notnull(v_data['observacion']) and str(v_data['observacion']).strip():
            st.markdown(f"📝 **Observación:** {v_data['observacion']}")

    st.divider()

    st.subheader("📅 Cronograma de Cuotas y Pagos")
    df_cuotas = cargar_datos("SELECT * FROM detalle_ventas WHERE venta_id = :id_v ORDER BY item_cuota ASC", params={"id_v": int(id_venta)})

    if not df_cuotas.empty:
        cols_num = ["monto_cuota", "monto_pago", "saldo_cuota"]
        for col in cols_num:
            if col in df_cuotas.columns:
                df_cuotas[col] = pd.to_numeric(df_cuotas[col], errors='coerce').fillna(0.0)

        for col_f in ['fecha_vencimiento', 'fecha_pago']:
            if col_f in df_cuotas.columns:
                df_cuotas[col_f] = pd.to_datetime(df_cuotas[col_f], errors='coerce').dt.strftime('%d/%m/%Y')

        fmt_dict = {col: "{:,.2f}" for col in cols_num if col in df_cuotas.columns}
        st.dataframe(df_cuotas.style.format(fmt_dict, na_rep="-"), use_container_width=True)
    else:
        st.info("No hay cuotas registradas para esta venta.")

    if st.button("Cerrar Detalle", use_container_width=True):
        limpiar_modal_ver()
        st.rerun()


# --- DIÁLOGO 2: PAGO RÁPIDO DESDE HISTORIAL ---
@st.dialog("💳 Cobro Rápido de Cuota")
def dialog_pago_rapido(id_venta, producto, cliente):
    df_cuota_pendiente = cargar_datos("""
        SELECT * FROM detalle_ventas 
        WHERE venta_id = :id_v AND (estado = 'Activo' OR estado IS NULL OR saldo_cuota > 0)
        ORDER BY item_cuota ASC 
        LIMIT 1
    """, params={"id_v": int(id_venta)})

    if df_cuota_pendiente.empty:
        st.success("🎉 ¡Esta venta no tiene cuotas pendientes de pago!")
        if st.button("Cerrar", use_container_width=True):
            limpiar_modal_pago()
            st.rerun()
        return

    cuota = df_cuota_pendiente.iloc[0]
    num_cuota = int(cuota['item_cuota'])
    monto_cuota = float(cuota['monto_cuota']) if pd.notnull(cuota['monto_cuota']) else 0.0
    monto_pago_prev = float(cuota['monto_pago']) if pd.notnull(cuota['monto_pago']) else 0.0
    saldo_actual = float(cuota['saldo_cuota']) if pd.notnull(cuota['saldo_cuota']) and float(cuota['saldo_cuota']) > 0 else monto_cuota

    if "cobro_rapido_exitoso" not in st.session_state:
        st.session_state.cobro_rapido_exitoso = False

    if not st.session_state.cobro_rapido_exitoso:
        st.markdown(f"**Venta #:** {id_venta} | **Cliente:** {cliente}")
        st.markdown(f"**Producto:** {producto}")
        st.info(f"📌 **Cuota a Pagar:** N° {num_cuota} | **Saldo Pendiente:** Gs. {saldo_actual:,.0f}")

        tipo_pago_opcion = st.radio("Modalidad de Pago:", ["Pagar Saldo Completo", "Pago Parcial"], horizontal=True)

        if tipo_pago_opcion == "Pagar Saldo Completo":
            monto_a_cobrar = saldo_actual
        else:
            monto_a_cobrar = st.number_input("Monto a Cobrar (Gs.):", min_value=1.0, max_value=saldo_actual, value=min(saldo_actual, 50000.0), step=5000.0)

        col_si, col_no = st.columns(2)
        if col_si.button("✅ Registrar Pago", use_container_width=True, type="primary"):
            try:
                ahora = datetime.now()
                nuevo_pago_acumulado = monto_pago_prev + monto_a_cobrar
                nuevo_saldo = max(0.0, saldo_actual - monto_a_cobrar)
                nuevo_estado_cuota = "Cancelado" if nuevo_saldo == 0 else "Activo"

                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE detalle_ventas 
                        SET monto_pago = :pago, saldo_cuota = :saldo, 
                            estado = :est, fecha_pago = :hoy 
                        WHERE venta_id = :id_v AND item_cuota = :item
                    """), {
                        "pago": nuevo_pago_acumulado,
                        "saldo": nuevo_saldo,
                        "est": nuevo_estado_cuota,
                        "hoy": ahora,
                        "id_v": id_venta,
                        "item": num_cuota
                    })

                    if nuevo_saldo == 0:
                        conn.execute(text("""
                            UPDATE ventas 
                            SET cuota = COALESCE(cuota, 0) + 1, fecha_ultimo_pago = :hoy 
                            WHERE venta_id = :id_v
                        """), {"hoy": me_hoy if 'me_hoy' in locals() else ahora, "id_v": id_venta})

                        conn.execute(text("""
                            UPDATE ventas 
                            SET estado = 'Cancelado' 
                            WHERE venta_id = :id_v AND cuota >= total_cuota
                        """), {"id_v": id_venta})

                st.session_state.cobro_rapido_exitoso = True
                st.session_state.monto_cobrado_hoy = monto_a_cobrar
                st.session_state.num_cuota_cobrada = num_cuota
                st.rerun()
            except Exception as e:
                st.error(f"Error al procesar el pago: {e}")

        if col_no.button("❌ Cancelar", use_container_width=True):
            limpiar_modal_pago()
            st.rerun()

    else:
        st.success(f"🎉 ¡Pago de Gs. {st.session_state.monto_cobrado_hoy:,.0f} registrado con éxito!")
        
        link_wa = generar_link_whatsapp(
            st.session_state.usuario_actual,
            st.session_state.num_cuota_cobrada,
            id_venta,
            producto,
            cliente,
            st.session_state.monto_cobrado_hoy
        )
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px;">
                    📲 Enviar Comprobante por WhatsApp
                </div>
            </a>
        """, unsafe_allow_html=True)

        if st.button("Finalizar y Cerrar", use_container_width=True):
            limpiar_modal_pago()
            st.rerun()


# --- DIÁLOGO 3: ELIMINAR VENTA COMPLETA ---
@st.dialog("⚠️ Eliminar Venta")
def dialog_eliminar_venta(id_venta, producto, cliente):
    st.warning(f"¿Está seguro de que desea eliminar permanentemente la **Venta #{id_venta}**?")
    st.markdown(f"**Cliente:** {cliente}\n\n**Producto:** {producto}")
    st.error("🚨 Esta acción eliminará la venta y todas sus cuotas registradas de la base de datos. No se puede deshacer.")

    col_confirmar, col_cancelar = st.columns(2)

    if col_confirmar.button("🔥 Sí, Eliminar", use_container_width=True, type="primary"):
        try:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM detalle_ventas WHERE venta_id = :id_v"), {"id_v": id_venta})
                conn.execute(text("DELETE FROM ventas WHERE venta_id = :id_v"), {"id_v": id_venta})

            st.success(f"✅ Venta #{id_venta} eliminada correctamente.")
            limpiar_modal_eliminar()
            st.rerun()
        except Exception as e:
            st.error(f"Error al eliminar la venta: {e}")

    if col_cancelar.button("❌ Cancelar", use_container_width=True):
        limpiar_modal_eliminar()
        st.rerun()


def render_ventas():

    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = "Sistema"

    # --- CARGA DE DATOS BASE ---
    df_v = cargar_datos("SELECT * FROM ventas ORDER BY venta_id DESC")
    
    try:
        df_clientes = cargar_datos("""
            SELECT 
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
        except Exception:
            df_clientes = pd.DataFrame()

    PLACEHOLDER_CLIENTE = "-- Seleccione un Cliente --"
    opciones_clientes = [PLACEHOLDER_CLIENTE]
    dict_clientes = {}
    if not df_clientes.empty and 'nombre' in df_clientes.columns:
        for _, r in df_clientes.iterrows():
            nom = str(r['nombre']).strip() if pd.notnull(r['nombre']) else "Sin nombre"
            tel = str(r['telefono']).strip() if 'telefono' in r and pd.notnull(r['telefono']) else ""
            label_c = f"{nom} (Tel: {tel})" if tel else nom
            opciones_clientes.append(label_c)
            dict_clientes[label_c] = nom

    try:
        df_productos = cargar_datos("SELECT * FROM ecommerce_productos ORDER BY nombre ASC")
    except Exception:
        df_productos = pd.DataFrame()

    PLACEHOLDER_PRODUCTO = "-- Seleccione un Producto --"
    opciones_productos = [PLACEHOLDER_PRODUCTO]
    dict_productos = {}

    if not df_productos.empty and 'nombre' in df_productos.columns:
        for _, r in df_productos.iterrows():
            nom_p = str(r['nombre']).strip() if pd.notnull(r['nombre']) else ""
            precio_p = float(r['precio']) if 'precio' in r and pd.notnull(r['precio']) else 0.0
            stock_p = int(r['stock']) if 'stock' in r and pd.notnull(r['stock']) else 0
            cant_cuotas_p = int(r['cant_cuotas']) if 'cant_cuotas' in r and pd.notnull(r['cant_cuotas']) else 12
            monto_cuota_p = float(r['monto_cuota']) if 'monto_cuota' in r and pd.notnull(r['monto_cuota']) else 0.0
            
            label_p = f"{nom_p} - Precio: Gs. {precio_p:,.0f} (Stock: {stock_p})"
            opciones_productos.append(label_p)
            dict_productos[label_p] = {
                "nombre": nom_p,
                "precio": precio_p,
                "stock": stock_p,
                "cant_cuotas": cant_cuotas_p,
                "monto_cuota": monto_cuota_p
            }

    # --- BARRA LATERAL: REGISTRO DE VENTAS ---
    st.sidebar.header("🆕 Registrar Nueva Venta")

    if len(opciones_clientes) == 1:
        st.sidebar.warning("⚠️ No hay clientes registrados. Vaya al menú '⚙️ Paramétrico -> 👤 Gestión de Clientes' para registrar uno.")
    elif len(opciones_productos) == 1:
        st.sidebar.warning("⚠️ No hay productos registrados. Vaya al menú '⚙️ Paramétrico -> 📦 Gestión de Productos' para registrar productos.")
    else:
        cliente_label_sel = st.sidebar.selectbox(
            "👤 Buscar / Seleccionar Cliente*", 
            options=opciones_clientes,
            index=0,
            key="sb_cliente_venta"
        )
        cliente_seleccionado = dict_clientes.get(cliente_label_sel, "")
        producto_label_sel = st.sidebar.selectbox(
            "📦 Buscar / Seleccionar Producto*",
            options=opciones_productos,
            index=0,
            key="sb_producto_venta"
        )

        info_p = dict_productos.get(producto_label_sel, {})
        producto_seleccionado = info_p.get("nombre", "")
        precio_default = info_p.get("precio", 0.0)
        cuotas_default = info_p.get("cant_cuotas", 1)
        if cuotas_default < 1:
            cuotas_default = 1
        monto_cuota_default = info_p.get("monto_cuota", 0.0)

        with st.sidebar.form("form_registro", clear_on_submit=True):
            vendedor = st.text_input("Vendedor*", value=st.session_state.get("usuario_actual", ""))
            precio_final = st.number_input("Precio Total Venta*", min_value=0.0, value=precio_default, format="%.2f")
            cantidad_cuotas = st.number_input("Cantidad de Cuotas*", min_value=1, value=int(cuotas_default), step=1)
            monto_cuota_input = st.number_input("Monto por Cuota*", min_value=0.0, value=monto_cuota_default, format="%.2f")
            comision = st.number_input("Comisión*", min_value=0.0, format="%.2f")
            
            tipo_pago = st.selectbox("Tipo de Pago*", ["Mensual con entrega", "Mensual sin entrega", "Semanal"])
            estado_input = st.selectbox("Estado*", ["Activo", "Cancelado"])
            
            btn_crear = st.form_submit_button("Generar Venta y Cronograma")
            
            if btn_crear:
                if cliente_label_sel == PLACEHOLDER_CLIENTE or not cliente_seleccionado:
                    st.sidebar.error("❌ Debe seleccionar un cliente registrado válido.")
                elif producto_label_sel == PLACEHOLDER_PRODUCTO or not producto_seleccionado:
                    st.sidebar.error("❌ Debe seleccionar un producto registrado válido.")
                elif vendedor and precio_final > 0 and cantidad_cuotas > 0:
                    try:
                        fecha_actual = datetime.now()
                        
                        if tipo_pago == "Mensual con entrega":
                            cuota_inicial = 1
                            fecha_u_pago = fecha_actual
                        else:
                            cuota_inicial = 0
                            fecha_u_pago = None

                        with engine.begin() as conn:
                            sql_venta = text("""
                                INSERT INTO ventas (producto, cliente, vendedor, precio, total_cuota, monto_cuota, comision, tipo_pago, estado, fecha_creacion, cuota, fecha_ultimo_pago)
                                VALUES (:p, :c, :vend, :pre, :tcuo, :mcuo, :com, :tpago, :est, :fecha, :cuo, :fupago)
                                RETURNING venta_id
                            """)
                            res = conn.execute(sql_venta, {
                                "p": producto_seleccionado, "c": cliente_seleccionado, "vend": vendedor, "pre": precio_final, 
                                "tcuo": cantidad_cuotas, "mcuo": monto_cuota_input, 
                                "com": comision, "tpago": tipo_pago, "est": estado_input, "fecha": fecha_actual,
                                "cuo": cuota_inicial, "fupago": fecha_u_pago
                            })
                            nuevo_id = res.fetchone()[0]

                            conn.execute(text("""
                                UPDATE ecommerce_productos 
                                SET stock = GREATEST(0, stock - 1) 
                                WHERE nombre = :p
                            """), {"p": producto_seleccionado})

                            sql_cuota = text("""
                                INSERT INTO detalle_ventas (venta_id, item_cuota, monto_cuota, monto_pago, saldo_cuota, estado, fecha_vencimiento, fecha_pago)
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

                        st.sidebar.success(f"✅ Venta #{nuevo_id} procesada exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error al procesar la venta: {e}")
                else:
                    st.sidebar.warning("⚠️ Por favor complete todos los campos requeridos.")

    # --- CUERPO PRINCIPAL ---
    st.title("📊 Sistema de Control de Ventas e Ingresos")

    # CONTROL DE CAMBIO DE PESTAÑA: Limpia inmediatamente modales activos si el usuario cambia de tab
    def on_tab_change():
        limpiar_modal_ver()
        limpiar_modal_pago()
        limpiar_modal_eliminar()

    tab_lista, tab_detalles, tab_editar, tab_editar_detalles = st.tabs([
        "📋 Listado de Ventas", 
        "🔍 Ver Detalles de Cuotas", 
        "✏️ Modificar Venta", 
        "💳 Modificar Cuota"
    ])

    # --- PESTAÑA 1: LISTADO GENERAL CON FILTROS Y RESALTADO DE MOROSIDAD ---
    with tab_lista:
        st.subheader("📋 Historial de Ventas")
        if not df_v.empty:
            col_f1, col_f2, col_f3 = st.columns([2, 2, 1.8])
            with col_f1:
                filtro_nombre = st.text_input("🔍 Buscar por producto:", placeholder="Ej: HONOR X7D...")
            with col_f2:
                filtro_cliente = st.text_input("👤 Buscar por cliente:", placeholder="Ej: Juan Pérez...")
            with col_f3:
                filtro_estado = st.selectbox("📌 Estado / Filtro:", ["Activas", "🔴 Atrasados", "Todas", "Canceladas"], index=0)
            
            df_display = df_v.copy()
            hace_un_mes = datetime.now() - timedelta(days=30)

            if 'estado' in df_display.columns:
                if filtro_estado == "Activas":
                    df_display = df_display[df_display['estado'].astype(str).str.strip().str.capitalize() == "Activo"]
                elif filtro_estado == "Canceladas":
                    df_display = df_display[df_display['estado'].astype(str).str.strip().str.capitalize() == "Cancelado"]
                elif filtro_estado == "🔴 Atrasados":
                    cond_activo = df_display['estado'].astype(str).str.strip().str.capitalize() == "Activo"
                    f_pagos_dt = pd.to_datetime(df_display['fecha_ultimo_pago'], errors='coerce')
                    cond_atrasado = (f_pagos_dt < hace_un_mes) & (pd.notnull(f_pagos_dt))
                    df_display = df_display[cond_activo & cond_atrasado]

            if filtro_nombre:
                df_display = df_display[df_display['producto'].str.contains(filtro_nombre, case=False, na=False)]
            if filtro_cliente:
                df_display = df_display[df_display['cliente'].str.contains(filtro_cliente, case=False, na=False)]

            st.write(f"Mostrando **{len(df_display)}** ventas ({filtro_estado}):")

            if df_display.empty:
                st.info(f"No hay ventas que coincidan con el filtro '{filtro_estado}'.")
            else:
                for _, fila in df_display.iterrows():
                    id_v = fila['venta_id']
                    prod_v = fila['producto']
                    cli_v = fila['cliente']
                    precio_v = float(fila['precio']) if pd.notnull(fila['precio']) else 0.0
                    cuota_pagada = int(fila['cuota']) if pd.notnull(fila['cuota']) else 0
                    tot_cuotas = int(fila['total_cuota']) if pd.notnull(fila['total_cuota']) else 1
                    est_v = str(fila['estado']).strip()
                    
                    f_u_pago = pd.to_datetime(fila.get('fecha_ultimo_pago'), errors='coerce')
                    
                    if pd.isnull(f_u_pago):
                        color_border = "#9E9E9E"
                        badge_html = "<span style='background-color: #E0E0E0; color: #424242; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>⚪ NUEVA VENTA</span>"
                        txt_fecha_pago = "Sin pagos registrados"
                    elif f_u_pago < hace_un_mes and est_v.lower() == "activo":
                        color_border = "#FF4B4B"
                        badge_html = "<span style='background-color: #FFCDD2; color: #B71C1C; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔴 ATRASADO (+1 MES)</span>"
                        txt_fecha_pago = f"Último pago: {f_u_pago.strftime('%d/%m/%Y')}"
                    else:
                        color_border = "#2E7D32"
                        badge_html = "<span style='background-color: #C8E6C9; color: #1B5E20; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🟢 AL DÍA</span>"
                        txt_fecha_pago = f"Último pago: {f_u_pago.strftime('%d/%m/%Y')}"

                    st.markdown(f"""
                        <div style="border-left: 6px solid {color_border}; padding: 10px; border-radius: 6px; background-color: rgba(128, 128, 128, 0.05); margin-bottom: 10px;">
                    """, unsafe_allow_html=True)

                    c_info, c_cuotas, c_monto, c_acciones = st.columns([2.5, 1.5, 1.5, 3.5])
                    
                    with c_info:
                        st.markdown(f"**Venta #{id_v}** - {prod_v} &nbsp; {badge_html}", unsafe_allow_html=True)
                        st.caption(f"👤 Cliente: **{cli_v}** | Vendedor: {fila.get('vendedor', '-')}")
                    
                    with c_cuotas:
                        st.markdown(f"**Cuotas:** {cuota_pagada} / {tot_cuotas}")
                        st.caption(f"🗓️ {txt_fecha_pago}")
                    
                    with c_monto:
                        st.markdown(f"**Gs. {precio_v:,.0f}**")
                        st.caption(f"Estado: **{est_v}**")

                    with c_acciones:
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        
                        with btn_col1:
                            if st.button("👁️ Ver", key=f"btn_ver_grid_{id_v}", use_container_width=True):
                                limpiar_modal_pago()
                                limpiar_modal_eliminar()
                                st.session_state.ver_venta_id = id_v
                                st.rerun()

                        with btn_col2:
                            pago_habilitado = (est_v.lower() == "activo" and cuota_pagada < tot_cuotas)
                            if st.button("💳 Pagar", key=f"btn_pago_grid_{id_v}", disabled=not pago_habilitado, type="primary", use_container_width=True):
                                limpiar_modal_ver()
                                limpiar_modal_eliminar()
                                st.session_state.pago_rapido_datos = {
                                    "id": id_v,
                                    "producto": prod_v,
                                    "cliente": cli_v
                                }
                                st.rerun()

                        with btn_col3:
                            if st.button("🗑️", key=f"btn_del_grid_{id_v}", use_container_width=True, help="Eliminar venta completa"):
                                limpiar_modal_ver()
                                limpiar_modal_pago()
                                st.session_state.eliminar_venta_datos = {
                                    "id": id_v,
                                    "producto": prod_v,
                                    "cliente": cli_v
                                }
                                st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

            # --- ACTIVADORES DE DIÁLOGOS CON AUTO-LIMPIEZA ---
            if "ver_venta_id" in st.session_state:
                id_v_active = st.session_state.ver_venta_id
                # Si el usuario hace clic en la "X", eliminamos la clave explícitamente
                st.session_state.pop("ver_venta_id", None)
                dialog_ver_venta_completa(id_v_active)

            elif "pago_rapido_datos" in st.session_state:
                datos_p = st.session_state.pago_rapido_datos
                st.session_state.pop("pago_rapido_datos", None)
                dialog_pago_rapido(datos_p['id'], datos_p['producto'], datos_p['cliente'])

            elif "eliminar_venta_datos" in st.session_state:
                datos_d = st.session_state.eliminar_venta_datos
                st.session_state.pop("eliminar_venta_datos", None)
                dialog_eliminar_venta(datos_d['id'], datos_d['producto'], datos_d['cliente'])

        else:
            st.info("No hay ventas registradas aún.")

    # --- PESTAÑA 2: DETALLES DE CUOTAS ---
    with tab_detalles:
        st.subheader("🔍 Consulta de Detalles y Cobros")
        if not df_v.empty:
            id_sel = st.selectbox("Seleccione ID de Venta:", df_v['venta_id'], key="det_sel")
            df_d = cargar_datos("SELECT * FROM detalle_ventas WHERE venta_id = :id_p ORDER BY item_cuota ASC", params={"id_p": int(id_sel)})
            
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
                            datos_venta = df_v[df_v['venta_id'] == id_sel].iloc[0]
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
                                            WHERE venta_id = :id_p AND item_cuota = :item
                                        """), {"hoy": ahora, "id_p": info['id_p'], "item": info['item']})
                                        
                                        conn.execute(text("""
                                            UPDATE ventas SET cuota = COALESCE(cuota, 0) + 1, fecha_ultimo_pago = :hoy 
                                            WHERE venta_id = :id_p
                                        """), {"hoy": ahora, "id_p": info['id_p']})
                                        
                                        conn.execute(text("""
                                            UPDATE ventas SET estado = 'Cancelado' 
                                            WHERE venta_id = :id_p AND cuota >= total_cuota
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

    # --- PESTAÑA 3: EDICIÓN DE DATOS DE VENTA ---
    with tab_editar:
        st.subheader("✏️ Modificar Información de Venta")
        if not df_v.empty:
            id_edit = st.selectbox("Elija el ID del producto a editar:", df_v['venta_id'], key="edit_sel")
            fila_actual = df_v[df_v['venta_id'] == id_edit].iloc[0]
            obs_actual = str(fila_actual['observacion']) if 'observacion' in fila_actual and pd.notnull(fila_actual['observacion']) else ""
            
            with st.form("form_edicion"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_prod = st.text_input("Producto", value=fila_actual['producto'])
                    
                    lista_nombres = list(dict_clientes.values())
                    if lista_nombres and fila_actual['cliente'] in lista_nombres:
                        idx_cliente_actual = lista_nombres.index(fila_actual['cliente'])
                        nuevo_clie = st.selectbox("Cliente", options=lista_nombres, index=idx_cliente_actual)
                    else:
                        nuevo_clie = st.text_input("Cliente", value=fila_actual['cliente'])
                        
                    nuevo_precio = st.number_input("Precio", value=float(fila_actual['precio'] if fila_actual['precio'] else 0))
                
                with col2:
                    nueva_cuota = st.number_input("Cuota", value=int(fila_actual['cuota']) if pd.notnull(fila_actual['cuota']) else 0, step=1)
                    opciones_est = ["Activo", "Cancelado"]
                    est_db = str(fila_actual['estado']).strip().capitalize()
                    try:
                        idx_est = [opt.lower() for opt in opciones_est].index(est_db.lower())
                    except Exception:
                        idx_est = 0
                    nuevo_est = st.selectbox("Estado", opciones_est, index=idx_est)

                nueva_obs = st.text_input("Observación", value=obs_actual, max_chars=50, help="Máximo 50 caracteres")

                if st.form_submit_button("Guardar Cambios"):
                    sql_update = """
                        UPDATE ventas 
                        SET producto=:p, cliente=:c, precio=:pre, cuota=:cuo, estado=:e, observacion=:obs
                        WHERE venta_id=:id
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
            id_venta_sel = st.selectbox("Seleccione ID de Venta:", df_v['venta_id'], key="edit_det_v")
            df_cuotas = cargar_datos("SELECT * FROM detalle_ventas WHERE venta_id = :id_p ORDER BY item_cuota ASC", params={"id_p": int(id_venta_sel)})
            
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
                            WHERE venta_id=:id_p AND item_cuota=:item
                        """
                        ejecutar_query(sql_upd_det, {
                            "m": monto_c, "p": pago_c, "s": saldo_c, "e": nuevo_est_c, 
                            "fp": f_pago, "fv": f_venc, "id_p": id_venta_sel, "item": id_cuota_sel
                        })
                        st.success(f"✅ Cuota {id_cuota_sel} actualizada con fechas.")
                        st.rerun()