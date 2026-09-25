import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos, engine
from sqlalchemy import text

# =============================================================================
# 1. TIENDA Y CATÁLOGO E-COMMERCE (Módulo Principal)
# =============================================================================
def render_ecommerce():
    st.title("🛒 Tienda E-Commerce")

    c_search, c_order = st.columns([3, 1])
    with c_search:
        busqueda = st.text_input("🔍 Buscar producto...", placeholder="Ej: Parlante JBL, Honor...", key="ecom_search_input")
    with c_order:
        orden = st.selectbox("Ordenar por:", ["Menor Precio Contado", "Mayor Precio Contado", "Nombre A-Z"], key="ecom_order_select")

    st.divider()

    col_filtros, col_productos = st.columns([1, 3])

    df_prods = cargar_datos("SELECT * FROM ecommerce_productos WHERE estado = 'Activo' ORDER BY id_producto DESC")

    with col_filtros:
        st.markdown("### 🎛️ Filtros")
        
        categorias_disponibles = ["Todas"] + sorted(df_prods['categoria'].dropna().unique().tolist()) if not df_prods.empty and 'categoria' in df_prods.columns else ["Todas"]
        cat_sel = st.selectbox("Categoría:", categorias_disponibles)

        if not df_prods.empty and 'marca' in df_prods.columns:
            marcas_disponibles = ["Todas"] + sorted(df_prods['marca'].dropna().unique().tolist())
            marca_sel = st.selectbox("Marca:", marcas_disponibles)
        else:
            marca_sel = "Todas"

    with col_productos:
        df_display = df_prods.copy()

        if not df_display.empty:
            # Aplicar filtros
            if busqueda:
                df_display = df_display[df_display['nombre'].str.contains(busqueda, case=False, na=False)]
            if cat_sel != "Todas":
                df_display = df_display[df_display['categoria'] == cat_sel]
            if marca_sel != "Todas":
                df_display = df_display[df_display['marca'] == marca_sel]

            # Ordenamiento
            if orden == "Menor Precio Contado":
                df_display = df_display.sort_values(by="precio", ascending=True)
            elif orden == "Mayor Precio Contado":
                df_display = df_display.sort_values(by="precio", ascending=False)
            elif orden == "Nombre A-Z":
                df_display = df_display.sort_values(by="nombre", ascending=True)

            st.write(f"Showing **{len(df_display)}** productos:")

            # Renderizado de Tarjetas de Productos
            cols_grid = st.columns(3)
            for i, (_, row) in enumerate(df_display.iterrows()):
                col_curr = cols_grid[i % 3]
                with col_curr:
                    with st.container(border=True):
                        img_url = row['imagen_url'] if pd.notnull(row['imagen_url']) and str(row['imagen_url']).startswith("http") else "https://via.placeholder.com/300x200?text=Sin+Imagen"
                        #st.image(img_url, use_column_width=True)
                        # ✅ LÍNEA CORREGIDA
                        st.image(img_url, use_container_width=True)
                        st.markdown(f"**{row['nombre']}**")
                        
                        precio = float(row['precio']) if pd.notnull(row['precio']) else 0.0
                        monto_c = float(row['monto_cuota']) if pd.notnull(row['monto_cuota']) else 0.0
                        cant_c = int(row['cant_cuotas']) if pd.notnull(row['cant_cuotas']) else 0

                        st.markdown(f"💰 **Gs. {precio:,.0f}** (Contado)")
                        if cant_c > 0 and monto_c > 0:
                            st.caption(f"🗓️ {cant_c} cuotas de Gs. {monto_c:,.0f}")
                        
                        stock = int(row['stock']) if pd.notnull(row['stock']) else 0
                        if stock > 0:
                            st.caption(f"✅ Stock: {stock}")
                        else:
                            st.caption("❌ Agotado")
        else:
            st.info("No hay productos disponibles en el catálogo.")


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
    
    # Cargar datos actualizados de productos
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
                precio = st.number_input("Precio Total*", min_value=0.0, format="%.2f")
                cant_cuotas = st.number_input("Cantidad de Cuotas", min_value=1, value=12, step=1)
            with col2:
                monto_cuota = st.number_input("Monto Cuota", min_value=0.0, format="%.2f")
                stock = st.number_input("Stock Inicial*", min_value=0, value=1, step=1)
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
                            (nombre, marca, categoria, precio, cant_cuotas, monto_cuota, stock, estado, imagen_url, youtube_url, descripcion)
                            VALUES (:n, :m, :c, :p, :cc, :mc, :s, :e, :img, :yt, :d)
                        """)
                        with engine.begin() as conn:
                            conn.execute(sql_ins, {
                                "n": nombre, "m": marca, "c": categoria, "p": precio,
                                "cc": cant_cuotas, "mc": monto_cuota, "s": stock, "e": estado,
                                "img": imagen_url, "yt": youtube_url, "d": descripcion
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
                with col2:
                    e_monto_cuota = st.number_input("Monto Cuota", value=float(fila_p['monto_cuota']) if pd.notnull(fila_p['monto_cuota']) else 0.0, format="%.2f")
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
                                monto_cuota=:mc, stock=:s, estado=:e, imagen_url=:img, youtube_url=:yt, descripcion=:d
                            WHERE id_producto=:id
                        """)
                        with engine.begin() as conn:
                            conn.execute(sql_upd, {
                                "n": e_nombre, "m": e_marca, "c": e_categoria, "p": e_precio,
                                "cc": e_cant_cuotas, "mc": e_monto_cuota, "s": e_stock, "e": e_estado,
                                "img": e_img, "yt": e_yt, "d": e_desc, "id": id_prod_sel
                            })
                        st.success(f"✅ Producto ID #{id_prod_sel} actualizado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar producto: {e}")
        else:
            st.info("No hay productos para modificar.")

    # --- PESTAÑA 3: LISTA GENERAL DE PRODUCTOS ---
    with tab_tabla:
        st.subheader("📋 Catálogo de Productos Registrados")
        if not df_prods.empty:
            st.dataframe(df_prods, use_container_width=True)
        else:
            st.info("No hay productos registrados en la base de datos.")