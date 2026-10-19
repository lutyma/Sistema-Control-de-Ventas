import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

# =============================================================================
# 1. TIENDA Y CATÁLOGO E-COMMERCE (Modo Cliente con Botones Azul Claro)
# =============================================================================
def render_ecommerce():
    # --- ESTILOS CSS AVANZADOS ---
    st.markdown("""
        <style>
        .amazon-navbar {
            background-color: #131921;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .amazon-navbar span {
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background 0.2s;
        }
        .amazon-navbar span:hover {
            background-color: #37475A;
        }

        /* Banner principal con degradado Lila y Verde */
        .ecom-hero-banner {
            background: linear-gradient(135deg, #7b1fa2 0%, #2e7d32 100%);
            padding: 25px;
            border-radius: 10px;
            color: white;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        .ecom-hero-banner h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
        }
        .ecom-hero-banner p {
            margin: 5px 0 0 0;
            font-size: 13px;
            color: #e8f5e9;
            font-weight: 500;
        }

        /* FUERZA EL COLOR AZUL CLARO EN BOTONES */
        div.stButton > button, div.stButton > button[kind="primary"] {
            background-color: #0288d1 !important;
            color: #ffffff !important;
            border: 1px solid #0277bd !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            transition: all 0.2s ease-in-out !important;
        }
        div.stButton > button:hover, div.stButton > button[kind="primary"]:hover {
            background-color: #0277bd !important;
            color: #ffffff !important;
            border-color: #01579b !important;
        }
        div.stButton > button * {
            color: #ffffff !important;
        }

        .precio-oferta {
            color: #B12704;
            font-size: 18px;
            font-weight: 700;
        }
        .badge-envio {
            background-color: #007600;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }
        .badge-pedido-cli {
            background-color: #ffa41c;
            color: #111;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- BARRA SUPERIOR ---
    st.markdown("""
        <div class="amazon-navbar">
            <div>🛒 <b>SuperTienda Online</b></div>
            <div style="display: flex; gap: 15px;">
                <span>🔥 Ofertas del Día</span>
                <span>📦 Envíos Rápidos</span>
                <span>⭐ Garantizados</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- BANNER PRINCIPAL ---
    st.markdown("""
        <div class="ecom-hero-banner">
            <h1>Explora por Categorías y Departamentos</h1>
            <p>Encuentra tecnología, electrodomésticos y accesorios organizados para ti.</p>
        </div>
    """, unsafe_allow_html=True)

    # Control de permisos internos (Vendedor/Admin)
    rol_actual = str(st.session_state.get("rol_usuario", "")).lower() if st.session_state.get("autenticado", False) else "cliente"
    es_vendedor_o_admin = rol_actual in ["admin", "vendedor"]

    # Cargar datos de la base de datos
    df_prods = cargar_datos("SELECT * FROM ecommerce_productos WHERE estado = 'Activo' ORDER BY id_producto DESC")

    # Inicializar categoría seleccionada en session_state
    if "categoria_activa" not in st.session_state:
        st.session_state.categoria_activa = "Todas"

    # --- FILTROS Y BUSCADOR ---
    c_search, c_order = st.columns([3, 1])
    with c_search:
        busqueda = st.text_input("🔍 ¿Qué estás buscando hoy?", placeholder="Ej: Parlante, freidora, celular...", key="ecom_search_input")
    with c_order:
        orden = st.selectbox("Ordenar por:", ["Menor Precio Contado", "Mayor Precio Contado", "Nombre A-Z"], key="ecom_order_select")

    # Obtener categorías únicas de la base de datos
    categorias_disponibles = sorted(df_prods['categoria'].dropna().unique().tolist()) if not df_prods.empty and 'categoria' in df_prods.columns else []

    # --- DISEÑO DE SECCIONES CON IMÁGENES Y BOTONES "VER" ---
    if not busqueda and st.session_state.categoria_activa == "Todas" and categorias_disponibles:
        st.markdown("### 🌟 Departamentos Destacados")
        
        imagenes_cat = {
            "Celular": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300&auto=format&fit=crop&q=60",
            "Audio": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&auto=format&fit=crop&q=60",
            "Electrodoméstico": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=300&auto=format&fit=crop&q=60",
            "Calzado": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&auto=format&fit=crop&q=60",
            "Electrónica": "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=300&auto=format&fit=crop&q=60",
            "Informática": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=300&auto=format&fit=crop&q=60"
        }
        
        imagen_default = "https://www.shutterstock.com/shutterstock/photos/2826333763/display_1500/stock-vector-smart-home-technology-icon-collection-featuring-smart-speakers-security-cameras-robotic-devices-2826333763.jpg"

        cols_sec = st.columns(min(len(categorias_disponibles), 4))
        for idx, cat in enumerate(categorias_disponibles):
            col_target = cols_sec[idx % len(cols_sec)]
            img_categoria = imagenes_cat.get(cat, imagen_default)
            
            with col_target:
                with st.container(border=True):
                    st.image(img_categoria, use_container_width=True)
                    st.markdown(f"<p style='text-align: center; font-weight: 600; font-size: 15px; margin: 8px 0;'>{cat}</p>", unsafe_allow_html=True)
                    if st.button(f"Ver {cat}", key=f"btn_cat_{cat}", use_container_width=True, type="primary"):
                        st.session_state.categoria_activa = cat
                        st.rerun()
        st.divider()

    # Botón para volver al catálogo general
    if st.session_state.categoria_activa != "Todas":
        c_vol, _ = st.columns([2, 5])
        with c_vol:
            if st.button("⬅️ Ver Todos los Departamentos", use_container_width=True, type="primary"):
                st.session_state.categoria_activa = "Todas"
                st.rerun()

    # --- FILTRADO DE PRODUCTOS ---
    df_display = df_prods.copy()

    if not df_display.empty:
        if busqueda:
            df_display = df_display[df_display['nombre'].str.contains(busqueda, case=False, na=False)]
        elif st.session_state.categoria_activa != "Todas":
            df_display = df_display[df_display['categoria'] == st.session_state.categoria_activa]

        if orden == "Menor Precio Contado":
            df_display = df_display.sort_values(by="precio", ascending=True)
        elif orden == "Mayor Precio Contado":
            df_display = df_display.sort_values(by="precio", ascending=False)
        elif orden == "Nombre A-Z":
            df_display = df_display.sort_values(by="nombre", ascending=True)

        titulo_seccion = f"Resultados en '{st.session_state.categoria_activa}'" if st.session_state.categoria_activa != "Todas" else "Catálogo General"
        st.markdown(f"### 📦 {titulo_seccion} ({len(df_display)} productos)")

        if df_display.empty:
            st.info("No se encontraron productos en esta sección.")
        else:
            cols_grid = st.columns(3)
            for i, (_, row) in enumerate(df_display.iterrows()):
                col_curr = cols_grid[i % 3]
                with col_curr:
                    with st.container(border=True):
                        img_url = row['imagen_url'] if pd.notnull(row['imagen_url']) and str(row['imagen_url']).startswith("http") else "https://via.placeholder.com/300x200?text=Sin+Imagen"
                        st.image(img_url, use_container_width=True)
                        
                        st.markdown(f"<div style='font-weight: 600; font-size: 15px; min-height: 45px;'>{row['nombre']}</div>", unsafe_allow_html=True)
                        
                        precio = float(row['precio']) if pd.notnull(row['precio']) else 0.0
                        monto_c = float(row['monto_cuota']) if pd.notnull(row['monto_cuota']) else 0.0
                        cant_c = int(row['cant_cuotas']) if pd.notnull(row['cant_cuotas']) else 0

                        st.markdown(f"<span class='precio-oferta'>Gs. {precio:,.0f}</span> <span style='font-size:11px; color:#555;'>(Contado)</span>", unsafe_allow_html=True)
                        
                        if cant_c > 0 and monto_c > 0:
                            st.markdown(f"<span style='font-size: 12px; color: #007185;'>o hasta <b>{cant_c} cuotas</b> de Gs. {monto_c:,.0f}</span>", unsafe_allow_html=True)
                        
                        stock = int(row['stock']) if pd.notnull(row['stock']) else 0
                        tipo_disp = str(row.get('tipo_disponibilidad', 'Stock Propio')).strip()

                        st.write("")
                        if tipo_disp == "Bajo Pedido" or stock == 0:
                            st.markdown("<span class='badge-pedido-cli'>🚚 Disponible Bajo Pedido</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span class='badge-envio'>✔ Stock Disponible</span>", unsafe_allow_html=True)

                        st.divider()

                        # CONTENIDO EXCLUSIVO PARA VENDEDORES Y ADMINS
                        if es_vendedor_o_admin:
                            comision_v = float(row.get('comision_vendedor', 0.0)) if pd.notnull(row.get('comision_vendedor')) else 0.0
                            
                            st.markdown(f"""
                                <div style="background-color: rgba(46, 125, 50, 0.08); padding: 8px; border-radius: 6px; border-left: 4px solid #2E7D32; margin-bottom: 8px;">
                                    <span style="font-weight: bold; font-size: 11px; color: #1B5E20;">💵 COMISIÓN INTERNA:</span><br>
                                    <span style="font-weight: bold; font-size: 13px; color: #2E7D32;">Gs. {comision_v:,.0f}</span>
                                </div>
                            """, unsafe_allow_html=True)

                            if st.button("🛍️ Cargar Venta", key=f"btn_cargar_v_{row['id_producto']}", use_container_width=True, type="primary"):
                                st.session_state.producto_desde_ecom = {
                                    "id_producto": row['id_producto'],
                                    "nombre": row['nombre'],
                                    "precio": precio,
                                    "cant_cuotas": cant_c,
                                    "monto_cuota": monto_c,
                                    "comision": comision_v
                                }
                                st.session_state.redireccionar_a = "📊 Gestión de Ventas"
                                st.rerun()
    else:
        st.info("No hay productos disponibles en el catálogo.")

# =============================================================================
# DIÁLOGO DE ELIMINACIÓN DE PRODUCTO
# =============================================================================
@st.dialog("⚠️ Confirmar Eliminación de Producto")
def dialog_eliminar_producto(id_prod, nombre_prod):
    st.warning(f"¿Está seguro de que desea eliminar el producto **{nombre_prod}** (ID: {id_prod})?")
    st.error("🚨 Esta acción eliminará permanentemente el producto del catálogo.")

    c_conf, c_canc = st.columns(2)
    if c_conf.button("🔥 Sí, Eliminar", use_container_width=True, type="primary"):
        try:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM ecommerce_productos WHERE id_producto = :id"), {"id": id_prod})
            st.success(f"✅ Producto '{nombre_prod}' eliminado correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al eliminar producto: {e}")

    if c_canc.button("❌ Cancelar", use_container_width=True):
        st.rerun()

# =============================================================================
# 2. GESTIÓN DE PRODUCTOS (Paramétrico -> Submódulo)
# =============================================================================
def render_gestion_productos():
    st.title("⚙️ Paramétrico - Gestión de Productos")
    
    tab_nuevo, tab_editar, tab_tabla = st.tabs([
        "➕ Nuevo Producto", 
        "✏️ Modificar Producto",
        "📋 Lista de Productos"
    ])
    
    try:
        df_prods = cargar_datos("SELECT * FROM ecommerce_productos ORDER BY id_producto DESC")
    except Exception:
        df_prods = pd.DataFrame()

    # --- PESTAÑA 1: NUEVO PRODUCTO ---
    with tab_nuevo:
        st.subheader("➕ Registrar Nuevo Producto")
        with st.form("form_alta_producto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del Producto*")
                marca = st.text_input("Marca")
                categoria = st.text_input("Categoría")
                precio = st.number_input("Precio Total Venta*", min_value=0.0, format="%.2f")
                cant_cuotas = st.number_input("Cantidad de Cuotas", min_value=1, value=12, step=1)
                comision_vendedor = st.number_input("Comisión Vendedor (Gs.)*", min_value=0.0, value=0.0, format="%.2f")
            
            with col2:
                monto_cuota = st.number_input("Monto Cuota", min_value=0.0, format="%.2f")
                tipo_disponibilidad = st.selectbox("Modalidad Stock*", ["Stock Propio", "Bajo Pedido"])
                stock = st.number_input("Stock Inicial", min_value=0, value=1, step=1)
                estado = st.selectbox("Estado", ["Activo", "Inactivo"])
                imagen_url = st.text_input("URL Imagen")
                youtube_url = st.text_input("URL Video YouTube")
            
            descripcion = st.text_area("Descripción")
            btn_guardar = st.form_submit_button("Guardar Producto", type="primary")

            if btn_guardar:
                if nombre and precio > 0:
                    try:
                        sql_ins = text("""
                            INSERT INTO ecommerce_productos 
                            (nombre, marca, categoria, precio, cant_cuotas, monto_cuota, stock, estado, imagen_url, youtube_url, descripcion, comision_vendedor, tipo_disponibilidad)
                            VALUES (:n, :m, :c, :p, :cc, :mc, :s, :e, :img, :yt, :d, :com, :disp)
                        """)
                        with engine.begin() as conn:
                            conn.execute(sql_ins, {
                                "n": nombre, "m": marca, "c": categoria, "p": precio,
                                "cc": cant_cuotas, "mc": monto_cuota, "s": stock, "e": estado,
                                "img": imagen_url, "yt": youtube_url, "d": descripcion,
                                "com": comision_vendedor, "disp": tipo_disponibilidad
                            })
                        st.success(f"✅ Producto '{nombre}' registrado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar producto: {e}")
                else:
                    st.warning("⚠️ El nombre y el precio son obligatorios.")

    # --- PESTAÑA 2: MODIFICAR PRODUCTO ---
    with tab_editar:
        st.subheader("✏️ Modificar / Editar Producto")
        if not df_prods.empty:
            mapa_p = {f"{r['id_producto']} - {r['nombre']}": r['id_producto'] for _, r in df_prods.iterrows()}
            prod_sel_label = st.selectbox("Seleccione el producto a editar:", list(mapa_p.keys()))
            id_prod_sel = mapa_p[prod_sel_label]
            
            fila_p = df_prods[df_prods['id_producto'] == id_prod_sel].iloc[0]
            
            with st.form("form_edicion_producto"):
                col1, col2 = st.columns(2)
                with col1:
                    e_nombre = st.text_input("Nombre", value=str(fila_p['nombre']))
                    e_marca = st.text_input("Marca", value=str(fila_p['marca']) if pd.notnull(fila_p['marca']) else "")
                    e_categoria = st.text_input("Categoría", value=str(fila_p['categoria']) if pd.notnull(fila_p['categoria']) else "")
                    e_precio = st.number_input("Precio Total", value=float(fila_p['precio']) if pd.notnull(fila_p['precio']) else 0.0, format="%.2f")
                    e_cant_cuotas = st.number_input("Cantidad Cuotas", value=int(fila_p['cant_cuotas']) if pd.notnull(fila_p['cant_cuotas']) else 1, step=1)
                    e_comision = st.number_input("Comisión Vendedor (Gs.)", value=float(fila_p['comision_vendedor']) if 'comision_vendedor' in fila_p and pd.notnull(fila_p['comision_vendedor']) else 0.0, format="%.2f")
                
                with col2:
                    e_monto_cuota = st.number_input("Monto Cuota", value=float(fila_p['monto_cuota']) if pd.notnull(fila_p['monto_cuota']) else 0.0, format="%.2f")
                    
                    opts_disp = ["Stock Propio", "Bajo Pedido"]
                    val_disp_db = str(fila_p.get('tipo_disponibilidad', 'Stock Propio')).strip()
                    idx_disp = opts_disp.index(val_disp_db) if val_disp_db in opts_disp else 0
                    e_tipo_disp = st.selectbox("Modalidad Stock", opts_disp, index=idx_disp)

                    e_stock = st.number_input("Stock", value=int(fila_p['stock']) if pd.notnull(fila_p['stock']) else 0, step=1)
                    
                    opts_est = ["Activo", "Inactivo"]
                    idx_est = opts_est.index(fila_p['estado']) if 'estado' in fila_p and fila_p['estado'] in opts_est else 0
                    e_estado = st.selectbox("Estado", opts_est, index=idx_est)
                    
                    e_img = st.text_input("URL Imagen", value=str(fila_p['imagen_url']) if pd.notnull(fila_p['imagen_url']) else "")
                    e_yt = st.text_input("URL YouTube", value=str(fila_p['youtube_url']) if pd.notnull(fila_p['youtube_url']) else "")
                
                e_desc = st.text_area("Descripción", value=str(fila_p['descripcion']) if pd.notnull(fila_p['descripcion']) else "")
                btn_actualizar = st.form_submit_button("Actualizar Producto")

                if btn_actualizar:
                    try:
                        sql_upd = text("""
                            UPDATE ecommerce_productos 
                            SET nombre=:n, marca=:m, categoria=:c, precio=:p, cant_cuotas=:cc, 
                                monto_cuota=:mc, stock=:s, estado=:e, imagen_url=:img, youtube_url=:yt, descripcion=:d,
                                comision_vendedor=:com, tipo_disponibilidad=:disp
                            WHERE id_producto=:id
                        """)
                        with engine.begin() as conn:
                            conn.execute(sql_upd, {
                                "n": e_nombre, "m": e_marca, "c": e_categoria, "p": e_precio,
                                "cc": e_cant_cuotas, "mc": e_monto_cuota, "s": e_stock, "e": e_estado,
                                "img": e_img, "yt": e_yt, "d": e_desc, "com": e_comision, "disp": e_tipo_disp, "id": id_prod_sel
                            })
                        st.success(f"✅ Producto ID #{id_prod_sel} actualizado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar producto: {e}")
        else:
            st.info("No hay productos para modificar.")

    # --- PESTAÑA 3: LISTA GENERAL DE PRODUCTOS CON ELIMINACIÓN ---
    with tab_tabla:
        st.subheader("📋 Catálogo de Productos Registrados")
        if not df_prods.empty:
            df_v_activas = cargar_datos("SELECT producto_id, producto FROM ventas WHERE LOWER(TRIM(estado)) = 'activo'")

            for _, row_p in df_prods.iterrows():
                id_p = int(row_p['id_producto']) if pd.notnull(row_p['id_producto']) else 0
                nom_p = str(row_p['nombre']) if pd.notnull(row_p['nombre']) else "-"
                precio_p = float(row_p['precio']) if pd.notnull(row_p['precio']) else 0.0
                stock_p = int(row_p['stock']) if pd.notnull(row_p['stock']) else 0
                com_p = float(row_p['comision_vendedor']) if 'comision_vendedor' in row_p and pd.notnull(row_p['comision_vendedor']) else 0.0
                disp_p = str(row_p.get('tipo_disponibilidad', 'Stock Propio'))
                est_p = str(row_p['estado']) if 'estado' in row_p and pd.notnull(row_p['estado']) else "Activo"

                tiene_venta_activa = False
                cant_ventas_act = 0
                if not df_v_activas.empty:
                    cond_id = (df_v_activas['producto_id'] == id_p) if 'producto_id' in df_v_activas.columns else False
                    cond_nom = (df_v_activas['producto'].astype(str).str.strip().str.lower() == nom_p.strip().lower())
                    ventas_match = df_v_activas[cond_id | cond_nom]
                    cant_ventas_act = len(ventas_match)
                    tiene_venta_activa = cant_ventas_act > 0

                c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
                with c1:
                    st.write(f"**ID:** {id_p}")
                with c2:
                    st.write(f"📦 **{nom_p}**")
                with c3:
                    st.caption(f"💰 Precio: Gs. {precio_p:,.0f} | 💵 Comis: Gs. {com_p:,.0f} | Mod: {disp_p} (Stock: {stock_p})")
                with c4:
                    if tiene_venta_activa:
                        st.button(
                            "🗑️", 
                            key=f"btn_del_prod_{id_p}", 
                            disabled=True, 
                            help=f"No se puede eliminar: está asociado a {cant_ventas_act} venta(s) activa(s)."
                        )
                    else:
                        if st.button("🗑️", key=f"btn_del_prod_{id_p}", help="Eliminar producto"):
                            dialog_eliminar_producto(id_p, nom_p)

                st.divider()
        else:
            st.info("No hay productos registrados en la base de datos.")