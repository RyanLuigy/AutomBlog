import streamlit as st

from exibir import exibir_page
from form import form_page

st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("---")
st.sidebar.title("🧭 Menu")
pagina = st.sidebar.radio("Escolha uma página:", ["Blogs Agendados", "Cadastro de Blogs"])

if pagina == "Blogs Agendados":
    exibir_page()   # função que você cria no arquivo blogs.py
elif pagina == "Cadastro de Blogs":
    form_page()   # função que você cria no outro arquivo