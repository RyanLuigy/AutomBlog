import streamlit as st

from exibir import exibir_page
from form import form_page

import streamlit as st

# --- Sessão de login ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.title("🔒 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == st.secrets["login"]["user"] and senha == st.secrets["login"]["password"]:
            st.session_state["logado"] = True
            st.success("✅ Login realizado com sucesso!")
            st.experimental_rerun()  # recarrega a página para mostrar conteúdo
        else:
            st.error("❌ Usuário ou senha incorretos")

else:
    # --- Conteúdo protegido ---
    st.sidebar.image("logo.png", use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.title("🧭 Menu")
    pagina = st.sidebar.radio("Escolha uma página:", ["Blogs Agendados", "Cadastro de Blogs"])

    if pagina == "Blogs Agendados":
        exibir_page()   # função que você cria no arquivo blogs.py
    elif pagina == "Cadastro de Blogs":
        form_page()   # função que você cria no outro arquivo
    if st.button("Sair"):
        st.session_state["logado"] = False
        st.experimental_rerun()

