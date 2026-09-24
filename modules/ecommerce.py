import streamlit as st
import pandas as pd
from database.connection import ejecutar_query, cargar_datos

def render_ecommerce():
    st.title("🛒 Tienda E-Commerce")
    
    tab_tienda, tab_catalogo_admin, tab_nuevo, tab_editar = st.tabs([
        "🛍️ Catálogo / Tienda", "📋 Gestión (Tabla)", "➕ Nuevo Producto", "✏️ Modificar Producto"
    ])
    
    # --- TAB 1: TIENDA VISUAL CON DEMOSTRACIÓN EN YOUTUBE ---
    with tab_tienda:
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
            categorias_disponibles = ["Todas"] + sorted(df_prods['categoria'].dropna().unique().tolist()) if not df_prods.empty else ["Todas"]
            cat_sel = st.selectbox("Categoría:", categorias_disponibles)

            if 'marca' in df_prods.columns:
                marcas_disponibles = ["Todas"] + sorted(df_prods['marca'].dropna().unique().tolist()) if not df_prods.empty else ["Todas"]
                marca_sel = st.selectbox("Marca:", marcas_disponibles)
            else:
                marca_sel = "Todas"

        with col_productos:
            df_filtrado = df_prods.copy()
            if not df_filtrado.empty:
                if busqueda:
                    df_filtrado = df_filtrado[df_filtrado['nombre'].str.contains(busqueda, case=False, na=False)]
                if cat_sel != "Todas":
                    df_filtrado = df_filtrado[df_filtrado['categoria'] == cat_sel]
                if marca_sel != "Todas" and 'marca' in df_filtrado.columns:
                    df_filtrado = df_filtrado[df_filtrado['marca'] == marca_sel]

                if orden == "Menor Precio Contado":
                    df_filtrado = df_filtrado.sort_values(by="precio", ascending=True)
                elif orden == "Mayor Precio Contado":
                    df_filtrado = df_filtrado.sort_values(by="precio", ascending=False)
                elif orden == "Nombre A-Z":
                    df_filtrado = df_filtrado.sort_values(by="nombre", ascending=True)

                st.markdown(f"**Resultados encontrados:** {len(df_filtrado)}")

                # Cuadrícula de 3 columnas
                cols_grid = st.columns(3)
                for idx, prod in df_filtrado.reset_index(drop=True).iterrows():
                    col_idx = idx % 3
                    with cols_grid[col_idx]:
                        with st.container(border=True):
                            img_url = prod['imagen_url'] if ('imagen_url' in prod and pd.notnull(prod['imagen_url']) and str(prod['imagen_url']).strip() != "") else "https://via.placeholder.com/200x200?text=Sin+Imagen"
                            
                            # Mostrar imagen principal del producto
                            st.image(img_url, use_container_width=True)
                            
                            st.markdown(f"**{prod['nombre']}**")
                            st.caption(f"Categoría: {prod.get('categoria', 'N/A')}")
                            
                            # Formato de Precios
                            precio_contado = f"Gs. {prod['precio']:,.0f}".replace(",", ".")
                            st.markdown(f"**Contado:** {precio_contado}")
                            
                            # Cuotas
                            cant_c = int(prod.get('cant_cuotas', 0) or 0)
                            monto_c = float(prod.get('monto_cuota', 0) or 0)
                            if cant_c > 0 and monto_c > 0:
                                cuota_fmt = f"Gs. {monto_c:,.0f}".replace(",", ".")
                                st.markdown(f"💳 **{cant_c} cuotas de {cuota_fmt}**")
                            else:
                                st.caption("Solo pago al contado")
                            
                            # --- SECCIÓN DEMOSTRACIÓN EN YOUTUBE ---
                            yt_link = prod.get('youtube_url') if 'youtube_url' in prod else None
                            if yt_link and pd.notnull(yt_link) and str(yt_link).strip() != "":
                                with st.expander("▶️ Ver Demostración (YouTube)"):
                                    st.video(str(yt_link).strip())
                            
                            st.button("🛒 Agregar", key=f"btn_prod_{prod['id_producto']}", use_container_width=True)
            else:
                st.info("No se encontraron productos que coincidan con la búsqueda.")

    # --- TAB 2: VISTA TABLA (ADMINISTRACIÓN) ---
    with tab_catalogo_admin:
        st.subheader("📋 Inventario Completo")
        df_all = cargar_datos("SELECT * FROM ecommerce_productos ORDER BY id_producto DESC")
        if not df_all.empty:
            formatos = {
                "precio": "Gs. {:,.0f}",
                "monto_cuota": "Gs. {:,.0f}",
                "stock": "{:d}"
            }
            st.dataframe(df_all.style.format(formatos, na_rep="-"), use_container_width=True)
        else:
            st.info("No hay productos cargados.")

    # --- TAB 3: NUEVO PRODUCTO CON CUOTAS Y YOUTUBE ---
    with tab_nuevo:
        st.subheader("➕ Agregar Producto al Catálogo")
        with st.form("form_nuevo_ecom", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto*")
            
            col_a, col_b = st.columns(2)
            with col_a:
                marca = st.text_input("Marca (Ej: JBL, Honor, HP)")
                categoria = st.text_input("Categoría (Ej: Audio, Electrónica)")
                precio_contado = st.number_input("Precio al Contado (Gs.)*", min_value=0.0, step=5000.0)
            
            with col_b:
                cant_cuotas = st.number_input("Cantidad de Cuotas", min_value=0, step=1, value=0)
                monto_cuota = st.number_input("Monto por Cuota (Gs.)", min_value=0.0, step=5000.0, value=0.0)
                stock = st.number_input("Stock Inicial*", min_value=0, step=1)
            
            imagen_url = st.text_input("URL de la Imagen (Ej: https://.../imagen.jpg)")
            youtube_url = st.text_input("URL de Demostración en YouTube (Ej: https://www.youtube.com/watch?v=...)")
            estado = st.selectbox("Estado", ["Activo", "Inactivo"])
            descripcion = st.text_area("Descripción")
            
            if st.form_submit_button("Guardar Producto"):
                if nombre and precio_contado >= 0:
                    try:
                        sql = """
                            INSERT INTO ecommerce_productos (nombre, marca, categoria, precio, cant_cuotas, monto_cuota, stock, estado, imagen_url, youtube_url, descripcion)
                            VALUES (:nom, :mar, :cat, :pre, :cant_c, :monto_c, :stk, :est, :img, :yt, :desc)
                        """
                        ejecutar_query(sql, {
                            "nom": nombre, "mar": marca, "cat": categoria, "pre": precio_contado,
                            "cant_c": cant_cuotas, "monto_c": monto_cuota, "stk": stock,
                            "est": estado, "img": imagen_url, "yt": youtube_url, "desc": descripcion
                        })
                        st.success("✅ Producto agregado correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")
                else:
                    st.warning("⚠️ Rellene los campos obligatorios (*)")

    # --- TAB 4: EDITAR PRODUCTO, CUOTAS Y YOUTUBE ---
    with tab_editar:
        st.subheader("✏️ Modificar Producto")
        df_edit = cargar_datos("SELECT * FROM ecommerce_productos ORDER BY id_producto DESC")
        if not df_edit.empty:
            id_prod_sel = st.selectbox("Seleccione ID del Producto:", df_edit['id_producto'], key="sel_ecom_edit_tab")
            fila = df_edit[df_edit['id_producto'] == id_prod_sel].iloc[0]
            
            with st.form("form_edit_ecom_full"):
                e_nombre = st.text_input("Nombre", value=fila['nombre'])
                
                c1, c2 = st.columns(2)
                with c1:
                    e_marca = st.text_input("Marca", value=fila['marca'] if pd.notnull(fila.get('marca')) else "")
                    e_cat = st.text_input("Categoría", value=fila['categoria'] if pd.notnull(fila['categoria']) else "")
                    e_precio = st.number_input("Precio al Contado (Gs.)", value=float(fila['precio']))
                
                with c2:
                    e_cant_c = st.number_input("Cantidad de Cuotas", value=int(fila.get('cant_cuotas', 0) or 0), step=1)
                    e_monto_c = st.number_input("Monto por Cuota (Gs.)", value=float(fila.get('monto_cuota', 0) or 0), step=5000.0)
                    e_stock = st.number_input("Stock", value=int(fila['stock']), step=1)
                
                e_img = st.text_input("URL Imagen", value=fila['imagen_url'] if pd.notnull(fila.get('imagen_url')) else "")
                e_yt = st.text_input("URL YouTube", value=fila['youtube_url'] if 'youtube_url' in fila and pd.notnull(fila.get('youtube_url')) else "")
                e_estado = st.selectbox("Estado", ["Activo", "Inactivo"], index=0 if fila['estado'] == "Activo" else 1)
                e_desc = st.text_area("Descripción", value=fila['descripcion'] if pd.notnull(fila['descripcion']) else "")
                
                if st.form_submit_button("Actualizar Producto"):
                    sql_u = """
                        UPDATE ecommerce_productos 
                        SET nombre=:nom, marca=:mar, categoria=:cat, precio=:pre, cant_cuotas=:cant_c, monto_cuota=:monto_c, stock=:stk, estado=:est, imagen_url=:img, youtube_url=:yt, descripcion=:desc
                        WHERE id_producto=:id
                    """
                    ejecutar_query(sql_u, {
                        "nom": e_nombre, "mar": e_marca, "cat": e_cat, "pre": e_precio,
                        "cant_c": e_cant_c, "monto_c": e_monto_c, "stk": e_stock,
                        "est": e_estado, "img": e_img, "yt": e_yt, "desc": e_desc, "id": id_prod_sel
                    })
                    st.success("✅ Producto actualizado correctamente")
                    st.rerun()