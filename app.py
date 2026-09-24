import streamlit as st
import pandas as pd
import urllib.parse
from sqlalchemy import create_engine, text
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Gestión de Ventas y Cuotas", layout="wide")

# --- ESTILO PARA OCULTAR MENÚS (Pegar aquí) ---
st.markdown("""
    <style>
    /* 1. Ocultar el menú superior y el encabezado */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 2. Ocultar el botón flotante azul de la esquina inferior derecha (Toolbar) */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    /* 3. Ocultar botones de 'Manage app' y badges de Streamlit Cloud */
    .stAppDeployButton {
        display: none !important;
    }
    
    /* 4. Selector de fuerza bruta para cualquier elemento flotante en las esquinas */
    div[class^="viewerBadge"], div[class*="viewerBadge"] {
        display: none !important;
    }
    
    /* 5. Quitar el espacio extra del footer y el widget de estado */
    .stApp > footer {
        display: none !important;
    }
    
    /* 6. Ajuste opcional: subir un poco el contenido para aprovechar el espacio */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Obtener la URL desde los secretos de Streamlit
# Si no existe en secrets, fallará con un error descriptivo
try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
    # Nota: Neon requiere sslmode=require, asegúrate de que la URL en secrets la incluya
    engine = create_engine(DATABASE_URL)
# engine = create_engine('postgresql://postgres:postgres@localhost:5432/productos')
except Exception as e:
    st.error("No se pudo encontrar la configuración de la base de datos en Secrets.")
    st.stop()

def ejecutar_query(query, params=None):
    """Ejecuta comandos INSERT, UPDATE, DELETE"""
    with engine.begin() as conn:
        conn.execute(text(query), params)

def cargar_datos(query, params=None):
    """Ejecuta consultas SELECT y devuelve un DataFrame"""
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

import urllib.parse

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
    
# --- NUEVO: FUNCIÓN DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = None

    if not st.session_state.autenticado:
        st.title("🔐 Acceso al Sistema")
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                # Traemos todas las credenciales de Secrets
                creds = st.secrets["credentials"]
                
                # Validamos si el usuario existe y si la clave coincide
                if usuario in creds and clave == str(creds[usuario]):
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario # Guardamos quién entró
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

# --- USO DE LA FUNCIÓN ---
    # Aquí sigue el resto de tu aplicación...

# def login():
#     if "autenticado" not in st.session_state:
#         st.session_state.autenticado = False

#     if not st.session_state.autenticado:
#         st.title("🔐 Acceso al Sistema")
#         with st.form("login_form"):
#             usuario = st.text_input("Usuario")
#             clave = st.text_input("Contraseña", type="password")
#             submit = st.form_submit_button("Entrar")
            
#             if submit:
#                 # AQUÍ defines tu usuario y contraseña
#                 if usuario == "admin" and clave == "admin":
#                     st.session_state.autenticado = True
#                     st.rerun()
#                 else:
#                     st.error("Usuario o contraseña incorrectos")
#         return False
#     return True

# --- LÓGICA DE CONTROL ---
if login():
    # Mostrar quién está logueado en el sidebar
    st.sidebar.write(f"👤 Usuario: **{st.session_state.usuario_actual}**")
    
    if st.sidebar.button("Log out"):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.rerun()


    # --- 2. BARRA LATERAL: REGISTRO CON LÓGICA DE CRONOGRAMA ---
    st.sidebar.header("🆕 Registrar Nueva Venta")
    with st.sidebar.form("form_registro", clear_on_submit=True):
        producto = st.text_input("Producto*")
        cliente = st.text_input("Cliente*")
        
        # NUEVO: Campo Vendedor
        vendedor = st.text_input("Vendedor*")
        
        precio = st.number_input("Precio Total*", min_value=0.0, format="%.2f")
        cantidad_cuotas = st.number_input("Cantidad de Cuotas*", min_value=1, step=1)
        monto_cuota_input = st.number_input("Monto por Cuota*", min_value=0.0, format="%.2f")
        comision = st.number_input("Comisión*", min_value=0.0, format="%.2f")
        
        tipo_pago = st.selectbox("Tipo de Pago*", [
            "Mensual con entrega", 
            "Mensual sin entrega", 
            "Semanal"
        ])
        estado_input = st.selectbox("Estado*", ["Activo", "Cancelado"])
        
        btn_crear = st.form_submit_button("Generar Venta y Cronograma")
        
        if btn_crear:
            # Validamos que 'vendedor' también tenga contenido
            if producto and cliente and vendedor and precio > 0 and cantidad_cuotas > 0:
                try:
                    with engine.begin() as conn:
                        # 1. Insertar Cabecera de Venta (Agregamos :vend y la columna vendedor)
                        sql_venta = text("""
                            INSERT INTO ventas (producto, cliente, vendedor, precio, total_cuota, monto_cuota, comision, tipo_pago, estado, fecha_creacion)
                            VALUES (:p, :c, :vend, :pre, :tcuo, :mcuo, :com, :tpago, :est, :fecha)
                            RETURNING id_producto
                        """)
                        
                        fecha_actual = datetime.now()
                        res = conn.execute(sql_venta, {
                            "p": producto, 
                            "c": cliente, 
                            "vend": vendedor, # Enviamos el valor del nuevo input
                            "pre": precio, 
                            "tcuo": cantidad_cuotas,
                            "mcuo": monto_cuota_input, 
                            "com": comision, 
                            "tpago": tipo_pago,
                            "est": estado_input, 
                            "fecha": fecha_actual
                        })
                        nuevo_id = res.fetchone()[0]

                        # 2. Lógica de Generación de Cuotas (Se mantiene igual)
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
                                "id_p": nuevo_id,
                                "item": i,
                                "monto": monto_cuota_input,
                                "pago": monto_pagado,
                                "saldo": saldo,
                                "est_c": estado_cuota,
                                "fv": vencimiento,
                                "fp": pago
                            })

                    st.sidebar.success(f"✅ Venta #{nuevo_id} y cronograma {tipo_pago} generados.")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
            else:
                # Mensaje de advertencia si falta el vendedor u otros campos
                st.sidebar.warning("⚠️ Por favor rellene todos los campos obligatorios (*), incluyendo el Vendedor.")

    # --- 3. CUERPO PRINCIPAL ---
    st.title("📊 Sistema de Control de Ventas e Ingresos")

    tab_lista, tab_detalles, tab_editar, tab_editar_detalles = st.tabs([
        "📋 Listado de Ventas", "🔍 Ver Detalles de Cuotas", "✏️ Modificar Venta", "💳 Modificar Cuota"
    ])


   # --- PESTAÑA 1: LISTADO GENERAL ---
    with tab_lista:
        st.subheader("📋 Historial de Ventas")
        
        df_v = cargar_datos("SELECT * FROM ventas ORDER BY id_producto DESC")
        
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

            # --- CONFIGURACIÓN DE FORMATOS ---
            
            # 1. Formatear Fecha (NUEVO)
            if 'fecha_ultimo_pago' in df_display.columns:
                # Aseguramos que Pandas lo reconozca como fecha
                df_display['fecha_ultimo_pago'] = pd.to_datetime(df_display['fecha_ultimo_pago'], errors='coerce')

            # 2. Formatear Números Enteros
            columnas_enteras = ["cuota", "total_cuota"]
            for col in columnas_enteras:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).astype(int)

            # 3. Definir Diccionario de Formatos
            formatos = {}
            
            # Formato Dinero
            cols_dinero = ["monto_total", "precio", "monto_cuota", "comision"]
            for col in cols_dinero:
                if col in df_display.columns:
                    formatos[col] = "{:,.2f}"
            
            # Formato Enteros
            for col in columnas_enteras:
                if col in df_display.columns:
                    formatos[col] = "{:d}"

            # Formato Fecha (NUEVO): Día/Mes/Año Hora:Minuto
            if 'fecha_ultimo_pago' in df_display.columns:
                formatos['fecha_ultimo_pago'] = lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else "-"

            # --- MOSTRAR LA TABLA ---
            if not df_display.empty:
                st.write(f"Mostrando {len(df_display)} registros:")
                # Agregamos na_rep="-" para que cualquier otro valor nulo se vea como un guion
                st.dataframe(df_display.style.format(formatos, na_rep="-"), use_container_width=True)
            else:
                st.warning(f"No se encontraron resultados para los filtros aplicados.")
                
        else:
            st.info("No hay ventas registradas aún.")

    # --- PESTAÑA 2: DETALLES DE CUOTAS (MAESTRO-DETALLE) ---
    with tab_detalles:
        st.subheader("🔍 Consulta de Detalles y Cobros")
        if not df_v.empty:
            id_sel = st.selectbox("Seleccione ID de Venta:", df_v['id_producto'], key="det_sel")
            
            # Cargamos los datos de los detalles
            query_det = "SELECT * FROM detalle_ventas WHERE producto_id = :id_p ORDER BY item_cuota ASC"
            df_d = cargar_datos(query_det, params={"id_p": int(id_sel)})
            
            if not df_d.empty:
                st.write(f"### Detalles de la Venta #{id_sel}")
                
                # Limpieza de nulos
                columnas_num = ["saldo_cuota", "monto_pago", "monto_cuota"]
                for col in columnas_num:
                    if col in df_d.columns:
                        df_d[col] = pd.to_numeric(df_d[col], errors='coerce').fillna(0.0)

                # Visualización de la tabla
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
                        if st.button(f"Pagar Cuota {int(fila['item_cuota'])}", 
                                    key=f"btn_pagar_{id_sel}_{fila['item_cuota']}", 
                                    disabled=not esta_activo):
                            #Buscamos los datos del producto y cliente en el DataFrame de ventas (df_v)
                            datos_venta = df_v[df_v['id_producto'] == id_sel].iloc[0]
                            st.session_state.cuota_a_pagar = {
                                "id_p": id_sel,
                                "item": fila['item_cuota'],
                                "monto": fila['monto_cuota'],
                                "producto": datos_venta['producto'], # Guardamos el nombre del producto
                                "cliente": datos_venta['cliente']    # Guardamos el nombre del cliente
                            }

                # --- MODAL DE CONFIRMACIÓN ACTUALIZADO ---
                if "cuota_a_pagar" in st.session_state:
                    info = st.session_state.cuota_a_pagar
                    
                    @st.dialog("¿Confirmar pago de cuota?")
                    def confirmar_pago():
                        # Verificamos si ya se procesó el pago en esta sesión de diálogo
                        if "pago_exitoso" not in st.session_state:
                            st.session_state.pago_exitoso = False

                        if not st.session_state.pago_exitoso:
                            st.warning(f"Se registrará el pago de la Cuota {int(info['item'])} para la Venta #{info['id_p']}.")
                            c_si, c_no = st.columns(2)
                            
                            if c_si.button("SÍ, confirmar", use_container_width=True, type="primary"):
                                try:
                                    ahora = datetime.now()
                                    with engine.begin() as conn:
                                        # 1. Actualizar detalle
                                        conn.execute(text("""
                                            UPDATE detalle_ventas SET monto_pago = monto_cuota, saldo_cuota = 0, 
                                            estado = 'Cancelado', fecha_pago = :hoy 
                                            WHERE producto_id = :id_p AND item_cuota = :item
                                        """), {"hoy": ahora, "id_p": info['id_p'], "item": info['item']})
                                        
                                        # 2. Contador y Fecha último pago
                                        conn.execute(text("""
                                            UPDATE ventas SET cuota = COALESCE(cuota, 0) + 1, fecha_ultimo_pago = :hoy 
                                            WHERE id_producto = :id_p
                                        """), {"hoy": ahora, "id_p": info['id_p']})
                                        
                                        # 3. Check final
                                        conn.execute(text("""
                                            UPDATE ventas SET estado = 'Cancelado' 
                                            WHERE id_producto = :id_p AND cuota >= total_cuota
                                        """), {"id_p": info['id_p']})

                                    st.session_state.pago_exitoso = True
                                    st.rerun() # Refrescamos para mostrar el botón de WhatsApp

                                except Exception as e:
                                    st.error(f"Error al procesar el pago: {e}")
                            
                            if c_no.button("NO, cancelar", use_container_width=True):
                                del st.session_state.cuota_a_pagar
                                st.rerun()
                        else:
                            # ESTADO: PAGO YA REALIZADO, MOSTRAR WHATSAPP Y CIERRE
                            st.success(f"✅ ¡Pago procesado con éxito por {st.session_state.usuario_actual}!")
                            
                            # link = generar_link_whatsapp(
                            #     st.session_state.usuario_actual, 
                            #     int(info['item']), 
                            #     info['id_p']
                            # )

                            # --- Línea 416 aproximadamente ---
                            link = generar_link_whatsapp(
                                st.session_state.usuario_actual, 
                                int(info['item']), 
                                info['id_p'],
                                info['producto'],  # <--- Agregamos este
                                info['cliente']    # <--- Agregamos este
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
                                # Limpiamos estados antes de cerrar
                                del st.session_state.cuota_a_pagar
                                del st.session_state.pago_exitoso
                                st.rerun()

                    confirmar_pago()

    # --- PESTAÑA 3: EDICIÓN DE DATOS (CABECERA) ---
    with tab_editar:
        st.subheader("✏️ Modificar Información de Venta")
        if not df_v.empty:
            id_edit = st.selectbox("Elija el ID del producto a editar:", df_v['id_producto'], key="edit_sel")
            
            # Obtenemos la fila actual para precargar los datos
            fila_actual = df_v[df_v['id_producto'] == id_edit].iloc[0]

            # Precargar el valor actual de 'observacion' si existe en el DataFrame
            obs_actual = str(fila_actual['observacion']) if 'observacion' in fila_actual and pd.notnull(fila_actual['observacion']) else ""
            
            with st.form("form_edicion"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_prod = st.text_input("Producto", value=fila_actual['producto'])
                    nuevo_clie = st.text_input("Cliente", value=fila_actual['cliente'])
                    nuevo_precio = st.number_input("Precio", value=float(fila_actual['precio'] if fila_actual['precio'] else 0))
                
                with col2:
                    # AGREGAMOS EL CAMPO CUOTA (como entero, sin decimales)
                    nueva_cuota = st.number_input("Cuota", 
                                                value=int(fila_actual['cuota']) if pd.notnull(fila_actual['cuota']) else 0,
                                                step=1)
                    
                    # Lógica No Case Sensitive para el estado
                    opciones_est = ["Activo", "Cancelado"]
                    est_db = str(fila_actual['estado']).strip().capitalize()
                    try:
                        idx_est = [opt.lower() for opt in opciones_est].index(est_db.lower())
                    except:
                        idx_est = 0
                    
                    nuevo_est = st.selectbox("Estado", opciones_est, index=idx_est)

                # NUEVO CAMPO: Observación (fuera de las columnas para ocupar todo el ancho, o donde prefieras)
                nueva_obs = st.text_input("Observación", value=obs_actual, max_chars=50, help="Máximo 50 caracteres")

                if st.form_submit_button("Guardar Cambios"):
                    # Actualizamos la SQL incluyendo el campo cuota
                    sql_update = """
                        UPDATE ventas 
                        SET producto=:p, cliente=:c, precio=:pre, cuota=:cuo, estado=:e, observacion=:obs
                        WHERE id_producto=:id
                    """
                    ejecutar_query(sql_update, {
                        "p": nuevo_prod, 
                        "c": nuevo_clie, 
                        "pre": nuevo_precio, 
                        "cuo": nueva_cuota, # <-- Nuevo valor
                        "e": nuevo_est, 
                        "obs": nueva_obs,
                        "id": id_edit
                    })
                    st.success(f"✅ Venta #{id_edit} actualizada correctamente")
                    st.rerun()
        else:
            st.info("No hay datos disponibles para editar.")



    # --- PESTAÑA 4: EDICIÓN DE DETALLES (CUOTAS) ---
    with tab_editar_detalles:
        st.subheader("💳 Modificar Detalle de Cuota Individual")
        if not df_v.empty:
            id_venta_sel = st.selectbox("Seleccione ID de Venta:", df_v['id_producto'], key="edit_det_v")
            
            # Cargamos las cuotas incluyendo las nuevas columnas de fecha
            df_cuotas = cargar_datos("SELECT * FROM detalle_ventas WHERE producto_id = :id_p ORDER BY item_cuota ASC", 
                                    params={"id_p": int(id_venta_sel)})
            
            if not df_cuotas.empty:
                id_cuota_sel = st.selectbox("Seleccione el N° de Cuota a editar:", 
                                            df_cuotas['item_cuota'], 
                                            key="edit_cuota_sel")
                
                fila_cuota = df_cuotas[df_cuotas['item_cuota'] == id_cuota_sel].iloc[0]
                
                with st.form("form_edicion_cuota"):
                    c1, c2 = st.columns(2)
                    with c1:
                        monto_c = st.number_input("Monto Cuota", value=float(fila_cuota['monto_cuota']))
                        pago_c = st.number_input("Monto Pago", value=float(fila_cuota['monto_pago'] if fila_cuota['monto_pago'] else 0))
                        # Campo Fecha de Vencimiento
                        f_venc = st.date_input("Fecha de Vencimiento", 
                                            value=pd.to_datetime(fila_cuota['fecha_vencimiento']).date() if pd.notnull(fila_cuota['fecha_vencimiento']) else datetime.now().date())
                    
                    with c2:
                        saldo_c = st.number_input("Saldo Cuota", value=float(fila_cuota['saldo_cuota']))
                        # Campo Fecha de Pago (se activa cuando el cliente paga)
                        f_pago = st.date_input("Fecha de Pago", 
                                            value=pd.to_datetime(fila_cuota['fecha_pago']).date() if pd.notnull(fila_cuota['fecha_pago']) else None)
                        
                        opciones_est_c = ["Activo", "Cancelado"]
                        est_c_db = str(fila_cuota['estado']).strip().capitalize()
                        idx_c = opciones_est_c.index(est_c_db) if est_c_db in opciones_est_c else 0
                        nuevo_est_c = st.selectbox("Estado Cuota", opciones_est_c, index=idx_c)

                    if st.form_submit_button("Actualizar Cuota"):
                        # Consulta SQL actualizada con las fechas
                        sql_upd_det = """
                            UPDATE detalle_ventas 
                            SET monto_cuota=:m, monto_pago=:p, saldo_cuota=:s, 
                                estado=:e, fecha_pago=:fp, fecha_vencimiento=:fv
                            WHERE producto_id=:id_p AND item_cuota=:item
                        """
                        ejecutar_query(sql_upd_det, {
                            "m": monto_c, 
                            "p": pago_c, 
                            "s": saldo_c, 
                            "e": nuevo_est_c, 
                            "fp": f_pago, 
                            "fv": f_venc,
                            "id_p": id_venta_sel, 
                            "item": id_cuota_sel
                        })
                        st.success(f"✅ Cuota {id_cuota_sel} actualizada con fechas.")
                        st.rerun()
            else:
                st.warning("Esta venta no tiene cuotas registradas.")
        else:
            st.info("No hay ventas disponibles.")