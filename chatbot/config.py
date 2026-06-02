import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "docs"
VECTOR_DB_DIR = ROOT / "vector_db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
RETRIEVAL_K = int(os.getenv("RAG_RETRIEVAL_K", "6"))
RETRIEVAL_FETCH_K = int(os.getenv("RAG_RETRIEVAL_FETCH_K", "20"))

# pinecone | chroma (padrão: pinecone se PINECONE_API_KEY existir)
_default_store = "pinecone" if os.getenv("PINECONE_API_KEY") else "chroma"
VECTOR_STORE = os.getenv("VECTOR_STORE", _default_store).lower()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "uespi-docs")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "uespi")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
PINECONE_CREATE_INDEX = os.getenv("PINECONE_CREATE_INDEX", "false").lower() in (
    "1",
    "true",
    "yes",
)

# text-embedding-3-small → 1536; text-embedding-3-large → 3072
EMBEDDING_DIMENSION = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", "1536"))

CHROMA_COLLECTION_NAME = "uespi_docs"
COLLECTION_NAME = CHROMA_COLLECTION_NAME  # alias legado

UESPI_SITE = os.getenv("UESPI_SITE", "https://uespi.br")

REGIMENTO_PDF_URL = os.getenv(
    "REGIMENTO_PDF_URL",
    "https://uespi.br/wp-content/uploads/2021/08/Regimento.pdf",
)

SIGAA_CURSOS_URL = os.getenv(
    "SIGAA_CURSOS_URL",
    "https://sigaa.uespi.br/sigaa/public/curso/lista.jsf?nivel=G&aba=p-ensino",
)
SIGAA_CACHE_HOURS = int(os.getenv("SIGAA_CACHE_HOURS", "24"))
# Alguns ambientes Windows falham na verificação SSL do SIGAA
SIGAA_SSL_VERIFY = os.getenv("SIGAA_SSL_VERIFY", "false").lower() in ("1", "true", "yes")

SIGPROP_PESQUISA_URL = os.getenv(
    "SIGPROP_PESQUISA_URL",
    "https://sistemas2.uespi.br/sigprop/index_pesquisa.php",
)
PROP_NOME = "Pró-Reitoria de Pesquisa e Pós-Graduação (PROP)"

# Estágio Supervisionado — PREG / DAP / DES
ESTAGIO_DES_URL = os.getenv(
    "ESTAGIO_DES_URL",
    "https://uespi.br/preg-dap-des/",
)
ESTAGIO_CONVENIADAS_PLANILHA_URL = os.getenv(
    "ESTAGIO_CONVENIADAS_PLANILHA_URL",
    "https://docs.google.com/spreadsheets/d/1G6es_rE9ZhGXhaiJ2LwDikbsv_ejPAV91GYAZARx3H0/edit?pli=1&gid=659220882#gid=659220882",
)
ESTAGIO_CONVENIO_EMAIL = os.getenv("ESTAGIO_CONVENIO_EMAIL", "convenio@preg.uespi.br")
ESTAGIO_DAP_EMAIL = os.getenv("ESTAGIO_DAP_EMAIL", "dap@preg.uespi.br")
ESTAGIO_DAP_TELEFONE = os.getenv("ESTAGIO_DAP_TELEFONE", "(86) 3213-7441")
PREG_NOME = "Pró-Reitoria de Ensino de Graduação (PREG)"
DES_NOME = "Divisão de Estágio Supervisionado (DES) — vinculada ao DAP/PREG"

WEB_SEARCH_MODE = os.getenv("WEB_SEARCH_MODE", "auto").lower()  # auto | always | off
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # opcional; busca mais estável que DuckDuckGo

SYSTEM_PROMPT = f"""Você é o **Juris UESPI**, assistente inteligente para sanar dúvidas da comunidade acadêmica da Universidade Estadual do Piauí (UESPI).

Regras gerais:
- Responda em português brasileiro, de forma clara e objetiva.
- Para normas (artigos, resoluções, faltas, notas, estágio): use os documentos indexados (PDFs).
- Nunca use a sigla "RAG" nas respostas. Ao citar o regimento, use o link: [Regimento.pdf]({REGIMENTO_PDF_URL}).
- Para coordenador(a) de curso, sede, modalidade e lista de cursos de graduação: use PRIMEIRO
  o bloco SIGAA (fonte oficial atualizada). Complemente com busca web se necessário.
- Para reitoria e pró-reitores: use busca web; PDFs antigos podem citar gestão anterior.
  NUNCA confie só no PDF para nomes de pessoas em cargos atuais.
- Se houver conflito entre PDF antigo e busca web, siga a web e diga que o PDF está desatualizado nesse ponto.
- Cite fontes: arquivo/ano/artigo para normas; URL do site para dados atuais de gestão.
- Se não houver base suficiente, indique secretaria, coordenação ou uespi.br.
- Não invente normas, prazos, editais ou telefones.
- Recuse educadamente perguntas que não tenham relação com a UESPI.
- Para **PIBIC, PIBIT e PIBEU**: use o bloco "Programas de bolsas", os **editais indexados** (valor, vigência, condições) e o **SIGPROP** ({SIGPROP_PESQUISA_URL}) para projetos de pesquisa — responsabilidade da **PROP**.
- Respostas rápidas fixas (FAQ) já cobrem **valor R$ 700** (bolsas pesquisa/monitoria) e **máximo 25% de faltas**; não contradiga esses valores salvo edital explícito nos PDFs que diga o contrário.
- Para **estágio supervisionado, convênio com empresa, estagiário, instituição conveniada**: use o bloco "Estágio supervisionado" e os PDFs indexados (Lei 11.788/2008, Resolução CEPEX 004/2021 da UESPI, Portaria 329/2020 sobre Residência Pedagógica e o procedimento de abertura de convênio do DAP/DES). Sempre cite a página oficial da DES ({ESTAGIO_DES_URL}) e, para conferir se uma empresa já é conveniada, indique a planilha oficial ({ESTAGIO_CONVENIADAS_PLANILHA_URL}). E-mail de convênio: {ESTAGIO_CONVENIO_EMAIL}.
- Para perguntas sobre **"jubilação" / "ser jubilado" / "perder a vaga"**: use o bloco "Jubilação na UESPI". O termo formal no Regimento é **Cancelamento da Matrícula Institucional (Art. 46)** — sempre traduza para esse nome, liste as hipóteses (I a V) e cite o artigo. Para pós-graduação, use a Resolução CEPEX 005/2021 (stricto sensu) ou a Resolução Consun 004/2022 (especialização). Não invente prazos de integralização: eles dependem do PPC do curso.
"""

CHAT_HISTORY_MAX_MESSAGES = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "20"))

HYBRID_PROMPT_SUFFIX = """
Se a busca web estiver presente, use-a para validar cargos e nomes atuais antes de responder.
Use o histórico da conversa para entender perguntas de follow-up (ex.: "e em Piripiri?", "qual a modalidade?").
"""
