import os
import sys
import base64
import pandas as pd
from datetime import datetime, timezone
from dateutil import parser
from loguru import logger
from autom import get_google_services, postar_blog


# === Configuração do logger ===
logger.remove()  # Remove qualquer configuração padrão
logger.add(sys.stdout, level="INFO")  # Mostra logs no console (GitHub Actions)
logger.add("logs_auto_post.log", rotation="1 MB", level="INFO", enqueue=True, backtrace=True, diagnose=True)

def main():
    logger.info("=== Iniciando auto_post.py ===")

    # 1. Conexão com serviços Google
    try:
        services = get_google_services()
        if services is None:
            raise Exception("Falha ao autenticar com os serviços Google.")
        logger.success("Conexão com serviços Google bem-sucedida.")
    except Exception as e:
        logger.exception(f"Erro na autenticação: {e}")
        logger.complete()
        return

    # 2. Ler planilha
    try:
        gc = services["gc"]
        SHEET_NAME = os.getenv("SHEET_NAME")
        sheet = gc.open(SHEET_NAME).get_worksheet(2)
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados)
        logger.info(f"Planilha '{SHEET_NAME}' carregada com {len(df)} registros.")
    except Exception as e:
        logger.exception(f"Erro ao ler planilha: {e}")
        logger.complete()
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

            logger.debug(f"[{i}] {post['titulo']} - Agendado para {data_agendada.isoformat()}")

            if data_agendada <= now:
                pendentes.append((i, post))
        except Exception as e:
            logger.warning(f"Erro ao verificar linha {i}: {e}")

    if not pendentes:
        logger.info("Nenhum post pendente ou agendado para agora.")
        logger.complete()
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
            logger.exception(f"Erro ao postar '{post['titulo']}': {e}")

    logger.info("=== Finalização do script ===")
    logger.complete()  # Garante que os logs sejam gravados antes de encerrar


if __name__ == "__main__":
    main()
