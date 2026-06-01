"""Interface web do chatbot UESPI (Gradio)."""

import gradio as gr

from chatbot.chain import get_answer
from chatbot.status import status_message


def chat(message, history: list) -> str:
    # Gradio type=messages: message pode ser str ou {"role","content"}
    if isinstance(message, dict):
        text = message.get("content", "")
        if isinstance(text, list):
            text = " ".join(
                p.get("text", "") for p in text if isinstance(p, dict)
            )
    else:
        text = str(message or "")

    if not text.strip():
        return "Digite sua pergunta sobre a UESPI."

    # Histórico = mensagens anteriores (sem a atual)
    prior = list(history or [])
    return get_answer(text.strip(), prior)


def main():
    with gr.Blocks(title="Chat UESPI") as demo:
        gr.Markdown(
            "# Assistente UESPI\n"
            "**Juris UESPI** — assistente inteligente para a comunidade acadêmica. "
            "Normas nos PDFs; cursos via **SIGAA**; reitoria via busca web."
        )
        gr.Markdown(status_message())

        gr.ChatInterface(
            fn=chat,
            type="messages",
            examples=[
                "Quem é o coordenador do curso de Ciência da Computação em Piripiri?",
                "E em Teresina, qual o coordenador do mesmo curso?",
                "Qual o número máximo de faltas para não reprovar?",
                "Quem é o reitor atual da UESPI?",
            ],
            title="Conversa",
        )

    demo.launch()


if __name__ == "__main__":
    main()
