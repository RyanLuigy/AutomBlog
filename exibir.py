import pandas as pd
import streamlit as st
import base64
from autom import get_google_services, postar_blog  # função Selenium separada

def exibir_page():

    st.title("🚀 Postar Blogs Agendados")

    services = get_google_services()

    # 1. VERIFICAÇÃO CRUCIAL
    if services is None:
        st.error("ERRO DE AUTENTICAÇÃO: Não foi possível conectar aos serviços Google.")
        st.info("Verifique se o seu arquivo `.streamlit/secrets.toml` está correto e completo.")
        st.stop()

    # 2. Desempacotamento seguro
    gc = services["gc"]
    SHEET_NAME = st.secrets["SHEET_NAME"]
    sheet = gc.open(SHEET_NAME).get_worksheet(2)
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    if st.toggle("Ver histórico de posts agendados com a automação", False):
        with st.container(border=True):
            st.subheader("Histórico de posts agendados com a automação")
            st.dataframe(df)

    posts_pendentes = False
    
    for i, post in enumerate(dados):
       
        if post["status"] == "pendente":
            posts_pendentes = True
            conteudo_html = base64.b64decode(post["conteudo_encoded"]).decode("utf-8")
            with st.container(border=True):
                st.subheader(post["titulo"])
                st.markdown(f"**Categoria:** {post['categoria']} | **Agendado para:** {post['data_agendada']}")


                with st.expander("👁️ Visualizar conteúdo"):
                    
                    st.write(post["imagem_url"])
                    
                    st.markdown(conteudo_html, unsafe_allow_html=True)

                    st.divider()
                    st.markdown("**Tags:** " + post["tags"])

                    if st.button(f"📤 Postar agora", key=f"postar_{i}"):
                        st.info(f"Postando '{post['titulo']}'...")
                        try:
                            postar_blog(
                                post["categoria"],
                                post["titulo"],
                                post["tags"],
                                conteudo_html,
                                post["imagem_url"]
                            )
                            sheet.update_cell(i+2, 8, "publicado")
                            st.success("✅ Publicado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao postar: {e}")
    if not posts_pendentes:
        with st.container(border=True):
            st.subheader("Post agendados pendentes")
            st.info("Nenhum post agendado!")