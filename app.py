import streamlit as st
from modules.auth import login, logout
from modules.ventas import render_ventas
from modules.ecommerce import render_ecommerce, render_gestion_productos
from modules.clientes import render_clientes
from modules.vendedores import render_vendedores

# --- 1. CONFIGURACIÓN Y ESTILOS CSS ---
st.set_page_config(
    page_title="Sistema de Ventas e Ingresos",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stStatusWidget"] { display: none !important; }
    .stAppDeployButton { display: none !important; }
    div[class^="viewerBadge"], div[class*="viewerBadge"] { display: none !important; }
    .stApp > footer { display: none !important; }
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }

    /* --- OPTIMIZACIÓN ADICIONAL PARA MÓVILES (RAMA LOCAL) --- */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        div.stButton > button {
            width: 100% !important;
            margin-bottom: 5px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GESTIÓN DE SESIÓN Y VISTA PÚBLICA / PRIVADA-- ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# MODO USUARIO AUTENTICADO (Vendedor / Admin)
if st.session_state.autenticado:
    if "redireccionar_a" in st.session_state:
        st.session_state.navegacion_principal = st.session_state.pop("redireccionar_a")

    if "navegacion_principal" not in st.session_state:
        st.session_state.navegacion_principal = "📊 Gestión de Ventas"

    st.sidebar.markdown(f"👤 Usuario: **{st.session_state.usuario_actual}**")
    st.sidebar.markdown("---")
    
    modulo_seleccionado = st.sidebar.radio(
        "📌 Seleccione Módulo:",
        ["📊 Gestión de Ventas", "🛒 E-Commerce", "⚙️ Paramétrico"],
        key="navegacion_principal"
    )
    
    submodulo_param = None
    if modulo_seleccionado == "⚙️ Paramétrico":
        submodulo_param = st.sidebar.selectbox(
            "📂 Selección de Gestión:",
            ["👤 Gestión de Clientes", "👔 Gestión de Vendedores", "📦 Gestión de Productos"]
        )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        logout()

    # Enrutamiento privado
    if modulo_seleccionado == "📊 Gestión de Ventas":
        render_ventas()
    elif modulo_seleccionado == "🛒 E-Commerce":
        render_ecommerce()
    elif modulo_seleccionado == "⚙️ Paramétrico":
        if submodulo_param == "👤 Gestión de Clientes":
            render_clientes()
        elif submodulo_param == "👔 Gestión de Vendedores":
            render_vendedores()
        elif submodulo_param == "📦 Gestión de Productos":
            render_gestion_productos()

# MODO CLIENTE PÚBLICO (Sin Login)
else:
    c_top1, c_top2 = st.columns([3, 1])
    with c_top1:
        st.info("🛍️ Estás navegando como cliente en la tienda.")
    with c_top2:
        with st.popover("🔑 Iniciar Sesión"):
            st.markdown("### Acceso Personal")
            login(form_key="login_form_top")

    st.sidebar.title("🛍️ Bienvenido a la Tienda")
    st.sidebar.info("Estás navegando como cliente.")
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("🔑 Acceso Administrador / Vendedor"):
        login(form_key="login_form_sidebar")
        
    # Renderizar exclusivamente el catálogo público
    render_ecommerce()