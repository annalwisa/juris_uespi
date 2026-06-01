# Documentos da UESPI

Coloque PDFs, `.txt` ou `.md` aqui. Depois indexe:

```bash
python -m chatbot.ingest_cli --reset
```

## Documentos desatualizados

Edite `manifest.yaml` nesta pasta para controlar vigência:

| status | Comportamento |
|--------|----------------|
| `vigente` | Prioridade na resposta |
| `desatualizado` | Usado só se relevante; o chat avisa que pode estar velho |
| `revogado` | **Não entra** na busca |

Exemplo:

```yaml
documents:
  Guia_do_Estudante_UESPI_2019.pdf:
    year: 2019
    status: desatualizado
    nota: "Conferir site da UESPI"
```

Alterou o `manifest.yaml`? Rode de novo `ingest_cli --reset`.

## Busca web (reitoria e gestão atual)

**Coordenador, sede e modalidade** dos cursos: consulta automática ao **SIGAA** (dados atualizados). Campi: `data/campi_cursos.yaml`. Atualizar cache: `python -m chatbot.sigaa_cli`.

**Reitoria**: busca web. **Normas** (faltas, resoluções): PDFs indexados.
