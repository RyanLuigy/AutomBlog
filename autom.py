from email.mime.text import MIMEText
import os
import tempfile
import requests
import json
import time
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import smtplib


# -------------------------------------------------------------------
# 🔐 Função de leitura de segredos híbrida
# -------------------------------------------------------------------

def get_secret(key: str, default=None):
    """Tenta obter o segredo do Streamlit ou do ambiente"""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
        elif "service_account" in st.secrets and key in st.secrets["service_account"]:
            return st.secrets["service_account"][key]
    except Exception:
        pass  # não está rodando dentro do Streamlit

    return os.getenv(key, default)


# -------------------------------------------------------------------
# 🔑 Autenticação Google Sheets
# -------------------------------------------------------------------

def get_google_services():
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    creds_json = None

    # Tenta Streamlit
    try:
        if "service_account" in st.secrets:
            creds_json = st.secrets["service_account"]  # dicionário completo
    except Exception:
        pass

    # Tenta GitHub Actions
    if not creds_json:
        raw_env = os.getenv("GOOGLE_CREDENTIALS")
        if raw_env:
            creds_json = json.loads(raw_env)

    if not creds_json:
        print("❌ Não foi possível encontrar as credenciais do Google.")
        return None

    try:
        creds = Credentials.from_service_account_info(creds_json, scopes=SCOPE)
        gc = gspread.authorize(creds)
        drive_service = build("drive", "v3", credentials=creds)
        return {'creds': creds, 'gc': gc, 'drive': drive_service}
    except Exception as e:
        print(f"Erro ao autenticar com Google: {e}")
        return None


# -------------------------------------------------------------------
# 📸 Função para baixar imagem temporária
# -------------------------------------------------------------------

def baixar_imagem_para_arquivo(url):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    suffix = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    fd, caminho = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(caminho, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return caminho


def enviar_email(titulo, remetentes):

    # Credenciais do Gmail
    EMAIL = get_secret("email_gmail")
    SENHA = get_secret("senha_gmail")

    corpo = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f4f7; padding:20px;">
        <div style="max-width:600px; margin:auto; background-color:#ffffff; padding:30px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
        
        <!-- Logo -->
        <div style="text-align:center; margin-bottom:20px;">
            <img src="https://www.cimatecjr.com.br/assets/img/logo.png?v=1.01" width="120" alt="CIMATEC Jr.">
        </div>
        
        <!-- Título -->
        <h2 style="text-align:center; color:#004aad; margin-bottom:20px;">Olá!</h2>
        
        <!-- Mensagem -->
        <p style="font-size:16px; color:#333;">
            O blog '<b>{titulo} {remetentes}</b>' acaba de ser postado com sucesso!
        </p>
        
        <p style="font-size:16px; color:#333;">
            Confira em:
        </p>
        
        <!-- Botão CTA -->
        <p style="text-align:center; margin-top:30px;">
            <a href="https://www.cimatecjr.com.br/blog" target="_blank" 
            style="background-color:#004aad; color:#ffffff; padding:12px 25px; text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block;">
            Acessar o Blog
            </a>
        </p>

        <!-- Rodapé opcional -->
        <p style="font-size:12px; color:#888; text-align:center; margin-top:40px;">
            © 2025 CIMATEC Jr. Todos os direitos reservados.
        </p>
        
        </div>
    </body>
    </html>
    """

    # Criar e-mail
    msg = MIMEText(corpo, "html")
    msg["Subject"] = f"[BLOG POSTADO] {titulo}"
    msg["From"] = EMAIL
    # msg["To"] = ", ".join(remetentes)
    msg["To"] = "ryanluigy@cimatecjr.com.br"

    # Enviar
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, SENHA)
        server.send_message(msg)

# -------------------------------------------------------------------
# 🤖 Função principal de postagem
# -------------------------------------------------------------------

def postar_blog(categoria, titulo, tags, conteudo, img_url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    usuario = get_secret("BLOG_USER")
    senha = get_secret("BLOG_PASS")

    if not usuario or not senha:
        print("❌ Credenciais do blog não configuradas.")
        return

    wait = WebDriverWait(driver, 10)

    # Login
    driver.get("https://www.cimatecjr.com.br/admin/login")
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(usuario)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(senha)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()

    # Página de postagem
    wait.until(EC.url_contains("admin"))
    driver.get("https://www.cimatecjr.com.br/admin/blog/show")

    wait.until(EC.presence_of_element_located((By.NAME, "category_id"))).send_keys(categoria)
    wait.until(EC.presence_of_element_located((By.NAME, "title"))).send_keys(titulo)
    wait.until(EC.presence_of_element_located((By.NAME, "tags"))).send_keys(tags)

    caminho_temp = baixar_imagem_para_arquivo(img_url)
    wait.until(EC.presence_of_element_located((By.NAME, "file"))).send_keys(caminho_temp)

    elemento = driver.find_element(By.CSS_SELECTOR, "div.note-editable.panel-body[contenteditable='true']")
    driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento, conteudo)
    driver.execute_script("""document.querySelector('textarea[name="content"]').value = arguments[0];""", conteudo)

    botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pull-right > button.btn-primary[type='submit']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", botao)
    time.sleep(1)
    botao.click()

    
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))
    linha = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr:nth-child(1)")))
    numero = linha.find_element(By.TAG_NAME, "td").text
    imagem_td = linha.find_elements(By.TAG_NAME, "td")[1]
    imagem_upload_site = imagem_td.find_element(By.TAG_NAME, "img").get_attribute("src")
    driver.get("https://www.cimatecjr.com.br/admin/blog/" + numero + "/edit")
    time.sleep(1)
    novo_conteudo = f"<img src={imagem_upload_site}>" + conteudo
    elemento1 = driver.find_element(By.CSS_SELECTOR, "div.note-editable.panel-body[contenteditable='true']")
    driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento1, novo_conteudo)
    driver.execute_script("""document.querySelector('textarea[name="content"]').value = arguments[0];""", novo_conteudo)
    time.sleep(2)
    botao1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pull-right > button.btn-primary[type='submit']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", botao1)
    time.sleep(1)
    botao1.click()

    # Confirmação
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))
    os.remove(caminho_temp)
    driver.quit()

    print(f"✅ Post '{titulo}' publicado com sucesso!")
