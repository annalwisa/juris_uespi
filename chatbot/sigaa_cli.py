"""Atualiza cache local do SIGAA: python -m chatbot.sigaa_cli"""

from chatbot.config import SIGAA_CURSOS_URL
from chatbot.sigaa import CACHE_FILE, refresh_cache


def main():
    print(f"Atualizando cache SIGAA de {SIGAA_CURSOS_URL} ...")
    count = refresh_cache()
    print(f"Concluído: {count} cursos salvos em {CACHE_FILE}")


if __name__ == "__main__":
    main()
