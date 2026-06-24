# Juris UESPI

Chatbot para a comunidade da **Universidade Estadual do Piauí**. O foco é responder dúvidas acadêmicas com base em documentos oficiais (regimento, resoluções, editais) e em fontes atualizadas do site da universidade, coordenação de cursos no SIGAA, direção de centros e campi na agenda telefônica, e busca web quando faz sentido.

Projeto desenvolvido no contexto do meu TCC. A interface em React está em [annalwisa/juris_uespi-frontend](https://github.com/annalwisa/juris_uespi-frontend); este repositório é o backend.

**Stack:** Python, LangChain, OpenAI, Pinecone (ou Chroma local), FastAPI.

## Testar sem indexar PDFs

Os documentos já estão no **Pinecone** (índice `uespi-docs`, namespace `uespi`). Quem for só testar não precisa colocar PDFs em `data/docs/` nem rodar o `ingest_cli`.

1. Copie `.env.example` para `.env`
2. Preencha `OPENAI_API_KEY` e `PINECONE_API_KEY`
3. Deixe `VECTOR_STORE=pinecone` (padrão quando a chave do Pinecone existe)

```bash
uv sync
uv run python -m chatbot.api
```

Confira em `http://127.0.0.1:8000/api/status` se aparece **Base ativa** com a contagem de trechos.

### Frontend

Clone o repositório:

```bash
git clone https://github.com/annalwisa/juris_uespi-frontend.git
cd juris_uespi-frontend
npm install && npm run dev
```

Abra `http://localhost:5173`. O Vite encaminha `/api/*` para a API na porta 8000.

> O comando `python -m chatbot.app` sobe o Gradio, que não expõe `/api/chat`. Com o React, use só a API acima.

### Gradio

```bash
uv run python -m chatbot.app
```

Abre em `http://127.0.0.1:7860`.

## Chave do Pinecone

Quem for rodar o backend na própria máquina precisa da chave. Opções:

- **API hospedada** (recomendado para quem só quer testar a interface): você sobe este backend com a chave no servidor; o tester usa o frontend apontando para essa URL, sem Pinecone no `.env` dele.

Para só consumir o índice já populado, precisa da chave com acesso ao projeto onde está o índice `uespi-docs`.

## Reindexar

Ao mudar arquivos em `data/docs/` ou recriar o índice:

```bash
python -m chatbot.ingest_cli --reset
```

**não obrigatório** para quem só consome o índice no Pinecone. Status de vigência por arquivo: `data/docs/manifest.yaml`.

## Chroma local (sem Pinecone)

No `.env`:

```env
VECTOR_STORE=chroma
```

Aí sim é preciso indexar localmente, os vetores vão para `vector_db/`. Sem `PINECONE_API_KEY`, o padrão já cai no Chroma.

## De onde vêm as respostas

RAG sobre os PDFs indexados (Pinecone ou Chroma). Além disso:

- **SIGAA** — cursos de graduação (coordenador, sede, modalidade). Cache 24h; `python -m chatbot.sigaa_cli` para atualizar
- **Agenda telefônica** — diretores de centro e campus
- **Busca web** — reitoria e complementos (`WEB_SEARCH_MODE`: `auto`, `always`, `off`)
- **FAQ** fixo em `data/faq_respostas.yaml`

Com Pinecone, a busca híbrida (BM25) só entra se você tiver rodado o ingest localmente, sem isso, funciona só a busca densa, que é o caso normal para quem testa.

## Avaliação

Perguntas em `data/eval/golden_qa.yaml`:

```bash
python -m chatbot.evaluate_cli --profile baseline --limit 3 --out data/eval/baseline.csv
python -m chatbot.evaluate_cli --profile full --limit 3 --out data/eval/full.csv
```

## Pastas


| Pasta         | Conteúdo                                    |
| ------------- | ------------------------------------------- |
| `chatbot/`    | API, RAG, ingestão, integrações             |
| `data/docs/`  | PDFs (para reindexar; opcional para testar) |
| `data/eval/`  | golden set e resultados                     |
| `data/cache/` | cache SIGAA e agenda telefônica             |
| `vector_db/`  | Chroma e BM25 (modo local)                  |
| `tests/`      | testes automatizados                        |


Variáveis completas: `.env.example`.