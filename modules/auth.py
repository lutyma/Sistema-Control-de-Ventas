import streamlit as st

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
                creds = st.secrets.get("credentials", {})
                if usuario in creds and clave == str(creds[usuario]):
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

def logout():
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.rerun()