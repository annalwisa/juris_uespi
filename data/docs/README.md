# Documentos da UESPI

PDFs usados na indexação. **Quem for só testar o chatbot não precisa mexer aqui** os trechos já estão no Pinecone (índice `uespi-docs`).

Esta pasta importa para quem for **reindexar**:

```bash
python -m chatbot.ingest_cli --reset
```

## Vigência (`manifest.yaml`)

| status | Comportamento |
|--------|----------------|
| `vigente` | Prioridade na resposta |
| `desatualizado` | Usado se relevante; o chat avisa |
| `revogado` | Não entra na busca |

Depois de editar o manifest, rode o `ingest_cli --reset` de novo.

## Outras fontes (sem PDF)

Coordenação de curso: SIGAA. Campi e cursos por centro: YAML em `data/`. Reitoria: busca web. Normas: PDFs no Pinecone.
