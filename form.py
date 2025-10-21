import streamlit as st
import datetime
import base64
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Supondo que 'autom' seja seu arquivo de biblioteca com a função get_google_services
from autom import get_google_services 

def form_page():
    st.title("Agendar Blog (Upload → Drive → Sheets)")

    activate_preview = st.toggle("Pré-visualização do Blog", value=False)

    if activate_preview:
        st.set_page_config(layout="wide")
    else:
        st.set_page_config(layout="centered")


    services = get_google_services()

    # 1. VERIFICAÇÃO CRUCIAL: Checa se o resultado NÃO é None
    if services is None:
        st.error("ERRO DE AUTENTICAÇÃO: Não foi possível conectar aos serviços Google.")
        st.info("Verifique se o seu arquivo `.streamlit/secrets.toml` está correto e completo.")
        st.stop()
    # ----------------------------------------

    # 2. Desempacotamento seguro (só é executado se services não for None)
    gc = services["gc"]
    drive_service = services["drive"]

    SHEET_NAME = st.secrets["SHEET_NAME"]
    PASTA_ID = st.secrets["PASTA_ID"]
    sheet = gc.open(SHEET_NAME).get_worksheet(2)

    def upload_para_drive(uploaded_file, pasta_id=PASTA_ID):
        file_bytes = uploaded_file.read()
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=uploaded_file.type, resumable=False)
        
        metadata = {"name": uploaded_file.name, "parents": [pasta_id]}
        
        # ⚠️ Adicione supportsAllDrives=True aqui
        uploaded = drive_service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()
        
        file_id = uploaded.get("id")

        drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
            fields="id",
            supportsAllDrives=True
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"


    # -------------------------------------------------------------
    # DIVISÃO DO LAYOUT: COLUNAS PARA FORMULÁRIO E PRÉ-VISUALIZAÇÃO
    # -------------------------------------------------------------

    if activate_preview:
        # Ativo: Colunas 50/50
        col_form, col_preview = st.columns([1, 1])
    else:
        # Inativo: Cria apenas uma coluna principal (largura 1). 
        # Usamos [1] e atribuímos a col_form, e criamos col_preview como 
        # uma coluna dummy que não será usada.
        col_form = st.columns([1])[0] 
        col_preview = None # Definimos como None para evitar o erro de desempacotamento

    with col_form:
        st.header("Dados do Post")
        
        # MOVIDO PARA FORA DO FORMULÁRIO: Este widget agora atualiza 
        # a página em tempo real, permitindo a pré-visualização dinâmica.
        conteudo = st.text_area("Conteúdo (Markdown/HTML) do post", 
                                height=300, 
                                key="conteudo_input",
                                help="Use Markdown (e.g., **negrito**, # cabeçalho) para formatação ou cole HTML.")
        
        with st.form("agendar_form"):
            categoria = st.selectbox("Categoria", ["Tecnologia", "Inovação", "Gestão e Negócios", "Construção Cívil e Segurança", "Sustentabilidade", "Química e Alimentos"])
            titulo = st.text_input("Título do post")
            tags = st.text_input("Tags (separadas por ;)")
            imagem_upload = st.file_uploader("Imagem de destaque", type=["png", "jpg", "jpeg"])
            
            # Nota para o usuário, já que o conteúdo está acima
            st.caption("O campo 'Conteúdo' está acima para permitir a pré-visualização em tempo real.")
            
            data_agendada = st.date_input("Data agendada", datetime.date.today())
            hora_agendada = st.time_input("Hora agendada", datetime.datetime.now().time())
            submit = st.form_submit_button("Salvar agendamento")

    if submit:
        # O valor do text_area é acessado via st.session_state (permanece o mesmo)
        conteudo_salvar = st.session_state.get("conteudo_input", "")
        
        if not (titulo and conteudo_salvar and imagem_upload):
            st.warning("Preencha título, conteúdo e envie uma imagem.")
        else:
            try:
                with st.spinner("Fazendo upload e salvando na planilha..."):
                    imagem_url = upload_para_drive(imagem_upload)
                    
                    # Codificação do conteúdo
                    conteudo_encoded = base64.b64encode(conteudo_salvar.encode("utf-8")).decode("utf-8")
                    
                    linha = [
                        str(datetime.datetime.now()),
                        titulo,
                        categoria,
                        tags,
                        imagem_url,
                        conteudo_encoded,
                        f"{data_agendada} {hora_agendada}",
                        "pendente"
                    ]
                    sheet.append_row(linha)
                    st.success("✅ Post salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro no upload ou na planilha: {e}")


    # -------------------------------------------------------------
    # PRÉ-VISUALIZAÇÃO DINÂMICA (FORA DO FORMULÁRIO)
    # -------------------------------------------------------------

    if activate_preview and col_preview is not None:
        with col_preview:
            st.header("Pré-visualização (Markdown/HTML)")
            
            conteudo_para_preview = st.session_state.get("conteudo_input", "Comece a digitar aqui para ver a pré-visualização...")
            
            st.markdown(conteudo_para_preview, unsafe_allow_html=True)
