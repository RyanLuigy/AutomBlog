import os
import tempfile
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build

@st.cache_resource(ttl=3600)
def get_google_services():
    
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    try:
        # Acessa a seção como um dicionário diretamente
        secrets_dict = st.secrets["service_account"]
        
        creds = Credentials.from_service_account_info(
            secrets_dict,
            scopes=SCOPE
        )
        
        gc = gspread.authorize(creds)
        drive_service = build("drive", "v3", credentials=creds)
        
        return {
            'creds': creds,
            'gc': gc,
            'drive': drive_service
        }
    except Exception:
        return None

def baixar_imagem_para_arquivo(url):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    suffix = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    fd, caminho = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(caminho, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return caminho  # caminho local do arquivo temporário

def postar_blog(categoria, titulo, tags, conteudo, img_url):
    
    options = Options()
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    usuario = st.secrets["BLOG_USER"]
    senha = st.secrets["BLOG_PASS"]
    wait = WebDriverWait(driver, 5)
    driver.get("https://www.cimatecjr.com.br/admin/login")
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(usuario)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(senha)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
    wait = WebDriverWait(driver, 10)
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
    driver.get("https://www.cimatecjr.com.br/admin/blog")
    wait = WebDriverWait(driver, 10)
    linha = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr:nth-child(1)")))
    numero = linha.find_element(By.TAG_NAME, "td").text
    imagem_td = linha.find_elements(By.TAG_NAME, "td")[1]
    imagem_upload_site = imagem_td.find_element(By.TAG_NAME, "img").get_attribute("src")
    driver.get("https://www.cimatecjr.com.br/admin/blog/" + numero + "/edit")
    time.sleep(10)
    novo_conteudo = f"<img src={imagem_upload_site}>" + conteudo
    novo_conteudo = conteudo
    elemento1 = driver.find_element(By.CSS_SELECTOR, "div.note-editable.panel-body[contenteditable='true']")
    driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento1, novo_conteudo)
    driver.execute_script("""document.querySelector('textarea[name="content"]').value = arguments[0];""", novo_conteudo)
    time.sleep(20)
    botao1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pull-right > button.btn-primary[type='submit']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", botao1)
    time.sleep(1)
    botao1.click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr.odd")))
    time.sleep(10)
    os.remove(caminho_temp)