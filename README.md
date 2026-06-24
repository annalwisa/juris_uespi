# Chatbot UESPI

Assistente para tirar dúvidas sobre a **Universidade Estadual do Piauí (UESPI)**, com **RAG** (busca nos PDFs + resposta fundamentada) via LangChain, OpenAI e **Pinecone** (ou Chroma local).

### RAG e documentos desatualizados

- Busca **20 trechos** similares e usa os **6** mais relevantes após priorizar ano e vigência.
- Configure `data/docs/manifest.yaml` para marcar PDFs como `vigente`, `desatualizado` ou `revogado`.
- O modelo prioriza normas mais recentes e avisa quando usa fonte antiga.
- **SIGAA** (oficial): lista de cursos de graduação com coordenador, sede e modalidade — [SIGAA público](https://sigaa.uespi.br/sigaa/public/curso/lista.jsf?nivel=G&aba=p-ensino). Cache local 24h; atualizar com `python -m chatbot.sigaa_cli`.
- **Busca web** (`ddgs`): reitoria e complemento. Modo: `WEB_SEARCH_MODE=auto` no `.env`.
- **Estágios supervisionados** (PREG/DAP/DES): cobertos pelos PDFs indexados (Lei 11.788/2008, Resolução CEPEX 004/2021, Portaria 329/2020, Procedimento de Convênio) + página oficial [uespi.br/preg-dap-des](https://uespi.br/preg-dap-des/) e [planilha pública de instituições conveniadas](https://docs.google.com/spreadsheets/d/1G6es_rE9ZhGXhaiJ2LwDikbsv_ejPAV91GYAZARx3H0/edit?pli=1&gid=659220882#gid=659220882). E-mail para abrir convênio: `convenio@preg.uespi.br`.

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

1. **Pinecone:** em [app.pinecone.io](https://app.pinecone.io), crie um índice **serverless** com:
  - **Dimensão:** `1536` (modelo `text-embedding-3-small`)
  - **Métrica:** cosine  
   Ou defina `PINECONE_CREATE_INDEX=true` para o projeto criar o índice na primeira indexação (região padrão: `aws` / `us-east-1`).
2. Instale dependências:

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

1. Inicie a **API** (backend para o frontend React):

```bash
uv run python -m chatbot.api
```

A API fica em `http://127.0.0.1:8000` (porta `API_PORT` no `.env`).

2. Na pasta irmã `juris_uespi-frontend`, suba a interface:

```bash
npm install && npm run dev
```

Abra `http://localhost:5173`. O Vite encaminha `/api/*` para a API na porta 8000.

> **Não use** `python -m chatbot.app` com o frontend — esse comando sobe o Gradio, que é outra interface e não expõe `/api/chat`.

### Gradio (opcional)

Interface alternativa sem React:

```bash
uv run python -m chatbot.app
```

Abre em `http://127.0.0.1:7860` (porta padrão do Gradio).

## Chroma (local, sem Pinecone)

No `.env`:

```env
VECTOR_STORE=chroma
```

Remova ou comente `PINECONE_API_KEY`. Os vetores ficam em `vector_db/` na máquina.

## Avaliação do RAG (métricas do TCC)

Conjunto de perguntas em `data/eval/golden_qa.yaml`. Calcula **Context Precision**, **Context Recall**, **Faithfulness** e **Answer Relevancy**.

```bash
# Baseline (só busca densa)
python -m chatbot.evaluate_cli --profile baseline --limit 3 --out data/eval/baseline.csv

# Completo (rerank + híbrido + multi-query)
python -m chatbot.evaluate_cli --profile full --limit 3 --out data/eval/full.csv
```

Após alterar PDFs ou ativar busca híbrida, reindexe (gera também o índice BM25):

```bash
python -m chatbot.ingest_cli --reset
```

Variáveis em `.env`: `RAG_RERANKER_ENABLED`, `RAG_HYBRID_ENABLED`, `RAG_MULTI_QUERY_ENABLED`.

## Estrutura

- `chatbot/` — ingestão, RAG, Pinecone/Chroma e Gradio
- `chatbot/evaluation.py` — métricas de avaliação
- `data/docs/` — PDFs e textos
- `data/eval/` — golden set e resultados de avaliação
- `vector_db/` — Chroma local e `bm25_index.pkl` (busca híbrida)

