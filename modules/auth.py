import streamlit as st

def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = None
    if "rol_usuario" not in st.session_state:
        st.session_state.rol_usuario = None

    if not st.session_state.autenticado:
        st.title("🔐 Acceso al Sistema")

        creds = st.secrets.get("credentials", {})

        with st.form("login_form"):
            usuario_input = st.text_input("Usuario")
            clave_input = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                u_clean = usuario_input.strip().lower()
                p_clean = str(clave_input).strip()

                if u_clean in creds:
                    datos_user = creds[u_clean]
                    
                    # Extraer la contraseña de la estructura dict de TOML
                    if isinstance(datos_user, dict) or hasattr(datos_user, "get"):
                        pass_db = str(datos_user.get("password", "")).strip()
                        rol_db = str(datos_user.get("role", "vendedor")).strip()
                    else:
                        pass_db = str(datos_user).strip()
                        rol_db = "admin"

                    if p_clean == pass_db:
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = u_clean
                        st.session_state.rol_usuario = rol_db
                        st.rerun()
                    else:
                        st.error(f"Contraseña incorrecta para el usuario '{u_clean}'.")
                else:
                    st.error(f"El usuario '{u_clean}' no existe.")
        return False
    return True

def logout():
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.rol_usuario = None
    st.rerun()