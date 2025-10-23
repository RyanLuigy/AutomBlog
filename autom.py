import os
import tempfile
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 🔁 Detecta automaticamente se está em ambiente Streamlit
USING_STREAMLIT = "STREAMLIT_SERVER_STATUS" in os.environ or "streamlit" in os.getcwd()

if USING_STREAMLIT:
    import streamlit as st


# ============================================================
# 1. Conexão com os serviços Google
# ============================================================
def get_google_services():
    """Conecta com Sheets/Drive tanto no Streamlit quanto no GitHub Actions"""
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    creds = None

    try:
        if USING_STREAMLIT:
            # Lê credenciais do st.secrets
            secrets_dict = st.secrets["service_account"]
            creds = Credentials.from_service_account_info(secrets_dict, scopes=SCOPE)

        elif os.path.exists("service_account.json"):
            # Lê credenciais do arquivo local (usado no GitHub Actions)
            with open("service_account.json", "r") as f:
                service_json = json.load(f)
            creds = Credentials.from_service_account_info(service_json, scopes=SCOPE)

        else:
            raise Exception("Credenciais do Google não encontradas.")

        gc = gspread.authorize(creds)
        drive_service = build("drive", "v3", credentials=creds)

        return {"creds": creds, "gc": gc, "drive": drive_service}

    except Exception as e:
        if USING_STREAMLIT:
            st.error(f"Erro ao conectar com Google: {e}")
        else:
            print(f"❌ Erro ao conectar com Google: {e}")
        return None


# ============================================================
# 2. Download da imagem
# ============================================================
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


# ============================================================
# 3. Função principal de postagem automática
# ============================================================
def postar_blog(categoria, titulo, tags, conteudo, img_url):
    """Publica um blog automaticamente via Selenium"""

    # Configurações de execução headless
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    # Caminho do driver
    chromedriver_path = "/usr/bin/chromedriver" if os.path.exists("/usr/bin/chromedriver") else "chromedriver"
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # Credenciais de login
    usuario = (
        st.secrets["BLOG_USER"] if USING_STREAMLIT else os.getenv("BLOG_USER")
    )
    senha = (
        st.secrets["BLOG_PASS"] if USING_STREAMLIT else os.getenv("BLOG_PASS")
    )

    wait = WebDriverWait(driver, 10)

    try:
        # Login
        driver.get("https://www.cimatecjr.com.br/admin/login")
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(usuario)
        wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(senha)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()

        # Página de postagem
        driver.get("https://www.cimatecjr.com.br/admin/blog/show")
        wait.until(EC.presence_of_element_located((By.NAME, "category_id"))).send_keys(categoria)
        wait.until(EC.presence_of_element_located((By.NAME, "title"))).send_keys(titulo)
        wait.until(EC.presence_of_element_located((By.NAME, "tags"))).send_keys(tags)

        # Upload da imagem
        caminho_temp = baixar_imagem_para_arquivo(img_url)
        wait.until(EC.presence_of_element_located((By.NAME, "file"))).send_keys(caminho_temp)

        # Inserção do conteúdo HTML
        elemento = driver.find_element(By.CSS_SELECTOR, "div.note-editable.panel-body[contenteditable='true']")
        driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento, conteudo)
        driver.execute_script("""document.querySelector('textarea[name="content"]').value = arguments[0];""", conteudo)

        # Envio inicial
        botao = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pull-right > button.btn-primary[type='submit']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", botao)
        time.sleep(1)
        botao.click()

        # Espera publicação
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))

        # Edição final para garantir imagem principal no conteúdo
        driver.get("https://www.cimatecjr.com.br/admin/blog")
        linha = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr:nth-child(1)")))
        numero = linha.find_element(By.TAG_NAME, "td").text
        imagem_td = linha.find_elements(By.TAG_NAME, "td")[1]
        imagem_upload_site = imagem_td.find_element(By.TAG_NAME, "img").get_attribute("src")

        driver.get(f"https://www.cimatecjr.com.br/admin/blog/{numero}/edit")
        time.sleep(5)

        novo_conteudo = f'<img src="{imagem_upload_site}">' + conteudo
        elemento1 = driver.find_element(By.CSS_SELECTOR, "div.note-editable.panel-body[contenteditable='true']")
        driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento1, novo_conteudo)
        driver.execute_script("""document.querySelector('textarea[name="content"]').value = arguments[0];""", novo_conteudo)

        # Enviar atualização
        botao1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pull-right > button.btn-primary[type='submit']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", botao1)
        time.sleep(1)
        botao1.click()

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))

        print(f"✅ Postagem concluída: {titulo}")

    except Exception as e:
        print(f"❌ Erro ao postar '{titulo}': {e}")
    finally:
        driver.quit()
        if 'caminho_temp' in locals() and os.path.exists(caminho_temp):
            os.remove(caminho_temp)
