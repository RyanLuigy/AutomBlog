import os
import tempfile
import requests
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

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
    """
    Autentica tanto no Streamlit (st.secrets) quanto no GitHub Actions (GOOGLE_CREDENTIALS)
    """
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    creds_json = get_secret("service_account", None)

    # Caso o Streamlit não tenha o bloco [service_account]
    if not isinstance(creds_json, dict):
        raw_env = get_secret("GOOGLE_CREDENTIALS")
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

    # Confirmação
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))
    os.remove(caminho_temp)
    driver.quit()

    print(f"✅ Post '{titulo}' publicado com sucesso!")
