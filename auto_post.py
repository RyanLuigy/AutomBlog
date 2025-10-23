import os
import base64
import pandas as pd
from datetime import datetime
from autom import get_google_services, postar_blog  # suas funções já existentes
from loguru import logger
from dateutil import parser
from datetime import datetime, timezone
import sys

# Remove os handlers default
logger.remove()

# Adiciona console (stdout) e arquivo
logger.add(sys.stdout, level="INFO")  # mostra no GitHub Actions
logger.add("logs_auto_post.log", rotation="1 MB", level="INFO")  # grava em arquivo


def main():
    logger.info("=== Iniciando auto_post.py ===")

    # 1. Conexão com serviços Google
    try:
        services = get_google_services()
        if services is None:
            raise Exception("Falha ao autenticar com os serviços Google.")
    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
        return

    # 2. Ler planilha
    try:
        gc = services["gc"]
        SHEET_NAME = os.getenv("SHEET_NAME")
        sheet = gc.open(SHEET_NAME).get_worksheet(2)
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        logger.info(f"Planilha carregada com {len(df)} registros.")
    except Exception as e:
        logger.error(f"Erro ao ler planilha: {e}")
        return

    # 3. Filtrar posts pendentes e que estejam no horário de agendamento
    now = datetime.now(timezone.utc)
    pendentes = []

    for i, post in enumerate(dados):
        try:
            status = post["status"].strip().lower()
            if status != "pendente":
                continue

            data_agendada = parser.isoparse(post["data_agendada"])
            if data_agendada.tzinfo is None:
                data_agendada = data_agendada.replace(tzinfo=timezone.utc)

            if data_agendada <= now:
                pendentes.append((i, post))

        except Exception as e:
            logger.warning(f"Erro ao verificar linha {i}: {e}")

    if not pendentes:
        logger.info("Nenhum post pendente ou agendado para agora.")
        return

    # 4. Postar os conteúdos
    for i, post in pendentes:
        try:
            logger.info(f"Postando: {post['titulo']}")
            conteudo_html = base64.b64decode(post["conteudo_encoded"]).decode("utf-8")

            postar_blog(
                post["categoria"],
                post["titulo"],
                post["tags"],
                conteudo_html,
                post["imagem_url"]
            )

            # Atualiza o status para publicado
            sheet.update_cell(i + 2, 8, "publicado")
            logger.success(f"✅ Post '{post['titulo']}' publicado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao postar '{post['titulo']}': {e}")

    logger.info("=== Finalização do script ===")

