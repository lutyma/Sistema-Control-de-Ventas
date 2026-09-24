import streamlit as st
from modules.auth import login, logout
from modules.ventas import render_ventas
from modules.ecommerce import render_ecommerce

# --- 1. CONFIGURACIÓN Y ESTILOS CSS ---
st.set_page_config(page_title="Sistema Integral de Gestión", layout="wide")

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
    
    # NAVEGACIÓN PRINCIPAL
    st.sidebar.markdown("---")
    modulo_seleccionado = st.sidebar.radio(
        "📌 Seleccione Módulo:",
        ["📊 Gestión de Ventas", "🛒 E-Commerce"]
    )
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        logout()

    # --- ENRUTAMIENTO DE MÓDULOS ---
    if modulo_seleccionado == "📊 Gestión de Ventas":
        render_ventas()
    elif modulo_seleccionado == "🛒 E-Commerce":
        render_ecommerce()