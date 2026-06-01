# Chatbot UESPI

Assistente para tirar dúvidas sobre a **Universidade Estadual do Piauí (UESPI)**, com **RAG** (busca nos PDFs + resposta fundamentada) via LangChain, OpenAI e **Pinecone** (ou Chroma local).

### RAG e documentos desatualizados

- Busca **20 trechos** similares e usa os **6** mais relevantes após priorizar ano e vigência.
- Configure `data/docs/manifest.yaml` para marcar PDFs como `vigente`, `desatualizado` ou `revogado`.
- O modelo prioriza normas mais recentes e avisa quando usa fonte antiga.
- **SIGAA** (oficial): lista de cursos de graduação com coordenador, sede e modalidade — [SIGAA público](https://sigaa.uespi.br/sigaa/public/curso/lista.jsf?nivel=G&aba=p-ensino). Cache local 24h; atualizar com `python -m chatbot.sigaa_cli`.
- **Busca web** (`ddgs`): reitoria e complemento. Modo: `WEB_SEARCH_MODE=auto` no `.env`.

## Configuração

1. Crie o arquivo `.env` na raiz (copie de `.env.example`):

```env
OPENAI_API_KEY=sua_chave_openai
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

VECTOR_STORE=pinecone
PINECONE_API_KEY=sua_chave_pinecone
PINECONE_INDEX_NAME=uespi-docs
PINECONE_NAMESPACE=uespi
```

2. **Pinecone:** em [app.pinecone.io](https://app.pinecone.io), crie um índice **serverless** com:
   - **Dimensão:** `1536` (modelo `text-embedding-3-small`)
   - **Métrica:** cosine  
   Ou defina `PINECONE_CREATE_INDEX=true` para o projeto criar o índice na primeira indexação (região padrão: `aws` / `us-east-1`).

3. Instale dependências:

```bash
uv sync
# ou: pip install -r requirements.txt
```

## Uso

1. Coloque PDFs em `data/docs/`.

2. Envie os trechos para o Pinecone:

```bash
python -m chatbot.ingest_cli --reset
```

3. Inicie o chat:

```bash
python -m chatbot.app
```

### Interface web (React)

Na pasta irmã `juris_uespi-frontend` há uma UI em branco e azul. Suba a API e o frontend:

```bash
# Terminal 1 — API
python -m chatbot.api

# Terminal 2 — frontend (juris_uespi-frontend)
npm install && npm run dev
```

Abra `http://localhost:5173`.

## Chroma (local, sem Pinecone)

No `.env`:

```env
VECTOR_STORE=chroma
```

Remova ou comente `PINECONE_API_KEY`. Os vetores ficam em `vector_db/` na máquina.

## Estrutura

- `chatbot/` — ingestão, RAG, Pinecone/Chroma e Gradio
- `data/docs/` — PDFs e textos
- `vector_db/` — só quando `VECTOR_STORE=chroma`
