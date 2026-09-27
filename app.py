import streamlit as st
from modules.auth import login, logout
from modules.ventas import render_ventas
from modules.ecommerce import render_ecommerce
from modules.clientes import render_clientes

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
    </style>
""", unsafe_allow_html=True)

# --- 2. CONTROL DE ACCESO (LOGIN) ---
if login():
    # --- BARRA LATERAL GENERAL ---
    st.sidebar.markdown(f"👤 Usuario: **{st.session_state.usuario_actual}**")
    st.sidebar.markdown("---")
    
    # NAVEGACIÓN PRINCIPAL
    modulo_seleccionado = st.sidebar.radio(
        "📌 Seleccione Módulo:",
        ["📊 Gestión de Ventas", "🛒 E-Commerce", "⚙️ Paramétrico"]
    )
    
    # Submenú desplegable si elige Paramétrico
    submodulo_param = None
    if modulo_seleccionado == "⚙️ Paramétrico":
        submodulo_param = st.sidebar.selectbox(
            "📂 Selección de Gestión:",
            ["👤 Gestión de Clientes", "📦 Gestión de Productos"]
        )
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        logout()

    # --- ENRUTAMIENTO DE MÓDULOS ---
    if modulo_seleccionado == "📊 Gestión de Ventas":
        render_ventas()
    elif modulo_seleccionado == "🛒 E-Commerce":
        render_ecommerce()
    elif modulo_seleccionado == "⚙️ Paramétrico":
        if submodulo_param == "👤 Gestión de Clientes":
            render_clientes()
        elif submodulo_param == "📦 Gestión de Productos":
            # Renderiza la vista dedicada a gestión de productos
            from modules.ecommerce import render_gestion_productos
            render_gestion_productos()