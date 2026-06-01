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
- Em perguntas sobre **faltas** ou **frequência**, inclua sempre o alerta fornecido no bloco "Alertas": disciplinas com duas aulas no mesmo dia podem registrar **uma ausência como duas faltas**.
- Para **PIBIC, PIBIT e PIBEU**: use o bloco "Programas de bolsas", os **editais indexados** (valor, vigência, condições) e o **SIGPROP** ({SIGPROP_PESQUISA_URL}) para projetos de pesquisa — responsabilidade da **PROP**.
- Respostas rápidas fixas (FAQ) já cobrem **valor R$ 700** (bolsas pesquisa/monitoria) e **máximo 25% de faltas**; não contradiga esses valores salvo edital explícito nos PDFs que diga o contrário.
"""

CHAT_HISTORY_MAX_MESSAGES = int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "20"))

HYBRID_PROMPT_SUFFIX = """
Se a busca web estiver presente, use-a para validar cargos e nomes atuais antes de responder.
Use o histórico da conversa para entender perguntas de follow-up (ex.: "e em Piripiri?", "qual a modalidade?").
"""
